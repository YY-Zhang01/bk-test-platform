# 按条件查询主机

## 功能描述

按 host 模型条件查询主机，可返回主机完整属性。连块测用途：按 bk_host_id 查主机详情，验证主机当前是否可被 JOB 执行。

## 请求参数

| 字段 | 类型 | 必选 | 描述 |
|---|---|---|---|
| bk_supplier_account | string | 是 | 供应商账号，默认 0 |
| bk_biz_id | int | 是 | 业务 ID |
| condition | list | 是 | 查询条件，如 [{bk_obj_id:host, condition:[{field:bk_host_id, operator:$eq, value:主机ID}]}] |
| page | object | 否 | 分页 {start, limit, sort} |
