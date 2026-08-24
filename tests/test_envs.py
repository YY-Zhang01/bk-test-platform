# -*- coding: utf-8 -*-
"""多环境管理单元测试（纯本地逻辑，不碰蓝鲸）。

验证 envs.py 的读文件 / 覆盖优先级，以及客户端 env 参数的三级取值：
显式参数 > env 配置 > job_config.py 默认值。
"""
import json

import pytest

from app import envs
from app.api_client import JobClient
from app.cmdb_client import CmdbClient


@pytest.mark.unit
def test_模板环境_列出体验与本地CMDB():
    """envs.example.json 里应内置两个占位环境。"""
    names = envs.list_envs()
    assert 'experience' in names, f'模板应含体验环境: {names}'
    assert 'local_cmdb' in names, f'模板应含本地 CMDB 环境: {names}'


@pytest.mark.unit
def test_取不存在的环境_返回空dict():
    """get_env 对未知环境返回空 dict，调用方用 .get 兜底，不抛异常。"""
    assert envs.get_env('不存在的环境') == {}


@pytest.mark.unit
def test_local文件覆盖模板(monkeypatch, tmp_path):
    """envs.local.json 里的同名环境覆盖模板（local 优先，真凭证不入库）。"""
    local = tmp_path / 'envs.local.json'
    local.write_text(json.dumps({
        'experience': {'esb_host': 'https://from-local', 'bk_app_code': 'x'},
    }, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(envs, 'EXAMPLE', tmp_path / 'no-example.json')
    monkeypatch.setattr(envs, 'LOCAL', local)
    envs.clear_cache()
    cfg = envs.get_env('experience')
    assert cfg['esb_host'] == 'https://from-local'


@pytest.mark.unit
def test_客户端_env参数读环境配置(monkeypatch, tmp_path):
    """JobClient(env=...) / CmdbClient(env=...) 从 envs 读地址与凭证。

    契约点：CMDB 的 biz_id 复用 env 里的 scope_id（两者是同一个业务 ID）。
    """
    local = tmp_path / 'envs.local.json'
    local.write_text(json.dumps({
        'experience': {
            'esb_host': 'https://esb.example.com',
            'bk_app_code': 'myapp',
            'bk_app_secret': 's3cret',
            'bk_token': 'tok',
            'scope_type': 'biz',
            'scope_id': '888',
        },
    }, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(envs, 'EXAMPLE', tmp_path / 'no-example.json')
    monkeypatch.setattr(envs, 'LOCAL', local)
    envs.clear_cache()

    job = JobClient(env='experience')
    assert job.esb_host == 'https://esb.example.com'
    assert job.app_code == 'myapp'
    assert job.scope_id == '888'

    cmdb = CmdbClient(env='experience')
    assert cmdb.biz_id == '888', 'CMDB 业务 ID 应复用 env 的 scope_id'


@pytest.mark.unit
def test_客户端_显式参数优先于env(monkeypatch, tmp_path):
    """三级取值：显式参数 > env 配置。方便压测/调试临时覆盖单个值。"""
    local = tmp_path / 'envs.local.json'
    local.write_text(json.dumps({
        'experience': {'esb_host': 'https://from-env', 'scope_id': '1'},
    }, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(envs, 'EXAMPLE', tmp_path / 'no-example.json')
    monkeypatch.setattr(envs, 'LOCAL', local)
    envs.clear_cache()

    job = JobClient(env='experience', esb_host='https://override', scope_id='999')
    assert job.esb_host == 'https://override'
    assert job.scope_id == '999'


@pytest.mark.unit
def test_坏配置文件_不抛异常(monkeypatch, tmp_path):
    """envs.local.json 写坏了不能拖垮 import 和单测，静默跳过。"""
    bad = tmp_path / 'envs.local.json'
    bad.write_text('{ 这不是合法 JSON', encoding='utf-8')
    monkeypatch.setattr(envs, 'EXAMPLE', tmp_path / 'no-example.json')
    monkeypatch.setattr(envs, 'LOCAL', bad)
    envs.clear_cache()
    assert envs.list_envs() == []
