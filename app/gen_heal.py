# -*- coding: utf-8 -*-
"""AI 自愈闭环：生成 pytest 用例 → 自动跑 → 失败喂回 LLM 修 → 重试，参考 ghost。

与 gen_cases.py 的区别：
- gen_cases：一次性「文档 → LLM → 代码」，人工审阅
- gen_heal：闭环「生成 → collect 验证 → 真跑 → 拿错误喂回 → 修 → 重试 N 次」

诚实边界：没体验账号时，环境层用例跑出来是 skip（不是 fail），只能验证
「能收集 + 无 fail」；断言对不对要等账号。所以 final 区分三档：
- passed          = collect 通过 + 真跑无 fail
- collect_passed  = collect 通过，但跑起来没有可执行用例（全是 skip）
- failed          = 达到上限还没修好，转人工
"""
import subprocess
import sys
from pathlib import Path

from app.gen_cases import call_llm, load_docs, strip_code_fence

ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = ROOT / 'gen_cases'

COLLECT_TIMEOUT = 120
RUN_TIMEOUT = 240


def _collect(tmp_file: Path) -> tuple:
    """collect-only 验证：returncode 0 = 能收集（语法/import 正确）。"""
    cmd = [sys.executable, '-m', 'pytest', '--collect-only', '-q', str(tmp_file)]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                          text=True, timeout=COLLECT_TIMEOUT)
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]


def _run(tmp_file: Path) -> tuple:
    """真跑（--tb=short）：returncode 0 = 无 fail（skip 不算 fail）。"""
    cmd = [sys.executable, '-m', 'pytest', '--tb=short', '-q', str(tmp_file)]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                          text=True, timeout=RUN_TIMEOUT)
    out = (proc.stdout + proc.stderr)[-2000:]
    # 统计 fail 数，用于判断
    import re
    m = re.search(r'(\d+) failed', out)
    failed = int(m.group(1)) if m else 0
    return failed == 0, out


def _fix_code(code: str, error: str, api_key=None, base_url=None, model=None) -> str:
    """把错误喂回 LLM 让它修复，返回修复后的完整代码。"""
    prompt = (
        '你之前生成的 pytest 用例代码跑失败了，请修复后重新输出完整代码。\n\n'
        f'错误信息：\n{error}\n\n'
        f'当前代码：\n{code}\n\n'
        '要求：只输出修复后的 Python 代码，不要任何解释。'
    )
    return strip_code_fence(call_llm('_fix', prompt, api_key=api_key,
                                     base_url=base_url, model=model))


def heal(api_name: str, api_key=None, base_url=None, model=None,
         requirement=None, max_rounds: int = 3) -> dict:
    """自愈闭环主函数。返回 {ok, api_name, code, rounds, final}。"""
    docs = load_docs(api_name)
    if not docs:
        return {'ok': False, 'error': f'没找到含「{api_name}」的接口文档'}
    name, doc = docs[0]

    code = strip_code_fence(call_llm(name, doc, api_key=api_key, base_url=base_url,
                                     model=model, requirement=requirement))
    rounds = []

    TMP_DIR.mkdir(exist_ok=True)
    tmp_file = TMP_DIR / f'_heal_{name}.py'

    try:
        for i in range(1, max_rounds + 1):
            tmp_file.write_text(code + '\n', encoding='utf-8')

            # 第一步：collect 验证（语法 / import 错误）
            collect_ok, collect_out = _collect(tmp_file)
            if not collect_ok:
                rounds.append({'round': i, 'stage': 'collect', 'ok': False,
                               'output': collect_out})
                code = _fix_code(code, collect_out, api_key, base_url, model)
                continue

            # 第二步：真跑（无 fail 即通过，skip 不算 fail）
            run_ok, run_out = _run(tmp_file)
            if not run_ok:
                rounds.append({'round': i, 'stage': 'run', 'ok': False,
                               'output': run_out})
                code = _fix_code(code, run_out, api_key, base_url, model)
                continue

            # 成功了
            rounds.append({'round': i, 'stage': 'run', 'ok': True,
                           'output': run_out})
            # 判断是"真跑绿"还是"全 skip 没 fail"
            import re
            m = re.search(r'(\d+) passed', run_out)
            passed = int(m.group(1)) if m else 0
            final = 'passed' if passed > 0 else 'collect_passed'
            return {'ok': True, 'api_name': name, 'code': code,
                    'rounds': rounds, 'final': final}

        # 达到上限还没成功
        return {'ok': True, 'api_name': name, 'code': code,
                'rounds': rounds, 'final': 'failed'}
    finally:
        tmp_file.unlink(missing_ok=True)
