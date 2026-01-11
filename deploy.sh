#!/bin/bash

# Pear Admin Flask 一键部署脚本
# 使用方法：chmod +x deploy.sh && ./deploy.sh

set -e

echo "======================================"
echo "Pear Admin Flask Docker 部署脚本"
echo "======================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 root 用户运行此脚本${NC}"
    echo "使用方法: sudo ./deploy.sh"
    exit 1
fi

# 检测系统类型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo -e "${RED}无法检测系统类型${NC}"
    exit 1
fi

echo -e "${GREEN}检测到系统: $OS${NC}"
echo ""

# 1. 安装 Docker
echo "======================================"
echo "步骤 1: 安装 Docker"
echo "======================================"

if command -v docker &> /dev/null; then
    echo -e "${GREEN}Docker 已安装，版本：$(docker --version)${NC}"
else
    echo "正在安装 Docker..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt-get update
        apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
        
        # 添加 Docker 官方 GPG key
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        
        # 设置稳定版仓库
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io
        
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Alibaba"* ]]; then
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io
    else
        echo -e "${RED}不支持的操作系统${NC}"
        exit 1
    fi
    
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}Docker 安装完成${NC}"
fi

echo ""

# 2. 安装 Docker Compose
echo "======================================"
echo "步骤 2: 安装 Docker Compose"
echo "======================================"

if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}Docker Compose 已安装，版本：$(docker-compose --version)${NC}"
else
    echo "正在安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose 安装完成${NC}"
fi

echo ""

# 3. 配置环境变量
echo "======================================"
echo "步骤 3: 配置环境变量"
echo "======================================"

if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    
    # 生成随机密钥
    SECRET_KEY=$(openssl rand -hex 32)
    MYSQL_ROOT_PASSWORD=$(openssl rand -base64 16)
    MYSQL_PASSWORD=$(openssl rand -base64 16)
    
    cat > .env << EOF
# Flask 配置
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}

# MySQL 配置
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
MYSQL_DATABASE=pear_admin
MYSQL_USER=pear_admin
MYSQL_PASSWORD=${MYSQL_PASSWORD}

# 应用配置
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5050
EOF
    
    echo -e "${GREEN}.env 文件创建完成${NC}"
    echo -e "${YELLOW}重要：请保存以下密码信息${NC}"
    echo "----------------------------------------"
    echo "MySQL Root 密码: ${MYSQL_ROOT_PASSWORD}"
    echo "MySQL 应用密码: ${MYSQL_PASSWORD}"
    echo "Flask Secret Key: ${SECRET_KEY}"
    echo "----------------------------------------"
    echo -e "${YELLOW}这些信息已保存在 .env 文件中${NC}"
else
    echo -e "${GREEN}.env 文件已存在，跳过创建${NC}"
fi

echo ""

# 4. 构建和启动服务
echo "======================================"
echo "步骤 4: 构建和启动服务"
echo "======================================"

echo "正在构建 Docker 镜像..."
docker-compose build

echo ""
echo "正在启动服务..."
docker-compose up -d

echo ""
echo "等待服务启动（30秒）..."
sleep 30

echo ""

# 5. 检查服务状态
echo "======================================"
echo "步骤 5: 检查服务状态"
echo "======================================"

docker-compose ps

echo ""

# 6. 显示访问信息
echo "======================================"
echo "部署完成！"
echo "======================================"

# 获取服务器 IP
SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}应用访问地址：${NC}"
echo "  http://${SERVER_IP}:5050"
echo ""
echo -e "${YELLOW}常用命令：${NC}"
echo "  查看日志：docker-compose logs -f"
echo "  停止服务：docker-compose stop"
echo "  启动服务：docker-compose start"
echo "  重启服务：docker-compose restart"
echo "  删除服务：docker-compose down"
echo ""
echo -e "${YELLOW}注意事项：${NC}"
echo "  1. 请确保阿里云安全组已开放 5050 端口"
echo "  2. 数据库密码已保存在 .env 文件中"
echo "  3. 建议配置 Nginx 反向代理和 HTTPS"
echo "  4. 定期备份数据库和上传文件"
echo ""
echo -e "${GREEN}部署完成！${NC}"
