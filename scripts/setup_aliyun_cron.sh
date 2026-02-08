#!/bin/bash

# 获取项目绝对路径
PROJECT_DIR="/root/pear-admin-flask"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
SCRIPT_PATH="$PROJECT_DIR/scripts/backup_db.py"

# 检查文件是否存在
if [ ! -f "$PYTHON_BIN" ]; then
    # 尝试查找其他可能的 python 路径
    PYTHON_BIN=$(which python3)
fi

# 创建 Cron 任务 (每天凌晨 1:00)
# 使用 docker exec 在容器内运行备份脚本
CRON_JOB="0 1 * * * docker exec pear_admin_web python scripts/backup_db.py >> $PROJECT_DIR/scripts/backup.log 2>&1"

# 添加到 crontab (如果不存在)
(crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "$CRON_JOB") | crontab -

echo "✅ 阿里云服务器定时任务已设置成功！"
echo "⏰ 运行时间：每天凌晨 1:00"
echo "📄 脚本路径：$SCRIPT_PATH"
echo "📝 日志路径：$PROJECT_DIR/scripts/backup.log"
