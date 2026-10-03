# sunfan88.com HTTPS 部署

用于现有 Docker Compose 部署：默认申请 www.sunfan88.com 的 TLS 证书，配置 Nginx 443、HTTP 301 和自动续期。拉取这些文件不会自动启用 HTTPS；需要执行下面的部署脚本。

## 1. 放行实例使用的安全组

阿里云 ECS → 安全组 → 入方向 → 增加规则：允许、自定义 TCP、443/443、IPv4 来源 0.0.0.0/0、优先级 100。
在“实例列表”核对该安全组关联的是公网 IP 8.159.138.234。保留现有 80 入站规则。

如果实例启用了主机防火墙，也要允许 HTTPS。先检查实际使用哪种防火墙，只执行适用的命令：

```bash
sudo firewall-cmd --state
sudo ufw status
# firewalld 运行时：
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
# 或 UFW 已启用时：
sudo ufw allow 443/tcp
```

不要停止或清空防火墙。安全组规则参考：[阿里云官方说明](https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups)。

## 2. 从仓库拉取 HTTPS 支持

在服务器的现有项目目录拉取；先检查工作区修改。如果拉取报错，保留输出并处理冲突，不要强制覆盖或运行 git reset：

```bash
cd /root/pear-admin-flask
git status --short
git pull --ff-only origin main
git log -1 --oneline
```

本次更新增加 HTTPS 模板、申请/续期脚本和忽略规则。拉取完成后直接执行 HTTPS 脚本即可，这次无需运行 server_update.sh 重建应用。

若此前已应用离线补丁，先处理该补丁产生的本地修改，再拉取；证书和活动配置位于被忽略的 .https-state/，应保留。

## 3. 申请证书并启用 HTTPS

将下面的邮箱替换为自己的证书联系邮箱。脚本的 Certbot 命令包含 `--agree-tos`，执行会同意 Let's Encrypt 的 ACME Subscriber Agreement，并将此邮箱用于 ACME 账户注册。
默认只要求 `www.sunfan88.com` 解析到这台服务器，且公网 80 可访问。不带 www 的域名尚未配置解析时，不影响 www 的 HTTPS 部署。

```bash
cd /root/pear-admin-flask
bash scripts/setup_https.sh '你的证书联系邮箱'
sudo bash scripts/install_https_renewal.sh
```

流程：先检查申请域名的 DNS → 保留 HTTP → 验证 HTTP-01 路径 → 申请真实证书 → `nginx -t` → 启用 TLS → 校验本机及公网 HTTPS → 启用 301。
Nginx 重新加载后，本机和公网 TLS 探测分别最多尝试 5 次，连接未就绪时等待 1 秒再试；每次连接超时 5 秒、请求超时 15 秒。证书不可信或 HTTP 错误立即失败。持续失败会标明本机/公网、输出网关日志并恢复原配置。
脚本只重新创建或重新加载 nginx；web 与 MySQL 不重建。重新创建网关时会有短暂连接切换。
如果已有自定义 docker-compose.override.yml，脚本会停止，须先合并该配置。

需要同时支持不带 www 的 HTTPS 时，先给 `sunfan88.com` 配置指向该服务器的 A 记录（阿里云 DNS 的主机记录为 `@`），再显式申请两个名字：

```bash
HTTPS_INCLUDE_APEX=true bash scripts/setup_https.sh '你的证书联系邮箱'
```

证书目录名称仍为 `.https-state/letsencrypt/live/sunfan88.com/`，该名称不表示默认已经为裸域名签发证书。续期使用已签发证书保存的域名列表。

自动生成的 docker-compose.override.yml 会合并 80/443 端口和证书挂载，普通 Docker Compose 命令及 server_update.sh 会继续使用 HTTPS。
证书、ACME 账户、备份与活动配置均保存在 .https-state/，已由 Git 和 Docker 构建忽略。不要删除此目录或生成的 override 文件。

install_https_renewal.sh 先通过 Let's Encrypt staging 的续期测试和重新加载测试，再安装每天两次的 systemd timer。测试证书不会替换真实证书。

```bash
systemctl list-timers pear-admin-https-renew.timer --no-pager
journalctl -u pear-admin-https-renew.service --no-pager -n 50
docker compose exec -T nginx nginx -t
```

Certbot 使用方法参考：[官方 webroot 与续期文档](https://eff-certbot.readthedocs.io/en/stable/using.html)。Nginx TLS 配置参考：[官方 HTTPS 文档](https://nginx.org/en/docs/http/configuring_https_servers.html)。

## 4. 从另一台设备验收

```bash
curl -I --connect-timeout 10 https://www.sunfan88.com/pc/
curl -I --connect-timeout 10 'http://www.sunfan88.com/pc/?next=%2F'
```

第一个应返回 200，且证书校验成功。第二个应返回 301，Location 为 `https://www.sunfan88.com/pc/?next=%2F`。
浏览器打开 `https://www.sunfan88.com/pc/#/login?next=/`，检查证书可信、页面和静态资源正常；再实际登录检查业务访问。
浏览器的安全状态图标随版本可能显示为锁或站点控制图标；以证书有效和连接安全为准。

若本机 HTTPS 正常而外部仍超时，检查安全组是否关联正确实例、主机防火墙、443 映射和实际监听；此时不要先开启强制跳转。

## 5. 回滚与 HSTS

setup_https.sh 失败会恢复之前的 override 和活动 Nginx 配置，并仅重新创建 nginx。备份路径会打印到终端。
成功后需要回滚时：保留证书，恢复该次备份的配置；若原来没有 override，将生成文件改名为 docker-compose.override.disabled，再运行 `docker compose up -d --no-deps --force-recreate nginx`。
原来已经启用 HTTPS 时，须恢复备份内的 override、default.conf 和 http-mode.conf 三个文件。

HSTS 默认不启用。公网访问与续期都验证通过后，可在 `.https-state/nginx/default.conf` 的 HTTPS server 中启用短时 `max-age=300` 并运行 Nginx 检查/重新加载。
不要直接启用 includeSubDomains 或 preload。存在嵌套 add_header 的静态 JSON location 需要单独配置 HSTS 才会继承同样的响应头。

## 本地验证结果

- Docker Compose 合并验证：同时发布 80/443，活动配置挂载正确替换同目标的默认配置，证书与 webroot 挂载只读。
- Nginx 1.29.5 实测 7 项通过：HTTP 保持服务、ACME 内容、两个域名的证书校验/HTTPS 代理头、切换期间 HTTP 可用、上传文件/JSON 缓存、301 保留路径及参数、跳转后续期路径。
- 隔离命令桩 16 项通过：包含 DNS 预检、仅 www 部署、显式裸域名、连接就绪等待、本机/公网短暂 TLS EOF、持续失败回滚、证书信任失败和续期重新加载。
- 本机 Docker 引擎未运行，因此没有完成 Linux 容器和生产 ACME 联调；以上不代表公网 HTTPS 已上线。
