# -*- coding: utf-8 -*-
"""统一测试入口：一条命令跑全部或指定链路，自动出 HTML 报告。

平台模块之一（阶段0 交付）。用法：
    python run_tests.py              # 全量 + 报告
    python run_tests.py -m unit      # 只跑不依赖环境的纯函数测试
    python run_tests.py -m script    # 只跑链路1
    python run_tests.py --no-report  # 只跑不生成报告

链路标签在 pytest.ini 里注册：unit/script/fast_exec/plan/cron/account/file/
cmdb/integration/boundary/platform；冒烟建议 -m "unit and not platform"
（排除 platform 防"跑测试"自引用）。
报告落在 reports/ 目录，按时间戳归档；latest.html 永远是最新一份。
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / 'reports'


def main():
    parser = argparse.ArgumentParser(description='蓝鲸 JOB 测试平台统一入口')
    parser.add_argument('-m', '--marker', default='',
                        help='按链路标签筛选，如 unit/script/integration；'
                             '冒烟用 -m "unit and not platform"')
    parser.add_argument('--no-report', action='store_true', help='不生成 HTML 报告')
    args = parser.parse_args()

    cmd = [sys.executable, '-m', 'pytest', '-v']
    if args.marker:
        cmd += ['-m', args.marker]

    html_path = None
    if not args.no_report:
        REPORT_DIR.mkdir(exist_ok=True)
        html_path = REPORT_DIR / f'report_{time.strftime("%Y%m%d_%H%M%S")}.html'
        cmd += ['--html', str(html_path), '--self-contained-html']

    print('执行命令:', ' '.join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))

    if html_path and html_path.exists():
        latest = REPORT_DIR / 'latest.html'
        shutil.copyfile(html_path, latest)
        print(f'\n报告已生成: {html_path}')
        print(f'最新报告: {latest} (浏览器直接打开)')
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
