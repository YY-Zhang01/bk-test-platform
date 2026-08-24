# 架构文档

> 本文回答一个问题：**这台「双系统体检机」由哪些零件组成、怎么拼起来的、为什么这么拼**。
> 面试时被问「讲讲你的项目架构」或「为什么这么设计」，照本文讲即可。

## 一、一句话定位

给蓝鲸 **CMDB** 和 **JOB** 两个系统做全方位测试的平台：pytest 分层用例做「测试内核」，
FastAPI 单文件做「Web 入口」，SQLite 做「历史留痕」，客户端封装层做「与蓝鲸打交道的翻译官」。

```
┌─────────────────────────────────────────────────────────────┐
│                     Web 平台（web_app.py）                    │
│   总览 / 跑测试 / 接口调试 / 报告 / AI 生成 / 用例库           │
└───────────────┬──────────────────────────────┬──────────────┘
                │ 调客户端                       │ 调存储 / 用例索引
                ▼                                ▼
┌───────────────────────────────┐   ┌─────────────────────────┐
│ 客户端封装层（翻译官）           │   │ 支撑层                   │
│  BaseClient 基类               │   │  storage.py  SQLite 留痕 │
│   ├─ JobClient（jobv3 组件）   │   │  case_index.py 用例索引  │
│   └─ CmdbClient（cc 组件）     │   │  gen_cases.py AI 生成    │
└───────────────┬───────────────┘   │  envs.py 多环境          │
                │ ESB 网关          └─────────────────────────┘
                ▼
┌─────────────────────────────────────────────┐
│  蓝鲸 ESB 网关 → CMDB / JOB（被测系统）        │
└─────────────────────────────────────────────┘

                ▲ pytest 测试层
┌─────────────────────────────────────────────┐
│  tests/ 分层用例（111 个，直接调客户端）        │
│  conftest.py 提供 client fixture + 诚实 skip  │
└─────────────────────────────────────────────┘
```

## 二、模块组成（app/ 目录，9 个模块）

| 模块 | 职责 | 一句话 |
|------|------|--------|
| `base_client.py` | ESB 客户端基类 | 统一「拼 URL + 三件套 + 查结果」，子类只写差异 |
| `api_client.py` | JOB 客户端（jobv3 组件） | 封装 38 个 ESB 接口 + 1 个轮询组合方法，按 6 条链路分组 |
| `cmdb_client.py` | CMDB 客户端（cc 组件） | 封装 7 读 + 3 写接口，独立链路 + 跨系统数据源 |
| `envs.py` | 多环境管理 | 一套代码切多套环境（体验/本地 CMDB/生产），凭证不入库 |
| `job_config.py` | 单环境配置 | 模板默认值入库，真凭证走 `job_config_local.py`（gitignore） |
| `web_app.py` | Web 平台 | FastAPI 单文件，内嵌 HTML/JS，六大模块收进一个网页 |
| `storage.py` | SQLite 留痕 | 运行历史 + 接口调试日志，趋势图数据源 |
| `case_index.py` | 用例索引 | ast 提取测试函数，供「用例库」页 + 导出 CSV |
| `gen_cases.py` | AI 用例生成 | apidoc 喂大模型，产出用例草稿（人来把关） |

**依赖方向（单向，不循环）**：Web / 测试 → 客户端 → ESB；Web → 支撑层；客户端 → envs/job_config。

## 三、分层架构（两层「分层」别混）

本项目有**两套正交的分层**，面试常被追问，提前分清：

### 1. 测试分层（金字塔，测什么）

```
L3 连块测 integration（9 个）     两系统连起来对不对
L2 分开测（53 个）                JOB 六链路 + CMDB 链路，各自单独测
L1 工具层（22 个）                先保证自己写的工具没坏
     └ 横切：边界（12）+ 安全（7）
```

- 分开测 = 故障隔离（挂了问题一定在自己）
- 连块测 = 抓集成缺陷（两边各自对，放一起才暴露）
- 另有**正交口径**：43 个不依赖蓝鲸「现在能跑」，68 个依赖账号「诚实 skip」

### 2. 代码分层（怎么实现）

| 层 | 文件 | 依赖 |
|---|---|---|
| 表示层 | `web_app.py` | 客户端 + 支撑层 |
| 领域层 | `api_client.py` / `cmdb_client.py` | `base_client` + `envs`/`job_config` |
| 基础设施层 | `storage.py` / `case_index.py` / `gen_cases.py` | 无（标准库 / requests） |

## 四、三条数据流

### 流 1：测试执行（pytest → 蓝鲸 → 断言）

```
pytest 收集 tests/
  → conftest 提供 client fixture（凭证没配就 skip）
  → JobClient/CmdbClient._call() 拼 URL + 三件套 + 结果检查
  → 蓝鲸 ESB 网关 → CMDB/JOB 真实接口
  → 返回 {result, code, data}，客户端查 result/code
  → 断言业务结果 → passed/failed/skipped
```

### 流 2：Web 接口调试（在线调只读接口）

```
网页「接口调试」→ POST /api/probe {target, api, params}
  → 白名单校验（只读接口，写操作一律拒绝）
  → 客户端调用 → 蓝鲸
  → storage.log_probe() 留痕（每次调用都记，写失败不阻塞）
```

### 流 3：AI 用例生成（人来把关）

```
网页「AI 生成」→ POST /api/gen/generate {api_name, requirement}
  → gen_cases.call_llm() 把 apidoc + 需求喂大模型
  → 生成草稿 → 前端「验证可收集」（pytest --collect-only）
  → 通过后写入 tests/test_{api_name}_ai.py
```

## 五、关键设计决策（面试「为什么」的弹药）

| 决策 | 为什么这么做 | 反例/代价 |
|------|------------|----------|
| `BaseClient` 基类抽象 | 加新蓝鲸平台从「复制一份」变「填一份配置」；认证逻辑只维护一处 | 过度抽象会藏坑，所以只抽「真公共」的认证/调接口/查结果 |
| 多环境（`envs.py` 叠加式） | 切环境不改代码；真凭证走 `envs.local.json` 不入库 | 叠加式保留 `job_config.py`，旧用法不破坏 |
| 诚实 skip 不造假绿 | 没账号就 skip，面试官是行家，假绿一秒穿帮且穿帮即出局 | 68 个用例等账号，暂时跑不满 |
| `platform` marker 防递归 | Web 层测试会 subprocess 再起 pytest，不排除会无限递归（踩过 70s 超时） | 拆掉任何一半都会复发 |
| SQLite 而非 jsonl | 结构化聚合、并发安全、零运维 | 单机文件库，不做多实例共享（够用） |
| FastAPI 单文件内嵌 HTML | 阶段 0「有脸可用」，零构建零依赖 | 不做前端工程，复杂交互受限 |
| 写操作接口调试白名单拒绝 | 在线调试只开放只读，防止误操作搞脏共享体验环境 | 调试不了写接口（有需要再单开） |

## 六、目录结构

```
job-test/
├── app/                  # 产品代码（9 模块，见第二节）
├── tests/                # 分层用例（111 个 / 103 函数）+ tests/ui/（5 个 UI 用例）
├── scripts/              # 工具：run_tests 统一入口 / export_cases 导 CSV /
│                         #       gen_api_docs 生成 API 参考 / locustfile 压测
├── docs/                 # 业务笔记、API 文档、架构文档、面试弹药
│   ├── apidoc/           # JOB 38 份接口文档
│   ├── apidoc_cmdb/      # CMDB 7 份接口文档
│   └── research/         # CMDB 页面访谈 + ESB 调研快照
├── data/                 # SQLite 数据库（gitignore）
├── reports/              # pytest-html 报告（gitignore）
├── pytest.ini            # 13 个 marker + 分层约定
└── requirements.txt
```

## 七、技术选型与理由

| 选型 | 理由 |
|------|------|
| Python 3.12 + pytest | 测试岗位主流，参数化/标记/fixture 支持分层 |
| FastAPI | 轻量、自带文档、单文件即可跑；不引入前端工程 |
| requests | 调 ESB 够用，无异步需求 |
| SQLite（标准库 sqlite3） | 零运维留痕，单文件即可 |
| Locust | 只读接口压测，代码式定义场景 |
| Playwright（tests/ui/） | 浏览器自动化，用系统 Edge（channel=msedge）跑 |
| ast 解析（case_index） | 不运行代码也能提取用例清单，安全无副作用 |
