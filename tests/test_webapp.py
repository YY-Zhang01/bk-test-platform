# -*- coding: utf-8 -*-
"""Web 平台接口测试：首页/统计/跑测试/历史，全链路不依赖环境凭证。

用 FastAPI TestClient 直调路由，monkeypatch 把存储层指向临时库。
"""
import time

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.web_app import app

# unit：不依赖环境；platform：Web层测试，“跑测试”子进程会自引用，冒烟计划需排除
pytestmark = [pytest.mark.unit, pytest.mark.platform]


@pytest.fixture
def client(tmp_path, monkeypatch):
    """web 层存储指到临时库，不碰真实 data/platform.db。"""
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'platform.db')
    return TestClient(app)


def test_首页返回平台页面(client):
    """首页返回 200，内容含平台标识（Vue 挂载点或金字塔文案）。"""
    r = client.get('/')
    assert r.status_code == 200
    assert '金字塔' in r.text or '蓝鲸' in r.text


def test_用例统计接口返回全量数字(client):
    """stats 返回 total/unit/env，且 total = unit + env（口径自洽）。"""
    r = client.get('/api/stats')
    assert r.status_code == 200
    data = r.json()
    # 全量 77 个用例；unit 层（环境无关）真实可跑
    assert data['total'] >= 70
    assert data['unit'] >= 15
    assert data['total'] == data['unit'] + data['env']


def test_冒烟计划后台跑完并留历史(client):
    """跑冒烟计划，轮询到 done，returncode=0，趋势接口能查到该条历史。"""
    r = client.post('/api/run', params={'plan': 'smoke', 'report': False})
    assert r.status_code == 200
    task_id = r.json()['task_id']
    # 轮询任务状态，最多等 60 秒（unit 层秒出）
    st = {}
    for _ in range(120):
        st = client.get(f'/api/run/{task_id}').json()
        if st.get('done'):
            break
        time.sleep(0.5)
    assert st.get('done') is True
    assert st.get('returncode') == 0
    # 跑完自动落历史，趋势接口能查到这条记录
    items = client.get('/api/trend').json()['items']
    assert any(i['plan'] == 'smoke' for i in items)


def test_未知任务查询返回404(client):
    """查不存在的任务 id 返回 404。"""
    r = client.get('/api/run/不存在的任务')
    assert r.status_code == 404


def test_接口调试拒绝白名单外目标(client):
    """probe 目标不在白名单（只认 job/cmdb）时返回 400 拒绝。"""
    r = client.post('/api/probe', json={'target': 'hack', 'api': 'x'})
    assert r.status_code == 400


def test_接口调试拒绝写操作只开放只读(client):
    """probe 调写操作（create_script）被拒，只开放只读查询（防误操作）。"""
    r = client.post('/api/probe', json={'target': 'job',
                                        'api': 'create_script'})
    assert r.status_code == 400


def test_报告文件名白名单拒绝非法名(client):
    """报告文件名不合白名单格式返回 400，防目录穿越。"""
    r = client.get('/report/evil.html')
    assert r.status_code == 400
