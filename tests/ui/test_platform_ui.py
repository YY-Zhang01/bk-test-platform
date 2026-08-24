# -*- coding: utf-8 -*-
"""UI 自动化（Playwright）——测自己的 Web 平台（Vue3 + Element Plus 版）。

对应"交互式测试"的 UI 层：模拟真人操作浏览器，验证平台功能正常。
动线：打开平台 → 断言标题/侧栏 → 切「跑测试」→ 选冒烟 → 执行 → 断言出结果。

运行前提：
    pip install playwright
    # 先启动平台：后端 8000 + 前端 dev 5173（或已 build 部署的地址）

运行：
    python -m pytest tests/ui/test_platform_ui.py -m ui --run-ui
"""
import pytest

from playwright.sync_api import expect, sync_playwright

pytestmark = pytest.mark.ui

# 平台地址：本地 dev 用 localhost:5173；部署后改成实际地址
BASE_URL = 'http://localhost:5173'

# 用系统自带 Edge（channel='msedge'），免下载 chromium；
# 若想用 Playwright 自带浏览器，去掉 channel 参数即可。
CHANNEL = 'msedge'


def _new_browser(p):
    # headless=False：开可见窗口；slow_mo=500：每步间隔 500ms，能看清操作过程
    return p.chromium.launch(channel=CHANNEL, headless=False, slow_mo=500)


def test_平台首页能打开():
    """打开首页，标题应含「蓝鲸测试平台」，侧栏应有 7 个导航。"""
    with sync_playwright() as p:
        browser = _new_browser(p)
        page = browser.new_page()
        page.goto(BASE_URL)
        expect(page).to_have_title('蓝鲸测试平台')
        # 侧栏 7 个导航：总览/跑测试/接口调试/报告/AI生成/用例库/UI自动化
        expect(page.locator('.el-menu-item')).to_have_count(7)
        browser.close()


def test_切到跑测试并执行冒烟出结果():
    """切「跑测试」→ 选冒烟计划 → 执行 → 应出现执行输出。"""
    with sync_playwright() as p:
        browser = _new_browser(p)
        page = browser.new_page()
        page.goto(BASE_URL)
        # 点左侧「跑测试」菜单
        page.locator('.el-menu-item', has_text='跑测试').click()
        # 冒烟默认已选中，直接点「执行计划」
        page.locator('button', has_text='执行计划').click()
        # 等输出出现（冒烟秒出，最多等 90 秒）
        page.wait_for_selector('.output', timeout=90000)
        text = page.locator('.output').inner_text()
        assert 'passed' in text or 'collected' in text or 'failed' in text, \
            f'执行输出异常：{text[:200]}'
        browser.close()
