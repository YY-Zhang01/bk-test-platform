# -*- coding: utf-8 -*-
"""UI 自动化（Playwright）——测 CMDB 网页（蓝鲸配置平台官方在线体验 cmdb-exp）。

覆盖页面：资源目录 / 主机列表 / 拓扑 / 模型 / 动态分组 + 新建业务（左上角业务切换器下拉）。
选择器依据：本仓库 docs/research/cmdb-pages/*.md 的实测可访问性快照（本地 standalone 与
cmdb-exp 同是 bk-cmdb，页面结构一致）。

登录流程（不能跳步）：
    1. 先访问 /start，等它"创建独立容器半小时体验"（约几十秒）
    2. 跳转到 /login?c_url=/ 填 admin / admin
    3. 进入主界面
    4. 会话级登录一次，后续用例注入 cookie 复用

⚠️ 页面切换必须用 location.hash（等价于点菜单），不能用 page.goto 全页刷新——
    全页刷新会触发前端 localStorage 反序列化失败 → "系统发生异常"。

⚠️ SSL 证书过期，需 --ignore-certificate-errors（tests/ui/conftest.py 已配）。

运行：
    python -m pytest tests/ui/test_cmdb_ui.py -m ui --run-ui
"""
import time

import pytest

from playwright.sync_api import expect

pytestmark = pytest.mark.ui

# ---- 环境配置 ----
CMDB_URL = 'https://cmdb-exp.bktencent.com'                    # CMDB 官方在线体验环境
CMDB_START_URL = 'https://cmdb-exp.bktencent.com/start'        # 先访问它创建体验容器
CMDB_USER = 'admin'                                            # 体验账号
CMDB_PASSWORD = 'admin'                                        # 体验密码
# 业务 ID：cmdb-exp 里默认只有一个「蓝鲸」业务，ID=2
CMDB_BUSINESS_ID = 2


def _nav(page, route):
    """SPA 内部 hash 切换（等价于手动点菜单，不整页刷新）。"""
    page.evaluate(f"location.hash = '{route}'")
    page.wait_for_timeout(1500)


def _close_version_notice(page):
    """登录后弹"版本通告"，点右上角 X 关掉；关不掉按 ESC 兜底。"""
    page.wait_for_timeout(2000)
    for sel in ('.bk-dialog-close', '[class*="dialog-close"]',
                '.bk-dialog-header [class*="close"]'):
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=3000):
                loc.click()
                return
        except Exception:
            continue
    try:
        page.keyboard.press('Escape')
    except Exception:
        pass
    page.wait_for_timeout(800)


def _pick_user(page, dialog, field_name, username='admin'):
    """在创建业务表单里选人员（如"运维人员"）。

    bk-cmdb 的人员选择器不是 <input>，而是 contenteditable：
    点击容器聚焦 -> 输入用户名 -> 等 tippy 下拉出现 -> 点列表里的用户名 ->
    等已选值落到字段里。
    """
    # 用 data-vv-name 定位字段最稳，避免被"产品人员/测试人员"等同结构干扰
    field = dialog.locator(f'[data-vv-name="{field_name}"]').first
    field.locator('.user-selector-container').first.click()
    field.locator('.user-selector-input').first.type(username, delay=100)
    # 下拉挂在 body 上的 tippy 弹层，不能用 dialog 作用域
    page.locator('.user-selector-alternate-list-wrapper .item-name',
                 has_text=username).first.click()
    expect(field.locator('.user-selector-selected-value').first).to_be_visible(timeout=10000)


def _close_dialog(page):
    """关闭可能残留的创建业务弹窗，等遮罩消失后再返回。"""
    try:
        close = page.locator('.bk-dialog-close').first
        if close.is_visible(timeout=2000):
            close.click()
            page.wait_for_timeout(500)
    except Exception:
        pass
    try:
        cancel = page.get_by_role('button', name='取消').first
        if cancel.is_visible(timeout=2000):
            cancel.click()
            page.wait_for_timeout(500)
    except Exception:
        pass
    try:
        page.keyboard.press('Escape')
    except Exception:
        pass
    try:
        page.locator('.bk-dialog-wrapper').first.wait_for(state='hidden', timeout=5000)
    except Exception:
        pass


@pytest.fixture(scope='session')
def cmdb(browser):
    """会话级：登录一次，返回同一个 page，所有用例共用同一个浏览器窗口顺序操作。"""
    context = browser.new_context()
    page = context.new_page()
    page.goto(CMDB_START_URL, wait_until='domcontentloaded', timeout=180000)
    page.wait_for_url('**/login**', timeout=180000)
    page.locator('input[type="text"]').first.fill(CMDB_USER)
    page.locator('input[type="password"]').first.fill(CMDB_PASSWORD)
    page.locator('button:has-text("登录")').first.click()
    page.get_by_role('link', name='蓝鲸配置平台').wait_for(timeout=30000)
    _close_version_notice(page)
    yield page
    context.close()


# ---------- 首页 ----------

def test_CMDB进入首页(cmdb):
    """登录后顶部导航应有 首页/业务/资源/模型 等入口。"""
    banner = cmdb.get_by_role('banner')
    for name in ('首页', '业务', '资源', '模型', '运营分析', '平台管理'):
        expect(banner.get_by_role('link', name=name, exact=True)).to_be_visible()


# ---------- 新建业务（左上角业务切换器下拉里） ----------

def test_CMDB新建业务入口(cmdb):
    """进业务页 → 点左上角业务切换器（蓝鲸 (2)），下拉里应有「新建业务」入口。"""
    _nav(cmdb, f'/business/{CMDB_BUSINESS_ID}/index')
    cmdb.get_by_text('蓝鲸 (2)').first.click()
    expect(cmdb.get_by_text('新建业务', exact=True)).to_be_visible()
    cmdb.keyboard.press('Escape')  # 关掉下拉，不影响后续用例


def test_CMDB新建业务页能打开(cmdb):
    """点「新建业务」应弹出创建业务表单（含「业务名」输入框）。"""
    _nav(cmdb, f'/business/{CMDB_BUSINESS_ID}/index')
    cmdb.get_by_text('蓝鲸 (2)').first.click()
    cmdb.get_by_text('新建业务', exact=True).click()
    dialog = cmdb.get_by_role('article').first
    expect(dialog.get_by_role('textbox', name='请输入业务名')).to_be_visible(timeout=10000)


def test_CMDB新建业务后能查到(cmdb):
    """真操作 + 数据校验：新建业务，业务列表里能查到它。"""
    last_error = None
    for attempt in range(2):
        unique = f'zyy{int(time.time())}{attempt}'
        _nav(cmdb, f'/business/{CMDB_BUSINESS_ID}/index')
        cmdb.get_by_text('蓝鲸 (2)').first.click()
        cmdb.get_by_text('新建业务', exact=True).click()
        dialog = cmdb.get_by_role('article').first
        dialog.get_by_role('textbox', name='请输入业务名').fill(unique)
        _pick_user(cmdb, dialog, 'bk_biz_maintainer')
        dialog.get_by_role('button', name='提交').click()
        try:
            expect(cmdb.get_by_text(unique).first).to_be_visible(timeout=8000)
            return
        except AssertionError as exc:
            last_error = exc
            # cmdb-exp 创建接口偶发返回 1199998（业务没建成），关掉弹窗后换名重试
            _close_dialog(cmdb)
    raise last_error


# ---------- 资源目录 / 主机列表 ----------

def test_CMDB资源目录能打开(cmdb):
    """资源目录页应有标题 + 主机管理/组织架构分类。"""
    _nav(cmdb, '/resource')
    expect(cmdb.get_by_role('heading', name='资源目录', level=1)).to_be_visible()
    expect(cmdb.get_by_role('heading', name='主机管理', level=4)).to_be_visible()
    expect(cmdb.get_by_role('heading', name='组织架构', level=4)).to_be_visible()


def test_CMDB主机列表能打开(cmdb):
    """主机列表页应有标题 + 未分配/已分配筛选页签 + 主机表格列头。"""
    _nav(cmdb, '/resource/host')
    expect(cmdb.get_by_role('heading', name='主机', level=1)).to_be_visible()
    expect(cmdb.get_by_text('未分配')).to_be_visible()
    expect(cmdb.get_by_text('已分配')).to_be_visible()
    expect(cmdb.get_by_role('columnheader', name='内网IPv4')).to_be_visible()


def test_CMDB主机搜索能过滤(cmdb):
    """在主机列表搜索 IP，应出现「检索项」筛选条（内网IP|外网IP|精确）。"""
    _nav(cmdb, '/resource/host')
    box = cmdb.get_by_role('textbox', name='请输入IP或固资编号')
    box.fill('10.0.0.101')
    box.press('Enter')
    expect(cmdb.get_by_text('检索项')).to_be_visible(timeout=10000)


# ---------- 拓扑 ----------

def test_CMDB业务拓扑能打开(cmdb):
    """进入业务 → 业务拓扑：标题 + 内置"空闲机池"节点 + 主机列表标签。"""
    _nav(cmdb, f'/business/{CMDB_BUSINESS_ID}/index')
    expect(cmdb.get_by_role('heading', name='业务拓扑', level=1)).to_be_visible()
    expect(cmdb.get_by_text('空闲机池').first).to_be_visible()
    expect(cmdb.get_by_text('主机列表')).to_be_visible()


# ---------- 模型 ----------

def test_CMDB模型页能打开(cmdb):
    """模型页应有「新建模型」按钮。"""
    _nav(cmdb, '/model')
    expect(cmdb.get_by_role('button', name='新建模型')).to_be_visible()


# ---------- 动态分组 ----------

def test_CMDB动态分组能打开(cmdb):
    """进入业务 → 动态分组：页面标题应为「动态分组」。"""
    _nav(cmdb, f'/business/{CMDB_BUSINESS_ID}/custom-query')
    expect(cmdb.get_by_role('heading', name='动态分组', level=1)).to_be_visible()
