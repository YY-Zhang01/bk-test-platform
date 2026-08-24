# -*- coding: utf-8 -*-
"""SQLite 存储层：测试运行历史 + 接口调试记录。

为什么从 jsonl 升级到 SQLite（工程化考量，面试可讲）：
- 结构化：按测试计划筛选、聚合统计，一条 SQL 搞定，jsonl 得全量扫
- 并发安全：多线程收尾写历史互不干扰，jsonl 追加在并发下会错行
- 零运维：单文件数据库 + 标准库 sqlite3，不需要装数据库服务
- 可扩展：后续加"失败用例分析""接口调试回放"直接建表即可
"""
import sqlite3
import time
from contextlib import closing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'platform.db'


def _conn() -> sqlite3.Connection:
    """建连接 + 幂等建表（首次启动自动初始化 schema）。"""
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS runs (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      TEXT    NOT NULL,
            plan    TEXT    NOT NULL,
            passed  INTEGER NOT NULL DEFAULT 0,
            failed  INTEGER NOT NULL DEFAULT 0,
            skipped INTEGER NOT NULL DEFAULT 0,
            rate    REAL    NOT NULL DEFAULT 0,
            summary TEXT
        );
        CREATE TABLE IF NOT EXISTS probe_logs (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            ts     TEXT NOT NULL,
            target TEXT NOT NULL,
            api    TEXT NOT NULL,
            ok     INTEGER NOT NULL,
            result TEXT
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            created_ts TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            ts REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS case_status (
            test_name TEXT PRIMARY KEY,
            status    TEXT NOT NULL,
            ts        TEXT NOT NULL
        );
    ''')
    conn.commit()
    return conn


def save_run(plan: str, passed: int, failed: int, skipped: int,
             rate: float, summary: str) -> None:
    """跑完一次测试后落库（趋势图数据源）。"""
    with closing(_conn()) as conn, conn:
        conn.execute(
            'INSERT INTO runs (ts, plan, passed, failed, skipped, rate, summary)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?)',
            (time.strftime('%Y-%m-%d %H:%M:%S'), plan,
             passed, failed, skipped, rate, summary))


def list_runs(limit: int = 20) -> list:
    """最近 N 条运行记录（按时间正序返回，供折线图）。"""
    with closing(_conn()) as conn:
        rows = conn.execute(
            'SELECT * FROM runs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    return [dict(r) for r in reversed(rows)]


def log_probe(target: str, api: str, ok: bool, result: str) -> None:
    """接口调试记录（每次在线调用都留痕，写失败不阻塞调试）。"""
    try:
        with closing(_conn()) as conn, conn:
            conn.execute(
                'INSERT INTO probe_logs (ts, target, api, ok, result)'
                ' VALUES (?, ?, ?, ?, ?)',
                (time.strftime('%Y-%m-%d %H:%M:%S'), target, api,
                 1 if ok else 0, str(result)[:500]))
    except Exception:
        pass


def list_probe_logs(limit: int = 20) -> list:
    """最近 N 条接口调试记录（供前端「历史请求」回填复用）。"""
    with closing(_conn()) as conn:
        rows = conn.execute(
            'SELECT * FROM probe_logs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    return [dict(r) for r in rows]


def migrate_jsonl(old_file: Path) -> int:
    """一次性迁移：旧版 results_history.jsonl 的数据搬进 SQLite。

    只在 runs 表为空且旧文件存在时执行，迁移完把旧文件改名 .bak，
    保证重复启动不会重复导入。
    """
    if not old_file.exists():
        return 0
    import json
    with closing(_conn()) as conn:
        count = conn.execute('SELECT COUNT(*) AS n FROM runs').fetchone()['n']
        if count:
            old_file.replace(old_file.with_suffix('.jsonl.bak'))
            return 0
        rows = []
        with open(old_file, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        with conn:
            for r in rows:
                conn.execute(
                    'INSERT INTO runs (ts, plan, passed, failed, skipped,'
                    ' rate, summary) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (r.get('stamp', ''), r.get('plan', ''),
                     r.get('passed', 0), r.get('failed', 0),
                     r.get('skipped', 0), r.get('rate', 0), ''))
    old_file.replace(old_file.with_suffix('.jsonl.bak'))
    return len(rows)


# ── 会话 token（持久化：重启不丢登录态）──

def save_session(token: str) -> None:
    """签发会话 token，落库持久化（服务重启登录态仍在）。"""
    with closing(_conn()) as conn, conn:
        conn.execute('INSERT OR REPLACE INTO sessions (token, created_ts)'
                     ' VALUES (?, ?)',
                     (token, time.strftime('%Y-%m-%d %H:%M:%S')))


def has_session(token: str) -> bool:
    """校验 token 是否有效（登录过）。"""
    if not token:
        return False
    with closing(_conn()) as conn:
        row = conn.execute('SELECT 1 FROM sessions WHERE token = ?',
                           (token,)).fetchone()
    return row is not None


# ── 限流（持久化：重启不清零，防借重启刷接口）──

def log_rate(ip: str) -> None:
    """记录一次 AI 生成请求（时间戳 float，用于滑动窗口计数）。"""
    with closing(_conn()) as conn, conn:
        conn.execute('INSERT INTO rate_limits (ip, ts) VALUES (?, ?)',
                     (ip, time.time()))


def count_rate(ip: str, window: float = 60.0) -> int:
    """数某 IP 最近 window 秒内的请求次数。"""
    cutoff = time.time() - window
    with closing(_conn()) as conn:
        row = conn.execute(
            'SELECT COUNT(*) AS n FROM rate_limits WHERE ip = ? AND ts > ?',
            (ip, cutoff)).fetchone()
    return row['n']


# ── 用例执行状态（持久化：重启后用例库状态仍在）──

def save_case_status(name: str, status: str) -> None:
    """存单个用例的最近执行状态（passed/failed/skipped）。"""
    with closing(_conn()) as conn, conn:
        conn.execute('INSERT OR REPLACE INTO case_status (test_name, status, ts)'
                     ' VALUES (?, ?, ?)',
                     (name, status, time.strftime('%Y-%m-%d %H:%M:%S')))


def get_all_case_status() -> dict:
    """返回全部用例状态 {test_name: status}。"""
    with closing(_conn()) as conn:
        rows = conn.execute('SELECT test_name, status FROM case_status').fetchall()
    return {r['test_name']: r['status'] for r in rows}
