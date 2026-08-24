# -*- coding: utf-8 -*-
"""测试平台 Web 界面（FastAPI 单文件）。

把平台六大模块收进一个网页：
- 首页看分层金字塔 + 用例统计（调 /api/stats 实时 collect）
- 一键跑测试（后台 subprocess 跑 pytest，轮询看进度）
- 历史报告列表（点开即看 HTML 报告）
- AI 用例生成入口（前端留位，调 gen_cases.py 的逻辑在 /api/gen）

运行：python web_app.py → 浏览器开 http://127.0.0.1:8000
面试演示动线：打开首页 → 点"跑全量" → 看进度 → 点开报告。

为什么 FastAPI 单文件：平台阶段 0 的定位是"有脸可用"，不引入
前端工程；页面内嵌 HTML + 原生 JS，零依赖零构建。
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

# 项目根（web_app.py 在 app/ 下，CLI 直跑时 sys.path[0] 是 app/，
# 需要把根插入才能延迟导入 app 包 + 定位 reports/ 等根级目录）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import storage

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / 'reports'

# 一次性迁移：旧版 jsonl 历史数据搬进 SQLite（幂等，见 storage.migrate_jsonl）
storage.migrate_jsonl(BASE_DIR / 'results_history.jsonl')

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

app = FastAPI(title='蓝鲸双系统端到端测试平台')

# 公网访问密码：部署到服务器时设置环境变量 PLATFORM_PASSWORD 启用；
# 本地/测试不设置则完全放行，不影响现有用例。
PLATFORM_PASSWORD = os.environ.get('PLATFORM_PASSWORD', '')


@app.middleware('http')
async def 密码拦截(request: Request, call_next):
    """简单密码验证（HTTP Basic Auth）：设了 PLATFORM_PASSWORD 才生效。"""
    if not PLATFORM_PASSWORD:
        return await call_next(request)
    expected = 'Basic ' + base64.b64encode(
        f'admin:{PLATFORM_PASSWORD}'.encode('utf-8')).decode('utf-8')
    if request.headers.get('Authorization') == expected:
        return await call_next(request)
    return JSONResponse(status_code=401, content={'detail': '需要密码'},
                        headers={'WWW-Authenticate': 'Basic realm="bk-test-platform"'})

# 后台任务表：task_id -> {'proc': Popen, 'output': str, 'done': bool}
TASKS = {}

# 统计缓存（pytest collect-only 每次 ~0.2s，缓存 30 秒避免连点卡顿）
_STATS_CACHE = {'ts': 0, 'data': None}


def _pytest_collect(marker: str | None = None) -> dict:
    """collect-only 统计：总数 / unit 数 / 环境层数。"""
    cmd = [sys.executable, '-m', 'pytest', '--collect-only', '-q']
    if marker:
        cmd += ['-m', marker]
    env = dict(__import__('os').environ, PYTHONIOENCODING='utf-8')
    proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True,
                          text=True, encoding='utf-8', errors='replace',
                          env=env, timeout=120)
    out = proc.stdout + proc.stderr
    # pytest 9 三种格式都兼容：
    #   带 -m 过滤："18/77 tests collected (59 deselected)" → 取 selected
    #   不带过滤："77 tests collected"；旧版："collected 77 items"
    m = re.search(r'(\d+)/(\d+) tests? collected', out)
    if m:
        return {'count': int(m.group(1)), 'raw': out}
    m = re.search(r'(?:collected (\d+) items?|(\d+) tests? collected)', out)
    return {'count': int(m.group(1) or m.group(2)) if m else 0, 'raw': out}


def _stats() -> dict:
    now = time.time()
    if now - _STATS_CACHE['ts'] < 30 and _STATS_CACHE['data']:
        return _STATS_CACHE['data']
    total = _pytest_collect()
    unit = _pytest_collect(marker='unit')
    data = {
        'total': total['count'],
        'unit': unit['count'],
        'env': total['count'] - unit['count'],
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


# ---------------- API ----------------

@app.get('/', response_class=HTMLResponse)
def index():
    return INDEX_HTML


@app.get('/api/stats')
def stats():
    return _stats()


@app.post('/api/run')
def run(marker: str | None = Query(default=None),
        plan: str | None = Query(default=None),
        report: bool = Query(default=True)):
    """后台跑 pytest。plan 优先：预设计划映射到 marker 组合
    （冒烟/回归/只JOB/只连块测）；marker 可直接传 pytest 表达式。
    输出写日志文件（子进程 stdout 重定向），轮询读文件尾部。"""
    marker = PLANS.get(plan, marker)
    task_id = str(int(time.time() * 1000))
    cmd = [sys.executable, '-m', 'pytest', '-q', '--tb=short']
    if marker:
        cmd += ['-m', marker]
    if report:
        stamp = time.strftime('%Y%m%d_%H%M%S')
        out_html = REPORTS_DIR / f'report_{stamp}.html'
        cmd += ['--html', str(out_html), '--self-contained-html']
    log_path = BASE_DIR / f'.run_{task_id}.log'
    log_f = open(log_path, 'w', encoding='utf-8')
    env = dict(__import__('os').environ, PYTHONIOENCODING='utf-8')
    proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_f,
                            stderr=subprocess.STDOUT, env=env)
    TASKS[task_id] = {'proc': proc, 'log': str(log_path), 'done': False,
                      'cmd': ' '.join(cmd[-6:]),
                      'plan': plan or marker or 'all',
                      'report': bool(report)}
    # 收尾：记历史（趋势图用）+ 拷贝 latest.html + 清统计缓存
    def _on_exit(p, tid=task_id):
        p.wait()
        TASKS[tid]['done'] = True
        TASKS[tid]['returncode'] = p.returncode
        _save_history(tid)
        latest = REPORTS_DIR / 'latest.html'
        if report and out_html.exists():
            import shutil
            shutil.copy(out_html, latest)
        _STATS_CACHE['ts'] = 0
        try:
            log_f.close()
        except OSError:
            pass
    import threading
    threading.Thread(target=_on_exit, args=(proc,), daemon=True).start()
    return {'task_id': task_id}


@app.get('/api/run/{task_id}')
def task_status(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(404, '任务不存在或已过期')
    try:
        text = Path(task['log']).read_text(encoding='utf-8', errors='replace')
    except OSError:
        text = ''
    m = re.search(r'(\d+ passed[^\n]*)', text)
    return {'done': task['done'], 'running': task['proc'].poll() is None,
            'returncode': task.get('returncode'),
            'summary': m.group(1) if m else '',
            'output': text[-4000:],
            'cmd': task['cmd']}


@app.get('/api/reports')
def reports():
    return {'reports': _list_reports()}


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
    # 通过率口径 = 已执行用例（passed+failed）的通过率，skip 不进分母。
    # 前端趋势图用橙点标注"有跳过"的执行，避免 skip 被误读成 100% 全绿。
    total = passed + failed
    summary = m.group(0)
    storage.save_run(t['plan'], passed, failed, skipped,
                     round(passed / total, 3) if total else 0, summary)


@app.get('/api/trend')
def trend():
    """历史执行趋势（SQLite 最近 20 条），供首页通过率折线图。"""
    return {'items': storage.list_runs(20)}


@app.get('/api/gen')
def gen_info():
    """AI 用例生成的状态与说明（gen_cases.py，命令行工具）。"""
    from app import job_config
    apidoc_dir = BASE_DIR / 'docs' / 'apidoc'
    apidoc_count = len(list(apidoc_dir.glob('*.md'))) if apidoc_dir.exists() else 0
    return {
        'key_configured': bool(job_config.LLM_API_KEY),
        'model': job_config.LLM_MODEL or 'deepseek-chat',
        'apidoc_count': apidoc_count,
        'usage': 'python gen_cases.py  # 为 apidoc 里全部接口生成用例草稿',
    }


@app.post('/api/probe')
async def probe(req: Request):
    """接口调试（Postman 式，借鉴 MeterSphere 接口调试）：白名单内的
    只读方法可在线调用，返回原始 JSON。写操作一律拒绝。"""
    body = await req.json()
    target = body.get('target')
    api_name = body.get('api')
    params = body.get('params') or {}
    if target not in PROBE_METHODS:
        raise HTTPException(400, f'不支持的目标：{target}')
    if api_name not in PROBE_METHODS[target]:
        raise HTTPException(400, f'{target} 不开放 {api_name}（只开放只读查询）')
    try:
        if target == 'job':
            from app.api_client import JobClient
            client = JobClient()
        else:
            from app.cmdb_client import CmdbClient
            client = CmdbClient()
        result = getattr(client, api_name)(**params)
        storage.log_probe(target, api_name, True, result)
        return {'ok': True, 'data': result}
    except TypeError as e:
        storage.log_probe(target, api_name, False, str(e))
        return {'ok': False, 'error': f'参数与接口签名不匹配：{e}'}
    except Exception as e:
        storage.log_probe(target, api_name, False, str(e))
        return {'ok': False, 'error': str(e)}


@app.get('/report/{filename}')
def report_file(filename: str):
    """返回 reports/ 下的 HTML 报告（文件名白名单防目录穿越）。"""
    if not re.fullmatch(r'report_\d{8}_\d{6}\.html', filename) \
            and filename != 'latest.html':
        raise HTTPException(400, '非法报告文件名')
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, '报告不存在')
    return FileResponse(path, media_type='text/html')


# ---------------- 首页（内嵌 HTML，原生 JS 零依赖） ----------------

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>蓝鲸双系统端到端测试平台</title>
<style>
  :root {
    --bg: #f2f5fa; --card: #ffffff; --ink: #101828; --sub: #667085;
    --weak: #98a2b3; --blue: #2f54eb; --line: #eef1f6; --green: #12b76a;
    --shadow: 0 1px 3px rgba(16,24,40,.08), 0 1px 2px rgba(16,24,40,.04);
    --shadow-lg: 0 8px 24px rgba(16,24,40,.14);
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
         background: var(--bg); color: var(--ink);
         display: flex; flex-direction: column; min-height: 100vh; }
  header { background: #0f1c4d; color: #fff; padding: 16px 24px;
           display: flex; align-items: baseline; gap: 16px; flex-shrink: 0;
           flex-wrap: wrap; }
  header h1 { font-size: 20px; letter-spacing: 1px; }
  .badge { display: inline-block; margin-left: 14px; font-size: 12px;
           background: rgba(255,255,255,.16); border-radius: 20px;
           padding: 4px 13px; vertical-align: 4px; font-weight: 400;
           letter-spacing: 0; }
  .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%;
         background: #34d399; margin-right: 6px;
         animation: pulse 2s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: .3; } }
  header .sub { margin-top: 0; opacity: .7; font-size: 13px; }
  .cards { display: flex; gap: 14px; flex-wrap: wrap;
           position: relative; }
  .card { flex: 1; min-width: 180px; background: var(--card);
          border-radius: 12px; padding: 18px 16px; box-shadow: var(--shadow);
          display: flex; align-items: center; gap: 13px;
          transition: transform .15s, box-shadow .15s; }
  .card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
  .c-ico { width: 44px; height: 44px; border-radius: 11px; display: flex;
           align-items: center; justify-content: center; font-size: 18px;
           flex-shrink: 0; }
  .card .num { font-size: 25px; font-weight: 700; color: var(--ink);
               line-height: 1.15; }
  .card .label { font-size: 12px; color: var(--sub); margin-top: 3px; }
  section { background: var(--card); border-radius: 12px; padding: 20px 22px;
            margin-top: 20px; box-shadow: var(--shadow); overflow: visible; }
  section h2 { font-size: 15px; font-weight: 600; margin-bottom: 16px;
               color: var(--ink); padding-left: 11px; position: relative; }
  section h2::before { content: ''; position: absolute; left: 0; top: 2px;
           width: 4px; height: 16px; border-radius: 2px;
           background: linear-gradient(180deg, #3b82f6, #2f54eb); }
  .pyramid { text-align: center; padding: 6px 0; }
  .layer { margin: 9px auto 0; color: #fff; padding: 13px; border-radius: 10px;
           font-size: 13px; letter-spacing: .5px; cursor: default;
           transition: transform .15s, box-shadow .15s; }
  .layer:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
  .l3 { width: 36%; background: linear-gradient(135deg, #fbbf5c, #f79009); }
  .l2 { width: 68%; background: linear-gradient(135deg, #5b9bf8, #2f54eb); }
  .l1 { width: 100%; background: linear-gradient(135deg, #26408f, #0f1c4d); }
  .dims { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
          gap: 12px; }
  .dim { border: 1px solid var(--line); border-radius: 10px; padding: 14px 14px 12px;
         position: relative; background: #fafbff; }
  .d-t { font-weight: 600; font-size: 15px; margin-bottom: 4px; color: var(--ink); }
  .d-s { font-size: 12px; color: var(--sub); line-height: 1.5; }
  .tag { position: absolute; top: 12px; right: 12px; font-size: 11px;
         padding: 2px 8px; border-radius: 10px; }
  .tag.ok { background: #e7f9f0; color: #12b76a; }
  .tag.wait { background: #fff4e5; color: #f79009; }
  .btns { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  button { border: none; border-radius: 8px; padding: 10px 20px;
           font-size: 14px; cursor: pointer; color: #fff; font-weight: 500;
           transition: filter .15s, transform .1s, opacity .15s,
                       background .15s; }
  button:hover:not(:disabled) { filter: brightness(1.08); }
  button:active:not(:disabled) { transform: scale(.97); }
  button:disabled { opacity: .45; cursor: not-allowed; }
  .b-all { background: linear-gradient(135deg, #1d4ed8, #2f54eb);
           box-shadow: 0 4px 12px rgba(47,84,235,.32); }
  .b-unit { background: #fff; color: var(--blue); border: 1px solid #c7d4f5; }
  .b-unit:hover:not(:disabled) { background: #f5f8ff; filter: none; }
  #out, #p-result { background: #0d1117; font-family: Consolas,
             "Courier New", monospace; font-size: 12px;
             padding: 14px 16px; border-radius: 10px;
             max-height: 280px; overflow: auto; white-space: pre-wrap; }
  #out { color: #7ee2a8; display: none; }
  #p-result { color: #9fb8d9; margin-top: 12px; }
  #summary { margin-top: 10px; font-weight: 600; color: var(--green);
             display: none; font-size: 14px; }
  select { border: 1px solid #d4dcec; border-radius: 8px; padding: 9px 14px;
           font-size: 13px; background: #fff; color: var(--ink);
           min-width: 230px; outline: none; transition: border-color .15s; }
  select:focus, textarea:focus { border-color: var(--blue); }
  textarea { width: 100%; margin-top: 12px; border: 1px solid #d4dcec;
             border-radius: 8px; padding: 10px 12px; font-family: Consolas,
             "Courier New", monospace; font-size: 12.5px; color: var(--ink);
             outline: none; resize: vertical; background: #fafbff; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  td { padding: 10px 6px; border-bottom: 1px solid var(--line); }
  tr:hover td { background: #f8faff; }
  a { color: var(--blue); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .hint { color: var(--weak); font-size: 12px; margin-top: 8px; }
  canvas { display: block; width: 100%; height: 220px; }
  .layout { flex: 1; display: flex; align-items: stretch; min-height: 0; }
  .sidebar { width: 200px; flex-shrink: 0; background: #0f1c4d;
             padding: 16px 0; display: flex; flex-direction: column; gap: 2px; }
  .nav-item { text-align: left; background: transparent; color: rgba(255,255,255,.72);
              border: none; border-radius: 8px; margin: 0 10px; padding: 12px 16px;
              font-size: 14px; cursor: pointer; font-weight: 500;
              display: flex; align-items: center; gap: 10px; }
  .nav-item:hover:not(:disabled) { filter: none; background: rgba(255,255,255,.1);
                                   color: #fff; }
  .nav-item.active { background: var(--blue); color: #fff; font-weight: 600; }
  .nav-item .ico { font-size: 16px; }
  .content { flex: 1; min-width: 0; padding: 20px 24px 44px; }
  .tab-panel.hidden { display: none; }
</style>
</head>
<body>
<header>
  <h1>蓝鲸双系统端到端测试平台
    <span class="badge"><span class="dot"></span>服务运行中</span></h1>
  <p class="sub">CMDB × JOB ｜ 分开测保故障隔离 · 连块测抓集成缺陷 · 一页全览</p>
</header>
<div class="layout">
<aside class="sidebar">
  <button class="nav-item active" data-tab="overview"><span class="ico">▦</span>总览</button>
  <button class="nav-item" data-tab="run"><span class="ico">▶</span>跑测试</button>
  <button class="nav-item" data-tab="probe"><span class="ico">⌘</span>接口调试</button>
  <button class="nav-item" data-tab="reports"><span class="ico">▤</span>报告</button>
  <button class="nav-item" data-tab="gen"><span class="ico">✦</span>AI 生成</button>
</aside>
<main class="content">
  <div class="tab-panel" id="tab-overview">
  <div class="cards">
    <div class="card">
      <div class="c-ico" style="background:#e8efff;color:#2f54eb">▦</div>
      <div><div class="num" id="n-total">-</div>
      <div class="label">用例总数</div></div>
    </div>
    <div class="card">
      <div class="c-ico" style="background:#e7f9f0;color:#12b76a">✓</div>
      <div><div class="num" id="n-unit">-</div>
      <div class="label">unit（不等账号可跑）</div></div>
    </div>
    <div class="card">
      <div class="c-ico" style="background:#fff4e5;color:#f79009">⏳</div>
      <div><div class="num" id="n-env">-</div>
      <div class="label">环境层（等账号激活）</div></div>
    </div>
    <div class="card">
      <div class="c-ico" style="background:#f0ecff;color:#7a5af8">▤</div>
      <div><div class="num" id="n-report">-</div>
      <div class="label">历史报告</div></div>
    </div>
  </div>

  <section>
    <h2>执行趋势（已执行用例通过率 · 橙点=有跳过 · 最近 20 次）</h2>
    <canvas id="trend" width="900" height="220"></canvas>
  </section>

  <section>
    <h2>测试分层（对齐 HttpRunner：API 层 → 用例层 → 场景层）</h2>
    <div class="pyramid">
      <div class="layer l3">L3 场景层 integration：契约 / 联动 / 反向（跨系统）</div>
      <div class="layer l2">L2 用例层：JOB 六链路 + CMDB 独立链路（单系统分开测）</div>
      <div class="layer l1">L1 API 层 unit：客户端封装与拼参自洽（不依赖环境）</div>
    </div>
  </section>

  <section>
    <h2>全方位测试五大维度（性能 / 安全 / 边界 / 交互 / 端到端）</h2>
    <div class="dims">
      <div class="dim"><div class="d-t">功能</div><div class="d-s">JOB 6 链路 + CMDB · 91 用例</div><span class="tag ok">已落地</span></div>
      <div class="dim"><div class="d-t">边界</div><div class="d-s">等价类 / 边界值 / 非法值</div><span class="tag ok">已落地</span></div>
      <div class="dim"><div class="d-t">端到端</div><div class="d-s">数据契约 · 场景矩阵</div><span class="tag wait">待账号</span></div>
      <div class="dim"><div class="d-t">性能</div><div class="d-s">Locust 只读压测</div><span class="tag wait">待账号</span></div>
      <div class="dim"><div class="d-t">安全</div><div class="d-s">鉴权 / 越权 / 注入 / 高危</div><span class="tag wait">待账号</span></div>
    </div>
  </section>
  </div>

  <div class="tab-panel hidden" id="tab-run">
  <section>
    <h2>一键跑测试（测试计划）</h2>
    <div class="btns">
      <select id="plan">
        <option value="full">全量（出报告）</option>
        <option value="smoke">冒烟计划：只跑 unit（秒出）</option>
        <option value="regression">回归计划：unit + CMDB + 连块测</option>
        <option value="job-only">只测 JOB 六链路</option>
        <option value="e2e">只跑连块测（需账号）</option>
      </select>
      <button class="b-all" id="b-run">执行计划</button>
    </div>
    <pre id="out"></pre>
    <div id="summary"></div>
  </section>
  </div>

  <div class="tab-panel hidden" id="tab-probe">
  <section>
    <h2>接口调试（Postman 式，只读白名单）</h2>
    <div class="btns">
      <select id="p-target">
        <option value="job">JOB</option>
        <option value="cmdb">CMDB</option>
      </select>
      <select id="p-api"></select>
      <button class="b-unit" id="p-go">调用</button>
    </div>
    <textarea id="p-params" rows="3"
      placeholder='JSON 参数，如 {"limit": 10}'></textarea>
    <pre id="p-result">尚未调用。选好接口、填好参数，点"调用"。</pre>
  </section>
  </div>

  <div class="tab-panel hidden" id="tab-reports">
  <section>
    <h2>历史报告</h2>
    <table id="reports"><tbody></tbody></table>
    <div class="hint" id="report-hint"></div>
  </section>
  </div>

  <div class="tab-panel hidden" id="tab-gen">
  <section>
    <h2>AI 用例生成（gen_cases.py）</h2>
    <p>把 docs/apidoc/ 里 <b id="gen-doc-count">-</b> 份接口文档喂给大模型（<span id="gen-model">DeepSeek</span>），自动产出 pytest 用例草稿，人工审阅后并入正式用例目录。</p>
    <p class="hint">命令行用法：python gen_cases.py（全量）/ -i 接口名（单个）/ --collect（生成后验证可收集）。</p>
    <p class="hint" id="gen-status">加载中…</p>
  </section>
  </div>
</main>
</div>
<script>
const $ = id => document.getElementById(id);

// Tab 切换：总览 / 跑测试 / 接口调试 / 报告
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p =>
    p.classList.toggle('hidden', p.id !== 'tab-' + name));
  document.querySelectorAll('.nav-item').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === name));
}
document.querySelectorAll('.nav-item').forEach(b =>
  b.addEventListener('click', () => switchTab(b.dataset.tab)));
// 与后端 PROBE_METHODS 白名单保持一致（只读查询）
const PROBE_APIS = {
  job: ['get_script_list','get_script_version_list',
        'get_script_version_detail','get_job_instance_status'],
  cmdb: ['search_business','list_biz_hosts','search_host',
         'execute_dynamic_group','search_module','search_set',
         'search_object_attribute']
};
const PROBE_DEFAULTS = {
  'get_script_list': '{"limit": 10}',
  'get_script_version_list': '{"script_id": "脚本ID"}',
  'get_script_version_detail': '{"version_id": 1}',
  'get_job_instance_status': '{"job_instance_id": 1}',
  'search_business': '{"limit": 10}',
  'list_biz_hosts': '{"limit": 10}',
  'search_host': '{}',
  'execute_dynamic_group': '{"group_id": "分组ID"}',
  'search_module': '{"limit": 10}',
  'search_set': '{"limit": 10}',
  'search_object_attribute': '{"obj_id": "host"}'
};

function fillApis() {
  const t = $('p-target').value;
  $('p-api').innerHTML = PROBE_APIS[t].map(a =>
    `<option value="${a}">${a}</option>`).join('');
  $('p-params').value = PROBE_DEFAULTS[PROBE_APIS[t][0]] || '{}';
}
$('p-target').onchange = fillApis;
$('p-api').onchange = () => {
  $('p-params').value = PROBE_DEFAULTS[$('p-api').value] || '{}';
};

function drawTrend(items) {
  const c = $('trend'), ctx = c.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const cssW = c.clientWidth || 900;
  const cssH = 220;
  c.width = Math.round(cssW * dpr);
  c.height = Math.round(cssH * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const W = cssW, H = cssH, ox = 46, oy = 12,
        w = W - ox - 10, h = H - oy - 24;
  ctx.clearRect(0, 0, W, H);
  ctx.font = '11px Consolas';
  ctx.strokeStyle = '#e6eaf2'; ctx.fillStyle = '#999';
  [0, 50, 100].forEach(v => {
    const y = oy + h * (1 - v / 100);
    ctx.beginPath(); ctx.moveTo(ox, y); ctx.lineTo(ox + w, y); ctx.stroke();
    ctx.fillText(v + '%', 8, y + 4);
  });
  if (items.length < 2) {
    ctx.fillText('跑两次计划后这里出现通过率趋势', ox, oy + h / 2);
    return;
  }
  const step = w / (items.length - 1);
  ctx.strokeStyle = '#3a84ff'; ctx.lineWidth = 2;
  ctx.beginPath();
  items.forEach((it, i) => {
    const x = ox + i * step, y = oy + h * (1 - it.rate);
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  ctx.stroke();
  items.forEach((it, i) => {
    const x = ox + i * step, y = oy + h * (1 - it.rate);
    ctx.beginPath(); ctx.arc(x, y, 4, 0, 7);
    ctx.fillStyle = it.failed > 0 ? '#e5484d' : (it.skipped > 0 ? '#f79009' : '#2e9e5b');
    ctx.fill();
    if (i % 2 === 0) {
      ctx.fillStyle = '#666';
      ctx.fillText(it.passed, x - 6, y - 8);
      if (it.skipped > 0) {
        ctx.fillStyle = '#f79009';
        ctx.fillText('+'+it.skipped+'跳过', x + 6, y - 8);
      }
    }
  });
  ctx.fillStyle = '#999';
  ctx.fillText(items[0].ts, ox, H - 6);
  ctx.fillText(items[items.length - 1].ts, ox + w - 70, H - 6);
}

async function refreshStats() {
  const r = await fetch('/api/stats').then(x => x.json());
  $('n-total').textContent = r.total;
  $('n-unit').textContent = r.unit;
  $('n-env').textContent = r.env;
  $('n-report').textContent = r.reports.length;
  const tbody = $('reports').querySelector('tbody');
  tbody.innerHTML = r.reports.map(x =>
    `<tr><td><a href="${x.url}" target="_blank">${x.name}</a></td>` +
    `<td>${x.mtime}</td></tr>`).join('') || '<tr><td>暂无报告</td></tr>';
  $('report-hint').textContent = r.reports.length ?
    '点报告名在新标签页打开 HTML 报告' : '跑一次全量后这里会列出报告';
  const t = await fetch('/api/trend').then(x => x.json());
  drawTrend(t.items);
}
async function refreshGen() {
  const r = await fetch('/api/gen').then(x => x.json());
  $('gen-doc-count').textContent = r.apidoc_count;
  $('gen-model').textContent = r.model;
  $('gen-status').textContent = r.key_configured
    ? '✅ LLM_API_KEY 已配置，可生成用例草稿'
    : '⚠️ LLM_API_KEY 未配置（需 DeepSeek 开放平台申请），当前为展示性功能';
}
function setBusy(b) {
  $('b-run').disabled = b; $('plan').disabled = b;
}
async function run(plan) {
  setBusy(true);
  const out = $('out'); out.style.display = 'block'; out.textContent = '启动中…';
  $('summary').style.display = 'none';
  const url = '/api/run' + (plan !== 'full' ? '?plan=' + plan : '');
  const {task_id} = await fetch(url, {method: 'POST'}).then(x => x.json());
  const timer = setInterval(async () => {
    const s = await fetch('/api/run/' + task_id).then(x => x.json());
    out.textContent = s.output || '（等待输出…）';
    if (s.summary) { $('summary').style.display = 'block';
      $('summary').textContent = '结果：' + s.summary; }
    if (s.done) {
      clearInterval(timer);
      setBusy(false);
      out.textContent += '\n[完成] 返回码 ' + s.returncode;
      refreshStats();
    }
  }, 1500);
}
$('b-run').onclick = () => run($('plan').value);

$('p-go').onclick = async () => {
  const res = $('p-result');
  res.textContent = '调用中…';
  let params;
  try { params = JSON.parse($('p-params').value || '{}'); }
  catch (e) { res.textContent = '参数不是合法 JSON：' + e.message; return; }
  const body = {target: $('p-target').value, api: $('p-api').value, params};
  const r = await fetch('/api/probe', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)}).then(x => x.json());
  res.textContent = JSON.stringify(r, null, 2);
};
fillApis();
refreshStats();
refreshGen();
</script>
</body>
</html>
"""

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
