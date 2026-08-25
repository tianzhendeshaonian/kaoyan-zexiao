"""conftest：pytest 异步模式 = auto。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def pytest_collection_modifyitems(items):
    """自动给 async 测试加 asyncio mark，避免每个测试都手写装饰器。"""
    import pytest
    for item in items:
        if "asyncio" in item.keywords:
            continue
        if item.get_closest_marker("asyncio"):
            continue
