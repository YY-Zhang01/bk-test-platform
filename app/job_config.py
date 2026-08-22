# -*- coding: utf-8 -*-
"""JOB 测试环境配置（唯一需要手填的文件）。

体验账号到手后：
1. 把下面带 None 的项替换成真实值
2. 回到 job-test 目录运行 `pytest`
3. 用例会从"跳过"变成真正执行

凭证从哪来，见同目录《2026-08-22-JOB体验账号申请指引.md》。
"""

# ESB 网关地址。体验环境发放邮件里会给专属地址，填在这里
ESB_HOST = None

# ESB 认证三件套（每个接口请求都要带）
BK_APP_CODE = None    # 应用代号：开发者中心创建应用后获得
BK_APP_SECRET = None  # 应用密钥：与 app_code 配套
BK_TOKEN = None       # 用户 token：个人中心登录态

# 资源范围：测试业务。
# 体验环境登录作业平台后选一个业务（一般内置演示业务），
# 把业务 ID 填到 BK_SCOPE_ID
BK_SCOPE_TYPE = 'biz'
BK_SCOPE_ID = None

# ---- 以下为可选参数，不填则相关用例自动跳过 ----

# 快速执行的目标主机 ID（业务下已导入的主机）
# 不填：快速执行类用例跳过（没有主机无法真实下发脚本）
TARGET_HOST_ID = None

# Linux 执行账号别名（快速执行脚本必须指定执行账号）
ACCOUNT_ALIAS = 'root'

# 端到端用例用的 CMDB 动态分组 ID（在体验环境的 CMDB 里建好再填）
# 不填：端到端用例跳过，步骤见指引文档第 4 节
DYNAMIC_GROUP_ID = None

# 快速执行 SQL 用的 DB 账号 ID（体验环境"账号管理-DB账号"里建好再填）
# 不填：SQL 快速执行用例跳过
DB_ACCOUNT_ID = None

# ---- AI 用例生成器配置（可选，不填则 gen_cases.py 只打印获取指引）----

# 大模型 API（OpenAI 兼容协议，默认 DeepSeek）
LLM_BASE_URL = 'https://api.deepseek.com'
LLM_API_KEY = None    # DeepSeek 开放平台申请：platform.deepseek.com → API keys
LLM_MODEL = 'deepseek-chat'

# ---- 本地覆盖（模板入库、真凭证不入库）----
# 上面所有变量都是模板默认值，随 git 提交；真实凭证写同目录
# job_config_local.py（已 gitignore），导入后自动覆盖上面的值：
#   from app import job_config
#   job_config.ESB_HOST  # 读到的是 local 文件里的真值
try:
    from app.job_config_local import *  # noqa: F401,F403
except ImportError:
    pass
