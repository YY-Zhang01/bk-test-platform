# -*- coding: utf-8 -*-
"""UI 自动化（Playwright）——测自己的 Web 平台。

对应"交互式测试"的 UI 层：模拟真人操作浏览器，验证平台功能正常。
动线：打开平台 → 断言标题 → 切「跑测试」→ 选冒烟 → 执行 → 断言出结果。

运行前提：
    pip install playwright
    playwright install chromium
    # 先启动平台：python app/web_app.py（或已部署的服务器地址）

运行：
    python -m pytest tests/ui/test_platform_ui.py -m ui
"""
import pytest

from playwright.sync_api import expect, sync_playwright

pytestmark = pytest.mark.ui

# 平台地址：本地跑用 127.0.0.1:8000，服务器用 http://114.55.176.42:8000
BASE_URL = 'http://114.55.176.42:8000'

# 用系统自带 Edge（channel='msedge'），免下载 chromium；
# 若想用 Playwright 自带浏览器，去掉 channel 参数即可。
CHANNEL = 'msedge'


def _new_browser(p):
    # headless=False：开可见窗口；slow_mo=500：每步间隔 500ms，能看清操作过程
    return p.chromium.launch(channel=CHANNEL, headless=False, slow_mo=500)


def test_平台首页能打开():
    """打开首页，标题应为「蓝鲸双系统端到端测试平台」。"""
    with sync_playwright() as p:
        browser = _new_browser(p)
        page = browser.new_page()
        page.goto(BASE_URL)
        expect(page).to_have_title('蓝鲸双系统端到端测试平台')
        browser.close()


def test_切到跑测试并执行冒烟出结果():
    """切「跑测试」→ 选冒烟计划 → 执行 → 应出现「完成」和通过结果。"""
    with sync_playwright() as p:
        browser = _new_browser(p)
        page = browser.new_page()
        page.goto(BASE_URL)
        # 点左侧「跑测试」导航
        page.click('button[data-tab="run"]')
        # 选冒烟计划
        page.select_option('#plan', 'smoke')
        # 点执行
        page.click('#b-run')
        # 等结果出现（冒烟秒出，最多等 30 秒）
        page.wait_for_selector('#summary', timeout=30000)
        summary = page.locator('#summary').inner_text()
        assert '28 passed' in summary or 'passed' in summary, f'冒烟结果异常：{summary}'
        browser.close()
