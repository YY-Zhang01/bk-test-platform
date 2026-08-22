# -*- coding: utf-8 -*-
"""JOB 链路4：定时任务测试（crontab 式周期执行）。

这条链路对应"定时作业"页面的操作：
1. 新建定时任务   → 引用一个执行方案 + crontab 表达式
2. 新建后默认"暂停"→ 安全设计，必须手动启动才真正跑
3. 启动定时任务   → 状态 1（启动），到点自动执行方案
4. 删除定时任务   → 不再触发

数据自洽策略：fixture 自建自清（save_cron 建 → delete_cron 删）。
表达式用"每天凌晨 3 点"（0 0 3 * *），测试期间不会真实触发。
依赖：锚点方案（链路3 的 fixture，Web 端先建好模板）。

坑位清单（面试可讲）：
- 新建后默认暂停，不 update_cron_status 永远不会执行
- expression 与 execute_time 互斥（周期执行 vs 单次执行）
- expression 不支持 `?`（与标准 cron / Quartz 的差异）
"""
import pytest

from app.api_client import JobError

pytestmark = pytest.mark.cron  # 链路4：定时任务


# ---------- fixture：链路数据（自建自清） ----------

@pytest.fixture()
def 新定时任务(job_client, 锚点方案, unique_name):
    """建一个定时任务（每天凌晨 3 点，默认暂停），用完删除。"""
    cron = job_client.save_cron(job_plan_id=锚点方案['id'],
                                name=unique_name,
                                expression='0 0 3 * *')
    yield cron
    job_client.delete_cron(cron['id'])


# ---------- 用例 ----------

def test_新建定时任务_默认暂停(job_client, 新定时任务):
    """对应手动步骤：新建定时 → 列表里状态是"暂停"。

    坑位：新建后默认"暂停"，这是安全设计——防止误配表达式立刻触发。
    """
    cron_id = 新定时任务['id']
    crons = job_client.get_cron_list(cron_id=cron_id)
    assert crons, f'定时列表里查不到 {cron_id}'
    assert crons[0]['status'] == 2, \
        f'新建定时任务应默认暂停(status=2)，实际: {crons[0]}'


def test_定时详情_表达式保存正确(job_client, 新定时任务):
    """对应手动步骤：定时详情页 → 能看到 crontab 表达式和引用的方案。"""
    detail = job_client.get_cron_detail(新定时任务['id'])
    assert detail['expression'] == '0 0 3 * *', \
        f'表达式应原样保存，实际: {detail["expression"]}'
    assert detail['job_plan_id'] == 新定时任务['job_plan_id']


def test_启动定时任务_状态变启动(job_client, 新定时任务):
    """对应手动步骤：点"启动" → 状态 2（暂停）变 1（启动）。"""
    cron_id = 新定时任务['id']
    result = job_client.update_cron_status(cron_id, status=1)
    assert result['status'] == 1, f'启动后状态应为1，实际: {result}'

    detail = job_client.get_cron_detail(cron_id)
    assert detail['status'] == 1, f'详情状态应为1，实际: {detail["status"]}'

    # 恢复暂停，避免测试期间定时任务残留启动状态
    job_client.update_cron_status(cron_id, status=2)


def test_表达式带问号_被拒绝(job_client, 锚点方案, unique_name):
    """负面用例：expression 不支持 `?`（坑位实测）。

    标准 cron / Quartz 允许 `?`，但 JOB 的 ESB 接口明确不支持，
    传了应被参数校验拒绝。
    """
    with pytest.raises(JobError):
        job_client.save_cron(job_plan_id=锚点方案['id'], name=unique_name,
                             expression='0 0 3 * * ?')


def test_表达式与执行时间_同时传被拒绝(job_client, 锚点方案, unique_name):
    """负面用例：expression 与 execute_time 互斥，同时传应报错。

    语义：周期执行（crontab）和单次执行（时间戳）不能混在一张单上。
    """
    with pytest.raises(JobError):
        job_client.save_cron(job_plan_id=锚点方案['id'], name=unique_name,
                             expression='0 0 3 * *',
                             execute_time=int(1_800_000_000_000))


def test_删除定时任务_列表消失(job_client, 锚点方案, unique_name):
    """对应手动步骤：删除定时 → 列表里查不到。"""
    cron = job_client.save_cron(job_plan_id=锚点方案['id'], name=unique_name,
                                expression='0 0 3 * *')
    job_client.delete_cron(cron['id'])

    crons = job_client.get_cron_list(cron_id=cron['id'])
    assert crons == [], f'已删除的定时任务不应还在列表: {crons}'
