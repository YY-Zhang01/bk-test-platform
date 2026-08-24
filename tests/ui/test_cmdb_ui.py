# -*- coding: utf-8 -*-
"""UI 自动化（Playwright）——测 CMDB 网页（蓝鲸配置平台 v3.13.7）。

覆盖 5 大页面：业务列表 / 主机列表 / 拓扑 / 模型 / 动态分组，共 10 个用例。
选择器依据：本仓库 docs/research/cmdb-pages/*.md 的实测可访问性快照。

  已逐字核对（快照在手，基本稳）：
    - 登录页（login-page.md）：用户名 / 密码 / 登录
    - 首页导航（home.md）：蓝鲸配置平台 + 首页/业务/资源/模型/运营分析/平台管理
    - 业务拓扑（business.md / biz3-topo.md）：标题"业务拓扑" + 空闲机池 + 主机列表标签
    - 资源目录（resource.md）：标题"资源目录" + 主机管理/组织架构
    - 主机列表（host-all.md）：标题"主机" + 未分配/已分配/全部筛选页签 + 搜索框
    - 主机搜索（host-search.md）：搜索后出现"检索项"筛选条
  快照缺失、按社区版惯例写（跑一次核实，文案不同改对应选择器）：
    - 业务列表（#/business/index）："新建业务"按钮 → 弹窗"业务名称"
    - 模型（#/model）："新建模型"按钮
    - 动态分组（#/business/{id}/custom-query）：标题"动态分组"

前提：本地 CMDB 已跑起来（Docker：CMDB + MongoDB + Redis + ZooKeeper，默认 admin/admin）。

运行：
    python -m pytest tests/ui/test_cmdb_ui.py -m ui --run-ui
"""
import pytest

from playwright.sync_api import expect

pytestmark = pytest.mark.ui

# ---- 环境配置（按你的实际环境改） ----
CMDB_URL = 'http://127.0.0.1:8080'   # CMDB 网页地址
CMDB_USER = 'admin'                  # standalone 默认账号
CMDB_PASSWORD = 'admin'              # standalone 默认密码
# 业务 ID：进"业务"页后，左上角业务选择器显示"小洋测试业务 (3)"，括号里的数字就是 ID
CMDB_BUSINESS_ID = 3


def _login(page):
    """登录 CMDB 并等待进入主界面。"""
    page.goto(CMDB_URL)
    page.get_by_role('textbox', name='用户名').fill(CMDB_USER)
    page.get_by_role('textbox', name='密码').fill(CMDB_PASSWORD)
    page.get_by_role('button', name='登录').click()
    # 登录成功：顶部出现"蓝鲸配置平台"logo 链接（Docker 首次加载偏慢，放宽超时）
    expect(page.get_by_role('link', name='蓝鲸配置平台')).to_be_visible(timeout=15000)


@pytest.fixture()
def cmdb(page):
    """已登录的 CMDB 页面（每个用例独立登录）。"""
    _login(page)
    return page


# ---------- 登录 ----------

def test_CMDB登录页能打开(page):
    """登录页应有「用户名」「密码」输入框和「登录」按钮。"""
    page.goto(CMDB_URL)
    expect(page.get_by_role('textbox', name='用户名')).to_be_visible()
    expect(page.get_by_role('textbox', name='密码')).to_be_visible()
    expect(page.get_by_role('button', name='登录')).to_be_visible()


def test_CMDB登录后进入首页(cmdb):
    """登录后顶部导航应有 首页/业务/资源/模型 等入口。"""
    banner = cmdb.get_by_role('banner')
    for name in ('首页', '业务', '资源', '模型', '运营分析', '平台管理'):
        expect(banner.get_by_role('link', name=name, exact=True)).to_be_visible()


# ---------- 业务列表 ----------

def test_CMDB业务列表能打开(cmdb):
    """业务列表页应有「新建业务」按钮（业务写链路的入口）。"""
    cmdb.goto(f'{CMDB_URL}/#/business/index')
    # 社区版业务列表右上角固定"新建业务"按钮；若版本文案不同改这里
    expect(cmdb.get_by_role('button', name='新建业务')).to_be_visible()


def test_CMDB业务列表新建业务弹窗(cmdb):
    """点「新建业务」应弹出表单，含「业务名称」输入项。"""
    cmdb.goto(f'{CMDB_URL}/#/business/index')
    cmdb.get_by_role('button', name='新建业务').click()
    # 弹窗表单第一个字段是"业务名称"；若版本文案不同改这里
    expect(cmdb.get_by_text('业务名称')).to_be_visible(timeout=10000)


# ---------- 资源目录 / 主机列表 ----------

def test_CMDB资源目录能打开(cmdb):
    """资源目录页应有标题 + 主机管理/组织架构分类。"""
    cmdb.goto(f'{CMDB_URL}/#/resource')
    expect(cmdb.get_by_role('heading', name='资源目录', level=1)).to_be_visible()
    expect(cmdb.get_by_role('heading', name='主机管理', level=4)).to_be_visible()
    expect(cmdb.get_by_role('heading', name='组织架构', level=4)).to_be_visible()


def test_CMDB主机列表能打开(cmdb):
    """主机列表页应有标题 + 未分配/已分配筛选页签 + 主机表格列头。"""
    cmdb.goto(f'{CMDB_URL}/#/resource/host')
    expect(cmdb.get_by_role('heading', name='主机', level=1)).to_be_visible()
    expect(cmdb.get_by_text('未分配')).to_be_visible()
    expect(cmdb.get_by_text('已分配')).to_be_visible()
    # 主机表格列头（内网IPv4 是固定列）
    expect(cmdb.get_by_role('columnheader', name='内网IPv4')).to_be_visible()


def test_CMDB主机搜索能过滤(cmdb):
    """在主机列表搜索 IP，应出现「检索项」筛选条（内网IP|外网IP|精确）。"""
    cmdb.goto(f'{CMDB_URL}/#/resource/host')
    box = cmdb.get_by_role('textbox', name='请输入IP或固资编号')
    box.fill('10.0.0.101')
    box.press('Enter')
    # 搜索后出现"检索项"筛选条；结果可为空（"搜索结果为空"），但筛选条一定在
    expect(cmdb.get_by_text('检索项')).to_be_visible(timeout=10000)


# ---------- 拓扑 ----------

def test_CMDB业务拓扑能打开(cmdb):
    """进入业务 → 业务拓扑：标题 + 内置"空闲机池"节点 + 主机列表标签。"""
    cmdb.goto(f'{CMDB_URL}/#/business/{CMDB_BUSINESS_ID}/index')
    expect(cmdb.get_by_role('heading', name='业务拓扑', level=1)).to_be_visible()
    expect(cmdb.get_by_text('空闲机池')).to_be_visible()
    expect(cmdb.get_by_text('主机列表')).to_be_visible()


# ---------- 模型 ----------

def test_CMDB模型页能打开(cmdb):
    """模型页应有「新建模型」按钮。"""
    cmdb.goto(f'{CMDB_URL}/#/model')
    # 社区版模型页固定"新建模型"按钮；若版本文案不同改这里
    expect(cmdb.get_by_role('button', name='新建模型')).to_be_visible()


# ---------- 动态分组 ----------

def test_CMDB动态分组能打开(cmdb):
    """进入业务 → 动态分组：页面标题应为「动态分组」。"""
    cmdb.goto(f'{CMDB_URL}/#/business/{CMDB_BUSINESS_ID}/custom-query')
    expect(cmdb.get_by_role('heading', name='动态分组', level=1)).to_be_visible()
    # TODO: 若需交互测试，补"新建"按钮断言（文案随版本，可能为"新建"/"新增分组"）
