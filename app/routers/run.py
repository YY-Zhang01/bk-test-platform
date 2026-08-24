# -*- coding: utf-8 -*-
"""跑测试路由：后台跑 pytest + 轮询状态。"""
import os
import subprocess
import sys
import threading
import time

from fastapi import APIRouter, HTTPException, Query

from app import storage
from app.state import (BASE_DIR, PLANS, REPORTS_DIR, TASKS, _STATS_CACHE,
                       _count_progress, _parse_junit, _pytest_collect,
                       _save_history)

router = APIRouter()


@router.post('/api/run')
def run(marker: str | None = Query(default=None),
        plan: str | None = Query(default=None),
        report: bool = Query(default=True)):
    """后台跑 pytest。plan 优先：预设计划映射到 marker 组合。
    输出写日志文件（子进程 stdout 重定向），轮询读文件尾部。"""
    marker = PLANS.get(plan, marker)
    task_id = str(int(time.time() * 1000))
    junit_path = BASE_DIR / '.last_result.xml'
    cmd = [sys.executable, '-m', 'pytest', '-q', '--tb=short',
           '--junitxml', str(junit_path)]
    if marker:
        cmd += ['-m', marker]
    out_html = None
    if report:
        stamp = time.strftime('%Y%m%d_%H%M%S')
        out_html = REPORTS_DIR / f'report_{stamp}.html'
        cmd += ['--html', str(out_html), '--self-contained-html']
    log_path = BASE_DIR / f'.run_{task_id}.log'
    log_f = open(log_path, 'w', encoding='utf-8')
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    # 清除登录密码环境变量：pytest 子进程里 TestClient 直调路由不该被认证拦
    env.pop('PLATFORM_PASSWORD', None)
    env.pop('PLATFORM_USER', None)
    # 启动前 collect 拿总数（供前端进度条显示 已跑/总数）
    total = _pytest_collect(marker=marker)['count'] if marker else 0
    proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_f,
                            stderr=subprocess.STDOUT, env=env)
    TASKS[task_id] = {'proc': proc, 'log': str(log_path), 'done': False,
                      'cmd': ' '.join(cmd[-6:]),
                      'plan': plan or marker or 'all',
                      'report': bool(report), 'total': total}

    def _on_exit(p, tid=task_id):
        p.wait()
        TASKS[tid]['done'] = True
        TASKS[tid]['returncode'] = p.returncode
        _save_history(tid)
        latest = REPORTS_DIR / 'latest.html'
        if report and out_html and out_html.exists():
            import shutil
            shutil.copy(out_html, latest)
        _STATS_CACHE['ts'] = 0
        # 用例执行状态落库持久化（重启不丢）
        for name, status in _parse_junit(junit_path).items():
            storage.save_case_status(name, status)
        try:
            log_f.close()
        except OSError:
            pass

    threading.Thread(target=_on_exit, args=(proc,), daemon=True).start()
    return {'task_id': task_id}


@router.get('/api/run/{task_id}')
def task_status(task_id: str):
    """任务状态：done/running/returncode/summary/progress/total/output。"""
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(404, '任务不存在或已过期')
    try:
        from pathlib import Path
        text = Path(task['log']).read_text(encoding='utf-8', errors='replace')
    except OSError:
        text = ''
    import re
    m = re.search(r'(\d+ passed[^\n]*)', text)
    return {'done': task['done'], 'running': task['proc'].poll() is None,
            'returncode': task.get('returncode'),
            'summary': m.group(1) if m else '',
            'progress': _count_progress(text), 'total': task.get('total'),
            'output': text[-4000:],
            'cmd': task['cmd']}
