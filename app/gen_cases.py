# -*- coding: utf-8 -*-
"""AI 用例生成器：把 apidoc 接口文档喂给大模型，自动产出 pytest 用例草稿。

平台模块之一（阶段0 交付）：解决"接口多、手写用例慢"的问题。
生成的草稿只做骨架，需人工审阅后才能并入正式用例目录。

用法：
    python gen_cases.py                        # 为 apidoc 里全部接口生成草稿
    python gen_cases.py -i fast_execute_script # 只生成指定接口
    python gen_cases.py --collect              # 生成后跑 pytest --collect-only 验证

依赖：job_config.py 里的 LLM_API_KEY（DeepSeek 开放平台申请）。
没配 key 时打印获取指引后退出，不报错不炸。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import requests

# CLI 直跑时 sys.path[0] 是 app/，把项目根插入才能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import job_config

ROOT = Path(__file__).resolve().parent.parent
APIDOC_DIR = ROOT / 'docs' / 'apidoc'
APIDOC_CMDB_DIR = ROOT / 'docs' / 'apidoc_cmdb'
OUT_DIR = ROOT / 'gen_cases'

# 用例风格规范：喂给大模型的"写作要求"
STYLE_RULES = """
生成的 pytest 用例必须遵守项目风格：
1. 模块 docstring 说明这条链路的故事（对应 Web 端哪个页面、什么操作顺序）
2. 测试函数名用中文，格式 test_动作_断言目标，如 test_建脚本_列表能查到且内容自洽
3. 导入必须用 app 包完整路径：`from app.api_client import JobClient, JobError, b64_encode`、
   `from app.cmdb_client import CmdbClient, CmdbError`、`import pytest`。禁止写 `from api_client import`、`from conftest import`。
4. 依赖 job_client / cmdb_client fixture（conftest.py 已提供，作为测试函数参数直接用），数据自建自清
5. 每个用例 docstring 写"对应手动步骤"，把坑位写进注释
6. 接口参数按文档给的类型和必填项传，content/param 需要 Base64（用 api_client 的 b64_encode）
7. 断言要具体：查回的数据和传进去的数据自洽（内容、状态码、字段）
8. 负面用例用 pytest.raises(JobError)
9. 未配置锚点数据时用 pytest.skip 跳过，不造假绿
10. 只输出 Python 代码，不要任何解释
""".strip()


def load_docs(api_filter: str) -> list:
    """读 apidoc（JOB）+ apidoc_cmdb（CMDB）目录，返回 [(接口名, 文档内容)]。"""
    docs = []
    for d in (APIDOC_DIR, APIDOC_CMDB_DIR):
        if not d.exists():
            continue
        for md in sorted(d.glob('*.md')):
            name = md.stem
            if api_filter and api_filter not in name:
                continue
            content = md.read_text(encoding='utf-8')
            docs.append((name, content))
    return docs


def call_llm(api_name: str, doc: str, api_key: str = None,
             base_url: str = None, model: str = None,
             requirement: str = None) -> str:
    """调 OpenAI 兼容接口生成用例代码。

    api_key / base_url / model 可显式传入（网页粘贴的 key），
    不传则回落到 job_config 的默认配置；requirement 是额外需求描述。
    """
    key = api_key or job_config.LLM_API_KEY
    url = f"{(base_url or job_config.LLM_BASE_URL).rstrip('/')}/chat/completions"
    headers = {'Authorization': f'Bearer {key}'}
    user_content = f'接口名：{api_name}\n接口文档如下：\n{doc}'
    if requirement:
        user_content += f'\n\n额外需求：{requirement}'
    body = {
        'model': model or job_config.LLM_MODEL,
        'messages': [
            {'role': 'system',
             'content': f'你是蓝鲸作业平台(JOB)接口测试专家。根据接口文档生成 pytest 用例草稿。{STYLE_RULES}'},
            {'role': 'user',
             'content': user_content},
        ],
    }
    resp = requests.post(url, json=body, headers=headers, timeout=120)
    resp.raise_for_status()
    payload = resp.json()
    return payload['choices'][0]['message']['content']


def strip_code_fence(text: str) -> str:
    """去掉大模型常包的 ```python ``` 围栏。"""
    m = re.search(r'```(?:python)?\s*\n(.*?)```', text, re.DOTALL)
    return m.group(1) if m else text


def main():
    parser = argparse.ArgumentParser(description='AI 用例生成器（JOB 测试平台模块）')
    parser.add_argument('-i', '--interface', default='', help='只生成指定接口（文件名片段）')
    parser.add_argument('--collect', action='store_true', help='生成后跑 --collect-only 验证')
    args = parser.parse_args()

    if not job_config.LLM_API_KEY:
        print('LLM_API_KEY 未配置。获取步骤：')
        print('  1. 打开 https://platform.deepseek.com 注册/登录')
        print('  2. 左侧 API keys 创建一个 key')
        print('  3. 把 key 填到 job_config.py 的 LLM_API_KEY')
        return

    docs = load_docs(args.interface)
    if not docs:
        print(f'apidoc 目录里没找到匹配的文档: {args.interface or "(全部)"}')
        return

    OUT_DIR.mkdir(exist_ok=True)
    for api_name, doc in docs:
        out_file = OUT_DIR / f'test_{api_name}_ai.py'
        if out_file.exists():
            print(f'跳过（已存在）: {out_file.name}')
            continue
        print(f'生成中: {api_name} ...')
        try:
            code = strip_code_fence(call_llm(api_name, doc))
        except Exception as e:  # 生成器要能跳过单个失败继续跑
            print(f'  失败: {e}')
            continue
        header = (f'# -*- coding: utf-8 -*-\n'
                  f'"""AI 生成的用例草稿（接口 {api_name}）。\n\n'
                  f'本文件由 gen_cases.py 自动生成，只做骨架：\n'
                  f'需人工审阅（参数、断言、清理逻辑）后移入正式用例目录。\n"""\n')
        out_file.write_text(header + code + '\n', encoding='utf-8')
        print(f'  已写入: {out_file}')

    if args.collect:
        cmd = [sys.executable, '-m', 'pytest', '--collect-only', '-q', str(OUT_DIR)]
        subprocess.run(cmd, cwd=str(ROOT))


if __name__ == '__main__':
    main()
