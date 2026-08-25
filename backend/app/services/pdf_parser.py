"""PDF 解析服务（pdfplumber）。

⚠️ 合规要点（对应 CRAWLER_COMPLIANCE.md 安全清单 #14、#11）：
- 不抽取/不存储考生姓名、证件号、联系方式等隐私字段。
- 遇到姓名列自动跳过（关键字识别）。
- 文件大小上限 30MB，页数上限 200，超出拒绝解析（防恶意/超大 PDF 致内存炸 #11）。
- 解析在协程内通过线程池执行，避免阻塞事件循环。
"""
from __future__ import annotations

import asyncio
import io
import os
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from loguru import logger

from ..config import settings


MAX_FILE_BYTES = 30 * 1024 * 1024   # 30MB
MAX_PAGES = 200

# 姓名列识别关键字（命中即视为隐私列，跳过该列值）
NAME_HEADERS = {
    "姓名", "考生姓名", "名字", "考生", "name", "姓名/名称",
    "学号", "准考证号", "考生编号", "身份证", "身份证号", "证件号",
    "联系方式", "电话", "手机", "邮箱", "email",
}


@dataclass
class ParsedAdmissionRow:
    """拟录取名单中提取的单行（脱敏：无姓名）。"""
    score: int | None = None
    major_direction: str | None = None       # 专业/方向
    raw: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedPdfResult:
    doc_type: str                              # admission_list / retest_list / score_line
    rows: list[ParsedAdmissionRow] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    source_url: str = ""
    skipped_name_columns: int = 0              # 跳过的姓名列计数（审计）
    skipped_pages: int = 0


# ---------- 工具 ----------

def _is_int(s: str | None) -> bool:
    if not s:
        return False
    s = s.strip()
    return s.isdigit() or (s.startswith("-") and s[1:].isdigit())


def _to_int(s: str | None) -> int | None:
    if not s or not _is_int(s):
        return None
    return int(s.strip())


def _find_score_column(headers: list[str]) -> int | None:
    """在表头中找总分列索引。"""
    keys = ("总分", "录取总分", "初试总分", "总成绩", "成绩", "score", "total")
    for i, h in enumerate(headers):
        if h and any(k in h for k in keys):
            return i
    return None


def _find_name_columns(headers: list[str]) -> set[int]:
    """返回需要跳过的列索引集合（姓名/证件号/联系方式）。"""
    skip = set()
    for i, h in enumerate(headers):
        if not h:
            continue
        hl = h.strip().lower()
        if hl in NAME_HEADERS or any(k in h for k in NAME_HEADERS):
            skip.add(i)
    return skip


def _find_direction_column(headers: list[str]) -> int | None:
    keys = ("专业", "研究方向", "方向", "专业方向", "major", "direction")
    for i, h in enumerate(headers):
        if h and any(k in h for k in keys):
            return i
    return None


# ---------- 同步解析核心 ----------

def _parse_bytes_sync(data: bytes, doc_type: str = "admission_list",
                      source_url: str = "") -> ParsedPdfResult:
    """同步解析 PDF 字节流。"""
    # 防 #11：大文件/恶意 PDF 直接拒
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"PDF 过大({len(data)} bytes)，超过 {MAX_FILE_BYTES} 上限")
    try:
        import pdfplumber
    except ImportError as e:
        raise RuntimeError("pdfplumber 未安装") from e

    result = ParsedPdfResult(doc_type=doc_type, source_url=source_url)
    scores: list[int] = []

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        if len(pdf.pages) > MAX_PAGES:
            raise ValueError(f"PDF 页数过多({len(pdf.pages)})，超过 {MAX_PAGES}")
        for page_idx, page in enumerate(pdf.pages):
            try:
                tables = page.extract_tables() or []
            except Exception as e:
                logger.warning("page {} 解析失败: {}", page_idx, e)
                result.skipped_pages += 1
                continue
            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue
                headers = [str(x or "").strip() for x in tbl[0]]
                if not any(headers):
                    # 无表头，跳过（避免误抽）
                    continue
                skip_cols = _find_name_columns(headers)
                if skip_cols:
                    result.skipped_name_columns += len(skip_cols)
                score_col = _find_score_column(headers)
                dir_col = _find_direction_column(headers)
                if score_col is None:
                    # 无分数列，可能是说明性表格，跳过
                    continue
                for row in tbl[1:]:
                    if not row:
                        continue
                    score = _to_int(row[score_col]) if score_col < len(row) else None
                    direction = None
                    if dir_col is not None and dir_col < len(row):
                        direction = (row[dir_col] or "").strip() or None
                    # 收集非隐私字段（用于审计 raw，跳过姓名列）
                    raw: dict[str, str] = {}
                    for i, h in enumerate(headers):
                        if i in skip_cols:
                            continue
                        if i < len(row):
                            raw[h] = str(row[i] or "").strip()
                    result.rows.append(ParsedAdmissionRow(
                        score=score, major_direction=direction, raw=raw,
                    ))
                    if score is not None:
                        scores.append(score)

    # 聚合统计（脱敏：仅分数与人数）
    if scores:
        result.stats = {
            "count": len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "avg_score": round(sum(scores) / len(scores), 1),
        }
    return result


def build_score_segments(scores: Iterable[int], step: int = 10) -> list[dict]:
    """把分数列表聚合为脱敏分段分布。

    例：[350, 355, 360] → [{"min":350,"max":360,"count":2}, {"min":360,"max":370,"count":1}]
    """
    scores = [s for s in scores if s is not None]
    if not scores:
        return []
    lo = (min(scores) // step) * step
    hi = ((max(scores) // step) + 1) * step
    segments: list[dict] = []
    cur = lo
    while cur < hi:
        nxt = cur + step
        cnt = sum(1 for s in scores if cur <= s < nxt)
        if cnt > 0:
            segments.append({"min": cur, "max": nxt, "count": cnt})
        cur = nxt
    return segments


# ---------- 异步入口 ----------

async def parse_pdf_bytes(data: bytes, doc_type: str = "admission_list",
                          source_url: str = "") -> ParsedPdfResult:
    """在线程池内执行同步解析，避免阻塞事件循环。"""
    return await asyncio.to_thread(_parse_bytes_sync, data, doc_type, source_url)


async def parse_pdf_file(path: str, doc_type: str = "admission_list",
                         source_url: str = "") -> ParsedPdfResult:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    size = os.path.getsize(path)
    if size > MAX_FILE_BYTES:
        raise ValueError(f"PDF 过大({size} bytes)")
    with open(path, "rb") as f:
        data = f.read()
    return await parse_pdf_bytes(data, doc_type=doc_type, source_url=source_url)
