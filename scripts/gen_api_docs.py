# -*- coding: utf-8 -*-
"""一次性脚本：扫描客户端封装层的公开方法，生成 docs/API参考.md。

列：方法名 + 参数签名 + docstring 第一行（一句话作用）。
改完 api_client.py / cmdb_client.py 后重跑本脚本即可同步文档，不用手改。
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs' / 'API参考.md'

# (源文件, 类名, 一句话定位, 对应接口文档目录)
CLASSES = [
    ('app/api_client.py', 'JobClient',
     'JOB 作业平台客户端（ESB jobv3 组件）', 'docs/apidoc/'),
    ('app/cmdb_client.py', 'CmdbClient',
     'CMDB 配置平台客户端（ESB cc 组件）', 'docs/apidoc_cmdb/'),
]


def _sig(node):
    """函数签名参数串（去掉 self）。"""
    args = [a.arg for a in node.args.args if a.arg != 'self']
    return ', '.join(args)


def _scan(src_rel, cls_name):
    """扫描某个类下的公开方法，返回 [(name, sig, 一句话作用)]。"""
    path = ROOT / src_rel
    tree = ast.parse(path.read_text(encoding='utf-8'))
    methods = []
    for node in tree.body:
        if not (isinstance(node, ast.ClassDef) and node.name == cls_name):
            continue
        for m in node.body:
            if isinstance(m, ast.FunctionDef) and not m.name.startswith('_'):
                doc = (ast.get_docstring(m) or '').strip()
                first = doc.split('\n')[0].strip().rstrip('。')
                methods.append((m.name, _sig(m), first))
    return methods


def _render():
    lines = [
        '# API 参考（客户端封装层）',
        '',
        '> 本文件由 `scripts/gen_api_docs.py` 自动生成，改动客户端后重跑该脚本即可同步。',
        '> 每个方法的完整参数说明与示例见对应接口文档目录；参数名按官方文档整理，以体验环境实测为准。',
        '',
        '客户端都继承 `app/base_client.py` 的 `BaseClient`：统一拼 URL、带认证三件套、',
        '检查返回 `{result, code, message, data}`；差异只在组件名与少量额外参数。',
        '',
    ]
    for src_rel, cls_name, desc, doc_dir in CLASSES:
        methods = _scan(src_rel, cls_name)
        lines += [f'## {cls_name} — {desc}', '',
                  f'> 接口文档目录：`{doc_dir}`（{len(methods)} 个公开方法）', '',
                  '| 方法 | 参数 | 作用 |',
                  '|------|------|------|']
        for name, sig, first in methods:
            lines.append(f'| `{name}` | {sig} | {first} |')
        lines.append('')
    return '\n'.join(lines) + '\n'


def main():
    OUT.write_text(_render(), encoding='utf-8')
    total = sum(len(_scan(s, c)) for s, c, _, _ in CLASSES)
    print(f'已生成 {OUT}（{total} 个公开方法）')


if __name__ == '__main__':
    main()
