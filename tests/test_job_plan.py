# -*- coding: utf-8 -*-
"""JOB 链路3：作业编排测试（模板 → 方案 → 实例）。

这条链路对应"作业模板 / 执行方案"页面的操作：
1. 作业模板：把多个步骤（执行脚本+分发文件）编排好沉淀成模板
   （模板只能在 Web 端创建，API 只提供查询——这是 JOB 的产品设计）
2. 执行方案：由模板派生出"点餐单"，可改参数，对外执行的是方案
3. 启动方案 → 产生作业实例 → 执行历史里可查 → 可查实例全局变量的实际值

数据自洽策略：模板/方案是"锚点数据"，需要先在体验环境 Web 端
建一个最简单的模板（见指引文档第 3 节）；找不到可用方案时跳过。
模板与方案一对多：一个模板可派生多个方案。
"""
import pytest

pytestmark = pytest.mark.plan  # 链路3：作业编排（模板→方案→实例）


# ---------- 用例 ----------

def test_模板列表_非空(job_client, 锚点模板):
    """对应手动步骤：作业模板页 → 能看到模板列表。"""
    templates = job_client.get_job_template_list()
    ids = [t['id'] for t in templates]
    assert 锚点模板['id'] in ids, f'模板列表里找不到锚点模板: {ids}'


def test_方案列表_属于对应模板(job_client, 锚点模板, 锚点方案):
    """对应手动步骤：模板详情 → 方案列表里每个方案都挂着模板 ID。

    自洽点：方案与模板的关系是一对多，方案的 job_template_id 必须回指锚点模板。
    """
    plans = job_client.get_job_plan_list(job_template_id=锚点模板['id'])
    ids = [p['id'] for p in plans]
    assert 锚点方案['id'] in ids, f'方案列表里找不到锚点方案: {ids}'
    for p in plans:
        assert p['job_template_id'] == 锚点模板['id'], \
            f"方案 {p['id']} 的模板归属错误: {p}"


def test_方案详情_含全局变量列表(job_client, 锚点方案):
    """对应手动步骤：方案详情页 → 能看到方案可改的全局变量。"""
    detail = job_client.get_job_plan_detail(锚点方案['id'])
    assert detail['job_plan_id'] == 锚点方案['id']
    assert 'global_var_list' in detail, \
        f'方案详情应含 global_var_list: {detail.keys()}'


def test_启动方案_执行历史可查(job_client, 锚点方案, recent_time_range):
    """对应手动步骤：点"执行" → 执行历史里多一条记录。

    自洽点：execute 返回的作业实例 ID，必须能在执行历史里按 ID 精确查到；
    launch_mode 应为 2（API 调用）。
    """
    result = job_client.execute_job_plan(锚点方案['id'])
    instance_id = result['job_instance_id']
    assert instance_id, f'应返回作业实例ID: {result}'

    start_ms, end_ms = recent_time_range
    history = job_client.get_job_instance_list(
        create_time_start=start_ms, create_time_end=end_ms,
        job_instance_id=instance_id)
    assert history, f'执行历史里查不到实例 {instance_id}'
    assert history[0]['id'] == instance_id
    # 通过 API 启动的实例，执行方式应为 2
    assert history[0]['launch_mode'] == 2, \
        f'API 启动的实例 launch_mode 应为 2，实际: {history[0]}'


def test_实例全局变量_能查到值(job_client, 锚点方案, recent_time_range):
    """对应手动步骤：执行详情 → 查看该次执行各变量的实际取值。

    执行一次方案后，能按实例 ID 查回全局变量的实际值（快照）。
    """
    result = job_client.execute_job_plan(锚点方案['id'])
    instance_id = result['job_instance_id']

    data = job_client.get_job_instance_global_var_value(instance_id)
    assert data['job_instance_id'] == instance_id
    # 变量值列表可能为空（方案没配变量），结构必须合法
    assert 'step_instance_var_list' in data, f'返回结构异常: {data.keys()}'


def test_覆盖全局变量_执行时传值生效(job_client, 锚点方案):
    """坑位实测：execute_job_plan 传 global_var_list 可覆盖方案默认值。

    只对方案里第一个"字符型"变量做覆盖；方案没有可覆盖变量时跳过。
    """
    detail = job_client.get_job_plan_detail(锚点方案['id'])
    string_vars = [v for v in detail.get('global_var_list', [])
                   if v.get('type') == 1]  # type 1 = 字符
    if not string_vars:
        pytest.skip('锚点方案没有字符型全局变量，无法验证覆盖')

    target = string_vars[0]
    override = [{'id': target['id'], 'value': 'zyy_override_value'}]
    result = job_client.execute_job_plan(锚点方案['id'],
                                         global_var_list=override)
    data = job_client.get_job_instance_global_var_value(result['job_instance_id'])
    # 找该变量在各步骤里的取值，应至少有一处等于覆盖值
    values = [v['value']
              for step in data['step_instance_var_list']
              for v in step['global_var_list']
              if v['name'] == target['name']]
    assert 'zyy_override_value' in values, \
        f"覆盖值未生效，实际取值: {values}"
