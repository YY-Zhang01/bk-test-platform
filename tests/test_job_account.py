# -*- coding: utf-8 -*-
"""JOB 链路5：账号管理与高危命令检测测试（安全线）。

这条链路对应"账号管理 / 高危语句检测"页面的操作：
1. 执行账号   → 管理服务器 OS 账号（Linux/Windows），执行时"用谁的身份干活"
2. 高危规则   → 自定义正则规则匹配危险命令，动作分"扫描(1)"和"拦截(2)"
3. 脚本检测   → check_script 单次检测脚本是否命中高危规则

数据自洽策略：账号和规则都自建自清（create → 验证 → delete）。
高危规则是全局资源（无 bk_scope 参数，与业务无关）。

坑位清单（面试可讲）：
- Windows 账号必须传密码，Linux 可不传（参数校验）
- 高危规则新建后默认停用(0)，必须 enable 才生效
- check_script 返回命中级别：1警告 2错误 3致命
"""
import pytest

from app.api_client import JobError

pytestmark = pytest.mark.account  # 链路5：账号管理与高危命令检测


# ---------- fixture：链路数据（自建自清） ----------

@pytest.fixture()
def 新账号(job_client, unique_name):
    """建一个 Linux 系统账号，用完删除。"""
    created = job_client.create_account(account=unique_name, type_=1,
                                        category=1, alias=unique_name,
                                        description='pytest 自建测试账号')
    yield created
    job_client.delete_account(created['id'])


@pytest.fixture()
def 新高危规则(job_client, unique_name):
    """建一条拦截型高危规则（匹配唯一标记串），用完删除。"""
    rule = job_client.create_dangerous_rule(
        expression=f'{unique_name}_danger_cmd',
        language_list=[1], description='pytest 自建高危规则', action=2)
    yield rule
    job_client.delete_dangerous_rule(rule['id'])


# ---------- 用例 ----------

def test_建Linux账号_列表能查到(job_client, 新账号):
    """对应手动步骤：新建 Linux 系统账号 → 账号列表里能看到。"""
    accounts = job_client.get_account_list(account=新账号['account'])
    ids = [a['id'] for a in accounts]
    assert 新账号['id'] in ids, f'账号列表里找不到新账号: {ids}'
    assert accounts[0]['type'] == 1, 'Linux 账号 type 应为 1'


def test_建Windows账号_不传密码被拒(job_client, unique_name):
    """负面用例：Windows 账号必须传密码（坑位实测）。

    Linux 可不传密码（SSH 密钥/免密场景），Windows 必须传，
    这是参数校验层就能拦截的规则。
    """
    with pytest.raises(JobError):
        job_client.create_account(account=unique_name, type_=2, category=1)


def test_删除账号_列表消失(job_client, unique_name):
    """对应手动步骤：删除账号 → 列表里查不到。"""
    created = job_client.create_account(account=unique_name, type_=1,
                                        category=1, alias=unique_name)
    job_client.delete_account(created['id'])

    accounts = job_client.get_account_list(account=unique_name)
    ids = [a['id'] for a in accounts]
    assert created['id'] not in ids, f'已删除的账号不应还在列表: {ids}'


def test_高危检测_危险命令命中(job_client):
    """对应手动步骤：脚本内容里写了危险命令 → 检测有命中项。

    依赖环境预置高危规则（体验环境一般有默认规则）；
    若环境未预置则跳过，可用下一个用例自建规则验证。
    """
    hits = job_client.check_script('rm -rf /tmp', language=1)
    if not hits:
        pytest.skip('体验环境未预置高危规则，无法验证默认规则命中')
    for hit in hits:
        assert 'level' in hit and 'match_content' in hit, f'命中项结构异常: {hit}'


def test_自定义高危规则_启用后检测命中(job_client, 新高危规则, unique_name):
    """对应手动步骤：建规则 → 启用 → 用含该命令的脚本做检测 → 命中。

    坑位：新建规则默认停用(0)，必须先 enable 才参与检测。
    """
    rule_id = 新高危规则['id']
    assert 新高危规则['status'] == 0, '新建规则应默认停用'

    # 停用状态下检测，不应命中
    hits = job_client.check_script(f'echo {unique_name}_danger_cmd', language=1)
    matched = [h for h in hits if unique_name in str(h.get('match_content', ''))]
    assert matched == [], f'规则未启用时不应命中: {hits}'

    # 启用后应命中
    job_client.enable_dangerous_rule(rule_id)
    hits = job_client.check_script(f'echo {unique_name}_danger_cmd', language=1)
    matched = [h for h in hits if unique_name in str(h.get('match_content', ''))]
    assert matched, f'规则启用后应命中 {unique_name}_danger_cmd，实际: {hits}'


def test_高危规则_停用后不再命中(job_client, 新高危规则, unique_name):
    """对应手动步骤：停用规则 → 检测不再命中（规则生命周期验证）。"""
    rule_id = 新高危规则['id']
    job_client.enable_dangerous_rule(rule_id)

    job_client.disable_dangerous_rule(rule_id)
    hits = job_client.check_script(f'echo {unique_name}_danger_cmd', language=1)
    matched = [h for h in hits if unique_name in str(h.get('match_content', ''))]
    assert matched == [], f'规则停用后不应再命中: {hits}'


def test_高危规则列表_能查到自建规则(job_client, 新高危规则):
    """对应手动步骤：高危规则页 → 规则列表里能看到自建规则。"""
    rules = job_client.get_dangerous_rule_list()
    ids = [r['id'] for r in rules]
    assert 新高危规则['id'] in ids, f'规则列表里找不到自建规则: {ids}'
