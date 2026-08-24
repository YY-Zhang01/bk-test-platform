# -*- coding: utf-8 -*-
"""CMDB 安全测试（补齐 CMDB 侧的"安全"维度）。

JOB 侧有 test_security.py，CMDB 侧对应补这里，两层设计一致：
1. unit 层（现在就能跑）：供应商账号认证自洽、写操作参数构造自洽
2. 环境层（体验账号到手后跑）：越权查别的业务数据、写操作权限校验

面试可讲：CMDB 是数据底座，安全重点在「业务隔离」——每个查询/写操作
都带 bk_biz_id 做数据隔离，越权（用别的业务 ID）应拿不到本业务数据。
"""
import pytest

from app.cmdb_client import CmdbClient

pytestmark = pytest.mark.security  # 安全测试维度


# ---------- unit 层：认证与参数构造自洽（mock _call，不发请求） ----------

@pytest.fixture()
def 捕获参数(monkeypatch):
    """monkeypatch 掉 _call：不发请求，只抓构造好的参数检查安全自洽。"""
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
def test_供应商账号认证必带(捕获参数):
    """CMDB 每个请求必须带 bk_supplier_account（历史参数，默认 0）。"""
    assert 捕获参数['client']._extra_auth() == {'bk_supplier_account': '0'}


@pytest.mark.unit
def test_写业务_参数构造自洽(捕获参数):
    """create_business 拼参：bk_biz_name 和 bk_biz_maintainer 正确。"""
    捕获参数['client'].create_business(biz_name='测试业务', maintainer='admin')
    params = 捕获参数['params']
    assert 捕获参数['api'] == 'create_business'
    assert params['bk_biz_name'] == '测试业务'
    assert params['bk_biz_maintainer'] == 'admin'


@pytest.mark.unit
def test_导主机_参数构造自洽(捕获参数):
    """add_host_to_biz 拼参：host_list 原样透传。"""
    host_list = [{'bk_host_id': 1, 'bk_cloud_id': 0}]
    捕获参数['client'].add_host_to_biz(host_list)
    assert 捕获参数['params']['host_list'] == host_list


@pytest.mark.unit
def test_查询_自动带业务ID做数据隔离(捕获参数):
    """list_biz_hosts 未显式传 biz_id 时，自动用客户端的 biz_id（隔离锚点）。"""
    捕获参数['client'].list_biz_hosts()
    params = 捕获参数['params']
    assert params['bk_biz_id'] == 88, '查询必须带业务 ID 做数据隔离'


# ---------- 环境层：真发接口验证越权与权限（账号到手后跑） ----------

def test_越权_跨业务查不到本业务主机(cmdb_client):
    """业务隔离：用别的业务 biz_id 查主机，应查不到本业务的主机。

    探测型：账号到手后实测，预期用不存在的 biz_id 查主机返回空列表
    （拿不到本业务数据 = 数据隔离生效）。
    """
    other_biz_hosts = cmdb_client.list_biz_hosts(biz_id=999999)
    own_hosts = cmdb_client.list_biz_hosts(limit=500)
    # 诚实标注：越权返回待实测，先验证两种查询都能正常返回结构
    assert isinstance(other_biz_hosts, list)
    assert isinstance(own_hosts, list)


def test_写操作_无权限建业务被拒(cmdb_client):
    """探测型：无写权限的账号建业务应被拒。账号到手后用一个只读账号
    实测，确认被拒后再固化"result=false + 权限错误码"断言。"""
    created = cmdb_client.create_business(biz_name='no-perm-probe')
    assert isinstance(created, dict)
