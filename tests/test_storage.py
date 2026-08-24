# -*- coding: utf-8 -*-
"""存储层单元测试：SQLite 落库/查询/迁移，全部不依赖环境凭证。

monkeypatch 把 DB_PATH 指到临时目录，不碰真实 data/platform.db。
"""
import json
import sqlite3
from contextlib import closing

import pytest

from app import storage

pytestmark = pytest.mark.unit  # 存储层不依赖环境，纯本地 SQLite


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """把存储层指到临时库，测试互不污染真实数据。"""
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'platform.db')
    return tmp_path / 'platform.db'


def test_保存运行记录后能按最近N条查回(tmp_db):
    """保存两条运行记录，list_runs 按时间正序返回（旧→新），供首页折线图。"""
    storage.save_run('冒烟', 18, 0, 59, 1.0, 'all green')
    storage.save_run('回归', 77, 0, 0, 1.0, 'full')
    rows = storage.list_runs(20)
    assert len(rows) == 2
    # 按时间正序返回（旧→新），供折线图
    assert rows[0]['plan'] == '冒烟'
    assert rows[1]['plan'] == '回归'
    assert rows[1]['passed'] == 77
    assert rows[1]['rate'] == 1.0


def test_查询条数上限生效(tmp_db):
    """list_runs 的 limit 生效：取最近 N 条（id 最大），正序返回。"""
    for i in range(5):
        storage.save_run(f'plan{i}', i, 0, 0, 1.0, '')
    rows = storage.list_runs(limit=2)
    # limit 生效且取最近两条（id 最大的），正序返回
    assert [r['plan'] for r in rows] == ['plan3', 'plan4']


def test_接口调试留痕含成功失败位(tmp_db):
    """log_probe 记录成功/失败位（ok 1/0），落库可查，供接口调试历史。"""
    storage.log_probe('job', 'get_script_list', True, '{"ok": true}')
    storage.log_probe('cmdb', 'search_business', False, '超时')
    with closing(sqlite3.connect(tmp_db)) as conn:
        rows = conn.execute('SELECT * FROM probe_logs ORDER BY id').fetchall()
    assert len(rows) == 2
    assert rows[0][2] == 'job' and rows[0][4] == 1
    assert rows[1][4] == 0


def test_超长调试结果截断防爆库(tmp_db):
    """调试结果超 500 字符被截断，防止探针日志撑爆数据库。"""
    storage.log_probe('job', 'get_script_list', True, 'x' * 1000)
    with closing(sqlite3.connect(tmp_db)) as conn:
        result = conn.execute('SELECT result FROM probe_logs').fetchone()[0]
    assert len(result) == 500


def test_旧jsonl一次性迁移后不重复导入(tmp_path, monkeypatch, tmp_db):
    """旧 jsonl 迁移到 SQLite 后改 .bak，重复迁移返回 0 不重复导入。"""
    old = tmp_path / 'results_history.jsonl'
    old.write_text('\n'.join([
        json.dumps({'stamp': '2026-08-22 10:00:00', 'plan': '冒烟',
                    'passed': 10, 'failed': 0, 'skipped': 1, 'rate': 0.9}),
        json.dumps({'stamp': '2026-08-22 11:00:00', 'plan': '回归',
                    'passed': 20, 'failed': 1, 'skipped': 0, 'rate': 0.95}),
    ]) + '\n', encoding='utf-8')
    assert storage.migrate_jsonl(old) == 2
    # 迁移完旧文件改名 .bak 备份
    assert not old.exists()
    assert old.with_suffix('.jsonl.bak').exists()
    # 原路径再迁移：文件已不存在 → 0，数据不重复导入
    assert storage.migrate_jsonl(old) == 0
    assert len(storage.list_runs(20)) == 2


def test_迁移时表非空则跳过并备份旧文件(tmp_path, monkeypatch, tmp_db):
    """表已有数据时跳过迁移（防覆盖），旧文件仍备份为 .bak。"""
    storage.save_run('已有记录', 1, 0, 0, 1.0, '')
    old = tmp_path / 'results_history.jsonl'
    old.write_text(json.dumps({'stamp': '', 'plan': '旧数据',
                               'passed': 9, 'failed': 0, 'skipped': 0,
                               'rate': 1.0}) + '\n', encoding='utf-8')
    assert storage.migrate_jsonl(old) == 0
    assert old.with_suffix('.jsonl.bak').exists()
    # 表里只有已有的那条，旧数据没被导入
    assert len(storage.list_runs(20)) == 1


def test_无旧文件迁移直接返回零(tmp_path, monkeypatch, tmp_db):
    """没有旧 jsonl 文件时 migrate 返回 0，不报错。"""
    assert storage.migrate_jsonl(tmp_path / '不存在.jsonl') == 0
