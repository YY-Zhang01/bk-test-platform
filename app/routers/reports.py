# -*- coding: utf-8 -*-
"""报告路由：列表 + 删除 + 文件返回。"""
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app import storage
from app.state import REPORTS_DIR, _list_reports

router = APIRouter()


@router.get('/api/reports')
def reports():
    """报告列表 + 通过率（按文件名时间戳关联 runs 表）。"""
    items = _list_reports()
    runs = storage.list_runs(200)
    by_stamp = {}
    for r in runs:
        stamp = (r['ts'] or '').replace('-', '').replace(':', '').replace(' ', '_')
        by_stamp[stamp] = r
    for item in items:
        stamp = item['name'].replace('report_', '').replace('.html', '')
        r = by_stamp.get(stamp)
        if r:
            item['rate'] = r['rate']
            item['passed'] = r['passed']
            item['failed'] = r['failed']
            item['skipped'] = r['skipped']
    return {'reports': items}


@router.delete('/api/reports/{filename}')
def delete_report(filename: str):
    """删除报告文件（白名单防目录穿越）。"""
    if not re.fullmatch(r'report_\d{8}_\d{6}\.html', filename) \
            and filename != 'latest.html':
        raise HTTPException(400, '非法报告文件名')
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, '报告不存在')
    path.unlink()
    return {'ok': True, 'deleted': filename}


@router.get('/report/{filename}')
def report_file(filename: str):
    """返回 reports/ 下的 HTML 报告（文件名白名单防目录穿越）。"""
    if not re.fullmatch(r'report_\d{8}_\d{6}\.html', filename) \
            and filename != 'latest.html':
        raise HTTPException(400, '非法报告文件名')
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, '报告不存在')
    return FileResponse(path, media_type='text/html')
