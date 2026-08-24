# 查询模型属性

## 功能描述

查模型属性（字段字典）。用途：接口字段与页面对不上时查字典；也可做"字段变更回归"——上线前后比对字段集，发现模型字段被误改。核心字段 bk_host_id / bk_cloud_id 是 JOB 执行主机的最小契约。

## 请求参数

| 字段 | 类型 | 必选 | 描述 |
|---|---|---|---|
| bk_supplier_account | string | 是 | 供应商账号，默认 0 |
| bk_obj_id | string | 是 | 模型 ID，如 host（主机模型） |
| page | object | 否 | 分页 {start, limit, sort} |
