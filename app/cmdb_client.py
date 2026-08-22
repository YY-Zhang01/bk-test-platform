# -*- coding: utf-8 -*-
"""CMDB API 封装层（ESB cc 组件）。

把蓝鲸配置平台（bk-cmdb）的 ESB 接口封装成 python 方法，供两部分测试用：
1. 分开测：CMDB 自己一条独立链路（业务→主机→拓扑→动态分组）
2. 连块测：给跨系统场景矩阵提供"CMDB 侧查询"能力（数据契约校验）

与 JOB 客户端的异同（面试常问"CMDB 和 JOB 的 API 有什么不一样"）：
- 相同：都走 ESB 网关、认证三件套一样、返回结构 {result, code, message, data}
- 不同：组件名不同（JOB 是 jobv3，CMDB 是 cc）；CMDB 每个接口都要带
  bk_biz_id（业务 ID）做数据隔离，JOB 是 bk_scope_type/bk_scope_id
  二选一；CMDB 多数列表接口用 page.{start,limit,sort} 分页

关键数据契约（连块测的抓手）：
- JOB 的 bk_scope_id == CMDB 的 bk_biz_id（同一个业务 ID）
- JOB 的 host_id == CMDB 的 bk_host_id（同一台主机）
- JOB 的 dynamic_group_list[].id == CMDB 动态分组 ID

接口参数按蓝鲸开放平台 cc 组件公开文档整理，以体验环境 ESB 实测为准。
本地 JOB apidoc 存于 apidoc/，CMDB 侧接口文档待体验环境开通后补齐。
"""
import requests

from app import job_config


class CmdbError(Exception):
    """CMDB 接口返回 result=false 或 code!=0 时抛出，带错误码方便定位。"""


def make_page(start=0, limit=10, sort='') -> dict:
    """拼 CMDB 标准分页参数。sort 为字段名，如 'bk_host_id'。"""
    page = {'start': start, 'limit': limit}
    if sort:
        page['sort'] = sort
    return page


class CmdbClient:
    """配置平台 ESB 客户端。

    凭证与 JOB 完全复用（都是 ESB 三件套），业务 ID 复用
    job_config.BK_SCOPE_ID——因为 JOB 的 scope_id 本来就是 CMDB 的业务 ID。
    """

    def __init__(self, esb_host=None, app_code=None, app_secret=None,
                 token=None, biz_id=None):
        self.esb_host = esb_host or job_config.ESB_HOST
        self.app_code = app_code or job_config.BK_APP_CODE
        self.app_secret = app_secret or job_config.BK_APP_SECRET
        self.token = token or job_config.BK_TOKEN
        self.biz_id = biz_id or job_config.BK_SCOPE_ID

    # ---------------- 底层 ---------------- #

    def _call(self, api_name: str, params: dict):
        """统一请求入口：cc 组件 URL + 三件套 + 结果检查。"""
        url = f'{self.esb_host}/api/c/compapi/v2/cc/{api_name}/'
        body = {
            'bk_app_code': self.app_code,
            'bk_app_secret': self.app_secret,
            'bk_token': self.token,
            # 供应商账号是 CC 组件的历史遗留参数，默认 0（直属），
            # 不传部分接口会报"缺少 bk_supplier_account"
            'bk_supplier_account': '0',
        }
        body.update(params)
        resp = requests.post(url, json=body, timeout=30)
        if resp.status_code != 200:
            raise CmdbError(f'HTTP {resp.status_code}: {resp.text[:200]}')
        payload = resp.json()
        if not payload.get('result') or payload.get('code') != 0:
            raise CmdbError(f'接口 {api_name} 调用失败: '
                            f"code={payload.get('code')} "
                            f"message={payload.get('message', payload)[:200]}")
        return payload.get('data')

    # ---------------- 分开测：CMDB 独立链路 ----------------

    def search_business(self, biz_id=None, limit=100) -> list:
        """查业务列表。不带条件返回全量业务（受 ESB 权限限制）。

        连块测用途：校验 JOB 的 scope_id 在 CMDB 业务列表里（数据契约）。
        """
        params = {'page': make_page(limit=limit)}
        if biz_id:
            params['condition'] = {'bk_biz_id': biz_id}
        data = self._call('search_business', params)
        return data.get('info', [])

    def list_biz_hosts(self, biz_id=None, limit=200, fields=None) -> list:
        """按业务查主机（全业务或指定业务）。

        连块测用途：校验 JOB 的 TARGET_HOST_ID 在 CMDB 主机列表里。
        """
        params = {
            'bk_biz_id': biz_id or self.biz_id,
            'page': make_page(limit=limit),
        }
        if fields:
            params['fields'] = fields
        data = self._call('list_biz_hosts', params)
        return data.get('info', [])

    def search_host(self, biz_id=None, host_id=None, limit=200) -> list:
        """按条件查主机（host 模型条件查询，可返回主机完整属性）。

        连块测用途：查主机状态字段，验证主机当前是否可被 JOB 执行。
        """
        condition = [{
            'bk_obj_id': 'host',
            'fields': [],
            'condition': [{'field': 'bk_host_id',
                           'operator': '$eq',
                           'value': host_id}],
        }]
        params = {
            'bk_biz_id': biz_id or self.biz_id,
            'page': make_page(limit=limit),
            'condition': condition,
        }
        data = self._call('search_host', params)
        return data.get('info', [])

    def execute_dynamic_group(self, group_id, biz_id=None, limit=200) -> list:
        """执行动态分组：返回分组"现在"圈中的主机。

        坑位：动态分组圈的主机是实时算出来的（按分组条件），
        不是快照——同一分组两次执行结果可以不同。
        连块测用途：先查分组圈了哪些主机，再让 JOB 执行这些主机，
        验证"CMDB 圈人 → JOB 干活"的业务闭环。
        """
        params = {
            'bk_biz_id': biz_id or self.biz_id,
            'id': group_id,
            'page': make_page(limit=limit),
        }
        data = self._call('execute_dynamic_group', params)
        return data.get('info', [])

    def search_module(self, biz_id=None, limit=200) -> list:
        """查业务下的模块（拓扑第 2 层，模块挂在集群下）。"""
        params = {
            'bk_biz_id': biz_id or self.biz_id,
            'page': make_page(limit=limit),
        }
        data = self._call('search_module', params)
        return data.get('info', [])

    def search_set(self, biz_id=None, limit=200) -> list:
        """查业务下的集群（拓扑第 1 层，集群下挂模块）。"""
        params = {
            'bk_biz_id': biz_id or self.biz_id,
            'page': make_page(limit=limit),
        }
        data = self._call('search_set', params)
        return data.get('info', [])

    def search_object_attribute(self, obj_id='host', limit=200) -> list:
        """查模型属性（字段字典）。

        用途：接口字段与页面对不上时查字典；也可以做"字段变更回归"——
        上线前后比对字段集，发现模型字段被误改。
        """
        params = {
            'bk_obj_id': obj_id,
            'page': make_page(limit=limit),
        }
        data = self._call('search_object_attribute', params)
        return data.get('info', [])
