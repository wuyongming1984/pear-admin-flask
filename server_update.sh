#!/bin/bash
# 服务器端更新和重新部署脚本

set -e

echo "=================================================="
echo "Pear Admin Flask 服务器更新脚本"
echo "=================================================="
echo

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在项目目录
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误：请在项目根目录执行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}[1/6] 停止当前服务...${NC}"
docker-compose down

echo
echo -e "${GREEN}[2/6] 拉取最新代码...${NC}"
git pull origin main || {
    echo -e "${YELLOW}警告：Git 拉取失败，跳过此步骤${NC}"
}

echo
echo -e "${GREEN}[3/6] 检查 .env 文件...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}.env 文件不存在，创建新的配置文件${NC}"
    
    # 生成随机密钥
    SECRET_KEY=$(openssl rand -hex 32)
    MYSQL_ROOT_PASSWORD=$(openssl rand -base64 18)
    MYSQL_PASSWORD=$(openssl rand -base64 18)
    
    cat > .env << EOL
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
EOL
    
    echo -e "${GREEN}已创建 .env 文件${NC}"
    echo -e "${YELLOW}请保存以下密码信息：${NC}"
    echo "MySQL Root 密码: ${MYSQL_ROOT_PASSWORD}"
    echo "MySQL 应用密码: ${MYSQL_PASSWORD}"
    echo "Flask Secret Key: ${SECRET_KEY}"
else
    echo -e "${GREEN}.env 文件已存在${NC}"
fi

echo
echo -e "${GREEN}[4/6] 重新构建并启动服务...${NC}"
docker-compose up -d --build

echo
echo -e "${GREEN}[5/6] 等待 MySQL 启动...${NC}"
sleep 30

echo
echo -e "${GREEN}[6/6] 初始化数据库...${NC}"
docker-compose exec -T web flask init || {
    echo -e "${YELLOW}数据库可能已经初始化过了${NC}"
}

echo
echo "=================================================="
echo -e "${GREEN}✅ 服务更新完成！${NC}"
echo "=================================================="
echo
echo "服务状态："
docker-compose ps
echo
echo "应用地址: http://$(curl -s ifconfig.me):5050"
echo
echo "常用命令："
echo "  查看日志: docker-compose logs -f"
echo "  重启服务: docker-compose restart"
echo "  停止服务: docker-compose down"
echo
