# -*- coding: utf-8 -*-
"""多环境管理。

解决的问题：体验环境 / 本地 CMDB standalone / 生产 等多套蓝鲸环境的
地址和凭证不同，切环境时不用改 job_config.py，只要一个环境名。

设计原则（与 job_config.py 的 local 覆盖一脉相承，但面向"多套"而非"单套"）：
- envs.example.json 是模板（入库，占位符留空）
- envs.local.json 是真凭证（gitignore，不入库）
- 读优先级：envs.local.json > envs.example.json（同名环境 local 覆盖模板）

客户端接入方式（叠加式，不破坏旧代码）：
- 客户端构造传 `env='experience'` → 从 envs 读配置，作为第二优先级默认值
- 显式参数 > env 配置 > job_config.py 默认值
- 不传 env → 走原来的 job_config.py 逻辑，行为完全不变

用法：
    from app.envs import get_env, list_envs
    list_envs()            # ['experience', 'local_cmdb']
    get_env('experience')  # {'esb_host': ..., 'bk_app_code': ..., ...}
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL = HERE / 'envs.local.json'
EXAMPLE = HERE / 'envs.example.json'

_CACHE = None


def _load() -> dict:
    """读环境配置文件；坏文件静默跳过，不影响 import 与跑单测。"""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    merged = {}
    for path in (EXAMPLE, LOCAL):  # 模板先读，local 后读覆盖同名环境
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            merged.update(data)
    _CACHE = merged
    return merged


def list_envs() -> list:
    """所有环境名（排序稳定，供 Web 下拉 / CLI --env 提示）。"""
    return sorted(_load().keys())


def get_env(name: str) -> dict:
    """取一个环境配置；不存在返回空 dict（调用方用 .get 兜底，别假设有）。"""
    cfg = _load().get(name)
    return dict(cfg) if isinstance(cfg, dict) else {}


def clear_cache():
    """测试用：清掉缓存，强制重新读文件（配合 monkeypatch 临时写环境文件）。"""
    global _CACHE
    _CACHE = None
