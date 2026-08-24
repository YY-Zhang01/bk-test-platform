# -*- coding: utf-8 -*-
"""JOB API 封装层（ESB 接口）。

把蓝鲸作业平台（bk-job）的 ESB 接口封装成 python 方法，pytest 用例只关心
业务动作，不关心 HTTP 细节。参数名全部按官方文档编写，本地存档在 apidoc/。

ESB 调用规范（与 CMDB 的 /api/v3 完全不同，面试常问）：
1. 认证三件套：bk_app_code / bk_app_secret / bk_token，每个请求都带
2. URL 统一格式：{ESB_HOST}/api/c/compapi/v2/jobv3/{接口名}/
3. 返回统一结构：{result, code, message, data, permission}
   业务成功 = result 为 true 且 code 为 0，否则抛 JobError

接口清单（按 6 条链路分组，共 38 个）：
- 链路1 脚本管理：create_script / get_script_list / create_script_version /
  get_script_version_list / get_script_version_detail / publish_script_version /
  disable_script_version / delete_script_version / delete_script
- 链路2 快速执行：fast_execute_script / get_job_instance_status /
  get_job_instance_ip_log / operate_job_instance / operate_step_instance
- 链路3 作业编排：get_job_template_list / get_job_plan_list / get_job_plan_detail /
  execute_job_plan / get_job_instance_list / get_job_instance_global_var_value
- 链路4 定时任务：save_cron / get_cron_list / get_cron_detail /
  update_cron_status / delete_cron
- 链路5 账号与安全：create_account / get_account_list / delete_account /
  check_script / create_dangerous_rule / get_dangerous_rule_list /
  enable_dangerous_rule / disable_dangerous_rule / delete_dangerous_rule
- 链路6 文件与SQL：push_config_file / fast_transfer_file /
  generate_local_file_upload_url / fast_execute_sql
"""
import base64
import time

import requests

from app import job_config
from app.base_client import BaseClient, EsbError


class JobError(EsbError):
    """JOB 接口返回 result=false 或 code!=0 时抛出，带错误码方便定位。"""


def b64_encode(text: str) -> str:
    """脚本内容/参数统一 Base64 编码。

    坑位：多个参数要整体编码（"p1 p2" 当成一个整体），
    不是每个参数各编各的再拼起来。
    """
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')


def b64_decode(text: str) -> str:
    """Base64 解码（测试自洽断言用：编码后再解码必须等于原文）。"""
    return base64.b64decode(text).decode('utf-8')


def make_target_server(host_id_list=None, ip_list=None,
                       dynamic_group_list=None, topo_node_list=None) -> dict:
    """拼装 target_server（四种指定主机方式，可同时传多个取并集）。

    优先级/推荐：host_id_list > dynamic_group_list > topo_node_list > ip_list
    ip_list 官方已不推荐（管控区域维度容易踩坑）。
    dynamic_group_list 的 id 是 CMDB 动态分组 ID，这是 JOB 与 CMDB
    端到端串联的关键参数。
    """
    server = {}
    if host_id_list:
        server['host_id_list'] = host_id_list
    if ip_list:
        server['ip_list'] = ip_list
    if dynamic_group_list:
        server['dynamic_group_list'] = dynamic_group_list
    if topo_node_list:
        server['topo_node_list'] = topo_node_list
    return server


class JobClient(BaseClient):
    """作业平台 ESB 客户端。

    构造时读取 job_config.py；scope 相关的接口自动带 bk_scope_type/bk_scope_id，
    少数无资源范围的接口（check_script、高危规则系列）不带。
    认证/调接口/查结果复用 BaseClient，这里只保留 scope 相关差异。
    """

    component = 'jobv3'
    error_class = JobError

    def __init__(self, esb_host=None, app_code=None, app_secret=None,
                 token=None, scope_type=None, scope_id=None):
        super().__init__(esb_host, app_code, app_secret, token)
        self.scope_type = scope_type or job_config.BK_SCOPE_TYPE
        self.scope_id = scope_id or job_config.BK_SCOPE_ID

    def _scope(self, extra: dict | None = None) -> dict:
        """拼 bk_scope 参数。注意文档要求 string，这里统一转 str。"""
        params = {'bk_scope_type': self.scope_type,
                  'bk_scope_id': str(self.scope_id)}
        if extra:
            params.update(extra)
        return params

    # ---------------- 链路1：脚本管理 ---------------- #

    def create_script(self, name: str, language: int, content: str,
                      version: str, description: str = '',
                      version_desc: str = '') -> dict:
        """新建脚本（同时创建首个版本）。

        返回 data：{id: 首个版本ID, script_id: 脚本ID, status: 0未上线}
        脚本语言：1-shell 2-bat 3-perl 4-python 5-powershell 6-sql
        内容 content 必须 Base64（本函数自动编码）。
        """
        params = self._scope({
            'name': name,
            'script_language': language,
            'content': b64_encode(content),
            'version': version,
            'description': description,
            'version_desc': version_desc,
        })
        return self._call('create_script', params)

    def get_script_list(self, name: str = None, language: int = 0,
                        start: int = 0, length: int = 100) -> list:
        """业务脚本列表（name 模糊查询）。"""
        params = self._scope({'name': name, 'script_language': language,
                              'start': start, 'length': length})
        return self._call('get_script_list', params)['data']

    def create_script_version(self, script_id: str, content: str,
                              version: str, version_desc: str = '') -> dict:
        """给已有脚本追加新版本，返回 data：{id: 版本ID, status: 0}。"""
        params = self._scope({'script_id': script_id,
                              'content': b64_encode(content),
                              'version': version,
                              'version_desc': version_desc})
        return self._call('create_script_version', params)

    def get_script_version_list(self, script_id: str,
                                with_content: bool = False,
                                start: int = 0, length: int = 100) -> list:
        """脚本版本列表，元素含 {id, version, status, ...}。"""
        params = self._scope({'script_id': script_id,
                              'return_script_content': with_content,
                              'start': start, 'length': length})
        return self._call('get_script_version_list', params)['data']

    def get_script_version_detail(self, version_id: int) -> dict:
        """脚本版本详情（按版本 ID 查）。"""
        return self._call('get_script_version_detail',
                          self._scope({'id': version_id}))

    def publish_script_version(self, script_id: str,
                               version_id: int) -> dict:
        """上线脚本版本，返回 data：{id, script_id, status: 1}。

        上线后，之前的线上版本自动变"已下线(2)"，不影响已配置的作业。
        """
        return self._call('publish_script_version',
                          self._scope({'script_id': script_id,
                                       'script_version_id': version_id}))

    def disable_script_version(self, script_id: str,
                               version_id: int) -> dict:
        """禁用脚本版本，返回 data：{id, script_id, status: 3}。

        坑位：禁用不可恢复！且线上引用该版本的作业步骤会无法执行。
        """
        return self._call('disable_script_version',
                          self._scope({'script_id': script_id,
                                       'script_version_id': version_id}))

    def delete_script_version(self, script_id: str, version_id: int):
        """删除单个脚本版本。"""
        return self._call('delete_script_version',
                          self._scope({'script_id': script_id,
                                       'script_version_id': version_id}))

    def delete_script(self, script_id: str):
        """删除脚本，级联删除该脚本下所有版本。"""
        return self._call('delete_script', self._scope({'script_id': script_id}))

    # ---------------- 链路2：快速执行 ---------------- #

    def fast_execute_script(self, content: str = None, script_id: str = None,
                            script_version_id: int = None, param: str = None,
                            language: int = 1, account_alias: str = None,
                            account_id: int = None, target_server: dict = None,
                            task_name: str = None, timeout: int = None,
                            is_param_sensitive: int = 0,
                            callback_url: str = None) -> dict:
        """快速执行脚本（JOB 最核心能力），返回
        data：{job_instance_name, job_instance_id, step_instance_id}

        坑位1：脚本内容优先级 script_version_id > script_id > script_content，
        本函数对应只传其中一个。
        坑位2：content / param 必须 Base64（本函数自动编码）。
        坑位3：account_alias 与 account_id 必须存在一个，同时传时 account_id 优先。
        坑位4：用 script_content 时必须指定 script_language。
        """
        params = {'is_param_sensitive': is_param_sensitive,
                  'callback_url': callback_url}
        if script_version_id is not None:
            params['script_version_id'] = script_version_id
        elif script_id:
            params['script_id'] = script_id
        elif content is not None:
            # 优先级契约：version_id > script_id > content，互斥只传一个，
            # 避免调用方误以为 content 会生效
            params['script_content'] = b64_encode(content)
            params['script_language'] = language
        if param is not None:
            params['script_param'] = b64_encode(param)
        if account_id:
            params['account_id'] = account_id
        if account_alias:
            params['account_alias'] = account_alias
        if target_server:
            params['target_server'] = target_server
        if task_name:
            params['task_name'] = task_name
        if timeout is not None:
            # 注意不能用 if timeout：会把非法值 0 过滤掉，
            # 导致负面用例（服务端应拒绝 0）永远发不出去
            params['timeout'] = timeout
        return self._call('fast_execute_script', self._scope(params))

    def get_job_instance_status(self, job_instance_id: int,
                                return_ip_result: bool = False) -> dict:
        """查作业实例状态，返回 data：{finished, job_instance: {status, ...},
        step_instance_list: [{status, ...}]}。

        状态码：1等待执行 2正在执行 3成功 4失败 7等待确认
        10强制终止中 11强制终止成功 13确认终止
        """
        return self._call('get_job_instance_status',
                          self._scope({'job_instance_id': job_instance_id,
                                       'return_ip_result': return_ip_result}))

    def wait_finished(self, job_instance_id: int, timeout: int = 120) -> dict:
        """组合动作：轮询作业实例状态直到执行结束（默认最多等 120 秒）。

        作业执行是异步任务，fast_execute_script 只返回"取号单"，
        必须反复查状态直到 finished=true。
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            data = self.get_job_instance_status(job_instance_id)
            if data['finished']:
                return data
            time.sleep(3)
        raise JobError(f'作业实例 {job_instance_id} 在 {timeout}s 内未执行完')

    def get_job_instance_ip_log(self, job_instance_id: int,
                                step_instance_id: int, host_id: int = None,
                                cloud_id: int = None, ip: str = None) -> dict:
        """按主机查执行日志，返回 data：{log_type, ip, log_content, ...}。

        坑位：bk_host_id 存在时忽略 bk_cloud_id/ip。
        """
        params = {'job_instance_id': job_instance_id,
                  'step_instance_id': step_instance_id}
        if host_id:
            params['bk_host_id'] = host_id
        if cloud_id is not None:
            params['bk_cloud_id'] = cloud_id
        if ip:
            params['ip'] = ip
        return self._call('get_job_instance_ip_log', self._scope(params))

    def operate_job_instance(self, job_instance_id: int,
                             operation_code: int = 1) -> dict:
        """操作作业实例。operation_code：1=终止作业。"""
        return self._call('operate_job_instance',
                          self._scope({'job_instance_id': job_instance_id,
                                       'operation_code': operation_code}))

    def operate_step_instance(self, job_instance_id: int,
                              step_instance_id: int,
                              operation_code: int) -> dict:
        """操作步骤实例。operation_code：
        2失败IP重做 3忽略错误 6确认继续 8全部重试 9终止确认流程
        10重新发起确认 11进入下一步 12强制跳过。
        """
        return self._call('operate_step_instance',
                          self._scope({'job_instance_id': job_instance_id,
                                       'step_instance_id': step_instance_id,
                                       'operation_code': operation_code}))

    # ---------------- 链路3：作业编排 ---------------- #

    def get_job_template_list(self, name: str = None, creator: str = None,
                              start: int = 0, length: int = 100) -> list:
        """作业模板列表（模板本身只能在 Web 端创建，API 只读）。"""
        params = self._scope({'name': name, 'creator': creator,
                              'start': start, 'length': length})
        return self._call('get_job_template_list', params)['data']

    def get_job_plan_list(self, job_template_id: int = None,
                          name: str = None, creator: str = None,
                          start: int = 0, length: int = 100) -> list:
        """执行方案列表。一个模板可派生多个方案（一对多）。"""
        params = self._scope({'job_template_id': job_template_id,
                              'name': name, 'creator': creator,
                              'start': start, 'length': length})
        return self._call('get_job_plan_list', params)['data']

    def get_job_plan_detail(self, job_plan_id: int) -> dict:
        """执行方案详情，data 含 global_var_list（方案可改的全局变量）。"""
        return self._call('get_job_plan_detail',
                          self._scope({'job_plan_id': job_plan_id}))

    def execute_job_plan(self, job_plan_id: int,
                         global_var_list: list = None,
                         callback_url: str = None) -> dict:
        """启动执行方案，返回 data：{job_instance_name, job_instance_id}。

        global_var_list 传了就覆盖方案默认值，不传用默认值。
        """
        params = {'job_plan_id': job_plan_id, 'callback_url': callback_url}
        if global_var_list:
            params['global_var_list'] = global_var_list
        return self._call('execute_job_plan', self._scope(params))

    def get_job_instance_list(self, create_time_start: int,
                              create_time_end: int,
                              job_instance_id: int = None,
                              job_cron_id: int = None, operator: str = None,
                              name: str = None, launch_mode: int = None,
                              status: int = None, type_: int = None,
                              ip: str = None,
                              start: int = 0, length: int = 100) -> list:
        """作业实例列表（执行历史）。

        坑位：create_time_start/end 必传（Unix 毫秒时间戳）；
        传 job_instance_id 时其他过滤条件被忽略。
        launch_mode：1页面执行 2API调用 3定时执行。
        """
        params = self._scope({'create_time_start': create_time_start,
                              'create_time_end': create_time_end,
                              'job_instance_id': job_instance_id,
                              'job_cron_id': job_cron_id,
                              'operator': operator, 'name': name,
                              'launch_mode': launch_mode, 'status': status,
                              'type': type_, 'ip': ip,
                              'start': start, 'length': length})
        return self._call('get_job_instance_list', params)['data']

    def get_job_instance_global_var_value(self, job_instance_id: int) -> dict:
        """取作业实例全局变量的实际值，data 含 step_instance_var_list。"""
        return self._call('get_job_instance_global_var_value',
                          self._scope({'job_instance_id': job_instance_id}))

    # ---------------- 链路4：定时任务 ---------------- #

    def save_cron(self, job_plan_id: int, name: str,
                  expression: str = None, execute_time: int = None,
                  cron_id: int = None, global_var_list: list = None) -> dict:
        """新建/更新定时任务。

        坑位1：新建后默认"暂停"，必须 update_cron_status 才真正跑。
        坑位2：expression（分 时 日 月 周，如 0/5 * * * *）与 execute_time
        互斥，二者只可传一个；新建时不能同时为空。
        坑位3：expression 不支持 `?`（与标准 cron/Quartz 的差异）。
        更新时传 cron_id。
        """
        params = {'job_plan_id': job_plan_id, 'name': name,
                  'id': cron_id, 'expression': expression,
                  'execute_time': execute_time,
                  'global_var_list': global_var_list}
        return self._call('save_cron', self._scope(params))

    def get_cron_list(self, cron_id: int = None, name: str = None,
                      status: int = None, start: int = 0,
                      length: int = 100) -> list:
        """定时任务列表。status：1已启动 2已暂停。"""
        params = self._scope({'id': cron_id, 'name': name, 'status': status,
                              'start': start, 'length': length})
        return self._call('get_cron_list', params)['data']

    def get_cron_detail(self, cron_id: int) -> dict:
        """定时任务详情，data 含 {expression, status, global_var_list, ...}。"""
        return self._call('get_cron_detail', self._scope({'id': cron_id}))

    def update_cron_status(self, cron_id: int, status: int) -> dict:
        """更新定时任务状态。status：1启动 2暂停。"""
        return self._call('update_cron_status',
                          self._scope({'id': cron_id, 'status': status}))

    def delete_cron(self, cron_id: int):
        """删除定时任务。"""
        return self._call('delete_cron', self._scope({'id': cron_id}))

    # ---------------- 链路5：账号管理与高危命令检测 ---------------- #

    def create_account(self, account: str, type_: int, category: int = 1,
                       password: str = None, alias: str = None,
                       description: str = '') -> dict:
        """创建系统账号，返回 data：{id, account, type, os, ...}。

        type：1-Linux 2-Windows。
        坑位：type=Windows 时 password 必传，Linux 可不传。
        """
        params = self._scope({'account': account, 'type': type_,
                              'category': category, 'password': password,
                              'alias': alias, 'description': description})
        return self._call('create_account', params)

    def get_account_list(self, account: str = None, category: int = None,
                         alias: str = None, start: int = 0,
                         length: int = 100) -> list:
        """执行账号列表。"""
        params = self._scope({'account': account, 'category': category,
                              'alias': alias, 'start': start, 'length': length})
        return self._call('get_account_list', params)['data']

    def delete_account(self, account_id: int) -> dict:
        """删除账号，返回 data 是被删账号的信息。"""
        return self._call('delete_account', self._scope({'id': account_id}))

    def check_script(self, content: str, language: int = 1) -> list:
        """高危脚本检测（无 bk_scope 参数，全局能力）。

        返回命中列表：[{line, line_content, match_content, level, description}]
        level：1警告 2错误 3致命。
        """
        return self._call('check_script', {
            'script_language': language,
            'content': b64_encode(content),
        })

    def create_dangerous_rule(self, expression: str, language_list: list,
                              description: str, action: int = 2) -> dict:
        """新建高危语句检测规则（无 bk_scope 参数，全局资源）。

        expression 是匹配表达式（正则）；action：1扫描 2拦截。
        返回 data：{id, expression, status: 0停用, ...}。
        """
        return self._call('create_dangerous_rule', {
            'expression': expression,
            'script_language_list': language_list,
            'description': description,
            'action': action,
        })

    def get_dangerous_rule_list(self, expression: str = None,
                                action: int = None) -> list:
        """高危规则列表（无 bk_scope 参数），data 直接是数组。"""
        params = {'expression': expression, 'action': action}
        return self._call('get_dangerous_rule_list', params)

    def enable_dangerous_rule(self, rule_id: int) -> dict:
        """启用高危规则，返回 data：{id, status: 1}。"""
        return self._call('enable_dangerous_rule', {'id': rule_id})

    def disable_dangerous_rule(self, rule_id: int) -> dict:
        """停用高危规则，返回 data：{id, status: 0}。"""
        return self._call('disable_dangerous_rule', {'id': rule_id})

    def delete_dangerous_rule(self, rule_id: int):
        """删除高危规则。"""
        return self._call('delete_dangerous_rule', {'id': rule_id})

    # ---------------- 链路6：文件分发与 SQL 执行 ---------------- #

    def push_config_file(self, file_name: str, content: str,
                         file_target_path: str, account_alias: str,
                         target_server: dict, task_name: str = None) -> dict:
        """分发配置文件（小纯文本文件），返回 data：{job_instance_name,
        job_instance_id}。

        坑位：返回里没有 step_instance_id（与其它快速执行接口不同）。
        文件内容 content 自动 Base64。
        """
        params = {'account_alias': account_alias,
                  'file_target_path': file_target_path,
                  'file_list': [{'file_name': file_name,
                                 'content': b64_encode(content)}],
                  'target_server': target_server,
                  'task_name': task_name}
        return self._call('push_config_file', self._scope(params))

    def generate_local_file_upload_url(self, file_name_list: list) -> dict:
        """本地文件分发三步流程第1步：生成上传 URL。
        返回 data.url_map：{文件名: {upload_url, path}}。

        坑位：拿 upload_url 后用 HTTP PUT 上传文件内容（Content-Type
        application/octet-stream，URL 自带凭据，无需再加鉴权头）；
        第3步 fast_transfer_file 的源文件路径填这里返回的 path。
        """
        return self._call('generate_local_file_upload_url',
                          self._scope({'file_name_list': file_name_list}))

    def fast_transfer_file(self, file_target_path: str, file_source_list: list,
                           account_alias: str = None, account_id: int = None,
                           target_server: dict = None, timeout: int = None,
                           transfer_mode: int = 2, task_name: str = None,
                           callback_url: str = None) -> dict:
        """快速分发文件，返回 data：{job_instance_name, job_instance_id,
        step_instance_id}。

        file_source_list 元素：{file_list, account:{id/alias}, server,
        file_type(1服务器文件/3第三方), file_source_id/file_source_code}。
        坑位：目标执行账号 account_alias/account_id 必须存在一个；
        本地文件源要先用 generate_local_file_upload_url 拿 path。
        """
        params = {'file_target_path': file_target_path,
                  'file_source_list': file_source_list,
                  'account_alias': account_alias,
                  'account_id': account_id,
                  'target_server': target_server,
                  'timeout': timeout,
                  'transfer_mode': transfer_mode,
                  'task_name': task_name,
                  'callback_url': callback_url}
        return self._call('fast_transfer_file', self._scope(params))

    def fast_execute_sql(self, db_account_id: int,
                         script_content: str = None,
                         script_id: str = None,
                         script_version_id: int = None,
                         target_server: dict = None,
                         timeout: int = None,
                         callback_url: str = None) -> dict:
        """快速执行 SQL 脚本，返回 data：{job_instance_name,
        job_instance_id, step_instance_id}。

        坑位1：db_account_id 必填（账号管理里的 DB 账号，与系统账号不是
        一回事）；SQL 执行不认 account_alias。
        坑位2：脚本优先级同快速执行：script_version_id > script_id >
        script_content，只传其中一个。
        """
        params = {'db_account_id': db_account_id,
                  'target_server': target_server,
                  'timeout': timeout,
                  'callback_url': callback_url}
        if script_version_id is not None:
            params['script_version_id'] = script_version_id
        elif script_id:
            params['script_id'] = script_id
        elif script_content is not None:
            # 优先级同快速执行：互斥只传一个
            params['script_content'] = b64_encode(script_content)
        return self._call('fast_execute_sql', self._scope(params))
