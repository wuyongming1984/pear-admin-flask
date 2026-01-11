## 本地启动

环境要求：python 3.10 以上，安装了 poetry

初始化环境

```shell
poetry install
```

初始化数据库

```shell
flask init
```

启动

```shell
flask run
```

## Docker 部署

### 快速开始

使用 Docker Compose 一键部署：

```shell
# 创建环境变量文件
cp .env.example .env
# 编辑 .env 文件，修改密码等配置

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 阿里云服务器部署

详细部署步骤请查看：

- **快速指南**：[quick-deploy-guide.txt](./quick-deploy-guide.txt)
- **完整文档**：[DEPLOY.md](./DEPLOY.md)

一键部署脚本：

```shell
chmod +x deploy.sh
./deploy.sh
```

访问地址：`http://<服务器IP>:5050`

## 上传到 Git 仓库

详细的 Git 上传指南请查看：[GIT_GUIDE.md](./GIT_GUIDE.md)

### 首次上传步骤

```shell
# 配置 Git 用户信息
git config --global user.name "你的用户名"
git config --global user.email "your_email@example.com"

# 初始化并提交
git init
git add .
git commit -m "初始提交：完整项目包含 Docker 部署支持"

# 添加远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/pear-admin-flask.git

# 推送到远程仓库
git push -u origin main
```

### 日常更新代码

```shell
# 三步推送流程
git add .                          # 添加修改
git commit -m "描述你的修改"        # 提交修改
git push                           # 推送到远程
```

详细日常操作指南：[更新推送指南.md](./更新推送指南.md)

推荐平台：
- GitHub（国际）：https://github.com
- Gitee（国内速度快）：https://gitee.com

## 贡献指南

如果想参与项目的贡献，提交代码之前需要启用 pre-commit、commitizen 对代码进行校验，运行以下指令即可。

初始化 pre-commit

```shell
pre-commit install
```

检查代码是否符合规范

```shell
git add .
```

```shell
pre-commit run --all-files
```

初始化 commitizen

```shell
pre-commit install -t commit-msg
```

使用

```shell
cz commit
```

代替 `git commit` 进行提交
