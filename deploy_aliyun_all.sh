#!/bin/bash
# 阿里云服务器 - 一键部署脚本 (修复版)
# 自动安装依赖并修正执行路径

echo "=========================================="
echo "阿里云数据库一键部署工具 (v1.1)"
echo "=========================================="
echo ""

# 配置
PROJECT_DIR="/root/pear-admin-flask"
TMP_DIR="/tmp"

# 1. 安装必要的Python库
echo "🔧 步骤0: 安装依赖库..."
echo "正在安装 pymysql..."
pip3 install pymysql cryptography > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ 依赖库安装成功"
else
    echo "⚠️  依赖库安装可能有问题，尝试继续..."
fi
echo ""

# 2. 移动文件到正确位置
echo "📂 步骤1: 更新脚本..."
mkdir -p "$PROJECT_DIR/scripts"

# 移动Python脚本（如果存在）
if [ -f "$TMP_DIR/import_suppliers_mysql.py" ]; then
    mv -f "$TMP_DIR/import_suppliers_mysql.py" "$PROJECT_DIR/scripts/"
    chmod +x "$PROJECT_DIR/scripts/import_suppliers_mysql.py"
    echo "  ✓ 更新供应商导入脚本"
fi
if [ -f "$TMP_DIR/import_all_data.py" ]; then
    mv -f "$TMP_DIR/import_all_data.py" "$PROJECT_DIR/scripts/"
    chmod +x "$PROJECT_DIR/scripts/import_all_data.py"
    echo "  ✓ 更新统一导入工具"
fi

echo ""

# 3. 备份数据库
echo "📦 步骤2: 备份MySQL数据库..."
echo "⚠️  注意: 请输入 MySQL root 的【明文密码】"
echo "   (如果不知道密码，可尝试直接回车或者按 Ctrl+C 取消)"
echo ""

# 读取密码，允许为空
read -sp "请输入MySQL root密码: " MYSQL_PASSWORD
echo ""
echo ""

BACKUP_FILE="$TMP_DIR/pear_admin_backup_$(date +%Y%m%d_%H%M%S).sql"

mysqldump -u root -p"$MYSQL_PASSWORD" pear_admin > "$BACKUP_FILE" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ 数据库备份完成"
    echo "  备份文件: $BACKUP_FILE"
else
    echo "⚠️  数据库备份失败 (密码可能错误)"
    read -p "是否忽略备份并强行继续？(y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# 4. 运行统一导入工具
echo "▶️  步骤3: 启动数据导入工具..."
echo ""

# 切换到脚本目录执行，避免路径问题
cd "$PROJECT_DIR/scripts" || exit 1

# 执行脚本，传递密码
python3 import_all_data.py "$MYSQL_PASSWORD"

echo ""
echo "=========================================="
echo "✅ 执行结束"
echo "=========================================="
echo "如果仍有错误，请检查上方输出信息。"
