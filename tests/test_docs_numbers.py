# -*- coding: utf-8 -*-
"""文档一致性自检：README / 交接文档里的数字与结构描述必须和代码实测一致。

为什么需要它：用例数、Web 模块数、marker 数、测试文件数都是从代码里
数出来的（不是写死的）。改了代码忘了同步文档，这两条测试会 fail，提醒同步。

分两块：
- 数字自检：README 的用例总数 / 函数数 / 能跑数 / 等账号数
- 结构自检：README 的 Web 模块数 / marker 数 + 交接文档的测试文件数 / app 模块数
"""
from pathlib import Path

import pytest

from app.case_index import extract_cases

ROOT = Path(__file__).resolve().parent.parent
_CN = '零一二三四五六七八九'


def _cn(n):
    """阿拉伯数字转中文（1-19 够用，20+ 退回阿拉伯）。"""
    if n <= 9:
        return _CN[n]
    if n <= 19:
        return '十' + ('' if n == 10 else _CN[n - 10])
    return str(n)


def _count_markers(ini_text):
    """数 pytest.ini 里 markers 段注册的 marker 数。"""
    in_markers, count = False, 0
    for line in ini_text.splitlines():
        s = line.strip()
        if s == 'markers =':
            in_markers = True
            continue
        if in_markers:
            if not s or s.startswith('['):
                break
            if ':' in s and not s.startswith('#'):
                count += 1
    return count


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


@pytest.mark.unit
def test_文档结构描述与代码一致():
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    layout = (ROOT / 'frontend' / 'src' / 'layouts' / 'MainLayout.vue') \
        .read_text(encoding='utf-8')
    ini = (ROOT / 'pytest.ini').read_text(encoding='utf-8')

    # Web 平台导航模块数（Vue 前端 MainLayout 的 menus 数组项数）
    nav = layout.count("{ path: '")
    assert f'{_cn(nav)}模块' in readme, \
        f'README 应写「{_cn(nav)}模块」（前端侧栏实际 {nav} 个菜单）'

    # marker 注册数
    markers = _count_markers(ini)
    assert f'{markers} 个 marker' in readme, \
        f'README 应写 {markers} 个 marker（pytest.ini 实际注册 {markers} 个）'

    # 测试文件数 + app 模块数（交接文档里）
    test_files = len(list((ROOT / 'tests').glob('test_*.py')))
    app_modules = len([f for f in (ROOT / 'app').glob('*.py')
                       if f.name != '__init__.py'])
    handoff = (ROOT / 'docs' / '2026-08-23-job-test进度交接.md') \
        .read_text(encoding='utf-8')
    assert f'{test_files} 个测试文件' in handoff, \
        f'交接文档应写 {test_files} 个测试文件（tests/ 实际 {test_files} 个）'
    assert f'{app_modules} 个 py 模块' in handoff, \
        f'交接文档应写 {app_modules} 个 py 模块（app/ 实际 {app_modules} 个）'
