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
    """首页：返回 Vue build 的 index.html（前后端同源）。"""
    spa_index = DIST_DIR / 'index.html'
    if spa_index.exists():
        return FileResponse(spa_index)
    return HTMLResponse('<h2>前端未构建</h2><p>请先运行：cd frontend && npm run build</p>')


@app.get('/{full_path:path}')
def spa_fallback(full_path: str):
    """SPA 路由 fallback：Vue Router 的 history 模式，前端路由（/overview 等）
    刷新时回退到 index.html；API/报告路径不 fallback，返回 404。"""
    if full_path.startswith('api/') or full_path.startswith('report/'):
        raise HTTPException(404, '接口或报告不存在')
    spa_index = DIST_DIR / 'index.html'
    if spa_index.exists():
        return FileResponse(spa_index)
    raise HTTPException(404, '前端未构建')




if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
