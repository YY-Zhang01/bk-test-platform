# API 参考（客户端封装层）

> 本文件由 `scripts/gen_api_docs.py` 自动生成，改动客户端后重跑该脚本即可同步。
> 每个方法的完整参数说明与示例见对应接口文档目录；参数名按官方文档整理，以体验环境实测为准。

客户端都继承 `app/base_client.py` 的 `BaseClient`：统一拼 URL、带认证三件套、
检查返回 `{result, code, message, data}`；差异只在组件名与少量额外参数。

## JobClient — JOB 作业平台客户端（ESB jobv3 组件）

> 接口文档目录：`docs/apidoc/`（39 个公开方法）

| 方法 | 参数 | 作用 |
|------|------|------|
| `create_script` | name, language, content, version, description, version_desc | 新建脚本（同时创建首个版本） |
| `get_script_list` | name, language, start, length | 业务脚本列表（name 模糊查询） |
| `create_script_version` | script_id, content, version, version_desc | 给已有脚本追加新版本，返回 data：{id: 版本ID, status: 0} |
| `get_script_version_list` | script_id, with_content, start, length | 脚本版本列表，元素含 {id, version, status, ...} |
| `get_script_version_detail` | version_id | 脚本版本详情（按版本 ID 查） |
| `publish_script_version` | script_id, version_id | 上线脚本版本，返回 data：{id, script_id, status: 1} |
| `disable_script_version` | script_id, version_id | 禁用脚本版本，返回 data：{id, script_id, status: 3} |
| `delete_script_version` | script_id, version_id | 删除单个脚本版本 |
| `delete_script` | script_id | 删除脚本，级联删除该脚本下所有版本 |
| `fast_execute_script` | content, script_id, script_version_id, param, language, account_alias, account_id, target_server, task_name, timeout, is_param_sensitive, callback_url | 快速执行脚本（JOB 最核心能力），返回 |
| `get_job_instance_status` | job_instance_id, return_ip_result | 查作业实例状态，返回 data：{finished, job_instance: {status, ...}, |
| `wait_finished` | job_instance_id, timeout | 组合动作：轮询作业实例状态直到执行结束（默认最多等 120 秒） |
| `get_job_instance_ip_log` | job_instance_id, step_instance_id, host_id, cloud_id, ip | 按主机查执行日志，返回 data：{log_type, ip, log_content, ...} |
| `operate_job_instance` | job_instance_id, operation_code | 操作作业实例。operation_code：1=终止作业 |
| `operate_step_instance` | job_instance_id, step_instance_id, operation_code | 操作步骤实例。operation_code： |
| `get_job_template_list` | name, creator, start, length | 作业模板列表（模板本身只能在 Web 端创建，API 只读） |
| `get_job_plan_list` | job_template_id, name, creator, start, length | 执行方案列表。一个模板可派生多个方案（一对多） |
| `get_job_plan_detail` | job_plan_id | 执行方案详情，data 含 global_var_list（方案可改的全局变量） |
| `execute_job_plan` | job_plan_id, global_var_list, callback_url | 启动执行方案，返回 data：{job_instance_name, job_instance_id} |
| `get_job_instance_list` | create_time_start, create_time_end, job_instance_id, job_cron_id, operator, name, launch_mode, status, type_, ip, start, length | 作业实例列表（执行历史） |
| `get_job_instance_global_var_value` | job_instance_id | 取作业实例全局变量的实际值，data 含 step_instance_var_list |
| `save_cron` | job_plan_id, name, expression, execute_time, cron_id, global_var_list | 新建/更新定时任务 |
| `get_cron_list` | cron_id, name, status, start, length | 定时任务列表。status：1已启动 2已暂停 |
| `get_cron_detail` | cron_id | 定时任务详情，data 含 {expression, status, global_var_list, ...} |
| `update_cron_status` | cron_id, status | 更新定时任务状态。status：1启动 2暂停 |
| `delete_cron` | cron_id | 删除定时任务 |
| `create_account` | account, type_, category, password, alias, description | 创建系统账号，返回 data：{id, account, type, os, ...} |
| `get_account_list` | account, category, alias, start, length | 执行账号列表 |
| `delete_account` | account_id | 删除账号，返回 data 是被删账号的信息 |
| `check_script` | content, language | 高危脚本检测（无 bk_scope 参数，全局能力） |
| `create_dangerous_rule` | expression, language_list, description, action | 新建高危语句检测规则（无 bk_scope 参数，全局资源） |
| `get_dangerous_rule_list` | expression, action | 高危规则列表（无 bk_scope 参数），data 直接是数组 |
| `enable_dangerous_rule` | rule_id | 启用高危规则，返回 data：{id, status: 1} |
| `disable_dangerous_rule` | rule_id | 停用高危规则，返回 data：{id, status: 0} |
| `delete_dangerous_rule` | rule_id | 删除高危规则 |
| `push_config_file` | file_name, content, file_target_path, account_alias, target_server, task_name | 分发配置文件（小纯文本文件），返回 data：{job_instance_name, |
| `generate_local_file_upload_url` | file_name_list | 本地文件分发三步流程第1步：生成上传 URL |
| `fast_transfer_file` | file_target_path, file_source_list, account_alias, account_id, target_server, timeout, transfer_mode, task_name, callback_url | 快速分发文件，返回 data：{job_instance_name, job_instance_id, |
| `fast_execute_sql` | db_account_id, script_content, script_id, script_version_id, target_server, timeout, callback_url | 快速执行 SQL 脚本，返回 data：{job_instance_name, |

## CmdbClient — CMDB 配置平台客户端（ESB cc 组件）

> 接口文档目录：`docs/apidoc_cmdb/`（10 个公开方法）

| 方法 | 参数 | 作用 |
|------|------|------|
| `search_business` | biz_id, limit | 查业务列表。不带条件返回全量业务（受 ESB 权限限制） |
| `list_biz_hosts` | biz_id, limit, fields | 按业务查主机（全业务或指定业务） |
| `search_host` | biz_id, host_id, limit | 按条件查主机（host 模型条件查询，可返回主机完整属性） |
| `execute_dynamic_group` | group_id, biz_id, limit | 执行动态分组：返回分组"现在"圈中的主机 |
| `search_module` | biz_id, limit | 查业务下的模块（拓扑第 2 层，模块挂在集群下） |
| `search_set` | biz_id, limit | 查业务下的集群（拓扑第 1 层，集群下挂模块） |
| `search_object_attribute` | obj_id, limit | 查模型属性（字段字典） |
| `create_business` | biz_name, maintainer | 创建业务（写操作）。参数名待账号后以官方文档核实 |
| `add_host_to_biz` | host_list | 导入主机到业务（写操作）。参数名待账号后以官方文档核实 |
| `create_dynamic_group` | name, info | 创建动态分组（写操作）。参数名待账号后以官方文档核实 |

