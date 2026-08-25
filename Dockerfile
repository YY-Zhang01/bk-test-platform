# -*- coding: utf-8 -*-
# 蓝鲸双系统端到端测试平台 镜像
# 多阶段构建：先编译前端，再把后端 + 前端产物装进运行镜像，
# 这样干净环境无需本地预建 frontend/dist。
# 构建：docker build -t bk-e2e-platform .
# 运行：docker run -p 8000:8000 bk-e2e-platform
# 凭证：docker run -v "$(pwd)/app/job_config_local.py:/app/app/job_config_local.py" ...
#   （真凭证不入镜像，用挂载注入，见 app/job_config.py 的 local 覆盖机制）

# ---- 前端构建阶段 ----
FROM node:24-alpine AS frontend-build

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ---- 后端运行阶段 ----
FROM python:3.11-slim

# 镜像内固定 UTF-8，避免 pytest 中文输出乱码；HOST=0.0.0.0 让 -p 映射生效
ENV PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# 先装依赖再拷代码：requirements 没变时充分利用镜像层缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY tests/ tests/
COPY scripts/ scripts/
COPY docs/ docs/
COPY conftest.py pytest.ini LICENSE ./

# 前端产物来自上一阶段，运行时不需要 Node
COPY --from=frontend-build /build/frontend/dist/ frontend/dist/

EXPOSE 8000

# 与本地一致的启动方式（web_app.py 自带项目根定位逻辑）
CMD ["python", "app/web_app.py"]
