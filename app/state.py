# -*- coding: utf-8 -*-
"""共享状态 + 工具函数 + 常量（拆自 web_app.py）。

多个 router 要共享的东西都放这里，避免循环 import：
- 常量：PLANS / PROBE_METHODS / 各目录路径
- 全局状态：TASKS（运行中任务）、_STATS_CACHE（统计缓存）
- 工具函数：pytest collect、历史落库、junit 解析、进度计数、限流、apidoc 解析、生成历史存档
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from app import storage

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / 'reports'
DIST_DIR = BASE_DIR / 'frontend' / 'dist'
GEN_HISTORY_DIR = BASE_DIR / 'gen_cases' / 'history'

# 公网访问账号密码（部署时设环境变量启用；本地不设则完全放行）
PLATFORM_USER = os.environ.get('PLATFORM_USER', 'jwkj')
PLATFORM_PASSWORD = os.environ.get('PLATFORM_PASSWORD', '')

# 测试计划：预设 marker 组合（借鉴 MeterSphere 的"测试计划"概念）
PLANS = {
    'smoke': 'unit and not platform',  # 冒烟：不等账号秒出（排除 Web层测试防自引用）
    'regression': 'unit or cmdb or integration',          # 回归：全链路
    'job-only': 'script or fast_exec or plan or cron or account or file',
    'e2e': 'integration',                                 # 只跑连块测
}

# 接口调试白名单：只开放只读查询，写操作一律拒绝（防误操作）
PROBE_METHODS = {
    'job': ['get_script_list', 'get_script_version_list',
            'get_script_version_detail', 'get_job_instance_status'],
    'cmdb': ['search_business', 'list_biz_hosts', 'search_host',
             'execute_dynamic_group', 'search_module', 'search_set',
             'search_object_attribute'],
}

# 后台任务表：task_id -> {'proc', 'log', 'done', ...}
TASKS = {}

# 统计缓存（pytest collect-only 每次 ~0.2s，缓存 30 秒避免连点卡顿）
_STATS_CACHE = {'ts': 0, 'data': None}


def _pytest_collect(marker: str | None = None) -> dict:
    """collect-only 统计：总数 / unit 数 / 环境层数。"""
    cmd = [sys.executable, '-m', 'pytest', '--collect-only', '-q']
    if marker:
        cmd += ['-m', marker]
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    env.pop('PLATFORM_PASSWORD', None)
    env.pop('PLATFORM_USER', None)
    proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True,
                          text=True, encoding='utf-8', errors='replace',
                          env=env, timeout=120)
    out = proc.stdout + proc.stderr
    m = re.search(r'(\d+)/(\d+) tests? collected', out)
    if m:
        return {'count': int(m.group(1)), 'raw': out}
    m = re.search(r'(?:collected (\d+) items?|(\d+) tests? collected)', out)
    return {'count': int(m.group(1) or m.group(2)) if m else 0, 'raw': out}


def _stats() -> dict:
    """总览统计：总数 / unit 数 / 环境层数 / 报告列表。

    口径：total = unit + env；env 是「待环境」总数，里面再拆
    account（等账号）和 ui（需浏览器）两部分。"""
    now = time.time()
    if now - _STATS_CACHE['ts'] < 30 and _STATS_CACHE['data']:
        return _STATS_CACHE['data']
    total = _pytest_collect()
    unit = _pytest_collect(marker='unit')
    ui = _pytest_collect(marker='ui')
    data = {
        'total': total['count'],
        'unit': unit['count'],
        'env': total['count'] - unit['count'],
        'ui': ui['count'],
        'account': total['count'] - unit['count'] - ui['count'],
        'reports': _list_reports(),
    }
    _STATS_CACHE['ts'] = now
    _STATS_CACHE['data'] = data
    return data


def _list_reports() -> list:
    """报告列表（按修改时间倒序，排除 latest.html 副本）。"""
    if not REPORTS_DIR.exists():
        return []
    items = []
    for p in REPORTS_DIR.glob('*.html'):
        if p.name == 'latest.html':
            continue
        items.append({'name': p.name,
                      'mtime': time.strftime('%m-%d %H:%M',
                                             time.localtime(p.stat().st_mtime)),
                      'url': f'/report/{p.name}'})
    return sorted(items, key=lambda x: x['name'], reverse=True)


def _save_history(task_id: str):
    """跑完把结果摘要写进 SQLite，供首页趋势图用（storage.save_run）。"""
    t = TASKS[task_id]
    try:
        text = Path(t['log']).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return
    m = re.search(r'(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?', text)
    if not m:
        return
    passed, failed, skipped = (int(m.group(i) or 0) for i in (1, 2, 3))
    total = passed + failed
    summary = m.group(0)
    storage.save_run(t['plan'], passed, failed, skipped,
                     round(passed / total, 3) if total else 0, summary)


def _parse_junit(path) -> dict:
    """解析 pytest junitxml，返回 {测试名: passed/failed/skipped}。"""
    import xml.etree.ElementTree as ET
    status = {}
    try:
        tree = ET.parse(path)
        for tc in tree.iter('testcase'):
            name = tc.get('name')
            if name is None:
                continue
            if tc.find('failure') is not None or tc.find('error') is not None:
                status[name] = 'failed'
            elif tc.find('skipped') is not None:
                status[name] = 'skipped'
            else:
                status[name] = 'passed'
    except (ET.ParseError, OSError):
        pass
    return status


def _count_progress(text: str) -> int:
    """数 pytest -q 输出里的进度字符（. F E s 等组成的行），得到已跑用例数。"""
    count = 0
    for line in text.split('\n'):
        s = line.strip()
        if s and all(c in '.FEsxX' for c in s):
            count += len(s)
    return count


def _parse_api_doc(md_text: str) -> dict:
    """从 apidoc markdown 提取功能描述 + 参数表（字段/类型/必选/描述）。"""
    desc = ''
    m = re.search(r'###\s*功能描述\s*\n+(.*?)(?=###|\Z)', md_text, re.DOTALL)
    if m:
        desc = m.group(1).strip()
    params = []
    in_table = False
    for line in md_text.split('\n'):
        s = line.strip()
        if s.startswith('|') and '字段' in s and '类型' in s:
            in_table = True
            continue
        if in_table:
            if s.startswith('|') and '---' not in s and s:
                cells = [c.strip() for c in s.strip('|').split('|')]
                if len(cells) >= 4 and cells[0]:
                    params.append({'name': cells[0], 'type': cells[1],
                                   'required': cells[2], 'desc': cells[3]})
            elif not s.startswith('|'):
                in_table = False
    return {'desc': desc, 'params': params}


def _save_gen_history(api_name: str, code: str):
    """把生成草稿存档到历史目录。"""
    try:
        GEN_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime('%Y%m%d_%H%M%S')
        (GEN_HISTORY_DIR / f'{stamp}_{api_name}.py').write_text(code, encoding='utf-8')
    except OSError:
        pass


def _gen_rate_ok(ip: str, limit: int = 8) -> bool:
    """滑动窗口限流：60 秒内最多 limit 次 AI 生成。
    持久化到 SQLite（storage.rate_limits），重启不清零，防借重启刷接口。"""
    if storage.count_rate(ip) >= limit:
        return False
    storage.log_rate(ip)
    return True
