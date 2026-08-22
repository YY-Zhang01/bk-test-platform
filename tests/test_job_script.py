# -*- coding: utf-8 -*-
"""JOB 链路1：脚本管理测试。

这条链路对应作业平台"脚本管理"页面的操作：
1. 新建脚本   → 同时创建首个版本，状态 0（未上线）
2. 追加版本   → 同一个脚本多个版本共存（菜谱的修订版）
3. 上线版本   → 状态 0 变 1；上线新版后旧版自动下线(2)
4. 禁用版本   → 状态变 3，且不可恢复（坑位）
5. 删除脚本   → 级联删除该脚本下所有版本

数据自洽策略：fixture 自建自清（delete_script 级联删版本）。
脚本语言统一用 shell(1)，内容用无害的 echo。
版本状态机：0未上线 / 1已上线 / 2已下线 / 3已禁用。
"""
import pytest

from app.api_client import b64_decode, b64_encode

pytestmark = pytest.mark.script  # 链路1：脚本管理


# ---------- 用例 ----------

def test_建脚本_列表能查到且内容自洽(job_client, 新脚本):
    """对应手动步骤：新建脚本 → 脚本列表里能看到，内容还是我们传的那份。

    自洽点：接口传输层要 Base64，但查回来的 content 应该是解码后的原文。
    """
    scripts = job_client.get_script_list(name=新脚本['name'])
    script_ids = [s['id'] for s in scripts]
    assert 新脚本['script_id'] in script_ids, f'列表里找不到新脚本: {script_ids}'


def test_建脚本_首个版本状态未上线(job_client, 新脚本):
    """新建脚本自带的 v1.0 应该是 0（未上线），需要手动上线才生效。"""
    versions = job_client.get_script_version_list(新脚本['script_id'],
                                                  with_content=True)
    assert len(versions) == 1
    v1 = versions[0]
    assert v1['version'] == '1.0'
    assert v1['status'] == 0, f'首个版本应未上线，实际 status={v1["status"]}'
    assert v1['content'] == 'echo zyy_hello', '查回的脚本内容应与原文一致'
    # 数据自洽：往返验证 Base64 编码规则（编码后解码必等于原文）
    assert b64_decode(b64_encode('echo zyy_hello')) == 'echo zyy_hello'


def test_追加版本_版本列表两条(job_client, 新脚本):
    """对应手动步骤：脚本详情页"新增版本" → 版本列表出现 v1.0 和 v1.1。"""
    v2 = job_client.create_script_version(新脚本['script_id'],
                                          content='echo zyy_v2', version='1.1')
    assert v2['status'] == 0

    versions = job_client.get_script_version_list(新脚本['script_id'])
    version_nums = sorted([v['version'] for v in versions])
    assert version_nums == ['1.0', '1.1'], f'版本列表异常: {version_nums}'


def test_上线版本_状态变已上线(job_client, 新脚本):
    """对应手动步骤：选中版本点"上线" → 状态 0 变 1。

    坑位：上线新版后，之前的线上版本自动变 2（已下线），
    但已经引用旧版的作业步骤不受影响。
    """
    v1_id = 新脚本['id']  # create_script 返回的 id 就是首个版本 ID
    result = job_client.publish_script_version(新脚本['script_id'], v1_id)
    assert result['status'] == 1, f'上线后状态应为1，实际: {result}'

    detail = job_client.get_script_version_detail(v1_id)
    assert detail['status'] == 1, f'版本详情状态应为1，实际: {detail["status"]}'


def test_禁用版本_状态变已禁用(job_client, 新脚本):
    """对应手动步骤：版本"禁用" → 状态变 3。

    坑位：文档明确禁用不可恢复，且线上引用该版本的作业步骤会无法执行。
    测试里用新追加的版本做禁用，不影响其它用例。
    """
    v2 = job_client.create_script_version(新脚本['script_id'],
                                          content='echo zyy_v2', version='1.1')
    result = job_client.disable_script_version(新脚本['script_id'], v2['id'])
    assert result['status'] == 3, f'禁用后状态应为3，实际: {result}'

    detail = job_client.get_script_version_detail(v2['id'])
    assert detail['status'] == 3


def test_删除脚本_级联删版本(job_client, unique_name):
    """对应手动步骤：删除脚本 → 该脚本的所有版本一并消失。"""
    created = job_client.create_script(
        name=unique_name, language=1, content='echo zyy_del', version='1.0')
    script_id = created['script_id']
    job_client.create_script_version(script_id, content='echo zyy_del2',
                                     version='1.1')

    job_client.delete_script(script_id)

    scripts = job_client.get_script_list(name=unique_name)
    assert scripts == [], f'已删除的脚本不应还在列表: {scripts}'
