import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "pear-admin-flask")

    SQLALCHEMY_DATABASE_URI = ""

    ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(ROOT_PATH, "uploads")

    JWT_TOKEN_LOCATION = ["headers"]
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    # Aliyun OSS
    ALIYUN_ACCESS_KEY_ID = os.getenv("ALIYUN_ACCESS_KEY_ID")
    ALIYUN_ACCESS_KEY_SECRET = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
    ALIYUN_OSS_BUCKET_NAME = os.getenv("ALIYUN_OSS_BUCKET_NAME")
    ALIYUN_OSS_ENDPOINT = os.getenv("ALIYUN_OSS_ENDPOINT")


class DevelopmentConfig(BaseConfig):
    """开发配置"""

    # 优先从环境变量读取 MySQL 配置
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    
    if MYSQL_HOST and MYSQL_HOST != "127.0.0.1":
        # 如果配置了非本地的 MYSQL_HOST (或者是本地但明确想用MySQL)，则使用 MySQL
        MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
        MYSQL_USER = os.getenv("MYSQL_USER", "root")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
        MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pear_admin")

        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
            f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        )
    else:
        # 默认使用本地 SQLite
        SQLALCHEMY_DATABASE_URI = "sqlite:///pear_admin.db"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestingConfig(BaseConfig):
    """测试配置"""

    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"  # 内存数据库


class ProductionConfig(BaseConfig):
    """生产环境配置"""

    # 支持从环境变量读取数据库配置
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pear_admin")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


config = {"dev": DevelopmentConfig, "test": TestingConfig, "prod": ProductionConfig}
