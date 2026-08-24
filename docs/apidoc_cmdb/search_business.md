# 查询业务列表

## 功能描述

查业务列表，可选按业务 ID 过滤。数据契约锚点：JOB 的 bk_scope_id 必须能在 CMDB 业务列表里找到，这是两系统所有联动的根。

## 请求参数

| 字段 | 类型 | 必选 | 描述 |
|---|---|---|---|
| bk_supplier_account | string | 是 | 供应商账号（CC 组件历史参数，默认 0） |
| bk_biz_id | int | 否 | 业务 ID，传了则按业务过滤 |
| page | object | 否 | 分页 {start, limit, sort} |
