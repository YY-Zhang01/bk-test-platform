# -*- coding: utf-8 -*-
"""UI 测试的收集控制。

UI 测试需要浏览器 + 平台在跑，不适合默认全量跑、也不适合 CI（无浏览器）。
默认 skip 所有 ui 测试；显式传 --run-ui 才真正执行。

用法：
    python -m pytest tests/ui/ -m ui --run-ui      # 显式跑 UI
    python -m pytest                              # 全量跑，ui 自动 skip
"""
import pytest


def pytest_addoption(parser):
    parser.addoption('--run-ui', action='store_true', default=False,
                     help='真正执行 UI 测试（需浏览器 + 平台在跑）')


def pytest_collection_modifyitems(config, items):
    if config.getoption('--run-ui'):
        return
    skip_ui = pytest.mark.skip(reason='UI 测试需显式 --run-ui（需浏览器+平台）')
    for item in items:
        if 'ui' in item.keywords:
            item.add_marker(skip_ui)
