# -*- coding: utf-8 -*-
"""性能压测脚本（Locust）：只读接口基准压测。

运行方式（体验环境凭证配好后）：
    pip install locust
    locust -f locustfile.py --host <ESB_HOST>

打开 http://localhost:8089 填并发数，建议从"并发5 / 每秒1用户"起步。

为什么只压只读接口（面试话术）：
1. 体验环境是共享环境，申请时明确黑名单警告——压写接口会污染
   共享数据（建脚本/执行任务堆积脏数据），只读接口无副作用
2. 只读接口（列表查询）恰恰是线上高频接口，压它们最有代表性
3. 压测目标是"摸清接口性能基线"，不是压垮共享环境——
   基线数据（响应时间/吞吐量）在报告里一对比就有说服力

接口选择：
- get_job_instance_list：实例列表查询（带时间窗，最重的列表接口）
- get_script_list / get_account_list / get_job_template_list：元数据查询
- CMDB search_business：跨系统读，验证 CMDB 侧性能基线
"""
import sys
import time
from pathlib import Path

from locust import HttpUser, between, task

# locust -f 从 scripts/ 加载本文件时 sys.path[0] 是 scripts/，
# 把项目根插入才能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import job_config


def _auth_body() -> dict:
    """ESB 认证三件套（与 api_client._call 一致）。"""
    return {
        'bk_app_code': job_config.BK_APP_CODE,
        'bk_app_secret': job_config.BK_APP_SECRET,
        'bk_token': job_config.BK_TOKEN,
    }


def _recent_time_range() -> tuple:
    """get_job_instance_list 必传的起止时间窗（最近 24 小时，毫秒）。"""
    now_ms = int(time.time() * 1000)
    return now_ms - 24 * 3600 * 1000, now_ms


class JobReadOnlyUser(HttpUser):
    """只读接口压测用户。写接口一律不压（共享环境黑名单）。"""

    wait_time = between(0.5, 2)  # 模拟真实用户思考间隔，不是打满并发

    def on_start(self):
        if not (job_config.ESB_HOST and job_config.BK_APP_CODE
                and job_config.BK_APP_SECRET and job_config.BK_SCOPE_ID):
            raise RuntimeError(
                'job_config.py 凭证未配置：压测前先填好 ESB_HOST 和三件套')

    def _post_esb(self, api_path: str, params: dict):
        """统一 ESB 请求：三件套 + 参数。api_path 如
        /api/c/compapi/v2/jobv3/get_script_list/"""
        body = _auth_body()
        body.update(params)
        with self.client.post(api_path, json=body, catch_response=True) as r:
            # 业务失败也算失败：result=false 或 code!=0 时标记失败，
            # 避免把服务端报错误记成"压测通过"
            if r.status_code != 200:
                r.failure(f'HTTP {r.status_code}')
                return
            payload = r.json()
            if not payload.get('result') or payload.get('code') != 0:
                r.failure(f"业务失败 code={payload.get('code')}")

    @task(5)  # 权重最高：实例列表是最重的列表接口，压它最有代表性
    def 查作业实例列表(self):
        start_ms, end_ms = _recent_time_range()
        self._post_esb(
            '/api/c/compapi/v2/jobv3/get_job_instance_list/',
            {'bk_scope_type': job_config.BK_SCOPE_TYPE,
             'bk_scope_id': str(job_config.BK_SCOPE_ID),
             'create_time_start': start_ms,
             'create_time_end': end_ms,
             'start': 0, 'length': 20})

    @task(3)
    def 查脚本列表(self):
        self._post_esb(
            '/api/c/compapi/v2/jobv3/get_script_list/',
            {'bk_scope_type': job_config.BK_SCOPE_TYPE,
             'bk_scope_id': str(job_config.BK_SCOPE_ID),
             'start': 0, 'length': 20})

    @task(2)
    def 查账号列表(self):
        self._post_esb(
            '/api/c/compapi/v2/jobv3/get_account_list/',
            {'bk_scope_type': job_config.BK_SCOPE_TYPE,
             'bk_scope_id': str(job_config.BK_SCOPE_ID),
             'start': 0, 'length': 20})

    @task(1)
    def 查CMDB业务(self):
        """跨系统读：CMDB 侧性能基线（cc 组件，注意参数差异）。"""
        self._post_esb(
            '/api/c/compapi/v2/cc/search_business/',
            {'bk_supplier_account': '0',
             'page': {'start': 0, 'limit': 20}})
