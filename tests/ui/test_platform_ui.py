# -*- coding: utf-8 -*-
"""UI 自动化（Playwright）——测自己的 Web 平台（Vue3 + Element Plus 版）。

对应"交互式测试"的 UI 层：模拟真人操作浏览器，验证平台功能正常。
浏览器由 conftest 的 page fixture 统一提供（系统 Edge，失败自动截图）。

运行前提：
    pip install playwright pytest-playwright
    # 先启动平台：后端 8000 + 前端 dev 5173（或已 build 部署的地址）

运行：
    python -m pytest tests/ui/test_platform_ui.py -m ui --run-ui
"""
import pytest

from playwright.sync_api import expect

pytestmark = pytest.mark.ui

# 平台地址：本地 dev 用 localhost:5173；部署后改成实际地址
BASE_URL = 'http://localhost:5173'


def test_平台首页能打开(page):
    """打开首页，标题应含「蓝鲸测试平台」，侧栏应有 7 个导航。"""
    page.goto(BASE_URL)
    expect(page).to_have_title('蓝鲸测试平台')
    expect(page.locator('.el-menu-item')).to_have_count(7)


def test_切到跑测试并执行冒烟出结果(page):
    """切「跑测试」→ 选冒烟计划 → 执行 → 应出现执行输出。"""
    page.goto(BASE_URL)
    page.locator('.el-menu-item', has_text='跑测试').click()
    page.locator('button', has_text='执行计划').click()
    page.wait_for_selector('.output', timeout=90000)
    text = page.locator('.output').inner_text()
    assert 'passed' in text or 'collected' in text or 'failed' in text, \
        f'执行输出异常：{text[:200]}'
