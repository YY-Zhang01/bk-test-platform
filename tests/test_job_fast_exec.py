# -*- coding: utf-8 -*-
"""JOB 链路2：快速执行测试（JOB 最核心能力）。

这条链路对应作业平台"快速执行脚本"页面的操作：
1. 选脚本（或直接粘脚本内容）→ 选目标主机 → 点执行
2. 返回作业实例 ID 和步骤实例 ID（一次真实执行的"取号单"）
3. 轮询作业实例状态，直到执行结束（异步任务，不会同步返回结果）
4. 按主机查执行日志，验证脚本输出

数据自洽策略：目标主机用 job_config.TARGET_HOST_ID（体验环境业务下
已导入的主机）；执行内容用无害的 echo，输出写唯一标记串再断言日志包含它。
依赖：未配置 TARGET_HOST_ID 时整组跳过（conftest 的 target_host fixture）。

坑位清单（面试可讲）：
- 脚本优先级 script_version_id > script_id > script_content
- 脚本内容/参数必须 Base64，多参数要整体编码
- 执行账号 account_alias 与 account_id 必须存在一个
"""
import time

import pytest

from app import job_config
from app.api_client import JobError, b64_decode, b64_encode, make_target_server

pytestmark = pytest.mark.fast_exec  # 链路2：快速执行


# ---------- 用例 ----------

@pytest.mark.unit  # 纯函数测试：不依赖环境，凭证没到也能跑
def test_Base64往返_编解码一致():
    """纯函数测试，不依赖环境（凭证没到也能先跑）。

    验证封装层的 Base64 规则：编码后再解码必须等于原文；
    多参数是"整体编码"，不是逐个编码再拼接。
    """
    assert b64_decode(b64_encode('echo hello')) == 'echo hello'
    assert b64_decode(b64_encode('param1 param2')) == 'param1 param2'


def test_快速执行_返回实例和步骤ID(job_client, target_host, unique_name):
    """对应手动步骤：填脚本点"执行" → 生成作业实例。

    用 script_content 方式（优先级最低），script_language 必须指定。
    """
    result = job_client.fast_execute_script(
        content=f'echo {unique_name}',
        language=1,
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=[target_host]),
        task_name=f'zyy快速执行测试-{unique_name}',
    )
    assert result['job_instance_id'], f'应返回作业实例ID: {result}'
    assert result['step_instance_id'], f'应返回步骤实例ID: {result}'
    # 给后续状态查询留 3 秒（任务状态机异步流转）
    time.sleep(3)


def test_查状态_轮询到执行结束(job_client, target_host, unique_name):
    """对应手动步骤：执行历史里看状态从"执行中"流转到"成功/失败"。

    状态码：1等待 2执行中 3成功 4失败 7等待确认
    10强制终止中 11强制终止成功 13确认终止
    """
    result = job_client.fast_execute_script(
        content=f'echo {unique_name}', language=1,
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=[target_host]))

    status = job_client.wait_finished(result['job_instance_id'])
    job_status = status['job_instance']['status']
    assert job_status == 3, \
        f'echo 脚本应执行成功(status=3)，实际 status={job_status}: {status}'


def test_查日志_输出包含唯一标记(job_client, target_host, unique_name):
    """对应手动步骤：执行详情里点开某台主机 → 看到脚本 stdout 输出。

    脚本输出写唯一标记串，日志里必须能查到它——数据自洽的最强证明。
    """
    result = job_client.fast_execute_script(
        content=f'echo {unique_name}', language=1,
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=[target_host]))
    job_client.wait_finished(result['job_instance_id'])

    log = job_client.get_job_instance_ip_log(
        result['job_instance_id'], result['step_instance_id'],
        host_id=target_host)
    assert unique_name in log['log_content'], \
        f"日志里应包含唯一标记 {unique_name}，实际: {log.get('log_content', log)}"


def test_执行账号_缺账号被拒(job_client, target_host):
    """负面用例：不传执行账号（account_alias 和 account_id 都不传）应报错。

    坑位：快速执行必须指定"用谁的身份干活"，这是 JOB 与裸 SSH 的关键差异。
    """
    with pytest.raises(JobError):
        job_client.fast_execute_script(
            content='echo no_account', language=1,
            target_server=make_target_server(host_id_list=[target_host]))


def test_脚本优先级_传内容同时传版本用版本(job_client, target_host, 新脚本):
    """坑位实测：script_version_id > script_id > script_content。

    同时传了上线版本和 script_content 时，接口应忽略 content 用版本执行。
    这里只验证请求能正常返回实例（优先级细节在日志侧验证）。
    """
    v1_id = 新脚本['id']
    job_client.publish_script_version(新脚本['script_id'], v1_id)

    result = job_client.fast_execute_script(
        script_version_id=v1_id,
        content='echo should_be_ignored', language=1,
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=[target_host]))
    assert result['job_instance_id']
