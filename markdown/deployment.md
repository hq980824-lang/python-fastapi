# 部署到阿里云服务器复盘（systemd 方案）

> 把本地 FastAPI 项目部署到阿里云轻量应用服务器，服务常驻、开机自启、公网可访问。
> 部署时间：2026-06-18

---

## 一、服务器环境

| 项目 | 值 |
| --- | --- |
| 服务商 | 阿里云轻量应用服务器 |
| 公网 IP | 101.132.142.79 |
| 配置 | 2 vCPU / 2 GiB / 40 GiB |
| 系统 | Alibaba Cloud Linux 3（RHEL 系，用 `dnf`） |
| 应用端口 | 8106 |

---

## 二、部署步骤回顾

### 1. 摸清环境

```bash
cat /etc/os-release      # 看发行版
python3 --version        # 自带 3.6.8（太老，不能用）
mysql --version          # 自带 8.0.44 ✅
redis-cli --version      # 未装
```

### 2. 补齐运行环境

```bash
# 装 Python 3.11（系统自带 3.6 跑不了 int|str 语法，但不能动它）
sudo dnf install -y python3.11 python3.11-pip

# 装 Redis
sudo dnf install -y redis
sudo systemctl enable --now redis
redis-cli ping           # PONG

# MySQL 已自带，确认能连
sudo mysql -u root -p
```

> **关键点**：系统自带的 `python3`（3.6）很多系统工具依赖它，不要替换，额外装 `python3.11` 并显式用这个名字调用。

### 3. 拉代码 + 建虚拟环境

```bash
cd ~
git clone https://github.com/hq980824-lang/python-fastapi.git
cd python-fastapi

python3.11 -m venv .venv
source .venv/bin/activate         # 激活后命令行出现 (.venv)
pip install --upgrade pip
pip install -r requirements.txt
```

> **踩坑**：`requirements.txt` 缺了 `aiomysql`、`alembic`、`redis`、`Mako` 四个运行时依赖（本地用 Poetry 装的，没同步进 requirements）。已补全。

### 4. 创建 .env.prod

`.env*` 被 `.gitignore` 排除，不进仓库，需在服务器手动创建。用 heredoc 写入避免粘贴换行丢失：

```bash
cat > .env.prod << 'EOF'
MYSQL_HOST=127.0.0.1
...（略，REDIS_PASSWORD 留空，ENV 相关走 prod）
EOF
```

> **踩坑**：用 nano 直接粘贴多行，换行会被吃掉，所有配置挤成一行，pydantic 读不对。改用 `cat > file << 'EOF'` heredoc 方式可靠。

### 5. 初始化数据库

```bash
# 建空库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS fastapi_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 跑 Alembic 迁移建表（必须带 ENV=prod）
export ENV=prod
alembic upgrade head
alembic current          # 178922d0b0ba (head)
```

> **踩坑**：忘记带 `ENV=prod` 时，pydantic 读不到 `.env.prod`，报一堆 `Field required`。用 `export ENV=prod` 设进会话变量，后续命令免去前缀。

### 6. 前台试跑验证

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8106
```

看到 `Redis 连接成功` / `MySQL 连接成功` / `Application startup complete` 即正常。

> `--host 0.0.0.0` 必须，监听所有网卡，外网才能访问；写 127.0.0.1 只有本机能连。

### 7. 放行端口

- **阿里云安全组**：控制台加规则，TCP 8106，授权对象 0.0.0.0/0
- **本机防火墙**：`sudo firewall-cmd --state` 在跑就 `--add-port=8106/tcp`

浏览器访问 `http://101.132.142.79:8106/docs` 验证公网可达。

### 8. systemd 常驻

```bash
sudo tee /etc/systemd/system/fastapi.service > /dev/null << 'EOF'
[Unit]
Description=FastAPI Application (python-fastapi)
After=network.target mysqld.service redis.service

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/python-fastapi
Environment="ENV=prod"
ExecStart=/home/admin/python-fastapi/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8106
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable fastapi    # 开机自启
sudo systemctl start fastapi
sudo systemctl status fastapi    # active (running)
```

**常用管理命令：**

| 命令 | 作用 |
| --- | --- |
| `sudo systemctl status fastapi` | 查看运行状态 |
| `sudo systemctl restart fastapi` | 重启（代码更新后用） |
| `sudo systemctl stop fastapi` | 停止 |
| `journalctl -u fastapi -f` | 实时看日志 |

---

## 三、systemd 方案 vs Docker

| 维度 | 当前 systemd 方案 | Docker 方案 |
| --- | --- | --- |
| 环境一致性 | 依赖宿主机版本，换机器可能有差异 | 镜像锁死环境，到处一致 |
| 可复现性 | 靠手动命令，换机器重来一遍 | 一条 `docker compose up` 重建 |
| 环境隔离 | 都装宿主机，可能冲突，卸载有残留 | 容器隔离，删容器即干净 |
| 迁移/扩容 | 等于重新部署 | 镜像 pull 即用 |
| 回滚 | 代码靠 git，环境难回退 | 镜像按 tag 回滚 |
| 内存占用 | 低（2G 机器友好） | 较高（守护进程 + 多容器） |
| 上手成本 | 低，概念少，调试直观 | 高，要学 Dockerfile/compose/网络/volume |

**结论**：单机学习项目用 systemd 完全够，简单直观省内存。Docker 的价值在「多环境、多人协作、频繁迁移」时才兑现，建议作为独立学习主题专门深入，而非顺带使用。

---

## 四、改进步骤（按优先级）

当前方案能跑，但离「规范、安全、好维护」还有提升空间，按收益排序：

### P0 — 安全（最该先做）

1. **不要用 root 跑 MySQL 裸密码 + 应用直连公网**
   - 当前 8106 直接对公网开放，且无 HTTPS。建议加 **Nginx 反向代理**：Nginx 监听 80/443，反代到本地 8106，应用端口不再直接暴露。
   - 配 **HTTPS**（域名 + Let's Encrypt 免费证书），否则验证码、token 明文传输。
2. **MySQL 不用 root 跑应用**：建一个只对 `fastapi_db` 有权限的专用账号，改 `.env.prod`，降低泄露风险。
3. **Redis 加密码**：当前裸跑无密码，虽然只监听本地，但建议设 `requirepass` 并配进 `.env.prod`。

### P1 — 可维护性

4. **写部署/更新脚本**：把「git pull → pip install → alembic upgrade → systemctl restart」打包成一个 `deploy.sh`，避免每次手动敲、漏步骤。
5. **多 worker**：当前单进程。生产可用 `uvicorn ... --workers 4` 或 Gunicorn + UvicornWorker 提升并发（注意 2G 内存，worker 别开太多）。
6. **日志落盘**：当前日志靠 journalctl。可配置应用日志写文件 + 轮转，方便排查历史问题。

### P2 — 工程化

7. **完善 `requirements.txt` / 依赖管理**：这次就是因为缺依赖踩坑。本地确保 `pip freeze` 与实际一致，或服务器也用 Poetry。
8. **CI/CD 自动部署**：GitHub Actions 在 push 后自动 SSH 到服务器执行 deploy.sh，免手动。
9. **迁移到 Docker**：作为独立主题学习，用 docker-compose 编排 app + mysql + redis，获得环境一致性和可复现性。

---

## 五、更新代码的标准流程（现在就能用）

```bash
cd ~/python-fastapi
source .venv/bin/activate
git pull
pip install -r requirements.txt      # 有新依赖时
ENV=prod alembic upgrade head        # 有新迁移时
sudo systemctl restart fastapi       # 重启生效
```
