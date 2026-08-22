# -*- coding: utf-8 -*-
"""JOB 链路6：文件分发与 SQL 执行测试。

这条链路对应作业平台"文件分发"和"快速执行 SQL"页面的操作：
1. 推送配置文件   → 小文本文件直接下发到目标主机
2. 快速分发文件   → 服务器文件源（file_type=1）分发到目标机
3. 生成上传URL    → 本地文件分发三步流程的第一步
4. 快速执行 SQL   → 用 DB 账号在目标机上跑 SQL
5. 操作步骤实例   → 对执行中的步骤做失败IP重做/忽略错误等

数据自洽策略：目标主机用 target_host fixture；内容用无害文本，
断言执行状态成功(3)。DB 账号是锚点数据，未配置时跳过。

坑位清单（面试可讲）：
- push_config_file 返回没有 step_instance_id（与其它快速执行接口不同）
- generate_local_file_upload_url 是三步流程第1步：POST 拿地址，
  PUT 传内容（URL 自带凭据，无需鉴权头），path 给 fast_transfer_file 用
- fast_execute_sql 用 db_account_id（DB 账号），不认 account_alias（系统账号）
- operate_step_instance 的 operation_code 有 8 种语义
"""
import pytest

from app import job_config
from app.api_client import JobError, b64_decode, b64_encode, make_target_server

pytestmark = pytest.mark.file  # 链路6：文件分发与SQL执行


# ---------- 纯函数（不依赖环境） ----------

@pytest.mark.unit
def test_配置文件内容_Base64往返一致():
    """push_config_file 的内容要 Base64，编码后解码必须等于原文。"""
    content = 'zyy_config_test_内容自洽'
    assert b64_decode(b64_encode(content)) == content


# ---------- fixture ----------

@pytest.fixture()
def db账号(job_client):
    """SQL 快速执行用的 DB 账号 ID（锚点数据）。未配置时跳过。"""
    if not job_config.DB_ACCOUNT_ID:
        pytest.skip('未配置 DB_ACCOUNT_ID（体验环境账号管理里建 DB 账号）')
    return job_config.DB_ACCOUNT_ID


# ---------- 用例 ----------

def test_推送配置文件_返回作业实例ID(job_client, target_host, unique_name):
    """对应手动步骤：文件分发页选"配置文件" → 填内容点执行。"""
    result = job_client.push_config_file(
        file_name=f'{unique_name}.txt',
        content='zyy_config_file_test',
        file_target_path='/tmp/',
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=[target_host]))
    assert result['job_instance_id'], f'应返回作业实例ID: {result}'


def test_推送配置文件_执行成功(job_client, target_host, unique_name):
    """推配置 → 轮询状态到成功(3)。"""
    result = job_client.push_config_file(
        file_name=f'{unique_name}.txt', content='zyy_config_ok',
        file_target_path='/tmp/',
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=[target_host]))
    status = job_client.wait_finished(result['job_instance_id'])
    assert status['job_instance']['status'] == 3, \
        f"推配置应成功，实际: {status['job_instance']['status']}"


def test_推送配置_缺目标路径被拒(job_client, target_host):
    """负面用例：file_target_path 是必填项，传空应报错。"""
    with pytest.raises(JobError):
        job_client.push_config_file(
            file_name='bad.txt', content='x', file_target_path='',
            account_alias=job_config.ACCOUNT_ALIAS,
            target_server=make_target_server(host_id_list=[target_host]))


def test_生成上传URL_返回带凭据地址(job_client, unique_name):
    """对应手动步骤：本地文件分发第1步，选文件 → 生成上传地址。"""
    data = job_client.generate_local_file_upload_url(
        file_name_list=[f'{unique_name}.txt'])
    url_map = data['url_map']
    assert f'{unique_name}.txt' in url_map
    info = url_map[f'{unique_name}.txt']
    assert info['upload_url'], '应返回上传地址'
    assert info['path'], '应返回分发路径（给 fast_transfer_file 用）'


def test_快速分发文件_服务器文件源(job_client, target_host, unique_name):
    """对应手动步骤：文件分发页选"服务器文件" → 选源机 → 点执行。

    源和目标用同一台主机（自己传给自己），内容是无害的 /tmp 下文件。
    """
    result = job_client.fast_transfer_file(
        file_target_path='/tmp/',
        file_source_list=[{
            'file_list': ['/tmp/REGEX:*.txt'],
            'account': {'alias': job_config.ACCOUNT_ALIAS},
            'server': make_target_server(host_id_list=[target_host]),
            'file_type': 1,
        }],
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=[target_host]))
    assert result['job_instance_id']
    assert result['step_instance_id']


def test_快速分发文件_缺执行账号被拒(job_client, target_host):
    """负面用例：目标执行账号必填（account_alias/account_id 二选一）。"""
    with pytest.raises(JobError):
        job_client.fast_transfer_file(
            file_target_path='/tmp/',
            file_source_list=[{
                'file_list': ['/tmp/x.txt'],
                'account': {'alias': job_config.ACCOUNT_ALIAS},
                'file_type': 1,
            }],
            target_server=make_target_server(host_id_list=[target_host]))


def test_快速执行SQL_返回实例ID(job_client, target_host, db账号, unique_name):
    """对应手动步骤：快速执行 SQL 页 → 选 DB 账号 → 填 SQL 点执行。"""
    result = job_client.fast_execute_sql(
        db_account_id=db账号,
        script_content=f'SELECT "{unique_name}";',
        target_server=make_target_server(host_id_list=[target_host]))
    assert result['job_instance_id']


def test_快速执行SQL_缺DB账号被拒(job_client, target_host):
    """负面用例：db_account_id 必填，传 0 应报参数错误。"""
    with pytest.raises(JobError):
        job_client.fast_execute_sql(
            db_account_id=0,
            script_content='SELECT 1;',
            target_server=make_target_server(host_id_list=[target_host]))


def test_操作步骤_对失败步骤忽略错误(job_client, target_host, unique_name):
    """对应手动步骤：执行详情页对失败步骤点"忽略错误"（operation_code=3）。

    先造一个必然失败的脚本（exit 1），失败后对步骤做忽略错误操作。
    注意：该操作在 JOB 真实状态机里的适用时机待体验环境实测调整。
    """
    result = job_client.fast_execute_script(
        content=f'exit 1  # {unique_name}', language=1,
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=[target_host]))
    job_client.wait_finished(result['job_instance_id'])

    op = job_client.operate_step_instance(
        job_instance_id=result['job_instance_id'],
        step_instance_id=result['step_instance_id'],
        operation_code=3)
    assert op['step_instance_id'] == result['step_instance_id']
