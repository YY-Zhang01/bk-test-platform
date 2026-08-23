# -*- coding: utf-8 -*-
"""安全测试（面试官"全方位测试"里点名维度，本次补齐）。

六个安全维度分两层落地：
1. unit 层（现在就能跑，不依赖环境）：
   - 封装层安全自洽：高危检测内容自动 Base64、全局接口不带 scope
     （避免危险检测被错误绑定到某个业务上）
2. 环境层（体验账号到手后跑，诚实 skip）：
   - 鉴权：错误 token 被拒
   - 越权：用别的业务 scope 访问，拿不到本业务的资源
   - 注入：脚本参数塞 SQL 注入 payload 被拦
   - 高危命令：rm -rf / 被 check_script 命中拦截

面试可讲：安全测试 = 鉴权（谁不能进）+ 越权（进错了门看不了别人的东西）+
注入（塞恶意内容执行不了）+ 高危命令（危险动作要拦）。真实环境数据诚实
等账号，与项目"只读白名单 / 诚实 skip"同一底线。
"""
import pytest

from app import job_config
from app.api_client import (JobClient, JobError, b64_encode,
                            make_target_server)

pytestmark = pytest.mark.security  # 安全测试维度


# ---------- unit 层：封装层安全自洽（mock _call，不发请求） ----------

@pytest.fixture()
def 捕获参数(monkeypatch):
    """monkeypatch 掉 _call：不发请求，只抓构造好的参数检查安全自洽。"""
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
def test_高危检测_脚本内容自动Base64(捕获参数):
    """check_script 的内容必须 Base64，危险命令也要照常编码发送。"""
    捕获参数['client'].check_script('rm -rf /')
    params = 捕获参数['params']
    assert 捕获参数['api'] == 'check_script'
    assert params['content'] == b64_encode('rm -rf /')


@pytest.mark.unit
def test_高危检测_全局接口不带scope(捕获参数):
    """check_script 是全局能力，不应带 bk_scope（否则危险检测被绑到业务上）。"""
    捕获参数['client'].check_script('echo x')
    params = 捕获参数['params']
    assert 'bk_scope_type' not in params
    assert 'bk_scope_id' not in params


@pytest.mark.unit
def test_高危规则_全局接口不带scope(捕获参数):
    """create_dangerous_rule 也是全局资源，不带 bk_scope。"""
    捕获参数['client'].create_dangerous_rule(
        expression=r'rm\s+-rf', language_list=[1], description='拦截rm')
    params = 捕获参数['params']
    assert 捕获参数['api'] == 'create_dangerous_rule'
    assert 'bk_scope_type' not in params
    assert 'bk_scope_id' not in params


# ---------- 环境层：真发接口验证安全行为（账号到手后跑） ----------

def test_鉴权_错误token被拒(job_client):
    """用真实 app_code/secret + 错误 token 调接口，应被服务端拒绝。"""
    bad = JobClient(token='WRONG_TOKEN_FOR_SECURITY_TEST')
    with pytest.raises(JobError):
        bad.get_script_list()


def test_越权_跨业务scope查不到本业务脚本(job_client, unique_name):
    """业务隔离：用本业务建一个脚本，用"别的业务 scope"去查，应查不到。

    环境到位后精确断言：先用本 scope 建脚本并确认能查到，
    再用 scope_id='999999'（不存在的业务）查，断言该脚本不在结果里。
    """
    created = job_client.create_script(
        name=unique_name, language=1, content='echo secret_script',
        version='1.0')
    try:
        # 用不存在的业务 scope 查脚本列表，预期拿不到刚建的脚本
        other = JobClient(scope_id='999999')
        others = other.get_script_list(name=unique_name)
        own_ids = {s['id'] for s in
                   job_client.get_script_list(name=unique_name)}
        assert own_ids, '本业务应能查到刚建的脚本（对照组）'
        # 隔离断言：别的业务 scope 查同名脚本，不应出现本业务的 script_id
        assert all(s['id'] not in own_ids for s in others), \
            '跨业务 scope 不应查到本业务的脚本（越权隔离）'
    finally:
        job_client.delete_script(created['script_id'])


def test_注入_SQL注入参数被拒(job_client, target_host):
    """脚本参数塞 SQL 注入 payload，应被服务端参数校验 / 高危检测拦截。"""
    with pytest.raises(JobError):
        job_client.fast_execute_script(
            content='echo x', language=1,
            param="'; DROP TABLE runs; --",
            account_alias=job_config.ACCOUNT_ALIAS,
            target_server=make_target_server(host_id_list=[target_host]))


def test_高危命令_rm_rf被check_script命中(job_client):
    """check_script 对 rm -rf / 应返回命中列表（level 3 致命）。"""
    hits = job_client.check_script('rm -rf /')
    assert hits, 'rm -rf / 应被高危检测命中拦截'
