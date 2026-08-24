# 查询集群

## 功能描述

查业务下的集群（拓扑第 1 层，集群下挂模块）。用途：校验拓扑结构完整，集群-模块两层树无孤儿模块。

## 请求参数

| 字段 | 类型 | 必选 | 描述 |
|---|---|---|---|
| bk_supplier_account | string | 是 | 供应商账号，默认 0 |
| bk_biz_id | int | 是 | 业务 ID |
| page | object | 否 | 分页 {start, limit, sort} |
