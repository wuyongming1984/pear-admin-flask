# 使用官方 Python 3.10 镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 配置国内 Debian 镜像源（阿里云）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources || \
    (echo "deb http://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
     echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
     echo "deb http://mirrors.aliyun.com/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list)

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用国内镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 安装 poetry
RUN pip install --no-cache-dir poetry==1.7.1

# 复制项目文件
COPY pyproject.toml poetry.lock* ./

# 配置 poetry 不创建虚拟环境（因为已经在容器中）
RUN poetry config virtualenvs.create false

# 更新 lock 文件并安装项目依赖
RUN poetry lock --no-update && poetry install --only main --no-interaction --no-ansi

# 复制应用代码
COPY . .

# 创建 uploads 目录
RUN mkdir -p uploads

# 暴露端口
EXPOSE 5050

# 设置环境变量
ENV FLASK_APP=pear_admin:create_app()
ENV FLASK_ENV=production

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "4", "--timeout", "120", "pear_admin:create_app()"]
