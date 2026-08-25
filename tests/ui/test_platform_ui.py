# -*- coding: utf-8 -*-
"""UI 自动化（Playwright）——测自己部署在服务器上的 Web 平台。

对应"交互式测试"的 UI 层：在本地开真实浏览器，自动访问已部署的平台，
验证登录、总览、用例库、接口调试、报告、AI 生成、UI 自动化、跑测试等模块。
"""
import re

import pytest

from playwright.sync_api import expect

pytestmark = pytest.mark.ui

# 被测对象：部署在阿里云服务器上的平台
BASE_URL = 'http://114.55.176.42:8000'
PLATFORM_USER = 'jwkj'
PLATFORM_PASSWORD = 'jwkj'


@pytest.fixture(scope='session')
def platform(browser):
    """会话级登录一次，所有用例共用同一个已登录页面。"""
    context = browser.new_context()
    page = context.new_page()
    page.goto(f'{BASE_URL}/login', wait_until='domcontentloaded', timeout=60000)
    page.locator('input[placeholder="账号"]').fill(PLATFORM_USER)
    page.locator('input[placeholder="密码"]').fill(PLATFORM_PASSWORD)
    page.locator('button', has_text='登 录').click()
    page.locator('.el-menu-item').first.wait_for(timeout=30000)
    yield page
    context.close()


def test_平台首页能打开(platform):
    """登录后打开首页，标题应含「蓝鲸测试平台」，侧栏应有 7 个导航。"""
    platform.goto(BASE_URL)
    expect(platform).to_have_title(re.compile('蓝鲸测试平台'))
    expect(platform.locator('.el-menu-item')).to_have_count(7)


def test_登录页能打开(platform):
    """访问 /login，登录页应有账号框、密码框、登录按钮。"""
    platform.goto(f'{BASE_URL}/login')
    expect(platform.locator('input[placeholder="账号"]')).to_be_visible()
    expect(platform.locator('input[placeholder="密码"]')).to_be_visible()
    expect(platform.locator('button', has_text='登 录')).to_be_visible()


def test_总览页展示统计卡片和金字塔(platform):
    """总览页应有 4 个统计卡片 + 4 层金字塔 + 趋势图。"""
    platform.goto(f'{BASE_URL}/overview')
    expect(platform.locator('.stat-card')).to_have_count(4)
    expect(platform.locator('.pyr-level')).to_have_count(4)
    expect(platform.locator('canvas')).to_have_count(1, timeout=15000)


def test_用例库页展示分组和表格(platform):
    """用例库应有 5 个分组导航（含 UI 自动化），切到分组后表格有数据行。"""
    platform.goto(f'{BASE_URL}/cases')
    expect(platform.locator('.group-item')).to_have_count(5)
    expect(platform.locator('.el-table__row').first).to_be_visible()


def test_接口调试页展示表单(platform):
    """接口调试应有目标切换、接口下拉、参数框、发送按钮。"""
    platform.goto(f'{BASE_URL}/probe')
    expect(platform.locator('.el-select')).to_be_visible()
    expect(platform.locator('textarea')).to_be_visible()
    expect(platform.locator('button', has_text='发送')).to_be_visible()


def test_报告页能打开(platform):
    """报告页应能打开，显示报告表格或空状态提示。"""
    platform.goto(f'{BASE_URL}/reports')
    expect(platform.locator('.el-card').first).to_be_visible()


def test_AI生成页展示接口和按钮(platform):
    """AI 生成页应有接口下拉、需求框、生成/自愈按钮。"""
    platform.goto(f'{BASE_URL}/gen')
    expect(platform.locator('.el-select')).to_be_visible()
    expect(platform.locator('button', has_text='生成草稿')).to_be_visible()
    expect(platform.locator('button', has_text='自愈生成')).to_be_visible()


def test_UI自动化页展示分组(platform):
    """UI 自动化页应按被测对象分三组（平台/CMDB/JOB），左侧可切换。"""
    platform.goto(f'{BASE_URL}/ui')
    expect(platform.locator('.group-item')).to_have_count(3)


def test_切到跑测试并执行冒烟出结果(platform):
    """切「跑测试」→ 选冒烟计划 → 执行 → 应出现执行输出。"""
    platform.goto(BASE_URL)
    platform.locator('.el-menu-item', has_text='跑测试').click()
    platform.locator('button', has_text='执行计划').click()
    platform.wait_for_selector('.output', timeout=90000)
    text = platform.locator('.output').inner_text()
    assert 'passed' in text or 'collected' in text or 'failed' in text, \
        f'执行输出异常：{text[:200]}'
