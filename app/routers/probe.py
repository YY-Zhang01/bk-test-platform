# -*- coding: utf-8 -*-
"""接口调试路由：只读调用 + 历史 + 参数说明。"""
from fastapi import APIRouter, HTTPException, Request

from app import storage
from app.state import BASE_DIR, PROBE_METHODS, _parse_api_doc

router = APIRouter()


@router.post('/api/probe')
async def probe(req: Request):
    """接口调试（Postman 式）：白名单内的只读方法可在线调用，返回原始 JSON。
    写操作一律拒绝。"""
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


@router.get('/api/probe/history')
def probe_history():
    """接口调试历史（最近 20 条），前端「历史请求」点击回填复用。"""
    return {'items': storage.list_probe_logs(20)}


@router.get('/api/probe/meta')
def probe_meta(target: str, api: str):
    """接口参数说明（从 apidoc/apidoc_cmdb 解析参数表），前端选接口时展示。"""
    for d in (BASE_DIR / 'docs' / 'apidoc', BASE_DIR / 'docs' / 'apidoc_cmdb'):
        f = d / f'{api}.md'
        if f.exists():
            return _parse_api_doc(f.read_text(encoding='utf-8'))
    return {'desc': '', 'params': []}
