import os
import smtplib
import zipfile
import datetime
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# 加载配置
load_dotenv()

# 数据库配置
DB_HOST = os.getenv("MYSQL_HOST")
DB_USER = os.getenv("MYSQL_USER")
DB_PASS = os.getenv("MYSQL_PASSWORD")
DB_NAME = os.getenv("MYSQL_DATABASE")
MYSQLDUMP_PATH = os.getenv("MYSQLDUMP_PATH", "mysqldump") # 可在 .env 中配置完整路径

# 邮件配置
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = os.getenv("MAIL_PORT", 465)
MAIL_USER = os.getenv("MAIL_USERNAME")
MAIL_PASS = os.getenv("MAIL_PASSWORD")
MAIL_RECEIVER = os.getenv("MAIL_RECEIVER")

def backup_db():
    try:
        # 1. 创建备份文件名
        today = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"db_backup_{today}.sql"
        zip_filename = f"db_backup_{today}.zip"
        
        # 2. 执行 mysqldump
        print(f"正在备份数据库 {DB_NAME}...")
        dump_cmd = [
            MYSQLDUMP_PATH,
            "-h", DB_HOST,
            "-u", DB_USER,
            f"-p{DB_PASS}",
            DB_NAME
        ]
        
        with open(backup_filename, "w", encoding="utf-8") as f:
            subprocess.run(dump_cmd, stdout=f, check=True)
            
        # 3. 压缩文件
        print(f"正在压缩备份文件...")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(backup_filename)
        
        # 4. 发送邮件
        if os.path.exists(zip_filename):
            print(f"正在发送邮件至 {MAIL_RECEIVER}...")
            send_email(zip_filename)
        else:
            print("❌ 压缩文件创建失败，跳过发送邮件")
            return
        
        # 5. 清理临时文件
        if os.path.exists(backup_filename):
            os.remove(backup_filename)
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        
        print("✅ 数据库备份并发送成功！")
        
    except Exception as e:
        print(f"❌ 备份失败: {str(e)}")
        import sys
        sys.exit(1)

def send_email(attachment_path):
    msg = MIMEMultipart()
    msg['From'] = MAIL_USER
    msg['To'] = MAIL_RECEIVER
    msg['Subject'] = f"【系统备份】SF管理系统数据库备份_{datetime.datetime.now().strftime('%Y-%m-%d')}"
    
    body = f"您好，这是系统自动生成的每日数据库备份文件。\n备份时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    msg.attach(MIMEText(body, 'plain'))
    
    with open(attachment_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(attachment_path)}",
        )
        msg.attach(part)
    
    # 使用 SSL 发送
    server = smtplib.SMTP_SSL(MAIL_SERVER, int(MAIL_PORT))
    server.login(MAIL_USER, MAIL_PASS)
    server.send_message(msg)
    server.quit()

if __name__ == "__main__":
    if not all([MAIL_USER, MAIL_PASS, MAIL_RECEIVER, MAIL_SERVER]):
        print("❌ 错误: 请先在 .env 文件中配置邮件相关参数（MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD, MAIL_RECEIVER）")
    else:
        backup_db()
