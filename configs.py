import os
from datetime import timedelta


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "pear-admin-flask")

    SQLALCHEMY_DATABASE_URI = ""

    ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(ROOT_PATH, "uploads")

    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)


class DevelopmentConfig(BaseConfig):
    """开发配置"""

    SQLALCHEMY_DATABASE_URI = "sqlite:///pear_admin.db"
    # MySQL (可选，需要启动Docker)
    # SQLALCHEMY_DATABASE_URI = "mysql+pymysql://pear_admin:pear_admin123@127.0.0.1:3306/pear_admin"
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
