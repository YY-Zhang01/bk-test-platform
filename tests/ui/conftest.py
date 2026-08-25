# -*- coding: utf-8 -*-
"""UI 测试的收集控制 + 浏览器配置。

UI 测试需要浏览器 + 平台在跑，不适合默认全量跑、也不适合 CI（无浏览器）。
默认 skip 所有 ui 测试；显式传 --run-ui 才真正执行。

浏览器统一用系统 Edge（channel='msedge'），免下载 chromium；
失败自动截图（pytest-playwright 的 --screenshot=only-on-failure 由 /api/ui/run 带上）。
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


@pytest.fixture(scope='session')
def browser_type_launch_args(browser_type_launch_args):
    """统一用系统 Edge，开可见窗口，每步间隔 100ms（快跑；录视频要看清可改回 300-500）。

    --ignore-certificate-errors：cmdb-exp 的 SSL 证书过期，跳过证书校验，
    否则浏览器会停在"证书错误"页面进不去。
    """
    args = list(browser_type_launch_args.get('args', []))
    args.append('--ignore-certificate-errors')
    return {
        **browser_type_launch_args,
        'channel': 'msedge',
        'headless': False,
        'slow_mo': 100,
        'args': args,
    }
