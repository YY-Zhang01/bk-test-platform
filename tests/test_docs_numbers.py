# -*- coding: utf-8 -*-
"""文档数字自检：README 里的用例数字必须与代码实测一致。

为什么需要它：用例数是从 tests/ 里数出来的（不是写死的），每加一个
测试函数就 +1。如果改了代码忘了同步 README，这条测试会 fail，提醒去同步。
锁定 README 四处锚点（徽章 / 目录结构 / 能跑数 / 等账号数），全部动态算。
"""
from pathlib import Path

import pytest

from app.case_index import extract_cases

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.unit
def test_README用例数字与实测一致():
    cases = extract_cases()
    total = sum(c['count'] for c in cases)                 # 用例总数（参数化展开后）
    funcs = len(cases)                                     # 测试函数数
    unit = sum(c['count'] for c in cases if c['env'] == '否')  # 现在能跑的
    env = total - unit                                     # 等账号的

    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert f'Cases-{total}' in readme, \
        f'README 徽章应写 Cases-{total}（当前代码实测 {total} 个用例）'
    assert f'{total} 个 / {funcs} 函数' in readme, \
        f'README 目录结构应写 {total} 个 / {funcs} 函数'
    assert f'{unit} 个 unit 用例正常跑' in readme, \
        f'README 应写 {unit} 个 unit 用例正常跑'
    assert f'{env} 个环境层用例等账号激活' in readme, \
        f'README 应写 {env} 个环境层用例等账号激活'
