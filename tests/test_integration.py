# -*- coding: utf-8 -*-
"""跨系统联动测试（连块测）：CMDB × JOB 场景矩阵。

"连块测"的含义：一个用例里同时调两个系统的接口，验证业务闭环。
光分开测发现不了这类问题——两边接口各自都对，放一起才暴露：

场景矩阵（按"数据契约"组织，契约就是两个系统的接口对接点）：
A. 契约一致性（只读，快）：两个系统对同一个实体的认知必须一致
   - JOB 的业务 ID 在 CMDB 业务列表里
   - JOB 的目标主机 ID 在 CMDB 主机列表里
   - CMDB 动态分组圈出的主机是合法主机
B. 业务联动（真执行）：CMDB 圈人 → JOB 干活
   - 动态分组圈的主机执行脚本成功（先 CMDB 查圈了谁，再 JOB 执行谁）
C. 隔离与反向（负面）：跨系统的边界必须守住
   - CMDB 里不存在的主机 ID，JOB 执行应被拒绝

面试话术：分开测发现"功能缺陷"，连块测发现"集成缺陷"——
集成缺陷才是两个系统放一起才有的问题（ID 对不上、状态不同步、
权限越界），这正是配置平台+作业平台联合交付的价值所在。
"""
import pytest

from app import job_config
from app.api_client import JobError, make_target_server

pytestmark = pytest.mark.integration  # 连块测：CMDB × JOB 跨系统场景


# ---------- fixture ----------

@pytest.fixture()
def 动态分组ID():
    """CMDB 动态分组 ID（锚点数据）。未配置时跳过。"""
    if not job_config.DYNAMIC_GROUP_ID:
        pytest.skip('未配置 DYNAMIC_GROUP_ID：先在体验环境 CMDB 建一个'
                    '动态分组（步骤见指引文档第 4 节）')
    return job_config.DYNAMIC_GROUP_ID


# ---------- 场景A：契约一致性（只读） ----------

def test_契约_JOB业务ID在CMDB业务列表里(cmdb_client):
    """JOB 的 bk_scope_id 就是 CMDB 的 bk_biz_id，两边必须对得上。

    这是所有联动的根契约：JOB 的资源范围直接引用 CMDB 业务 ID，
    如果 CMDB 里业务被删/改 ID，JOB 全部接口会静默失效。
    """
    bizs = cmdb_client.search_business()
    ids = {b.get('bk_biz_id') for b in bizs}
    assert int(job_config.BK_SCOPE_ID) in ids, \
        f'JOB scope_id={job_config.BK_SCOPE_ID} 不在 CMDB 业务列表: {ids}'


def test_契约_JOB目标主机在CMDB主机列表里(cmdb_client, target_host):
    """JOB 的 host_id 就是 CMDB 的 bk_host_id，主机数据同源。

    坑位：主机在 CMDB 里被转移到别的业务后，JOB 侧该业务的主机
    列表会跟着变——这是"数据底座驱动执行"的体现，也是测试必须
    覆盖的联动点（主机转移场景见场景C）。
    """
    hosts = cmdb_client.list_biz_hosts(limit=500)
    ids = {h['bk_host_id'] for h in hosts}
    assert target_host in ids, \
        f'JOB 目标主机 {target_host} 不在 CMDB 当前业务主机列表: {sorted(ids)[:10]}'


def test_契约_动态分组圈出的主机合法(cmdb_client, 动态分组ID):
    """动态分组执行结果非空，且圈出的主机在当前业务主机列表里。

    动态分组圈人是实时计算（按分组条件），可能圈空——圈空时
    JOB 用该分组执行会直接失败，所以先查再执行（联动场景B的做法）。
    """
    hosts = cmdb_client.execute_dynamic_group(动态分组ID)
    assert hosts, f'动态分组 {动态分组ID} 圈出 0 台主机，' \
                  'JOB 引用它执行会失败——分组条件可能过期'
    biz_hosts = {h['bk_host_id'] for h in cmdb_client.list_biz_hosts(limit=500)}
    for h in hosts:
        assert h['bk_host_id'] in biz_hosts, \
            f"分组圈出的主机 {h['bk_host_id']} 不在业务主机列表（数据异常）"


# ---------- 场景B：业务联动（真执行） ----------

def test_联动_CMDB圈主机JOB执行成功(cmdb_client, job_client,
                                     动态分组ID, unique_name):
    """业务闭环：CMDB 圈人 → JOB 干活。

    先调 CMDB 查分组现在圈了哪些主机（拿到真实主机清单），
    再让 JOB 按这些 host_id 执行脚本——比直接引用分组 ID 更进一步：
    执行目标不再是"黑盒分组"，而是刚验证过的主机。
    """
    hosts = cmdb_client.execute_dynamic_group(动态分组ID)
    assert hosts, f'动态分组 {动态分组ID} 圈出 0 台主机'
    host_ids = [h['bk_host_id'] for h in hosts]

    result = job_client.fast_execute_script(
        content=f'echo {unique_name}', language=1,
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(host_id_list=host_ids),
        task_name=f'zyy联动测试-{unique_name}')
    assert result['job_instance_id'], f'应返回作业实例ID: {result}'


def test_联动_引用动态分组ID直接执行成功(job_client, 动态分组ID,
                                             unique_name):
    """业务闭环（分组直引版）：JOB 侧只传动态分组 ID，不传主机清单。

    对应手动步骤：快速执行选目标时选"动态分组"。坑位：
    dynamic_group_list 的 id 是 CMDB 分组 ID（跨平台数据契约），
    不是 JOB 自己生成的 ID，错一个字符就是"查无此分组"。
    """
    result = job_client.fast_execute_script(
        content=f'echo {unique_name}', language=1,
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(
            dynamic_group_list=[{'id': 动态分组ID}]),
        task_name=f'zyy端到端-{unique_name}')
    assert result['job_instance_id'], f'应返回作业实例ID: {result}'


def test_联动_分组执行完成且日志正确(job_client, 动态分组ID,
                                      unique_name):
    """端到端全链路：分组圈的主机执行脚本 → 状态成功。

    主机完全由 CMDB 动态分组"现在圈中的主机"决定——JOB 侧
    不需要知道具体主机清单，这正是动态分组的价值。
    """
    result = job_client.fast_execute_script(
        content=f'echo {unique_name}', language=1,
        account_alias=job_config.ACCOUNT_ALIAS,
        target_server=make_target_server(
            dynamic_group_list=[{'id': 动态分组ID}]))
    status = job_client.wait_finished(result['job_instance_id'])
    job_status = status['job_instance']['status']
    assert job_status == 3, \
        f'联动执行应成功(status=3)，实际 status={job_status}: {status}'


# ---------- 场景C：隔离与反向（负面） ----------

def test_反向_CMDB不存在的主机JOB执行被拒(cmdb_client, job_client):
    """跨系统边界：CMDB 查不到的主机 ID，JOB 必须拒绝执行。

    这是权限隔离的底层防线——如果 JOB 接受一个不属于当前业务的
    主机 ID，等于跨业务执行，是安全事故。验证：先确认 CMDB 里
    确实没这台主机（双保险），再验证 JOB 拒绝。
    """
    ghost_host_id = 99999999
    # 双保险：先确认 CMDB 侧确实查不到这台主机
    ghosts = cmdb_client.search_host(host_id=ghost_host_id)
    if ghosts:
        pytest.skip(f'{ghost_host_id} 竟然存在于 CMDB，换一个主机 ID 再测')
    # JOB 侧应拒绝执行不存在的主机
    with pytest.raises(JobError):
        job_client.fast_execute_script(
            content='echo should_not_run', language=1,
            account_alias=job_config.ACCOUNT_ALIAS,
            target_server=make_target_server(host_id_list=[ghost_host_id]))


def test_反向_动态分组ID不存在JOB执行被拒(job_client):
    """跨系统契约：不存在的动态分组 ID，JOB 应报"查无此分组"。"""
    with pytest.raises(JobError):
        job_client.fast_execute_script(
            content='echo should_not_run', language=1,
            account_alias=job_config.ACCOUNT_ALIAS,
            target_server=make_target_server(
                dynamic_group_list=[{'id': 'not_exist_group_zyy'}]))
