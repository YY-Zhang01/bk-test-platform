# -*- coding: utf-8 -*-
"""UI 自动化（Playwright）——测 JOB 网页（骨架，等 9 月体验账号）。

JOB 没有本地 standalone，强依赖整套蓝鲸基础套餐，只能等官方体验环境开放。
账号到手后：填 JOB_URL、补登录步骤、补断言，即可跑。

运行：
    python -m pytest tests/ui/test_job_ui.py -m ui --run-ui
"""
import pytest

from playwright.sync_api import expect

pytestmark = pytest.mark.ui

# JOB 体验环境地址：账号到手后替换
JOB_URL = 'https://替换为体验环境作业平台地址'


def test_JOB登录后进入作业平台(page):
    """登录体验环境 → 进入作业平台 → 断言左侧菜单（脚本管理/快速执行）。"""
    page.goto(JOB_URL)
    # TODO: 账号到手后补登录步骤（体验账号 + 密码）
    # page.fill('input[name="username"]', '<体验账号>')
    # page.fill('input[name="password"]', '<密码>')
    # page.click('button:has-text("登录")')
    expect(page.locator('text=快速执行').first).to_be_visible()
