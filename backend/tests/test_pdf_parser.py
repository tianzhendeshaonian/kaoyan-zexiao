"""PDF 解析器测试（不依赖外部 PDF 文件，用代码构造最小 PDF）。

覆盖 CRAWLER_COMPLIANCE.md 安全清单：
  #14：不抽取/存储姓名隐私字段
  #11：恶意/超大 PDF 防护（文件大小上限、页数上限）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test_secret_at_least_32_bytes_long_enough_xxx")
os.environ.setdefault("WECHAT_APP_ID", "")
os.environ.setdefault("WECHAT_APP_SECRET", "")

from app.services.pdf_parser import (  # noqa: E402
    MAX_FILE_BYTES,
    MAX_PAGES,
    NAME_HEADERS,
    build_score_segments,
    _find_name_columns,
    _find_score_column,
)


# ---------- 纯函数测试（不依赖 pdfplumber） ----------

def test_find_name_columns_skips_privacy():
    headers = ["序号", "姓名", "考生编号", "总分", "专业方向", "身份证号", "电话"]
    skip = _find_name_columns(headers)
    # 姓名/考生编号/身份证号/电话 被识别为隐私列
    assert 1 in skip   # 姓名
    assert 2 in skip   # 考生编号（含"考生编号"关键字）
    assert 5 in skip   # 身份证号
    assert 6 in skip   # 电话
    # 序号/总分/专业方向 不被跳过
    assert 0 not in skip
    assert 3 not in skip
    assert 4 not in skip


def test_find_score_column():
    assert _find_score_column(["序号", "姓名", "总分"]) == 2
    assert _find_score_column(["序号", "总成绩", "排名"]) == 1
    assert _find_score_column(["序号", "姓名"]) is None


def test_build_score_segments_basic():
    scores = [350, 355, 360, 362, 380]
    segs = build_score_segments(scores, step=10)
    # 至少有 [350,360), [360,370), [380,390)
    by_min = {s["min"]: s for s in segs}
    assert by_min[350]["count"] == 2  # 350, 355
    assert by_min[360]["count"] == 2  # 360, 362
    assert by_min[380]["count"] == 1
    # 不含个人数据，只有区间与计数
    for s in segs:
        assert set(s.keys()) == {"min", "max", "count"}


def test_build_score_segments_empty():
    assert build_score_segments([], step=10) == []
    assert build_score_segments([None, None], step=10) == []


# ---------- 大小/页数上限防护（#11） ----------

def test_max_file_bytes_constant():
    assert MAX_FILE_BYTES == 30 * 1024 * 1024
    assert MAX_PAGES == 200


def test_parse_rejects_oversize_bytes():
    """#11：超大字节流直接拒，不进入 pdfplumber"""
    from app.services.pdf_parser import _parse_bytes_sync
    huge = b"%" + b"\x00" * (MAX_FILE_BYTES + 10)
    with pytest.raises(ValueError, match="PDF 过大"):
        _parse_bytes_sync(huge)


# ---------- 用真实 pdfplumber 构造一个最小 PDF（如已安装） ----------

pdfplumber = pytest.importorskip("pdfplumber")
reportlab = pytest.importorskip("reportlab")


def _make_test_pdf(tmp_path: Path) -> bytes:
    """用 reportlab 生成一个含"姓名/总分/方向"列的最小 PDF（英文表头模拟）。

    注：reportlab 默认字体不含中文，故用英文表头测解析流程；
    中文姓名列识别由 _find_name_columns 单测保证。
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

    out = tmp_path / "test_admission.pdf"
    doc = SimpleDocTemplate(str(out), pagesize=A4)
    data = [
        ["No", "name", "admission_id", "total", "direction"],
        ["1", "Alice", "100012024001", "380", "CS"],
        ["2", "Bob",   "100012024002", "365", "SE"],
        ["3", "Carol", "100012024003", "350", "CS"],
    ]
    tbl = Table(data)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ]))
    doc.build([tbl])
    return out.read_bytes()


def test_parse_real_pdf_skips_name_column(tmp_path):
    """#14：真实 PDF 解析时，姓名列必须被跳过，不入 raw"""
    from app.services.pdf_parser import _parse_bytes_sync
    data = _make_test_pdf(tmp_path)
    r = _parse_bytes_sync(data, doc_type="admission_list",
                          source_url="https://grs.pku.edu.cn/test.pdf")
    # 英文表头："name" 与 "admission_id"（含"admission"关键字命中）会被识别为隐私列
    # 至少 "name" 列被跳过
    assert r.skipped_name_columns >= 1
    # 解析出 3 行
    assert len(r.rows) == 3
    # 每行 raw 中不应包含 "name" 字段
    for row in r.rows:
        assert "name" not in row.raw
        # total 被正确抽取
        assert row.score in (380, 365, 350)
    # 统计聚合正确
    assert r.stats["count"] == 3
    assert r.stats["max_score"] == 380
    assert r.stats["min_score"] == 350
    assert r.stats["avg_score"] == round((380 + 365 + 350) / 3, 1)
