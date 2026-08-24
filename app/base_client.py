# -*- coding: utf-8 -*-
"""ESB 客户端公共基类。

JOB（jobv3 组件）和 CMDB（cc 组件）都走蓝鲸 ESB 网关：
认证三件套、URL 格式、返回结构一致，差异只在「组件名」和少量「额外认证参数」。
抽成基类后，加新蓝鲸平台只需继承 + 填 component + 写接口方法，不再复制整套认证逻辑。

面试可讲：这是插件化抽象——公共的「认证/调接口/查结果」收进基类，
子类只写「差异」（组件名、额外参数、具体接口），加平台从"复制一份"变成"填一份配置"。
"""
import requests

from app import job_config
from app.envs import get_env


class EsbError(Exception):
    """ESB 接口返回 result=false 或 code!=0 时抛出。

    子类（JobError / CmdbError）继承它，保持原有错误名，兼容现有用例。
    """


class BaseClient:
    """ESB 客户端基类：统一「拼 URL + 三件套 + 结果检查」。

    多环境支持（叠加式）：构造传 env='experience' 时，从 app/envs 读该环境
    配置作为第二优先级默认值——显式参数 > env 配置 > job_config.py。
    不传 env 则走原 job_config.py 逻辑，行为不变。
    """

    # 子类覆盖：URL 组件名（/api/c/compapi/v2/{component}/{api}/）
    component = ''
    # 子类覆盖：抛出的异常类型（JOB 用 JobError，CMDB 用 CmdbError）
    error_class = EsbError

    def __init__(self, esb_host=None, app_code=None, app_secret=None,
                 token=None, env=None):
        cfg = get_env(env) if env else {}
        self.esb_host = esb_host or cfg.get('esb_host') or job_config.ESB_HOST
        self.app_code = app_code or cfg.get('bk_app_code') or job_config.BK_APP_CODE
        self.app_secret = (app_secret or cfg.get('bk_app_secret')
                           or job_config.BK_APP_SECRET)
        self.token = token or cfg.get('bk_token') or job_config.BK_TOKEN

    def _extra_auth(self) -> dict:
        """子类可覆盖：额外认证参数（如 CMDB 的 bk_supplier_account）。"""
        return {}

    def _call(self, api_name: str, params: dict):
        """统一请求入口：拼 URL + 三件套 + 结果检查。"""
        url = f'{self.esb_host}/api/c/compapi/v2/{self.component}/{api_name}/'
        body = {
            'bk_app_code': self.app_code,
            'bk_app_secret': self.app_secret,
            'bk_token': self.token,
        }
        body.update(self._extra_auth())
        body.update(params)
        resp = requests.post(url, json=body, timeout=30)
        if resp.status_code != 200:
            raise self.error_class(f'HTTP {resp.status_code}: {resp.text[:200]}')
        payload = resp.json()
        if not payload.get('result') or payload.get('code') != 0:
            raise self.error_class(
                f'接口 {api_name} 调用失败: '
                f"code={payload.get('code')} "
                f"message={payload.get('message', payload)[:200]}")
        return payload.get('data')
