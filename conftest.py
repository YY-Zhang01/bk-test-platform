# -*- coding: utf-8 -*-
"""项目根 conftest：把根目录加入 sys.path。

tests/ 是"无包模式"测试目录（不建 __init__.py），pytest 默认只把
tests/ 自己加进 sys.path。这里手动把项目根插入，让所有测试文件
能 `from app import ...` 导入产品代码。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
