# 按业务查询主机

## 功能描述

按业务查主机列表。数据契约：主机 ID 字段是 bk_host_id，即 JOB 快速执行的 host_id 来源（两系统共用同一主机 ID）。

## 请求参数

| 字段 | 类型 | 必选 | 描述 |
|---|---|---|---|
| bk_supplier_account | string | 是 | 供应商账号，默认 0 |
| bk_biz_id | int | 是 | 业务 ID |
| page | object | 否 | 分页 {start, limit, sort} |
| fields | list | 否 | 要返回的字段列表 |
