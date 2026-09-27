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
        base_cmd = [
            MYSQLDUMP_PATH,
            "-h", DB_HOST,
            "-u", DB_USER,
            f"-p{DB_PASS}"
        ]
        
        # 尝试使用新版参数（适用于本地环境/新版MySQL）
        advanced_args = ["--set-gtid-purged=OFF", "--column-statistics=0"]
        dump_cmd = base_cmd + advanced_args + [DB_NAME]
        
        print(f"尝试执行备份命令 (含高级参数)...")
        try:
            with open(backup_filename, "w", encoding="utf-8") as f:
                subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            # 如果失败，尝试兼容模式（适用于服务器/旧版MySQL）
            print(f"[WARNING] 高级参数备份失败，尝试使用兼容模式重试... 错误: {e.stderr.decode('utf-8', errors='ignore')}")
            
            # 关闭刚才可能创建的空文件
            try:
                os.remove(backup_filename)
            except:
                pass
                
            dump_cmd = base_cmd + [DB_NAME]
            print(f"尝试执行备份命令 (兼容模式)...")
            try:
                with open(backup_filename, "w", encoding="utf-8") as f:
                    subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, check=True)
            except subprocess.CalledProcessError as e2:
                # 如果还失败，尝试禁用 SSL (针对 2026 TLS/SSL error)
                error_msg = e2.stderr.decode('utf-8', errors='ignore')
                print(f"[WARNING] 兼容模式备份失败，尝试禁用 SSL 重试... 错误: {error_msg}")
                
                 # 关闭刚才可能创建的空文件
                try:
                    os.remove(backup_filename)
                except:
                    pass
                
                # 尝试 --skip-ssl (旧版) 或 --ssl-mode=DISABLED (新版)
                # 直接尝试两个参数都加，或者根据错误信息判断。这里简单起见，加 --skip-ssl
                dump_cmd = base_cmd + [DB_NAME, "--skip-ssl"]
                print(f"尝试执行备份命令 (禁用 SSL)...")
                with open(backup_filename, "w", encoding="utf-8") as f:
                     # 如果这次还失败，就直接抛出异常，不再捕获
                     subprocess.run(dump_cmd, stdout=f, check=True)
            
        # 3. 压缩文件
        print(f"正在压缩备份文件...")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(backup_filename)
        
        # 4. 发送邮件
        if os.path.exists(zip_filename):
            print(f"正在发送邮件至 {MAIL_RECEIVER}...")
            send_email(zip_filename)
            print("[INFO] 数据库备份并发送成功！")
        else:
            print("[ERROR] 压缩文件创建失败，跳过发送邮件")
            return
            
    except Exception as e:
        print(f"[ERROR] 备份流程失败: {str(e)}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
    finally:
        # 5. 无论成功失败，确保清理临时文件
        if 'backup_filename' in locals() and os.path.exists(backup_filename):
            try:
                os.remove(backup_filename)
                print(f"[INFO] 已清理本地文件: {backup_filename}")
            except:
                pass
        if 'zip_filename' in locals() and os.path.exists(zip_filename):
            try:
                os.remove(zip_filename)
                print(f"[INFO] 已清理本地文件: {zip_filename}")
            except:
                pass

def send_email(attachment_path):
    try:
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
        print(f"正在连接 SMTP 服务器 {MAIL_SERVER}:{MAIL_PORT} ...")
        server = smtplib.SMTP_SSL(MAIL_SERVER, int(MAIL_PORT), timeout=30)
        print("连接成功，正在登录...")
        server.login(MAIL_USER, MAIL_PASS)
        print("登录成功，正在发送邮件...")
        server.send_message(msg)
        print("发送成功，断开连接...")
        server.quit()
    except Exception as e:
        print(f"[ERROR] 邮件发送失败: {str(e)}")
        raise e

if __name__ == "__main__":
    if not all([MAIL_USER, MAIL_PASS, MAIL_RECEIVER, MAIL_SERVER]):
        print("[ERROR] 请先在 .env 文件中配置邮件相关参数（MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD, MAIL_RECEIVER）")
    else:
        backup_db()
