# -*- coding: utf-8 -*-
"""一次性脚本：把 tests/ 下所有用例提取成 CSV（Excel 可打开）。

列：文件 | 用例名 | 作用/设计原因 | 测试层级 | 是否等账号
"""
import ast
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / 'tests'
OUT = ROOT / 'docs' / '2026-08-23-用例清单.csv'

# 每个文件 -> (所属链路/维度, 是否环境层)
FILE_META = {
    'test_job_script.py':   ('JOB链路1·脚本管理', True),
    'test_job_fast_exec.py':('JOB链路2·快速执行', True),
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


def node_markers(node):
    """提取 @pytest.mark.xxx 和 @pytest.mark.parametrize(参数个数)。"""
    marks, params = [], []
    for d in node.decorator_list:
        # @pytest.mark.unit 这种（无括号，Attribute 形式）
        if isinstance(d, ast.Attribute) and isinstance(d.value, ast.Attribute) \
                and getattr(d.value, 'attr', '') == 'mark':
            marks.append(d.attr)
        # @pytest.mark.parametrize('x', [...]) 这种（Call 形式）
        elif isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) \
                and d.func.attr == 'parametrize' and len(d.args) >= 2 \
                and isinstance(d.args[1], (ast.List, ast.Tuple)):
            params.append(len(d.args[1].elts))
    return marks, params


rows = []
for f in sorted(TESTS.glob('test_*.py')):
    layer, env_default = FILE_META.get(f.name, ('其他', None))
    tree = ast.parse(f.read_text(encoding='utf-8'))
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name.startswith('test_')):
            continue
        doc = (ast.get_docstring(node) or '').strip()
        first = doc.split('\n')[0].strip()
        marks, params = node_markers(node)
        # 环境层判定：有用例级 @pytest.mark.unit → 不等账号；否则看文件级默认
        is_unit = 'unit' in marks
        if is_unit:
            env = '否'
        elif env_default is False:
            env = '否'
        else:
            env = '是'
        # parametrize 展开成多组时，在用例名后标注
        name = node.name
        if params:
            name += f' ×{params[0]}'
        rows.append([f.name, name, first, layer, ','.join(marks) or '-', env])

with open(OUT, 'w', encoding='utf-8-sig', newline='') as fp:
    w = csv.writer(fp)
    w.writerow(['文件', '用例名', '作用/设计原因', '所属层级/维度', 'marker', '是否等账号'])
    w.writerows(rows)

print(f'已生成 {len(rows)} 行 -> {OUT}')
