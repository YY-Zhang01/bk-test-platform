# -*- coding: utf-8 -*-
"""把 tests/ 下所有用例提取成 CSV（Excel 可打开），复用 case_index 的提取逻辑。

不再自己写一套 AST 解析（历史上与 case_index.py 重复、且漏了模块级 pytestmark
导致 marker/优先级错误），统一走 app.case_index.extract_cases()，保证和 Web 用例库一致。

列：文件 | 用例名 | 作用/设计原因 | 所属层级/维度 | marker | 优先级 | 是否等账号
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # 让 `import app` 能找到项目根

from app.case_index import extract_cases  # noqa: E402

OUT = ROOT / 'docs' / '2026-08-23-用例清单.csv'

_ENV_LABEL = {'否': '可跑', '是': '等账号', 'UI': '需浏览器'}


def main():
    rows = extract_cases()
    with open(OUT, 'w', encoding='utf-8-sig', newline='') as fp:
        w = csv.writer(fp)
        w.writerow(['文件', '用例名', '作用/设计原因', '所属层级/维度',
                    'marker', '优先级', '运行状态'])
        for r in rows:
            w.writerow([r['file'], r['name'], r['desc'], r['layer'],
                        r['marker'], r['priority'],
                        _ENV_LABEL.get(r['env'], r['env'])])
    print(f'已生成 {len(rows)} 行 -> {OUT}')


if __name__ == '__main__':
    main()
