# -*- coding: utf-8 -*-
# 蓝鲸双系统端到端测试平台 镜像
# 构建：docker build -t bk-e2e-platform .
# 运行：docker run -p 8000:8000 bk-e2e-platform
# 凭证：docker run -v "$(pwd)/app/job_config_local.py:/app/app/job_config_local.py" ...
#   （真凭证不入镜像，用挂载注入，见 app/job_config.py 的 local 覆盖机制）

FROM python:3.11-slim

# 镜像内固定 UTF-8，避免 pytest 中文输出乱码
ENV PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先装依赖再拷代码：requirements 没变时充分利用镜像层缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 与本地一致的启动方式（web_app.py 自带项目根定位逻辑）
CMD ["python", "app/web_app.py"]
