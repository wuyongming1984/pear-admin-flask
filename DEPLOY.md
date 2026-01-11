# 阿里云服务器 Docker 部署指南

## 服务器信息

- **实例 ID**: i-uf6grczcwjr1t7f5efkv
- **用户名**: root
- **访问方式**: SSH

## 一、连接到阿里云服务器

### 方法 1：使用 SSH 客户端（Windows 推荐使用 PowerShell 或 Git Bash）

```bash
# 获取服务器公网 IP（登录阿里云控制台查看）
# 假设公网 IP 为: xxx.xxx.xxx.xxx

ssh root@<你的服务器公网IP>
# 输入密码后登录
```

### 方法 2：使用阿里云控制台的远程连接功能

1. 登录阿里云控制台
2. 找到 ECS 实例 `i-uf6grczcwjr1t7f5efkv`
3. 点击"远程连接"按钮

## 二、在服务器上安装 Docker 和 Docker Compose

连接到服务器后，执行以下命令：

```bash
# 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 安装必要的依赖
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker 官方 GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 设置 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 验证 Docker 安装
docker --version

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证 Docker Compose 安装
docker-compose --version
```

### 如果是 CentOS/Alibaba Cloud Linux 系统

```bash
# 安装 Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 三、上传项目文件到服务器

### 方法 1：使用 SCP（从本地 Windows 执行）

```bash
# 在本地打开 PowerShell，进入项目目录
cd d:\pear_admin\pear-admin-flask

# 压缩项目文件（排除不需要的文件）
# 先安装 7-Zip 或使用 Windows 自带的压缩功能
# 压缩时排除：__pycache__, .git, *.db, *.sqlite, venv, .venv

# 使用 SCP 上传（替换 <服务器IP> 为实际 IP）
scp pear-admin-flask.zip root@<服务器IP>:/root/
```

### 方法 2：使用 Git（推荐）

```bash
# 在服务器上执行
cd /root
git clone <你的项目仓库地址>
cd pear-admin-flask
```

### 方法 3：使用 SFTP 工具

推荐使用 WinSCP 或 FileZilla：
1. 主机：`<服务器公网IP>`
2. 用户名：`root`
3. 密码：`你的密码`
4. 端口：`22`

## 四、配置环境变量

在服务器上创建 `.env` 文件：

```bash
cd /root/pear-admin-flask

# 创建环境变量文件
cat > .env << 'EOF'
# Flask 配置
FLASK_ENV=production
SECRET_KEY=请修改为强密钥-使用随机字符串

# MySQL 配置
MYSQL_ROOT_PASSWORD=强密码123456!
MYSQL_DATABASE=pear_admin
MYSQL_USER=pear_admin
MYSQL_PASSWORD=强密码abc123!

# 应用配置
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5050
EOF

# 生成随机 SECRET_KEY（可选）
echo "建议的 SECRET_KEY: $(openssl rand -hex 32)"
```

**重要**：请修改 `.env` 文件中的密码为强密码！

## 五、启动服务

```bash
cd /root/pear-admin-flask

# 构建并启动服务（首次启动会自动下载镜像和构建）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看 Web 应用日志
docker-compose logs -f web

# 查看 MySQL 日志
docker-compose logs -f mysql
```

## 六、配置阿里云安全组

1. 登录阿里云控制台
2. 找到 ECS 实例 `i-uf6grczcwjr1t7f5efkv`
3. 点击"安全组配置"
4. 添加以下安全组规则：

### 入方向规则

| 协议 | 端口范围 | 授权对象 | 说明 |
|------|---------|---------|------|
| TCP  | 22      | 0.0.0.0/0 | SSH 登录 |
| TCP  | 5050    | 0.0.0.0/0 | Flask 应用 |
| TCP  | 80      | 0.0.0.0/0 | HTTP（可选，用于 Nginx 反向代理）|
| TCP  | 443     | 0.0.0.0/0 | HTTPS（可选）|

**注意**：
- 生产环境建议限制 SSH（22端口）的访问 IP
- 如果不需要外部访问 MySQL，不要开放 3306 端口

## 七、访问应用

部署成功后，访问：

```
http://<服务器公网IP>:5050
```

默认登录账号（如果有的话，请查看数据库初始化脚本）

## 八、常用管理命令

```bash
# 停止服务
docker-compose stop

# 启动服务
docker-compose start

# 重启服务
docker-compose restart

# 停止并删除容器
docker-compose down

# 停止并删除容器及数据卷（危险！会删除数据库数据）
docker-compose down -v

# 重新构建镜像
docker-compose build --no-cache

# 查看容器运行状态
docker-compose ps

# 进入 Web 容器
docker-compose exec web bash

# 进入 MySQL 容器
docker-compose exec mysql bash

# 查看容器日志
docker-compose logs -f [服务名]

# 更新代码后重新部署
git pull  # 如果使用 Git
docker-compose down
docker-compose build --no-cache web
docker-compose up -d
```

## 九、数据备份

### 备份 MySQL 数据

```bash
# 备份数据库
docker-compose exec mysql mysqldump -u root -p密码 pear_admin > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
docker-compose exec -T mysql mysql -u root -p密码 pear_admin < backup_20260111_120000.sql
```

### 备份上传文件

```bash
# 备份 uploads 目录
tar -czf uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/
```

## 十、配置 Nginx 反向代理（可选，推荐）

### 安装 Nginx

```bash
sudo apt-get install -y nginx
```

### 创建 Nginx 配置

```bash
sudo nano /etc/nginx/sites-available/pear-admin
```

添加以下内容：

```nginx
server {
    listen 80;
    server_name <你的域名或服务器IP>;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件直接由 Nginx 提供（可选优化）
    location /static {
        alias /root/pear-admin-flask/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /root/pear-admin-flask/uploads;
        expires 30d;
    }
}
```

### 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/pear-admin /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

配置后，可以通过 `http://<服务器IP>` 访问（不需要端口号）

## 十一、配置 HTTPS（可选）

使用 Let's Encrypt 免费 SSL 证书：

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 获取证书（需要先配置域名解析）
sudo certbot --nginx -d yourdomain.com

# 自动续期测试
sudo certbot renew --dry-run
```

## 十二、监控和日志

### 查看系统资源

```bash
# 查看 Docker 容器资源使用
docker stats

# 查看磁盘使用
df -h

# 查看内存使用
free -h
```

### 设置日志轮转

```bash
# 配置 Docker 日志大小限制
sudo nano /etc/docker/daemon.json
```

添加：

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

重启 Docker：

```bash
sudo systemctl restart docker
```

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker-compose logs

# 检查端口占用
sudo netstat -tlnp | grep 5050

# 检查容器状态
docker-compose ps
docker inspect <容器ID>
```

### 数据库连接失败

```bash
# 检查 MySQL 容器是否运行
docker-compose ps mysql

# 进入 MySQL 容器检查
docker-compose exec mysql mysql -u root -p

# 检查网络连接
docker-compose exec web ping mysql
```

### 无法访问网站

1. 检查安全组是否开放 5050 端口
2. 检查服务器防火墙：`sudo ufw status`
3. 检查应用是否正常运行：`docker-compose logs web`

## 维护建议

1. **定期备份**：每天备份数据库和上传文件
2. **更新系统**：定期执行 `sudo apt-get update && sudo apt-get upgrade`
3. **监控日志**：定期查看应用日志，及时发现问题
4. **资源监控**：关注服务器 CPU、内存、磁盘使用情况
5. **安全加固**：
   - 修改 SSH 默认端口
   - 禁用 root 密码登录，使用密钥登录
   - 配置防火墙规则
   - 定期更新密码
