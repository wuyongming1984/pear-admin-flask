#!/bin/bash
# 阿里云服务器 - 故障诊断脚本
# 检查数据库连接、记录数和应用日志

echo "=========================================="
echo "故障诊断报告 $(date)"
echo "=========================================="
echo ""

# 1. 检查MySQL数据
echo "🔍 1. 检查数据库记录..."
echo "请输入 MySQL root 密码 (用于验证数据):"
read -sp "密码: " MYSQL_PASSWORD
echo ""

COUNT=$(mysql -u root -p"$MYSQL_PASSWORD" -N -e "SELECT COUNT(*) FROM pear_admin.ums_supplier;" 2>/dev/null)

if [ -n "$COUNT" ]; then
    echo "   ✅ 数据库连接成功"
    echo "   📊 供应商表记录数: $COUNT"
    
    if [ "$COUNT" -gt 0 ]; then
        echo "   ✓ 数据已存在于数据库中"
    else
        echo "   ❌ 表是空的！数据并未同步成功。"
    fi
else
    echo "   ❌ 无法连接数据库，请检查密码或服务状态。"
fi
echo ""

# 2. 检查 Flask 进程
echo "🔍 2. 检查 Flask 服务..."
PID=$(pgrep -f "flask run")
if [ -n "$PID" ]; then
    echo "   ✅ Flask 正在运行 (PID: $PID)"
    
    # 检查监听端口
    PORT=$(netstat -tulpn | grep 5050)
    if [ -n "$PORT" ]; then
        echo "   ✅ 监听端口 5050 正常"
    else
        echo "   ❌ 未发现 5050 端口监听"
    fi
else
    echo "   ❌ Flask 未运行"
fi
echo ""

# 3. 检查环境变量
echo "🔍 3. 检查应用配置..."
if [ -f "/root/pear-admin-flask/.env" ]; then
    echo "   ✓ 找到 .env 文件"
    # 检查数据库配置是否正确指向 MySQL
    DB_HOST=$(grep MYSQL_HOST /root/pear-admin-flask/.env)
    echo "   配置检查: $DB_HOST"
else
    echo "   ❌ 缺少 .env 文件，Flask 可能在使用默认配置(SQLite)"
fi
echo ""

# 4. 尝试重启服务
echo "🔄 4. 尝试重启服务..."
pkill -f "flask run"
sleep 2
cd /root/pear-admin-flask
nohup flask run --host=0.0.0.0 --port=5050 > /tmp/flask.log 2>&1 &
echo "   ✓ 服务已重启，正在写入日志..."
sleep 3

# 5. 检查最新日志
echo "   📑 最新日志 (最后10行):"
echo "-----------------------------------"
tail -n 10 /tmp/flask.log
echo "-----------------------------------"

echo ""
echo "诊断完成。"
