# -*- coding: utf-8 -*-
"""JOB 测试项目公共配置。

客户端 fixture + 通用工具，所有测试文件共用。
环境就绪后 `pytest` 直接跑；未配置凭证时全部 skip，不造假绿。
"""
import time
import uuid

import pytest

from app import job_config
from app.api_client import JobClient
from app.cmdb_client import CmdbClient


@pytest.fixture(scope='session')
def job_client():
    """JOB ESB 客户端。凭证没配好时整组 skip，并提示下一步。"""
    if not (job_config.ESB_HOST and job_config.BK_APP_CODE
            and job_config.BK_APP_SECRET and job_config.BK_SCOPE_ID):
        pytest.skip('JOB 体验环境凭证未配置：先申请账号，填好 job_config.py'
                    '（步骤见《2026-08-22-JOB体验账号申请指引.md》）')
    return JobClient()


@pytest.fixture(scope='session')
def cmdb_client():
    """CMDB ESB 客户端（与 JOB 共用 ESB 三件套，业务 ID 复用 scope_id）。

    分开测时 CMDB 链路独立跑，连块测时与 job_client 配合做契约校验。
    """
    if not (job_config.ESB_HOST and job_config.BK_APP_CODE
            and job_config.BK_APP_SECRET and job_config.BK_SCOPE_ID):
        pytest.skip('CMDB 体验环境凭证未配置：先申请账号，填好 job_config.py'
                    '（CMDB 与 JOB 共用 ESB 凭证，业务 ID 复用 BK_SCOPE_ID）')
    return CmdbClient()


@pytest.fixture()
def unique_name():
    """生成带时间戳的唯一名称，保证测试数据自洽、多次跑不撞车。"""
    return f"zyy{int(time.time())}{uuid.uuid4().hex[:4]}"


@pytest.fixture()
def 新脚本(job_client, unique_name):
    """建一个测试脚本（首个版本 v1.0），用完删除脚本级联清版本。

    放在公共层是因为：链路1（脚本管理）要用它，链路2（快速执行的
    脚本优先级用例）也要引用它，跨链路复用的数据对象放 conftest。
    返回 create_script 的 data：{id: 首个版本ID, script_id: 脚本ID}
    """
    created = job_client.create_script(
        name=unique_name, language=1,
        content='echo zyy_hello', version='1.0',
        description='pytest 自建测试脚本')
    yield created
    job_client.delete_script(created['script_id'])


@pytest.fixture()
def 锚点模板(job_client):
    """取一个作业模板做锚点（链路3、链路4 共用）。

    模板只能在 Web 端创建，API 只读；环境里没建过模板时 skip。
    """
    templates = job_client.get_job_template_list()
    if not templates:
        pytest.skip('体验环境暂无作业模板：先在 Web 端建一个'
                    '（步骤见指引文档第 3 节）')
    return templates[0]


@pytest.fixture()
def 锚点方案(job_client, 锚点模板):
    """取锚点模板下的一个执行方案（链路3、链路4 共用）。"""
    plans = job_client.get_job_plan_list(job_template_id=锚点模板['id'])
    if not plans:
        pytest.skip('锚点模板下没有执行方案：先在 Web 端给模板建方案')
    return plans[0]


@pytest.fixture()
def recent_time_range():
    """get_job_instance_list 必传的起止时间窗（最近 24 小时，毫秒）。"""
    now_ms = int(time.time() * 1000)
    return now_ms - 24 * 3600 * 1000, now_ms


@pytest.fixture()
def target_host():
    """快速执行的目标主机 ID。未在 job_config 配置时跳过相关用例。"""
    if not job_config.TARGET_HOST_ID:
        pytest.skip('未配置 TARGET_HOST_ID（体验环境业务下先导入一台主机）')
    return job_config.TARGET_HOST_ID
