# -*- coding: utf-8 -*-
"""测试平台 Web 后端入口（FastAPI）。

职责（瘦身后）：app 创建 + 登录拦截中间件 + 挂载各路由 + 托管前端 build 产物 + SPA fallback。
业务路由在 app/routers/ 下按模块拆分；共享状态/工具在 app/state.py。

运行：python app/web_app.py → 浏览器开 http://127.0.0.1:8000
"""
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# 项目根（web_app.py 在 app/ 下，CLI 直跑时 sys.path[0] 是 app/，
# 需要把根插入才能导入 app 包 + 定位 reports/ 等根级目录）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import storage  # noqa: E402
from app.state import DIST_DIR, PLATFORM_PASSWORD  # noqa: E402
from app.routers import auth, gen, probe, reports, run, stats, ui  # noqa: E402

# 一次性迁移：旧版 jsonl 历史数据搬进 SQLite（幂等，见 storage.migrate_jsonl）
storage.migrate_jsonl(Path(__file__).resolve().parent.parent / 'results_history.jsonl')

app = FastAPI(title='蓝鲸双系统端到端测试平台')

# Vue 前端静态资源：dist 存在就挂载 /assets（前后端同源托管）
if (DIST_DIR / 'assets').exists():
    app.mount('/assets', StaticFiles(directory=DIST_DIR / 'assets'), name='assets')


@app.middleware('http')
async def 登录拦截(request: Request, call_next):
    """token 认证：设了 PLATFORM_PASSWORD 才生效。
    放行：/api/login（登录接口）、/assets/*（静态资源）、非 API 路径（前端 SPA 自己判断登录态）。
    拦截：其他 /api/* 和 /report/*（需要 Bearer token）。
    token 存 SQLite（storage.sessions），服务重启登录态不丢。"""
    if not PLATFORM_PASSWORD:
        return await call_next(request)
    path = request.url.path
    if path == '/api/login' or path.startswith('/assets/'):
        return await call_next(request)
    if path.startswith('/api/') or path.startswith('/report/'):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:] if auth_header.startswith('Bearer ') else ''
        # 报告文件用 window.open 打开，新标签页不带 Authorization 头，
        # 改从 URL 的 ?token= 参数读（前端打开报告时带上）
        if not token and path.startswith('/report/'):
            token = request.query_params.get('token', '')
        if storage.has_session(token):
            return await call_next(request)
        return JSONResponse(status_code=401, content={'detail': '未登录'})
    return await call_next(request)


# 挂载业务路由
app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(run.router)
app.include_router(probe.router)
app.include_router(gen.router)
app.include_router(reports.router)
app.include_router(ui.router)


@app.get('/')
def index():
    """首页：优先返回 Vue build 的 index.html（前后端同源），否则回退旧内嵌 HTML。"""
    spa_index = DIST_DIR / 'index.html'
    if spa_index.exists():
        return FileResponse(spa_index)
    return HTMLResponse(INDEX_HTML)


@app.get('/{full_path:path}')
def spa_fallback(full_path: str):
    """SPA 路由 fallback：Vue Router 的 history 模式，前端路由（/overview 等）
    刷新时回退到 index.html；API/报告路径不 fallback，返回 404。"""
    if full_path.startswith('api/') or full_path.startswith('report/'):
        raise HTTPException(404, '接口或报告不存在')
    spa_index = DIST_DIR / 'index.html'
    if spa_index.exists():
        return FileResponse(spa_index)
    return HTMLResponse(INDEX_HTML)


# 旧内嵌 HTML（Vue 前端 build 产物不存在时的回退，正常部署用不上）
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
  .cards { display: flex; gap: 14px; flex-wrap: wrap; position: relative; }
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
           transition: filter .15s, transform .1s, opacity .15s, background .15s; }
  button:hover:not(:disabled) { filter: brightness(1.08); }
  button:active:not(:disabled) { transform: scale(.97); }
  button:disabled { opacity: .45; cursor: not-allowed; }
  .b-all { background: linear-gradient(135deg, #1d4ed8, #2f54eb);
           box-shadow: 0 4px 12px rgba(47,84,235,.32); }
  .b-unit { background: #fff; color: var(--blue); border: 1px solid #c7d4f5; }
  .b-unit:hover:not(:disabled) { background: #f5f8ff; filter: none; }
  #out, #p-result { background: #0d1117; font-family: Consolas, "Courier New",
             monospace; font-size: 12px; padding: 14px 16px; border-radius: 10px;
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
  canvas { display: block; width: 100%; height: 300px; }
  .gen-flow { display: flex; align-items: center; gap: 8px; margin: 16px 0;
              flex-wrap: wrap; }
  .gen-step { background: #f0f4ff; color: var(--blue); border-radius: 8px;
              padding: 8px 14px; font-size: 13px; }
  .gen-arrow { color: var(--weak); }
  .gen-title { font-size: 14px; font-weight: 600; margin: 18px 0 10px; color: var(--ink); }
  .gen-sample { background: #0d1117; color: #7ee2a8; font-family: Consolas,
                "Courier New", monospace; font-size: 12px; padding: 14px 16px;
                border-radius: 10px; overflow: auto; white-space: pre; line-height: 1.6; }
  input { border: 1px solid #d4dcec; border-radius: 8px; padding: 9px 14px;
          font-size: 13px; background: #fff; color: var(--ink);
          outline: none; transition: border-color .15s; }
  input:focus { border-color: var(--blue); }
  .case-group { margin-bottom: 18px; }
  .case-group-title { font-size: 14px; font-weight: 600; margin-bottom: 8px;
                      color: var(--ink); cursor: pointer; user-select: none; }
  .case-group-title:hover { color: var(--blue); }
  .case-item { border: 1px solid var(--line); border-radius: 8px;
               padding: 10px 14px; margin-bottom: 6px; background: #fafbff; }
  .case-name { font-size: 13px; font-weight: 500; color: var(--ink); }
  .case-desc { font-size: 12px; color: var(--sub); margin-top: 2px; }
  .layout { flex: 1; display: flex; align-items: stretch; min-height: 0; }
  .sidebar { width: 200px; flex-shrink: 0; background: #0f1c4d;
             padding: 16px 0; display: flex; flex-direction: column; gap: 2px; }
  .nav-item { text-align: left; background: transparent; color: rgba(255,255,255,.72);
              border: none; border-radius: 8px; margin: 0 10px; padding: 12px 16px;
              font-size: 14px; cursor: pointer; font-weight: 500;
              display: flex; align-items: center; gap: 10px; }
  .nav-item:hover:not(:disabled) { filter: none; background: rgba(255,255,255,.1); color: #fff; }
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
  <button class="nav-item" data-tab="cases"><span class="ico">☷</span>用例库</button>
</aside>
<main class="content">
  <div class="tab-panel" id="tab-overview">
  <div class="cards">
    <div class="card"><div class="c-ico" style="background:#e8efff;color:#2f54eb">▦</div>
      <div><div class="num" id="n-total">-</div><div class="label">用例总数</div></div></div>
    <div class="card"><div class="c-ico" style="background:#e7f9f0;color:#12b76a">✓</div>
      <div><div class="num" id="n-unit">-</div><div class="label">unit（不等账号可跑）</div></div></div>
    <div class="card"><div class="c-ico" style="background:#fff4e5;color:#f79009">⏳</div>
      <div><div class="num" id="n-env">-</div><div class="label">环境层（等账号激活）</div></div></div>
    <div class="card"><div class="c-ico" style="background:#f0ecff;color:#7a5af8">▤</div>
      <div><div class="num" id="n-report">-</div><div class="label">历史报告</div></div></div>
  </div>
  <section><h2>执行趋势（已执行用例通过率 · 最近 20 次）</h2>
    <canvas id="trend" width="900" height="300"></canvas></section>
  <section><h2>测试分层（对齐 HttpRunner：API 层 → 用例层 → 场景层）</h2>
    <div class="pyramid">
      <div class="layer l3">L3 场景层 integration：契约 / 联动 / 反向（跨系统）</div>
      <div class="layer l2">L2 用例层：JOB 六链路 + CMDB 独立链路（单系统分开测）</div>
      <div class="layer l1">L1 API 层 unit：客户端封装与拼参自洽（不依赖环境）</div>
    </div></section>
  <section><h2>全方位测试五大维度（功能 / 性能 / 安全 / 边界 / 端到端）</h2>
    <div class="dims">
      <div class="dim"><div class="d-t">功能</div><div class="d-s">JOB 6 链路 + CMDB · 111 用例</div><span class="tag ok">已落地</span></div>
      <div class="dim"><div class="d-t">边界</div><div class="d-s">等价类 / 边界值 / 非法值</div><span class="tag ok">已落地</span></div>
      <div class="dim"><div class="d-t">端到端</div><div class="d-s">两系统联动 · 数据契约是其中一环</div><span class="tag wait">待账号</span></div>
      <div class="dim"><div class="d-t">性能</div><div class="d-s">Locust 只读压测</div><span class="tag wait">待账号</span></div>
      <div class="dim"><div class="d-t">安全</div><div class="d-s">鉴权 / 越权 / 注入 / 高危</div><span class="tag wait">待账号</span></div>
    </div></section>
  </div>
  <div class="tab-panel hidden" id="tab-run">
  <section><h2>一键跑测试（测试计划）</h2>
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
    <pre id="out"></pre><div id="summary"></div></section>
  </div>
  <div class="tab-panel hidden" id="tab-probe">
  <section><h2>接口调试（Postman 式，只读白名单）</h2>
    <div class="btns">
      <select id="p-target"><option value="job">JOB</option><option value="cmdb">CMDB</option></select>
      <select id="p-api"></select>
      <button class="b-unit" id="p-go">调用</button>
    </div>
    <textarea id="p-params" rows="3" placeholder='JSON 参数，如 {"limit": 10}'></textarea>
    <pre id="p-result">尚未调用。选好接口、填好参数，点"调用"。</pre></section>
  </div>
  <div class="tab-panel hidden" id="tab-reports">
  <section><h2>历史报告</h2>
    <table id="reports"><tbody></tbody></table>
    <div class="hint" id="report-hint"></div></section>
  </div>
  <div class="tab-panel hidden" id="tab-gen">
  <section><h2>AI 用例生成（gen_cases.py）</h2>
    <p>人设：<b>蓝鲸 JOB 接口测试专家</b>——把 <span id="gen-doc-count">-</span> 份接口文档转成 pytest 用例草稿。粘贴你的大模型密钥，选接口生成，审阅后选择是否并入正式目录。</p>
    <div class="btns" style="margin-bottom:10px;">
      <input type="password" id="gen-key" placeholder="粘贴 LLM API Key（如 DeepSeek）" style="flex:1;min-width:260px;">
    </div>
    <div class="btns" style="margin-bottom:10px;"><select id="gen-api" style="flex:1;min-width:220px;"></select></div>
    <textarea id="gen-req" rows="2" placeholder="需求描述（可选），如：多生成负面用例、重点测超时和 Base64"></textarea>
    <div class="btns" style="margin-top:10px;">
      <button class="b-all" id="gen-go">生成草稿</button>
      <button class="b-unit" id="gen-validate" disabled>验证可收集</button>
      <button class="b-unit" id="gen-approve" disabled>✓ 并入 tests/</button>
    </div>
    <div id="gen-msg" class="hint" style="margin:12px 0;"></div>
    <pre id="gen-code" class="gen-sample" style="display:none;max-height:420px;">生成的草稿会显示在这里</pre>
    <p class="hint" id="gen-status" style="margin-top:10px;">加载中…</p></section>
  </div>
  <div class="tab-panel hidden" id="tab-cases">
  <section><h2>用例库（<span id="case-total">-</span> 个用例）</h2>
    <div class="btns" style="margin-bottom:14px;">
      <input type="text" id="case-search" placeholder="搜索用例名 / 作用" style="flex:1;min-width:200px;">
      <select id="case-filter" style="min-width:140px;">
        <option value="all">全部</option><option value="可跑">只看可跑</option><option value="等账号">只看等账号</option>
      </select>
    </div>
    <div id="case-groups"></div></section>
  </div>
</main>
</div>
<script>
const $ = id => document.getElementById(id);
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('hidden', p.id !== 'tab-' + name));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
}
document.querySelectorAll('.nav-item').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));
const PROBE_APIS = {
  job: ['get_script_list','get_script_version_list','get_script_version_detail','get_job_instance_status'],
  cmdb: ['search_business','list_biz_hosts','search_host','execute_dynamic_group','search_module','search_set','search_object_attribute']
};
const PROBE_DEFAULTS = {
  'get_script_list': '{"limit": 10}', 'get_script_version_list': '{"script_id": "脚本ID"}',
  'get_script_version_detail': '{"version_id": 1}', 'get_job_instance_status': '{"job_instance_id": 1}',
  'search_business': '{"limit": 10}', 'list_biz_hosts': '{"limit": 10}', 'search_host': '{}',
  'execute_dynamic_group': '{"group_id": "分组ID"}', 'search_module': '{"limit": 10}',
  'search_set': '{"limit": 10}', 'search_object_attribute': '{"obj_id": "host"}'
};
function fillApis() {
  const t = $('p-target').value;
  $('p-api').innerHTML = PROBE_APIS[t].map(a => `<option value="${a}">${a}</option>`).join('');
  $('p-params').value = PROBE_DEFAULTS[PROBE_APIS[t][0]] || '{}';
}
$('p-target').onchange = fillApis;
$('p-api').onchange = () => { $('p-params').value = PROBE_DEFAULTS[$('p-api').value] || '{}'; };
function drawTrend(items) {
  const c = $('trend'), ctx = c.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const cssW = c.clientWidth || 900, cssH = 300;
  c.width = Math.round(cssW * dpr); c.height = Math.round(cssH * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const W = cssW, H = cssH, ox = 50, oy = 30, w = W - ox - 46, h = H - oy - 30;
  ctx.clearRect(0, 0, W, H);
  ctx.font = '11px Consolas'; ctx.strokeStyle = '#e6eaf2'; ctx.fillStyle = '#999';
  [0, 50, 100].forEach(v => {
    const y = oy + h * (1 - v / 100);
    ctx.beginPath(); ctx.moveTo(ox, y); ctx.lineTo(ox + w, y); ctx.stroke();
    ctx.fillText(v + '%', 8, y + 4);
  });
  if (items.length < 2) { ctx.fillText('跑两次计划后这里出现通过率趋势', ox, oy + h / 2); return; }
  const step = w / (items.length - 1);
  ctx.strokeStyle = '#3a84ff'; ctx.lineWidth = 2; ctx.beginPath();
  items.forEach((it, i) => { const x = ox + i * step, y = oy + h * (1 - it.rate); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.stroke();
  items.forEach((it, i) => {
    const x = ox + i * step, y = oy + h * (1 - it.rate);
    ctx.beginPath(); ctx.arc(x, y, 4, 0, 7);
    ctx.fillStyle = it.failed > 0 ? '#e5484d' : (it.skipped > 0 ? '#f79009' : '#2e9e5b'); ctx.fill();
    if (i % 2 === 0) {
      ctx.fillStyle = '#666'; ctx.fillText(it.passed, x - 6, y - 8);
      if (it.skipped > 0) { ctx.fillStyle = '#f79009'; ctx.fillText('+'+it.skipped+'跳过', x + 6, y - 8); }
    }
  });
  ctx.fillStyle = '#999'; ctx.fillText(items[0].ts, ox, H - 6);
  ctx.fillText(items[items.length - 1].ts, ox + w - 70, H - 6);
}
async function refreshStats() {
  const r = await fetch('/api/stats').then(x => x.json());
  $('n-total').textContent = r.total; $('n-unit').textContent = r.unit;
  $('n-env').textContent = r.env; $('n-report').textContent = r.reports.length;
  const tbody = $('reports').querySelector('tbody');
  tbody.innerHTML = r.reports.map(x => `<tr><td><a href="${x.url}" target="_blank">${x.name}</a></td><td>${x.mtime}</td></tr>`).join('') || '<tr><td>暂无报告</td></tr>';
  $('report-hint').textContent = r.reports.length ? '点报告名在新标签页打开 HTML 报告' : '跑一次全量后这里会列出报告';
  const t = await fetch('/api/trend').then(x => x.json());
  drawTrend(t.items);
}
async function refreshGen() {
  const r = await fetch('/api/gen').then(x => x.json());
  $('gen-doc-count').textContent = r.apidoc_count;
  $('gen-api').innerHTML = r.apis.map(a => `<option value="${a}">${a}</option>`).join('');
  $('gen-status').textContent = r.key_configured ? '✅ 已配置默认 key，可直接生成' : '⚠️ 默认 key 未配置：请粘贴密钥';
}
let caseData = [];
async function refreshCases() {
  caseData = await fetch('/api/cases').then(x => x.json());
  $('case-total').textContent = caseData.total; renderCases();
}
function renderCases() {
  const kw = ($('case-search').value || '').trim().toLowerCase();
  const filter = $('case-filter').value;
  $('case-groups').innerHTML = caseData.groups.map(g => {
    const cases = g.cases.filter(c => {
      const okKw = !kw || c.name.toLowerCase().includes(kw) || (c.desc || '').toLowerCase().includes(kw);
      const okFilter = filter === 'all' || (filter === '可跑' ? c.env === '否' : c.env === '是');
      return okKw && okFilter;
    });
    if (cases.length === 0) return '';
    const items = cases.map(c => `<div class="case-item"><div class="case-name">${c.name} ` +
      (c.env === '是' ? '<span class="tag wait">等账号</span>' : '<span class="tag ok">可跑</span>') +
      `</div><div class="case-desc">${c.desc || ''}</div></div>`).join('');
    return `<div class="case-group"><div class="case-group-title" onclick="toggleGroup(this)">▸ ${g.group}（${cases.length}）</div><div class="case-group-body" style="display:none">${items}</div></div>`;
  }).join('');
}
function toggleGroup(el) {
  const body = el.nextElementSibling;
  const open = body.style.display === 'none';
  body.style.display = open ? 'block' : 'none';
  el.textContent = (open ? '▾ ' : '▸ ') + el.textContent.replace(/^[▸▾] /, '');
}
$('case-search').oninput = renderCases; $('case-filter').onchange = renderCases;
let genLastApi = ''; let genValidated = false;
$('gen-go').onclick = async () => {
  const apiKey = $('gen-key').value.trim(); const apiName = $('gen-api').value.trim();
  if (!apiKey) { $('gen-msg').textContent = '请先粘贴你的大模型密钥'; return; }
  if (!apiName) { $('gen-msg').textContent = '请填接口名'; return; }
  $('gen-msg').textContent = '生成中…（调大模型，可能要十几秒）';
  const r = await fetch('/api/gen/generate', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({api_key: apiKey, api_name: apiName, requirement: $('gen-req').value.trim()})}).then(x => x.json());
  if (r.ok) { genLastApi = r.api_name; genValidated = false; $('gen-code').textContent = r.code;
    $('gen-code').style.display = 'block'; $('gen-msg').textContent = '✅ 生成成功。请先点「验证可收集」。';
    $('gen-validate').disabled = false; $('gen-approve').disabled = true; }
  else { $('gen-msg').textContent = '❌ ' + r.error; $('gen-code').style.display = 'none';
    $('gen-validate').disabled = true; $('gen-approve').disabled = true; }
};
$('gen-validate').onclick = async () => {
  const code = $('gen-code').textContent; if (!genLastApi || !code) return;
  $('gen-msg').textContent = '验证中…';
  const r = await fetch('/api/gen/validate', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({api_name: genLastApi, code: code})}).then(x => x.json());
  if (r.ok && r.collected) { genValidated = true; $('gen-approve').disabled = false; $('gen-msg').textContent = '✅ 验证通过。'; }
  else { genValidated = false; $('gen-approve').disabled = true; $('gen-msg').textContent = '❌ 验证失败：\n' + (r.output || r.error); }
};
$('gen-approve').onclick = async () => {
  const code = $('gen-code').textContent; if (!genLastApi || !code) return;
  if (!genValidated) { $('gen-msg').textContent = '请先点「验证可收集」。'; return; }
  const r = await fetch('/api/gen/approve', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({api_name: genLastApi, code: code})}).then(x => x.json());
  $('gen-msg').textContent = r.ok ? '✅ 已并入：' + r.saved : '❌ ' + r.error;
};
function setBusy(b) { $('b-run').disabled = b; $('plan').disabled = b; }
async function run(plan) {
  setBusy(true); const out = $('out'); out.style.display = 'block'; out.textContent = '启动中…';
  $('summary').style.display = 'none';
  const url = '/api/run' + (plan !== 'full' ? '?plan=' + plan : '');
  const {task_id} = await fetch(url, {method: 'POST'}).then(x => x.json());
  const timer = setInterval(async () => {
    const s = await fetch('/api/run/' + task_id).then(x => x.json());
    out.textContent = s.output || '（等待输出…）';
    if (s.summary) { $('summary').style.display = 'block'; $('summary').textContent = '结果：' + s.summary; }
    if (s.done) { clearInterval(timer); setBusy(false);
      out.textContent += '\n[完成] 返回码 ' + s.returncode; refreshStats(); }
  }, 1500);
}
$('b-run').onclick = () => run($('plan').value);
$('p-go').onclick = async () => {
  const res = $('p-result'); res.textContent = '调用中…';
  let params; try { params = JSON.parse($('p-params').value || '{}'); }
  catch (e) { res.textContent = '参数不是合法 JSON：' + e.message; return; }
  const body = {target: $('p-target').value, api: $('p-api').value, params};
  const r = await fetch('/api/probe', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)}).then(x => x.json());
  res.textContent = JSON.stringify(r, null, 2);
};
fillApis(); refreshStats(); refreshGen(); refreshCases();
</script>
</body>
</html>
"""


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
