# -*- coding: utf-8 -*-
"""CMDB 独立链路测试（分开测的 CMDB 半边）。

"分开测"的含义：CMDB 的用例只依赖 CMDB 自己的接口，
JOB 挂了、JOB 没权限都不影响这条链路跑。反之 JOB 六条链路也一样。
分开测的价值 = 故障隔离：这半边挂了，问题一定在 CMDB，不用两头排查。

链路设计（只读为主，尊重共享环境）：
业务 → 主机 → 拓扑（集群/模块）→ 模型属性字典 → 动态分组执行

unit 层（不依赖环境）：分页参数构造、凭证复用逻辑。
环境层（体验账号到手后跑）：业务/主机/拓扑/分组四组查询。
"""
import pytest

from app import job_config
from app.cmdb_client import CmdbClient, make_page

pytestmark = pytest.mark.cmdb  # 分开测：CMDB 独立链路


# ---------- unit 层（不依赖环境） ----------

@pytest.mark.unit
def test_分页参数_构造正确():
    """make_page：默认 0 起点、10 条；传 sort 才带排序字段。"""
    page = make_page()
    assert page == {'start': 0, 'limit': 10}
    assert 'sort' not in page
    assert make_page(start=5, limit=50, sort='bk_host_id') == \
        {'start': 5, 'limit': 50, 'sort': 'bk_host_id'}


@pytest.mark.unit
def test_客户端_未配置时业务ID为空():
    """CMDB 客户端复用 job_config 配置；未配置时 biz_id 为 None，
    环境层用例会因 fixture skip 而不会真发请求。"""
    client = CmdbClient(esb_host=None)
    assert client.biz_id is None
    assert client.esb_host is None


@pytest.mark.unit
def test_客户端_构造参数可覆盖配置():
    """传参优先级：显式传参 > job_config。压测/多环境切换靠这个。"""
    client = CmdbClient(esb_host='http://fake', biz_id=88)
    assert client.esb_host == 'http://fake'
    assert client.biz_id == 88


# ---------- 环境层（体验账号到手后跑） ----------

def test_查业务_列表非空且含当前业务(cmdb_client):
    """对应手动步骤：CMDB 首页业务列表。

    数据契约锚点：JOB 的 BK_SCOPE_ID 必须能在 CMDB 业务列表里找到，
    这是两个系统所有联动的根（连块测还会复用这个断言）。
    """
    bizs = cmdb_client.search_business()
    assert bizs, '应至少有一个业务（体验环境一般内置演示业务）'
    ids = [b.get('bk_biz_id') for b in bizs]
    assert int(job_config.BK_SCOPE_ID) in ids, \
        f'JOB scope_id={job_config.BK_SCOPE_ID} 不在 CMDB 业务列表里: {ids}'


def test_查主机_当前业务主机列表非空(cmdb_client):
    """对应手动步骤：业务 → 主机页面。

    坑位：list_biz_hosts 的主机 ID 字段是 bk_host_id，
    这正是 JOB 快速执行的 host_id 来源——两个系统共用同一个主机 ID。
    """
    hosts = cmdb_client.list_biz_hosts(limit=200)
    assert hosts, '当前业务下应至少有一台主机'
    assert all('bk_host_id' in h for h in hosts), \
        f'主机数据缺 bk_host_id 字段: {hosts[0]}'


def test_查主机详情_按ID能查到(cmdb_client, target_host):
    """对应手动步骤：主机详情页。按 host_id 条件查询应返回该主机。"""
    hosts = cmdb_client.search_host(host_id=target_host)
    assert hosts, f'按 bk_host_id={target_host} 查主机应非空'
    host = hosts[0].get('host', hosts[0])
    assert host.get('bk_host_id') == target_host, \
        f'查回的主机 ID 不对: {host}'


def test_查拓扑_集群和模块结构完整(cmdb_client):
    """对应手动步骤：业务拓扑页（集群→模块两层树）。"""
    sets = cmdb_client.search_set(limit=200)
    modules = cmdb_client.search_module(limit=200)
    assert sets, '业务下应有至少一个集群'
    assert modules, '业务下应有至少一个模块'
    # 模块挂在集群下：每个模块都有 bk_set_id 指向某个集群
    set_ids = {s['bk_set_id'] for s in sets}
    orphan = [m for m in modules if m.get('bk_set_id') not in set_ids]
    assert not orphan, f'存在无主模块（挂的集群不存在）: {orphan[:3]}'


def test_查模型属性_host模型字段字典非空(cmdb_client):
    """对应手动步骤：模型管理 → 主机模型字段。

    用途：字段变更回归的基线——上线前后各跑一次，字段集变化即告警。
    """
    attrs = cmdb_client.search_object_attribute(obj_id='host')
    assert attrs, 'host 模型应有属性字段'
    names = {a['bk_property_id'] for a in attrs}
    # 核心字段必须在：主机 ID 和云区域是 JOB 执行主机的最小契约
    assert 'bk_host_id' in names, f'host 模型缺 bk_host_id: {names}'
    assert 'bk_cloud_id' in names, f'host 模型缺 bk_cloud_id: {names}'
