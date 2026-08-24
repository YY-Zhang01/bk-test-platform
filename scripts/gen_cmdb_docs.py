# -*- coding: utf-8 -*-
"""一次性脚本：根据 cmdb_client.py 封装的接口，生成 CMDB 接口文档到 docs/apidoc_cmdb/。
供 AI 用例生成时给 CMDB 侧当"原料"（对齐 JOB 侧 docs/apidoc/）。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs' / 'apidoc_cmdb'

CMDB_DOCS = [
    {
        'name': 'search_business',
        'title': '查询业务列表',
        'desc': '查业务列表，可选按业务 ID 过滤。数据契约锚点：JOB 的 bk_scope_id 必须能在 CMDB 业务列表里找到，这是两系统所有联动的根。',
        'params': [
            ('bk_supplier_account', 'string', '是', '供应商账号（CC 组件历史参数，默认 0）'),
            ('bk_biz_id', 'int', '否', '业务 ID，传了则按业务过滤'),
            ('page', 'object', '否', '分页 {start, limit, sort}'),
        ],
    },
    {
        'name': 'list_biz_hosts',
        'title': '按业务查询主机',
        'desc': '按业务查主机列表。数据契约：主机 ID 字段是 bk_host_id，即 JOB 快速执行的 host_id 来源（两系统共用同一主机 ID）。',
        'params': [
            ('bk_supplier_account', 'string', '是', '供应商账号，默认 0'),
            ('bk_biz_id', 'int', '是', '业务 ID'),
            ('page', 'object', '否', '分页 {start, limit, sort}'),
            ('fields', 'list', '否', '要返回的字段列表'),
        ],
    },
    {
        'name': 'search_host',
        'title': '按条件查询主机',
        'desc': '按 host 模型条件查询主机，可返回主机完整属性。连块测用途：按 bk_host_id 查主机详情，验证主机当前是否可被 JOB 执行。',
        'params': [
            ('bk_supplier_account', 'string', '是', '供应商账号，默认 0'),
            ('bk_biz_id', 'int', '是', '业务 ID'),
            ('condition', 'list', '是', '查询条件，如 [{bk_obj_id:host, condition:[{field:bk_host_id, operator:$eq, value:主机ID}]}]'),
            ('page', 'object', '否', '分页 {start, limit, sort}'),
        ],
    },
    {
        'name': 'execute_dynamic_group',
        'title': '执行动态分组',
        'desc': '执行动态分组，返回分组"现在"圈中的主机。坑位：动态分组圈的主机是实时算出来的（按分组条件），不是快照，同一分组两次执行结果可以不同。连块测用途：先查分组圈了哪些主机，再让 JOB 执行这些主机，验证"CMDB 圈人 → JOB 干活"。',
        'params': [
            ('bk_supplier_account', 'string', '是', '供应商账号，默认 0'),
            ('bk_biz_id', 'int', '是', '业务 ID'),
            ('id', 'string', '是', 'CMDB 动态分组 ID'),
            ('page', 'object', '否', '分页 {start, limit, sort}'),
        ],
    },
    {
        'name': 'search_module',
        'title': '查询模块',
        'desc': '查业务下的模块（拓扑第 2 层，模块挂在集群下）。坑位：模块有 bk_set_id 指向所属集群，可校验"无主模块"（挂的集群不存在）。',
        'params': [
            ('bk_supplier_account', 'string', '是', '供应商账号，默认 0'),
            ('bk_biz_id', 'int', '是', '业务 ID'),
            ('page', 'object', '否', '分页 {start, limit, sort}'),
        ],
    },
    {
        'name': 'search_set',
        'title': '查询集群',
        'desc': '查业务下的集群（拓扑第 1 层，集群下挂模块）。用途：校验拓扑结构完整，集群-模块两层树无孤儿模块。',
        'params': [
            ('bk_supplier_account', 'string', '是', '供应商账号，默认 0'),
            ('bk_biz_id', 'int', '是', '业务 ID'),
            ('page', 'object', '否', '分页 {start, limit, sort}'),
        ],
    },
    {
        'name': 'search_object_attribute',
        'title': '查询模型属性',
        'desc': '查模型属性（字段字典）。用途：接口字段与页面对不上时查字典；也可做"字段变更回归"——上线前后比对字段集，发现模型字段被误改。核心字段 bk_host_id / bk_cloud_id 是 JOB 执行主机的最小契约。',
        'params': [
            ('bk_supplier_account', 'string', '是', '供应商账号，默认 0'),
            ('bk_obj_id', 'string', '是', '模型 ID，如 host（主机模型）'),
            ('page', 'object', '否', '分页 {start, limit, sort}'),
        ],
    },
]

OUT.mkdir(parents=True, exist_ok=True)
for d in CMDB_DOCS:
    lines = [
        f'# {d["title"]}',
        '',
        '## 功能描述',
        '',
        d['desc'],
        '',
        '## 请求参数',
        '',
        '| 字段 | 类型 | 必选 | 描述 |',
        '|---|---|---|---|',
    ]
    for p in d['params']:
        lines.append(f'| {p[0]} | {p[1]} | {p[2]} | {p[3]} |')
    (OUT / f"{d['name']}.md").write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'已写 {d["name"]}.md')

print(f'完成，共 {len(CMDB_DOCS)} 份 -> {OUT}')
