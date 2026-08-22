# -*- coding: utf-8 -*-
"""参数边界测试（前辈提的"参数范围测试"落地）。

两层设计：
1. unit 层（现在就能跑，不依赖环境）：
   - Base64 边界内容往返（空串/中文/特殊字符/长串）
   - target_server 四种指定方式的组合
   - 封装层参数构造自洽：用 monkeypatch 截住 _call 不发请求，
     验证拼出来的参数对不对（该 Base64 的有没有编、互斥字段只传一个）
2. 环境层（体验账号到手后跑）：把边界值真发给接口，
   验证服务端校验：超时范围 1-86400、非法枚举被拒。

面试可讲：参数范围测试 = 等价类 + 边界值，三层递进——
正常值（代表）→ 边界值（1/86400 恰好在界上）→ 非法值（0/86401 越界，
期望服务端拒绝而不是悄悄放行）。
"""
import pytest

from app import job_config
from app.api_client import (JobClient, JobError, b64_decode, b64_encode,
                        make_target_server)

pytestmark = pytest.mark.boundary  # 参数边界测试


# ---------- unit 层：Base64 边界（纯函数） ----------

@pytest.mark.unit
@pytest.mark.parametrize('text', [
    '',                    # 空串
    'a',                   # 单字符
    'echo 你好世界',        # 中文
    'ls -la /tmp; rm -rf', # 高危字样（编码本身不该受影响）
    'x' * 1000,            # 长内容
    'line1\nline2\ttab',   # 换行和制表符
])
def test_Base64_各种内容往返一致(text):
    """边界内容编码再解码必须等于原文（空串、中文、特殊字符、长串）。"""
    assert b64_decode(b64_encode(text)) == text


@pytest.mark.unit
def test_target_server_四种指定方式可组合():
    """四种主机指定方式可以单独传，也可以组合传（服务端取并集）。"""
    server = make_target_server(
        host_id_list=[1, 2],
        ip_list=[{'bk_cloud_id': 0, 'ip': '1.1.1.1'}],
        dynamic_group_list=[{'id': 'grp1'}],
        topo_node_list=[{'id': 1, 'node_type': 'module'}])
    assert server['host_id_list'] == [1, 2]
    assert len(server['dynamic_group_list']) == 1
    assert len(server['topo_node_list']) == 1
    assert len(server['ip_list']) == 1


@pytest.mark.unit
def test_target_server_全空返回空字典():
    """什么都不传返回空字典，调用方自己决定要不要传 target_server。"""
    assert make_target_server() == {}


# ---------- unit 层：封装层参数构造自洽（mock _call，不发请求） ----------

@pytest.fixture()
def 捕获参数(monkeypatch):
    """monkeypatch 掉 _call：不真发请求，只把构造好的参数抓回来检查。

    这是"参数构造测试"的标准手法：测封装层的拼装逻辑，
    网络和服务端的行为留给环境层用例。
    """
    captured = {}

    def fake_call(api_name, params):
        captured['api'] = api_name
        captured['params'] = params
        return {}

    client = JobClient()
    monkeypatch.setattr(client, '_call', fake_call)
    captured['client'] = client
    return captured


@pytest.mark.unit
def test_快速执行_内容自动Base64且互斥字段只传一个(捕获参数):
    """传 script_content 时：内容被 Base64、语言自动带、script_id 不出现。"""
    捕获参数['client'].fast_execute_script(
        content='echo hi', language=1, account_alias='root',
        target_server=make_target_server(host_id_list=[1]))
    params = 捕获参数['params']
    assert 捕获参数['api'] == 'fast_execute_script'
    assert params['script_content'] == b64_encode('echo hi')
    assert params['script_language'] == 1
    assert 'script_id' not in params, '只传内容时不应出现 script_id'
    assert params['account_alias'] == 'root'


@pytest.mark.unit
def test_快速执行_传版本ID时内容被忽略(捕获参数):
    """优先级契约：script_version_id 优先级最高，content 不参与。"""
    捕获参数['client'].fast_execute_script(
        script_version_id=99, content='should_be_ignored',
        account_id=7, target_server=make_target_server(host_id_list=[1]))
    params = 捕获参数['params']
    assert params['script_version_id'] == 99
    assert 'script_content' not in params
    assert 'script_id' not in params
    assert params['account_id'] == 7


@pytest.mark.unit
def test_快速执行_超时0也能传出去(捕获参数):
    """坑位回归：timeout=0 是非法值，但必须能传给服务端让它拒绝。

    封装层不能用 if timeout 过滤（0 是 falsy），否则负面用例测不到
    服务端对 0 的拒绝。
    """
    捕获参数['client'].fast_execute_script(
        content='echo t', account_alias='root',
        target_server=make_target_server(host_id_list=[1]), timeout=0)
    params = 捕获参数['params']
    assert params['timeout'] == 0


@pytest.mark.unit
def test_推送配置_内容自动Base64且结构自洽(捕获参数):
    """push_config_file 拼参：file_list 结构对、内容编码、无 account_id。"""
    捕获参数['client'].push_config_file(
        file_name='a.txt', content='hello', file_target_path='/tmp/',
        account_alias='root', target_server=make_target_server(host_id_list=[1]))
    params = 捕获参数['params']
    assert params['file_list'][0]['file_name'] == 'a.txt'
    assert params['file_list'][0]['content'] == b64_encode('hello')
    assert params['account_alias'] == 'root'
    assert params['file_target_path'] == '/tmp/'
    assert 'account_id' not in params


@pytest.mark.unit
def test_快速执行SQL_DB账号必填字段自洽(捕获参数):
    """fast_execute_sql 拼参：db_account_id 在、系统账号字段不出现。"""
    捕获参数['client'].fast_execute_sql(
        db_account_id=32, script_content='SELECT 1;',
        target_server=make_target_server(host_id_list=[1]))
    params = 捕获参数['params']
    assert params['db_account_id'] == 32
    assert params['script_content'] == b64_encode('SELECT 1;')
    assert 'account_alias' not in params, 'SQL 执行不认系统账号'


# ---------- 环境层：真发接口验证服务端边界校验（账号到手后跑） ----------

@pytest.mark.parametrize('timeout', [1, 86400])
def test_快速执行_超时边界值合法(job_client, target_host, timeout):
    """边界值：1 秒（下界）和 86400 秒（上界）都是文档允许的合法值。"""
    result = job_client.fast_execute_script(
        content='echo boundary', language=1,
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=[target_host]),
        timeout=timeout)
    assert result['job_instance_id']


@pytest.mark.parametrize('timeout', [0, 86401, -1])
def test_快速执行_超时越界被拒(job_client, target_host, timeout):
    """越界值：0、86401、负数都应被服务端参数校验拒绝。"""
    with pytest.raises(JobError):
        job_client.fast_execute_script(
            content='echo bad_timeout', language=1,
            account_alias=job_config.ACCOUNT_ALIAS,
            target_server=make_target_server(host_id_list=[target_host]),
            timeout=timeout)


def test_建脚本_非法语言类型被拒(job_client, unique_name):
    """非法枚举：script_language 只支持 1-6，传 9 应被服务端拒绝。"""
    with pytest.raises(JobError):
        job_client.create_script(name=unique_name, language=9,
                                 content='echo bad_lang', version='1.0')


def test_操作作业实例_非法操作码被拒(job_client):
    """非法枚举：operate_job_instance 只支持 1=终止，传 99 应被拒绝。"""
    with pytest.raises(JobError):
        job_client.operate_job_instance(job_instance_id=0, operation_code=99)
