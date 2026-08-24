# -*- coding: utf-8 -*-
"""用例索引：提取 tests/ 下所有用例的信息（名字、作用、层级、marker、是否等账号）。

供 Web 平台「用例库」页面 + scripts/export_cases.py 复用。
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / 'tests'

# 文件 -> (所属层级/维度, 是否环境层)
FILE_META = {
    'test_job_script.py':   ('JOB链路1·脚本管理', True),
    'test_job_fast_exec.py': ('JOB链路2·快速执行', True),
    'test_job_plan.py':     ('JOB链路3·作业编排', True),
    'test_job_cron.py':     ('JOB链路4·定时任务', True),
    'test_job_account.py':  ('JOB链路5·账号+高危', True),
    'test_job_file_sql.py': ('JOB链路6·文件+SQL', True),
    'test_cmdb_core.py':    ('CMDB链路', True),
    'test_integration.py':  ('L3连块测·数据契约', True),
    'test_job_boundary.py': ('专项·参数边界', None),
    'test_security.py':     ('专项·安全', None),
    'test_storage.py':      ('L1工具·存储', False),
    'test_webapp.py':       ('L1工具·Web平台层', False),
    'test_envs.py':         ('L1工具·多环境', False),
    'test_docs_numbers.py': ('L1工具·文档数字自检', False),
}


def _node_markers(node):
    marks, params = [], []
    for d in node.decorator_list:
        if isinstance(d, ast.Attribute) and isinstance(d.value, ast.Attribute) \
                and getattr(d.value, 'attr', '') == 'mark':
            marks.append(d.attr)
        elif isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) \
                and d.func.attr == 'parametrize' and len(d.args) >= 2 \
                and isinstance(d.args[1], (ast.List, ast.Tuple)):
            params.append(len(d.args[1].elts))
    return marks, params


def extract_cases() -> list:
    """返回 [{file, name, desc, layer, marker, env}]，env 为 '是'/'否'。"""
    rows = []
    for f in sorted(TESTS.glob('test_*.py')):
        layer, env_default = FILE_META.get(f.name, ('其他', None))
        tree = ast.parse(f.read_text(encoding='utf-8'))
        for node in tree.body:
            if not (isinstance(node, ast.FunctionDef) and node.name.startswith('test_')):
                continue
            doc = (ast.get_docstring(node) or '').strip()
            first = doc.split('\n')[0].strip()
            marks, params = _node_markers(node)
            is_unit = 'unit' in marks
            env = '否' if is_unit else ('否' if env_default is False else '是')
            name = node.name
            count = params[0] if params else 1
            if params:
                name += f' ×{params[0]}'
            # 优先级：安全 P0，端到端/边界 P1，其余 P2（从 marker 推断）
            if 'security' in marks:
                priority = 'P0'
            elif 'integration' in marks or 'boundary' in marks:
                priority = 'P1'
            else:
                priority = 'P2'
            rows.append({'file': f.name, 'name': name, 'desc': first,
                         'desc_full': doc, 'layer': layer,
                         'marker': ','.join(marks) or '-',
                         'env': env, 'count': count, 'priority': priority})
    return rows


def group_cases() -> list:
    """按四大类分组：L1 / L2 / L3 / 专项。返回 [{group, cases:[...]}]。"""
    groups = [
        ('L1 工具层（现在能跑）', []),
        ('L2 用例层（分开测，等账号）', []),
        ('L3 场景层（连块测，等账号）', []),
        ('专项横切（边界 + 安全）', []),
    ]
    for c in extract_cases():
        layer = c['layer']
        if layer.startswith('L1'):
            groups[0][1].append(c)
        elif layer.startswith('L3'):
            groups[2][1].append(c)
        elif layer.startswith('专项'):
            groups[3][1].append(c)
        else:
            groups[1][1].append(c)
    return [{'group': g, 'cases': cs} for g, cs in groups]
