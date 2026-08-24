# -*- coding: utf-8 -*-
"""UI 自动化（Playwright）——测 CMDB 网页。

前提：本地 CMDB 环境已跑起来（Docker：CMDB + MongoDB + Redis + ZooKeeper）。
CMDB 有官方 standalone 镜像，本地起好后把 CMDB_URL 改成实际地址即可跑。

运行：
    python -m pytest tests/ui/test_cmdb_ui.py -m ui
"""
import pytest

from playwright.sync_api import expect, sync_playwright

pytestmark = pytest.mark.ui

# CMDB 地址：本地部署后按实际改（standalone 常见 80 / 8080 / 8090）
CMDB_URL = 'http://127.0.0.1:8080'


def test_CMDB登录页能打开():
    """打开 CMDB，登录页应有「用户名」「密码」输入框和「登录」按钮。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=False, slow_mo=500)
        page = browser.new_page()
        page.goto(CMDB_URL)
        expect(page.locator('text=用户名').first).to_be_visible()
        expect(page.locator('text=密码').first).to_be_visible()
        browser.close()


def test_CMDB登录后进入首页():
    """登录后，首页应有顶部导航（首页/业务/资源/模型）。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=False, slow_mo=500)
        page = browser.new_page()
        page.goto(CMDB_URL)
        # 本地默认管理员账号（按实际改）
        page.fill('input[placeholder*="用户名"]', 'admin')
        page.fill('input[placeholder*="密码"]', 'admin')
        page.click('button:has-text("登录")')
        expect(page.locator('text=蓝鲸配置平台').first).to_be_visible()
        browser.close()
