# -*- coding: utf-8 -*-
"""AI 用例生成路由：生成 / 自愈 / 验证 / 并入 / 历史。"""
import re
import subprocess
import sys

from fastapi import APIRouter, HTTPException, Request

from app.state import (BASE_DIR, GEN_HISTORY_DIR, _gen_rate_ok,
                       _save_gen_history)

router = APIRouter()


@router.get('/api/gen')
def gen_info():
    """AI 用例生成的状态与说明。"""
    from app import job_config
    dirs = [BASE_DIR / 'docs' / 'apidoc', BASE_DIR / 'docs' / 'apidoc_cmdb']
    apis = []
    for d in dirs:
        if d.exists():
            apis.extend(sorted(p.stem for p in d.glob('*.md')))
    apis = sorted(apis)
    return {
        'key_configured': bool(job_config.LLM_API_KEY),
        'model': job_config.LLM_MODEL or 'deepseek-chat',
        'apidoc_count': len(apis),
        'apis': apis,
        'usage': 'python gen_cases.py  # 为 apidoc/apidoc_cmdb 里全部接口生成用例草稿',
    }


@router.get('/api/gen/history')
def gen_history():
    """生成历史（最近 20 条，含草稿内容，前端点击加载回溯）。"""
    items = []
    for f in sorted(GEN_HISTORY_DIR.glob('*.py'), reverse=True)[:20]:
        items.append({
            'file': f.name,
            'api': f.stem.rsplit('_', 1)[-1],
            'ts': f.stem.rsplit('_', 1)[0] if '_' in f.stem else '',
            'code': f.read_text(encoding='utf-8'),
        })
    return {'items': items}


@router.post('/api/gen/generate')
async def gen_generate(req: Request):
    """接口名 → 调大模型生成用例草稿（key 走服务端配置，前端不传）。"""
    if not _gen_rate_ok(req.client.host if req.client else 'unknown'):
        raise HTTPException(429, 'AI 生成太频繁，请稍后再试（每分钟限 8 次）')
    from app import job_config
    body = await req.json()
    api_key = (body.get('api_key') or '').strip() or job_config.LLM_API_KEY
    if not api_key:
        return {'ok': False, 'error': '未配置 LLM_API_KEY：请在服务端 job_config_local.py 配置'}
    api_name = (body.get('api_name') or '').strip()
    from app.gen_cases import call_llm, load_docs, strip_code_fence
    docs = load_docs(api_name)
    if not docs:
        return {'ok': False, 'error': f'没找到含「{api_name}」的接口文档（docs/apidoc/）'}
    name, doc = docs[0]
    try:
        code = strip_code_fence(call_llm(
            name, doc, api_key=api_key,
            base_url=body.get('base_url') or None,
            model=body.get('model') or None,
            requirement=(body.get('requirement') or '').strip() or None))
        _save_gen_history(name, code)
        return {'ok': True, 'api_name': name, 'code': code}
    except Exception as e:
        return {'ok': False, 'error': f'生成失败：{e}'}


@router.post('/api/gen/approve')
async def gen_approve(req: Request):
    """审阅通过后，把草稿写入 tests/ 目录（test_接口名_ai.py）。"""
    body = await req.json()
    api_name = (body.get('api_name') or '').strip()
    code = body.get('code') or ''
    if not api_name or not code:
        return {'ok': False, 'error': '接口名和草稿内容不能为空'}
    if not re.fullmatch(r'[a-z0-9_]+', api_name):
        return {'ok': False, 'error': '接口名不合法'}
    out_dir = BASE_DIR / 'tests'
    out_dir.mkdir(exist_ok=True)
    filename = f'test_{api_name}_ai.py'
    header = (f'# -*- coding: utf-8 -*-\n'
              f'# AI 生成的用例草稿（接口 {api_name}），已通过 pytest 收集验证。\n'
              f'# 断言与清理逻辑仍需人工复核。\n')
    (out_dir / filename).write_text(header + code + '\n', encoding='utf-8')
    return {'ok': True, 'saved': f'tests/{filename}'}


@router.post('/api/gen/validate')
async def gen_validate(req: Request):
    """验证草稿能否被 pytest 收集（临时写文件跑 --collect-only）。"""
    body = await req.json()
    api_name = (body.get('api_name') or '').strip()
    code = body.get('code') or ''
    if not api_name or not code:
        return {'ok': False, 'error': '接口名和草稿内容不能为空'}
    if not re.fullmatch(r'[a-z0-9_]+', api_name):
        return {'ok': False, 'error': '接口名不合法'}
    tmp_dir = BASE_DIR / 'gen_cases'
    tmp_dir.mkdir(exist_ok=True)
    tmp_file = tmp_dir / f'_validate_{api_name}.py'
    tmp_file.write_text(code + '\n', encoding='utf-8')
    try:
        cmd = [sys.executable, '-m', 'pytest', '--collect-only', '-q', str(tmp_file)]
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True,
                              text=True, timeout=120)
        out = (proc.stdout + proc.stderr)[-800:]
        if proc.returncode == 0:
            return {'ok': True, 'collected': True, 'output': out}
        return {'ok': True, 'collected': False, 'output': out}
    finally:
        tmp_file.unlink(missing_ok=True)


@router.post('/api/gen/heal')
async def gen_heal(req: Request):
    """AI 自愈闭环（参考 ghost）：生成 → collect 验证 → 真跑 → 失败喂回修 → 重试。"""
    if not _gen_rate_ok(req.client.host if req.client else 'unknown'):
        raise HTTPException(429, 'AI 生成太频繁，请稍后再试（每分钟限 8 次）')
    from app import job_config
    from app.gen_heal import heal
    body = await req.json()
    api_key = (body.get('api_key') or '').strip() or job_config.LLM_API_KEY
    if not api_key:
        return {'ok': False, 'error': '未配置 LLM_API_KEY：请在服务端 job_config_local.py 配置'}
    api_name = (body.get('api_name') or '').strip()
    if not api_name:
        return {'ok': False, 'error': '请先选择接口'}
    max_rounds = int(body.get('max_rounds') or 3)
    max_rounds = max(1, min(max_rounds, 5))
    try:
        result = heal(api_name, api_key=api_key,
                      base_url=body.get('base_url') or None,
                      model=body.get('model') or None,
                      requirement=(body.get('requirement') or '').strip() or None,
                      max_rounds=max_rounds)
        if result.get('ok') and result.get('code'):
            _save_gen_history(result.get('api_name', api_name), result['code'])
        return result
    except Exception as e:
        return {'ok': False, 'error': f'自愈失败：{e}'}
