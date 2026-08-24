# 查询模块

## 功能描述

查业务下的模块（拓扑第 2 层，模块挂在集群下）。坑位：模块有 bk_set_id 指向所属集群，可校验"无主模块"（挂的集群不存在）。

## 请求参数

| 字段 | 类型 | 必选 | 描述 |
|---|---|---|---|
| bk_supplier_account | string | 是 | 供应商账号，默认 0 |
| bk_biz_id | int | 是 | 业务 ID |
| page | object | 否 | 分页 {start, limit, sort} |
