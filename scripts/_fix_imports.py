# -*- coding: utf-8 -*-
"""一次性迁移脚本：平铺 import 改为 app 包导入。跑完即删。"""
from pathlib import Path

root = Path(r'e:\ReshapingMyself\work\嘉为科技\job-test')
files = list((root / 'tests').glob('*.py')) + list((root / 'app').glob('*.py'))
for p in files:
    text = p.read_text(encoding='utf-8')
    text = text.replace('import job_config', 'from app import job_config')
    text = text.replace('from api_client import', 'from app.api_client import')
    text = text.replace('from cmdb_client import', 'from app.cmdb_client import')
    p.write_text(text, encoding='utf-8')
    print('done:', p.name)
