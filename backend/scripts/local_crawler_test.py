"""本地测试爬虫（仅本地测试，商用禁止）。

⚠️ 必须遵守 CRAWLER_COMPLIANCE.md：
  - 单线程 + 随机 2~5s 延时
  - 域名白名单 edu.cn
  - 遇 429/503 退避重试 3 次
  - 不存储姓名/证件号
  - 全量写 crawl_logs

示例运行：
    python -m scripts.local_crawler_test \\
        --pdf-url https://xxx.edu.cn/yyy.pdf \\
        --school-id 1 --year 2024 \\
        --school-major-id 2 --doc-type admission_list
"""
from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import CrawlLog, PdfSource
from app.services.pdf_parser import parse_pdf_bytes
from app.services.stats import upsert_admission_stat


UA = "KaoYanZexiaoBot/0.1 (local-test; contact: local-test@example.com)"


def _in_whitelist(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    return any(host.endswith("." + d) or host == d for d in settings.crawler_whitelist_domains)


@retry(
    reraise=True,
    stop=stop_after_attempt(settings.CRAWLER_RETRY_MAX),
    wait=wait_exponential(multiplier=2, min=4, max=32),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
)
async def _get(cli: httpx.AsyncClient, url: str) -> httpx.Response:
    r = await cli.get(url, timeout=15)
    if r.status_code in (429, 503, 500, 502, 504):
        r.raise_for_status()
    return r


async def crawl_and_parse(
    pdf_url: str,
    school_id: int,
    year: int,
    school_major_id: int | None = None,
    doc_type: str = "admission_list",
) -> dict:
    """下载 → 解析 → 写 admission_stats + pdf_sources + crawl_logs。"""
    if not _in_whitelist(pdf_url):
        logger.warning("URL 不在白名单，跳过：{}", pdf_url)
        return {"status": "skipped", "reason": "domain not in whitelist"}

    delay = random.uniform(settings.CRAWLER_DELAY_MIN_SEC, settings.CRAWLER_DELAY_MAX_SEC)
    logger.info("等待 {:.2f}s 后访问 {}", delay, pdf_url)
    await asyncio.sleep(delay)

    start = time.perf_counter()
    status = "ok"
    message = None
    http_code = None
    body = b""
    try:
        async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True) as cli:
            r = await _get(cli, pdf_url)
            http_code = r.status_code
            body = r.content
    except Exception as e:
        status = "failed"
        message = str(e)[:200]

    duration_ms = int((time.perf_counter() - start) * 1000)
    async with AsyncSessionLocal() as db:
        db.add(CrawlLog(
            target_url=pdf_url[:255], source_type=doc_type,
            http_code=http_code, duration_ms=duration_ms,
            delay_seconds=round(delay, 1), status=status, message=message,
        ))
        await db.commit()

    if status != "ok":
        return {"status": status, "http_code": http_code, "message": message}

    # 解析
    parse_status = "parsed"
    parse_msg = None
    parsed_count = 0
    skipped_name_cols = 0
    try:
        result = await parse_pdf_bytes(body, doc_type=doc_type, source_url=pdf_url)
        skipped_name_cols = result.skipped_name_columns
        scores = [r.score for r in result.rows if r.score is not None]
        parsed_count = len(scores)
        logger.info(
            "解析完成：rows={}, scores={}, skipped_name_cols={}",
            len(result.rows), parsed_count, skipped_name_cols,
        )

        # 写 admission_stats（仅当有 school_major_id 且为录取/复试名单）
        if school_major_id and doc_type in ("admission_list", "retest_list") and scores:
            retest_count = parsed_count if doc_type == "retest_list" else parsed_count
            admit_count = parsed_count if doc_type == "admission_list" else 0
            async with AsyncSessionLocal() as db:
                await upsert_admission_stat(
                    db, school_major_id=school_major_id, year=year,
                    retest_count=retest_count, admit_count=admit_count,
                    scores=scores, source_url=pdf_url,
                )
                await db.commit()
    except Exception as e:
        parse_status = "failed"
        parse_msg = str(e)[:200]

    # 写 pdf_sources 状态
    async with AsyncSessionLocal() as db:
        src = PdfSource(
            school_id=school_id, year=year, pdf_url=pdf_url[:255],
            doc_type=doc_type, status=parse_status,
            parsed_at=datetime.utcnow() if parse_status == "parsed" else None,
        )
        db.add(src)
        await db.commit()

    return {
        "status": parse_status, "http_code": http_code,
        "duration_ms": duration_ms, "body_bytes": len(body),
        "parsed_count": parsed_count, "skipped_name_cols": skipped_name_cols,
        "message": parse_msg,
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-url", required=True)
    ap.add_argument("--school-id", type=int, required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--school-major-id", type=int, default=None)
    ap.add_argument("--type", default="admission_list")
    args = ap.parse_args()
    r = await crawl_and_parse(
        args.pdf_url, school_id=args.school_id, year=args.year,
        school_major_id=args.school_major_id, doc_type=args.type,
    )
    logger.info("结果：{}", r)


if __name__ == "__main__":
    asyncio.run(main())
