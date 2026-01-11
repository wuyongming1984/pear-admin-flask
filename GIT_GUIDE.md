# Git 仓库上传指南

本指南将帮助您将 Pear Admin Flask 项目上传到 Git 仓库。

## 前提条件

1. 已安装 Git（检查：`git --version`）
2. 已注册 Git 托管平台账号（GitHub / Gitee / GitLab）

## 方法一：使用 GitHub（国际）

### 1. 在 GitHub 创建仓库

1. 登录 [https://github.com](https://github.com)
2. 点击右上角 "+" → "New repository"
3. 填写仓库信息：
   - Repository name: `pear-admin-flask`
   - Description: `Flask + Pear Admin 后台管理系统`
   - 选择 Public（公开）或 Private（私有）
   - **不要**勾选 "Initialize this repository with a README"
4. 点击 "Create repository"

### 2. 在本地初始化并上传

打开 PowerShell，进入项目目录：

```powershell
# 进入项目目录
cd d:\pear_admin\pear-admin-flask

# 配置 Git 用户信息（首次使用需要配置）
git config --global user.name "你的用户名"
git config --global user.email "your_email@example.com"

# 初始化 Git 仓库（如果还没有初始化）
git init

# 添加所有文件到暂存区
git add .

# 提交到本地仓库
git commit -m "初始提交：完整项目包含 Docker 部署支持"

# 添加远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/pear-admin-flask.git

# 推送到远程仓库
git push -u origin master
# 或者如果是 main 分支
# git push -u origin main
```

## 方法二：使用 Gitee（国内推荐，速度快）

### 1. 在 Gitee 创建仓库

1. 登录 [https://gitee.com](https://gitee.com)
2. 点击右上角 "+" → "新建仓库"
3. 填写仓库信息：
   - 仓库名称: `pear-admin-flask`
   - 仓库介绍: `Flask + Pear Admin 后台管理系统`
   - 选择 公开 或 私有
   - **不要**勾选 "使用 Readme 文件初始化这个仓库"
4. 点击 "创建"

### 2. 在本地初始化并上传

```powershell
# 进入项目目录
cd d:\pear_admin\pear-admin-flask

# 配置 Git 用户信息（首次使用需要配置）
git config --global user.name "你的用户名"
git config --global user.email "your_email@example.com"

# 初始化 Git 仓库（如果还没有初始化）
git init

# 添加所有文件到暂存区
git add .

# 提交到本地仓库
git commit -m "初始提交：完整项目包含 Docker 部署支持"

# 添加远程仓库（替换为你的仓库地址）
git remote add origin https://gitee.com/你的用户名/pear-admin-flask.git

# 推送到远程仓库
git push -u origin master
```

## 方法三：使用 GitLab

### 1. 在 GitLab 创建仓库

1. 登录 [https://gitlab.com](https://gitlab.com)
2. 点击 "New project" → "Create blank project"
3. 填写项目信息：
   - Project name: `pear-admin-flask`
   - Project description: `Flask + Pear Admin 后台管理系统`
   - Visibility Level: Public 或 Private
   - 取消勾选 "Initialize repository with a README"
4. 点击 "Create project"

### 2. 在本地初始化并上传

```powershell
# 进入项目目录
cd d:\pear_admin\pear-admin-flask

# 配置 Git 用户信息（首次使用需要配置）
git config --global user.name "你的用户名"
git config --global user.email "your_email@example.com"

# 初始化 Git 仓库（如果还没有初始化）
git init

# 添加所有文件到暂存区
git add .

# 提交到本地仓库
git commit -m "初始提交：完整项目包含 Docker 部署支持"

# 添加远程仓库（替换为你的仓库地址）
git remote add origin https://gitlab.com/你的用户名/pear-admin-flask.git

# 推送到远程仓库
git push -u origin master
```

## 重要：创建 .gitignore 文件

在上传前，确保项目有 `.gitignore` 文件，避免上传敏感信息和不必要的文件。

项目根目录应该已经有 `.gitignore` 文件，内容如下：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/
*.egg-info/
dist/
build/

# Flask
instance/
.webassets-cache
*.db
*.sqlite
*.sqlite3

# 环境变量（重要：不要上传敏感信息）
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 系统文件
.DS_Store
Thumbs.db

# 日志
*.log

# 上传文件（可选，根据需要调整）
uploads/

# Poetry
poetry.lock

# Docker
.dockerignore

# 临时文件
*.tmp
temp/
```

如果没有这个文件，请在项目根目录创建。

## 常见问题和解决方案

### 问题 1：已经有 .git 目录，需要重新关联远程仓库

```powershell
# 查看当前远程仓库
git remote -v

# 删除旧的远程仓库
git remote remove origin

# 添加新的远程仓库
git remote add origin https://github.com/你的用户名/pear-admin-flask.git

# 推送
git push -u origin master
```

### 问题 2：推送时要求输入用户名和密码

**GitHub 已不再支持密码认证**，需要使用 Personal Access Token：

1. GitHub 设置 → Developer settings → Personal access tokens → Generate new token
2. 选择权限（至少选择 `repo`）
3. 生成 Token 并保存
4. 推送时使用 Token 作为密码

**或者使用 SSH 方式**：

```powershell
# 生成 SSH 密钥
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 查看公钥
cat ~/.ssh/id_rsa.pub

# 复制公钥内容，添加到 GitHub/Gitee SSH Keys 设置中

# 修改远程仓库地址为 SSH 地址
git remote set-url origin git@github.com:你的用户名/pear-admin-flask.git

# 推送
git push -u origin master
```

### 问题 3：提示 "main" 和 "master" 分支问题

GitHub 新仓库默认使用 `main` 分支，旧项目可能使用 `master`：

```powershell
# 查看当前分支
git branch

# 如果是 master，重命名为 main
git branch -M main

# 推送到 main 分支
git push -u origin main
```

### 问题 4：推送被拒绝（rejected）

```powershell
# 强制推送（谨慎使用，会覆盖远程内容）
git push -f origin master

# 或者先拉取远程更改
git pull origin master --allow-unrelated-histories
git push origin master
```

### 问题 5：文件太大，推送失败

GitHub 单个文件限制 100MB，可以使用 Git LFS：

```powershell
# 安装 Git LFS
git lfs install

# 跟踪大文件
git lfs track "*.jpg"
git lfs track "*.png"

# 提交 .gitattributes
git add .gitattributes
git commit -m "配置 Git LFS"
git push
```

## 后续更新代码

当你修改代码后，使用以下命令更新到 Git：

```powershell
# 查看修改状态
git status

# 添加修改的文件
git add .

# 提交修改
git commit -m "描述你的修改内容"

# 推送到远程
git push
```

## 在服务器上拉取代码

上传到 Git 后，在阿里云服务器上可以这样拉取：

```bash
# 首次克隆
cd /root
git clone https://gitee.com/你的用户名/pear-admin-flask.git
cd pear-admin-flask

# 后续更新
git pull
```

## 推荐的 Git 工作流程

### 开发流程

```powershell
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 开发并提交
git add .
git commit -m "添加新功能"

# 3. 推送到远程
git push origin feature/new-feature

# 4. 在 Git 平台创建 Pull Request/Merge Request

# 5. 合并后切换回主分支
git checkout master
git pull
```

## 安全建议

1. **不要上传敏感信息**：
   - `.env` 文件（包含密码）
   - 数据库文件（`.db`, `.sqlite`）
   - 用户上传的文件（`uploads/`）
   - 私钥文件

2. **检查 .gitignore**：
   确保 `.gitignore` 已正确配置

3. **清理已提交的敏感文件**：
   
   ```powershell
   # 从 Git 历史中删除文件
   git rm --cached .env
   git commit -m "删除敏感文件"
   git push
   ```

4. **使用私有仓库**：
   生产项目建议使用私有仓库

## 常用 Git 命令速查

```powershell
# 查看状态
git status

# 查看提交历史
git log
git log --oneline

# 查看差异
git diff

# 撤销修改
git checkout -- 文件名

# 撤销暂存
git reset HEAD 文件名

# 回退到某个版本
git reset --hard 提交ID

# 创建分支
git branch 分支名

# 切换分支
git checkout 分支名

# 合并分支
git merge 分支名

# 删除分支
git branch -d 分支名

# 查看远程仓库
git remote -v

# 拉取更新
git pull

# 推送更新
git push
```

## Git 图形化工具推荐

如果不熟悉命令行，可以使用图形化工具：

1. **GitHub Desktop**：https://desktop.github.com/
   - 简单易用，适合初学者
   - 支持 GitHub 和其他 Git 仓库

2. **GitKraken**：https://www.gitkraken.com/
   - 功能强大，界面美观
   - 支持所有 Git 操作

3. **SourceTree**：https://www.sourcetreeapp.com/
   - 免费，功能完整
   - 支持 Windows 和 Mac

4. **TortoiseGit**：https://tortoisegit.org/
   - Windows 资源管理器集成
   - 右键菜单操作

## 完整示例：从零开始上传项目

```powershell
# 1. 安装 Git（如果还没有）
# 下载：https://git-scm.com/download/win

# 2. 进入项目目录
cd d:\pear_admin\pear-admin-flask

# 3. 配置 Git（首次使用）
git config --global user.name "Zhang San"
git config --global user.email "zhangsan@example.com"

# 4. 初始化仓库
git init

# 5. 添加文件
git add .

# 6. 提交
git commit -m "初始提交：完整项目"

# 7. 在 Gitee 创建仓库后，添加远程地址
git remote add origin https://gitee.com/zhangsan/pear-admin-flask.git

# 8. 推送
git push -u origin master

# 完成！
```

## 验证上传成功

1. 访问你的 Git 仓库页面
2. 刷新页面，应该能看到所有文件
3. 检查 README.md、Dockerfile、docker-compose.yml 等关键文件是否存在

## 下一步

上传成功后，你可以：

1. 在服务器上使用 `git clone` 拉取代码
2. 按照 DEPLOY.md 文档进行 Docker 部署
3. 配置 GitHub Actions / Gitee Go / GitLab CI 实现自动化部署

---

如有问题，请参考：
- Git 官方文档：https://git-scm.com/doc
- GitHub 帮助：https://docs.github.com/
- Gitee 帮助：https://gitee.com/help
