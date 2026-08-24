# -*- coding: utf-8 -*-
"""总览 / 趋势 / 用例库 路由。"""
from fastapi import APIRouter

from app import storage
from app.state import _stats

router = APIRouter()


@router.get('/api/stats')
def stats():
    """总览统计：总数 / unit 数 / 环境层数 / 报告列表。"""
    return _stats()


@router.get('/api/trend')
def trend():
    """历史执行趋势（SQLite 最近 20 条），供首页通过率折线图。"""
    return {'items': storage.list_runs(20)}


@router.get('/api/cases')
def cases():
    """用例库：按四大类分组返回全部用例（含优先级 + 最近执行状态）。"""
    from app.case_index import group_cases
    groups = group_cases()
    total_cases = sum(c['count'] for g in groups for c in g['cases'])
    total_funcs = sum(len(g['cases']) for g in groups)
    # 附上每个用例的最近执行状态（从 SQLite 读，持久化；去掉参数化后缀再匹配）
    status_map = storage.get_all_case_status()
    for g in groups:
        for c in g['cases']:
            base = c['name'].split(' ×')[0]
            c['status'] = status_map.get(base)
    return {
        'total': total_cases,
        'functions': total_funcs,
        'groups': groups,
    }
