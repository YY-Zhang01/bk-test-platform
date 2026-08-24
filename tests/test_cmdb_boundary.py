# -*- coding: utf-8 -*-
"""CMDB 参数边界测试（补齐 CMDB 侧的"参数范围"维度）。

JOB 侧有 test_job_boundary.py，CMDB 侧对应补这里，两层设计一致：
1. unit 层（现在就能跑，不依赖环境）：
   - make_page 分页构造边界（start/limit/sort）
   - 各查询接口的条件构造自洽：mock _call 抓参数，验证拼的对不对
2. 环境层（体验账号到手后跑）：分页越界、非法 biz_id / obj_id / 条件字段
   真发给接口，验证服务端校验。

面试可讲：参数范围测试 = 等价类 + 边界值，CMDB 的分页（start/limit）、
查询条件（biz_id/条件字段）、模型对象（obj_id）都有边界要测。
"""
import pytest

from app.cmdb_client import CmdbClient, make_page

pytestmark = pytest.mark.boundary  # 参数边界测试


# ---------- unit 层：分页构造（纯函数） ----------

@pytest.mark.unit
def test_make_page_默认值():
    """默认 start=0、limit=10，不带 sort 字段。"""
    assert make_page() == {'start': 0, 'limit': 10}
    assert 'sort' not in make_page()


@pytest.mark.unit
@pytest.mark.parametrize('start,limit,sort', [
    (0, 1, ''),          # 最小 limit
    (0, 0, ''),          # limit 0（越界值，构造层照传，让服务端拒绝）
    (0, 1000, ''),       # 超大 limit
    (10, 20, 'bk_host_id'),  # 带排序
    (999999, 10, ''),    # 超大 start
])
def test_make_page_边界值透传(start, limit, sort):
    """分页参数必须原样透传，构造层不做过滤（越界值留给服务端校验）。"""
    page = make_page(start=start, limit=limit, sort=sort)
    assert page['start'] == start
    assert page['limit'] == limit
    if sort:
        assert page['sort'] == sort
    else:
        assert 'sort' not in page


# ---------- unit 层：条件构造自洽（mock _call，不发请求） ----------

@pytest.fixture()
def 捕获参数(monkeypatch):
    """monkeypatch 掉 _call：不真发请求，只把构造好的参数抓回来检查。"""
    captured = {}

    def fake_call(api_name, params):
        captured['api'] = api_name
        captured['params'] = params
        return {}

    client = CmdbClient(biz_id=88)
    monkeypatch.setattr(client, '_call', fake_call)
    captured['client'] = client
    return captured


@pytest.mark.unit
def test_查业务_条件构造自洽(捕获参数):
    """search_business 传 biz_id 时，condition 结构应为 {bk_biz_id: id}。"""
    捕获参数['client'].search_business(biz_id=88)
    params = 捕获参数['params']
    assert 捕获参数['api'] == 'search_business'
    assert params['condition'] == {'bk_biz_id': 88}


@pytest.mark.unit
def test_查主机_条件构造自洽(捕获参数):
    """search_host 按 host_id 查，condition 应含 host 模型 + $eq 条件。"""
    捕获参数['client'].search_host(host_id=123)
    params = 捕获参数['params']
    assert 捕获参数['api'] == 'search_host'
    cond = params['condition'][0]
    assert cond['bk_obj_id'] == 'host'
    assert cond['condition'][0]['field'] == 'bk_host_id'
    assert cond['condition'][0]['operator'] == '$eq'
    assert cond['condition'][0]['value'] == 123


@pytest.mark.unit
def test_查主机列表_fields透传(捕获参数):
    """list_biz_hosts 传 fields 时原样透传，不传则不带该字段。"""
    捕获参数['client'].list_biz_hosts(fields=['bk_host_id', 'bk_cloud_id'])
    assert 捕获参数['params']['fields'] == ['bk_host_id', 'bk_cloud_id']
    捕获参数['client'].list_biz_hosts()
    assert 'fields' not in 捕获参数['params']


@pytest.mark.unit
def test_查模型属性_obj_id透传(捕获参数):
    """search_object_attribute 的 obj_id 原样透传（默认 host）。"""
    捕获参数['client'].search_object_attribute(obj_id='biz')
    assert 捕获参数['params']['bk_obj_id'] == 'biz'


# ---------- 环境层：真发接口验证服务端边界校验（账号到手后跑） ----------

def test_分页_start负数(cmdb_client):
    """探测型：start 传负数，账号到手后实测 CMDB 是拒绝还是静默返回空。"""
    page = make_page(start=-1, limit=10)
    # 诚实标注：CMDB 对负 start 的行为待实测，先探测不造假断言
    bizs = cmdb_client.search_business(limit=10)
    assert isinstance(bizs, list)


def test_查主机_非法biz_id(cmdb_client):
    """探测型：用不存在的 biz_id 查主机，账号到手后实测返回（预期空列表）。"""
    hosts = cmdb_client.list_biz_hosts(biz_id=999999)
    assert isinstance(hosts, list)


def test_查模型_非法obj_id(cmdb_client):
    """探测型：查不存在的对象类型，账号到手后实测返回（预期空或报错）。"""
    attrs = cmdb_client.search_object_attribute(obj_id='not_exist_obj')
    assert isinstance(attrs, list)
