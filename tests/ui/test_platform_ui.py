# -*- coding: utf-8 -*-
"""UI 自动化（Playwright）——测自己的 Web 平台（Vue3 + Element Plus 版）。

对应"交互式测试"的 UI 层：模拟真人操作浏览器，验证平台各模块功能正常。
浏览器由 conftest 的 page fixture 统一提供（系统 Edge，失败自动截图）。

运行前提：
    pip install playwright pytest-playwright
    # 先启动平台：python app/web_app.py → http://127.0.0.1:8000（托管前端 + API）

运行：
    python -m pytest tests/ui/test_platform_ui.py -m ui --run-ui
"""
import pytest

from playwright.sync_api import expect

pytestmark = pytest.mark.ui

# 平台地址：本地跑用后端托管地址（无密码）；部署后按实际改
BASE_URL = 'http://localhost:8000'


def test_平台首页能打开(page):
    """打开首页，标题应含「蓝鲸测试平台」，侧栏应有 7 个导航。"""
    page.goto(BASE_URL)
    expect(page).to_have_title('蓝鲸测试平台')
    expect(page.locator('.el-menu-item')).to_have_count(7)


def test_登录页能打开(page):
    """访问 /login，登录页应有账号框、密码框、登录按钮。"""
    page.goto(f'{BASE_URL}/login')
    expect(page.locator('input[placeholder="账号"]')).to_be_visible()
    expect(page.locator('input[placeholder="密码"]')).to_be_visible()
    expect(page.locator('button', has_text='登 录')).to_be_visible()


def test_总览页展示统计卡片和金字塔(page):
    """总览页应有 4 个统计卡片 + 4 层金字塔 + 趋势图。"""
    page.goto(f'{BASE_URL}/overview')
    expect(page.locator('.stat-card')).to_have_count(4)
    expect(page.locator('.pyr-level')).to_have_count(4)
    # canvas 需等 API 数据加载 + ECharts 初始化，给足超时
    expect(page.locator('canvas')).to_have_count(1, timeout=15000)


def test_用例库页展示分组和表格(page):
    """用例库应有 4 个分组导航，切到分组后表格有数据行。"""
    page.goto(f'{BASE_URL}/cases')
    expect(page.locator('.group-item')).to_have_count(4)
    # 默认选中第一个分组（L1 工具层），表格应有数据行
    expect(page.locator('.el-table__row').first).to_be_visible()


def test_接口调试页展示表单(page):
    """接口调试应有目标切换、接口下拉、参数框、发送按钮。"""
    page.goto(f'{BASE_URL}/probe')
    expect(page.locator('.el-select')).to_be_visible()
    expect(page.locator('textarea')).to_be_visible()
    expect(page.locator('button', has_text='发送')).to_be_visible()


def test_报告页能打开(page):
    """报告页应能打开，显示报告表格或空状态提示。"""
    page.goto(f'{BASE_URL}/reports')
    expect(page.locator('.el-card').first).to_be_visible()


def test_AI生成页展示接口和按钮(page):
    """AI 生成页应有接口下拉、需求框、生成/自愈按钮。"""
    page.goto(f'{BASE_URL}/gen')
    expect(page.locator('.el-select')).to_be_visible()
    expect(page.locator('button', has_text='生成草稿')).to_be_visible()
    expect(page.locator('button', has_text='自愈生成')).to_be_visible()


def test_UI自动化页展示分组(page):
    """UI 自动化页应按被测对象分组（平台/CMDB/JOB 三组）。"""
    page.goto(f'{BASE_URL}/ui')
    expect(page.locator('.group-card')).to_have_count(3)


def test_切到跑测试并执行冒烟出结果(page):
    """切「跑测试」→ 选冒烟计划 → 执行 → 应出现执行输出。"""
    page.goto(BASE_URL)
    page.locator('.el-menu-item', has_text='跑测试').click()
    page.locator('button', has_text='执行计划').click()
    page.wait_for_selector('.output', timeout=90000)
    text = page.locator('.output').inner_text()
    assert 'passed' in text or 'collected' in text or 'failed' in text, \
        f'执行输出异常：{text[:200]}'
