# -*- coding: utf-8 -*-
"""UI 自动化路由：列出测试 + 后台运行。"""
import ast
import os
import subprocess
import sys
import threading
import time

from fastapi import APIRouter

from app.state import BASE_DIR, REPORTS_DIR, TASKS

router = APIRouter()


@router.get('/api/ui')
def ui_tests():
    """列出 UI 自动化测试（扫描 tests/ui/ 的 test_*.py）。"""
    ui_dir = BASE_DIR / 'tests' / 'ui'
    tests = []
    for f in sorted(ui_dir.glob('test_*.py')):
        try:
            tree = ast.parse(f.read_text(encoding='utf-8'))
        except OSError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                doc = (ast.get_docstring(node) or '').strip()
                tests.append({'file': f.name, 'name': node.name,
                              'desc': doc.split('\n')[0].strip()})
    return {'tests': tests, 'count': len(tests),
            'note': 'UI 测试需要浏览器，请在本地跑（服务器无浏览器会失败）'}


@router.post('/api/ui/run')
def ui_run():
    """后台跑 UI 自动化测试（Playwright，需浏览器 + 被测系统在跑）。"""
    task_id = str(int(time.time() * 1000))
    # 失败自动截图（pytest-playwright），截图存 ui_screenshots/ 目录
    shot_dir = BASE_DIR / 'ui_screenshots'
    shot_dir.mkdir(exist_ok=True)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    ui_html = REPORTS_DIR / f'ui_report_{stamp}.html'
    cmd = [sys.executable, '-m', 'pytest', 'tests/ui', '-m', 'ui',
           '--run-ui', '-q', '--tb=short',
           '--screenshot', 'only-on-failure', '--output', str(shot_dir),
           '--html', str(ui_html), '--self-contained-html']
    log_path = BASE_DIR / f'.run_{task_id}.log'
    log_f = open(log_path, 'w', encoding='utf-8')
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    env.pop('PLATFORM_PASSWORD', None)
    env.pop('PLATFORM_USER', None)
    proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_f,
                            stderr=subprocess.STDOUT, env=env)
    TASKS[task_id] = {'proc': proc, 'log': str(log_path), 'done': False,
                      'cmd': 'pytest tests/ui --run-ui', 'plan': 'ui',
                      'report': False}

    def _on_exit(p, tid=task_id):
        p.wait()
        TASKS[tid]['done'] = True
        TASKS[tid]['returncode'] = p.returncode
        try:
            log_f.close()
        except OSError:
            pass

    threading.Thread(target=_on_exit, args=(proc,), daemon=True).start()
    return {'task_id': task_id}
