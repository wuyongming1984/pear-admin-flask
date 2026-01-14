#!/bin/bash
# 阿里云服务器 - 供应商数据导入脚本（MySQL版本）
# 支持从.env文件读取配置

echo "=========================================="
echo "供应商数据导入到阿里云服务器（MySQL）"
echo "=========================================="
echo ""

# 配置
PROJECT_DIR="/root/pear-admin-flask"
SQL_FILE="/tmp/旧数据库sf_db_prod.sql"

# 进入项目目录
cd "$PROJECT_DIR" || exit 1

# 检查SQL文件
echo "📥 步骤1: 检查SQL文件..."
if [ -f "$SQL_FILE" ]; then
    echo "✓ 找到SQL文件: $SQL_FILE"
    FILE_SIZE=$(du -h "$SQL_FILE" | cut -f1)
    echo "   文件大小: $FILE_SIZE"
else
    echo "❌ 错误: SQL文件不存在"
    echo "   请将 旧数据库sf_db_prod.sql 上传到 /tmp/"
    exit 1
fi

# 检查Python导入脚本
echo ""
echo "📝 步骤2: 检查导入脚本..."
IMPORT_SCRIPT="$PROJECT_DIR/scripts/import_suppliers_mysql.py"
if [ ! -f "$IMPORT_SCRIPT" ]; then
    echo "❌ 错误: 导入脚本不存在"
    echo "   请将 import_suppliers_mysql.py 上传到 $PROJECT_DIR/scripts/"
    exit 1
fi
echo "✓ 找到导入脚本"

# 检查.env文件
echo ""
echo "🔧 步骤3: 检查配置文件..."
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "✓ 找到.env配置文件"
    echo "   将从.env读取MySQL配置"
else
    echo "⚠️  未找到.env文件"
fi

# 获取MySQL密码
echo ""
echo "🔐 步骤4: 输入MySQL密码..."
echo "（如果.env中的密码可用将自动使用）"
read -sp "MySQL root密码（直接回车使用.env）: " MYSQL_PASSWORD
echo ""

# 备份数据库
echo ""
echo "📦 步骤5: 备份MySQL数据库..."
BACKUP_FILE="/tmp/pear_admin_backup_$(date +%Y%m%d_%H%M%S).sql"

if [ -z "$MYSQL_PASSWORD" ]; then
    # 尝试从.env读取密码（如果已经解密）
    echo "尝试使用.env配置..."
    mysqldump pear_admin > "$BACKUP_FILE" 2>/dev/null
else
    mysqldump -u root -p"$MYSQL_PASSWORD" pear_admin > "$BACKUP_FILE" 2>/dev/null
fi

if [ $? -eq 0 ]; then
    echo "✓ 数据库备份完成: $BACKUP_FILE"
else
    echo "⚠️  警告: 数据库备份失败"
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 执行Python导入脚本
echo ""
echo "▶️  步骤6: 执行数据导入..."

if [ -z "$MYSQL_PASSWORD" ]; then
    # 不传递密码参数，让脚本从.env读取或提示输入
    python3 scripts/import_suppliers_mysql.py
else
    # 传递密码参数
    python3 scripts/import_suppliers_mysql.py "$MYSQL_PASSWORD"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 导入完成！"
    echo "=========================================="
    echo ""
    echo "📌 重要信息:"
    echo "   - 备份文件: $BACKUP_FILE"
    echo "   - 数据库: pear_admin"
    echo "   - 表: ums_supplier"
    echo ""
    
    # 询问是否重启服务
    read -p "🔄 是否重启Flask服务？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "重启Flask服务..."
        
        # 停止现有进程
        pkill -f "flask run" 2>/dev/null
        pkill -f "gunicorn" 2>/dev/null
        
        # 检查是否使用systemd
        if systemctl list-units --full -all | grep -q "flask-app.service"; then
            sudo systemctl restart flask-app
            echo "✓ Flask服务已重启（systemd）"
        else
            # 后台启动
            sleep 2
            nohup flask run --host=0.0.0.0 --port=5050 > /tmp/flask.log 2>&1 &
            echo "✓ Flask服务已重启（后台进程）"
            echo "   日志: /tmp/flask.log"
        fi
        
        sleep 3
        
        # 测试服务
        if curl -s http://localhost:5050 > /dev/null 2>&1; then
            echo "✓ Flask服务运行正常"
        else
            echo "⚠️  警告: 服务可能未正常启动"
            echo "   请检查日志: tail -f /tmp/flask.log"
        fi
    fi
    
    echo ""
    echo "🌐 请访问以下地址验证:"
    echo "   http://8.159.138.234:5050/"
    echo "   登录后查看供应商管理"
    echo ""
else
    echo ""
    echo "❌ 导入失败！"
    echo "请检查错误信息并重试"
    echo ""
    echo "常见问题："
    echo "1. MySQL密码错误 - 请确认密码正确"
    echo "2. 数据库不存在 - 请确认数据库名称为 pear_admin"
    echo "3. 表不存在 - 请确认 ums_supplier 表已创建"
    exit 1
fi
