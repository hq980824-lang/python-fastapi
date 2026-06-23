# Docker 容器化部署复盘（Dockerfile + compose）

> 把 FastAPI + MySQL + Redis 从 systemd 部署迁移到 Docker，本地 Mac 上跑通 compose 三件套。
> 实现时间：2026-06-23
> 目标形态：一条 `docker compose up` 启动全套服务，容器间用服务名互连。

---

## 一、心智模型：systemd vs Docker

| systemd 思路 | Docker 思路 |
| --- | --- |
| 在装好环境的机器上让进程常驻 | 把「环境 + 代码」打包成镜像，机器只要有 Docker 就能跑 |
| 换机器重新装一遍依赖（见 deployment.md 第二节 8 步） | 镜像通用，换机器 `docker compose up` 重建 |

核心：**镜像 = 环境快照（只读模板）；容器 = 镜像跑起来的实例。** 一个镜像可跑多个容器。

---

## 二、单容器化（Dockerfile）

### Dockerfile 全文

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .                       # ① 先只拷依赖清单
RUN pip install --no-cache-dir -r requirements.txt
COPY . .                                      # ② 再拷代码
EXPOSE 8106
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8106"]
```

### 关键点

- **分层缓存（最重要）**：先 COPY requirements 装依赖，再 COPY 代码。口诀「变得少的放前面」。这样改代码不会触发重装依赖——实测改代码后 `RUN pip install` 走 CACHED 秒过。
- `CMD` 用 exec 数组形式，**必须双引号**（JSON 规范），单引号会解析失败。
- `--host 0.0.0.0` 必须，否则容器外连不进来。
- `RUN`（构建时执行，固化进镜像）vs `CMD`（容器启动时执行）。

### .dockerignore

```
.venv
__pycache__
*.pyc
.git
markdown
.env
.env.*
!.env.example
```

- `.env*` 必须排除：**密钥不进镜像**，否则谁拿到镜像谁有密码。配置改为运行时注入。
- `.venv` 是 Mac 的依赖，与容器 Linux 不兼容，且镜像已 pip 装过，拷进去冗余还冲突。

### 单容器运行（学习用，已被 compose 取代）

```bash
docker build -t fastapi-app .
docker run --rm -p 8106:8106 \
  --env-file .env.dev \
  -e MYSQL_HOST=host.docker.internal \   # 容器访问宿主机用这个特殊域名
  -e REDIS_HOST=host.docker.internal \
  fastapi-app
```

- `--env-file` 解决「裸跑报 24 个 Field required」（配置不在镜像里）。
- `-e` 覆盖 `--env-file` 同名值（优先级更高）。
- `host.docker.internal` = Docker Desktop 提供的「宿主机」别名（容器里的 127.0.0.1 是容器自己）。

---

## 三、多容器编排（docker-compose.yml）

最终编排 3 个服务，完整文件见项目根 `docker-compose.yml`。核心概念：

### 1. image vs build

- `image: mysql:8.0` —— 用现成镜像。
- `build: .` —— 用本项目 Dockerfile 现场构建（app 服务）。

### 2. 服务名互连（compose 最关键认知）

compose 自动建内部网络，**服务名即主机名**。app 连数据库不再是 `127.0.0.1`，而是服务名：

```yaml
environment:
  MYSQL_HOST: mysql     # ← 服务名，compose 内部 DNS 解析到 mysql 容器
  REDIS_HOST: redis
```

`environment` 优先级高于 `env_file`，所以覆盖掉 .env.dev 里的 127.0.0.1/localhost。比 `host.docker.internal` 更干净（容器间直连，不绕宿主机）。

### 3. volume 数据卷（有状态服务必须）

```yaml
volumes:
  - mysql_data:/var/lib/mysql    # MySQL 数据目录
  - redis_data:/data             # Redis 持久化目录
# 底部还要声明：
volumes:
  mysql_data:
  redis_data:
```

- 容器是「用完即弃」的，`docker compose down` 删容器后，数据存卷里才不丢。
- ⚠️ **危险命令 `docker compose down -v`**：`-v` 连卷一起删，数据真没了。平时 down 别加 -v。

### 4. healthcheck + depends_on 条件等待

`depends_on` 简单列表只保证**启动顺序**，不保证依赖**真的 ready**。MySQL「容器起了」和「初始化完能连」差十几秒。解法：

```yaml
mysql:
  healthcheck:
    test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uroot", "-proot123"]
    interval: 5s
    timeout: 3s
    retries: 10
    start_period: 20s        # 给 MySQL 初始化宽限期，期间失败不计数

app:
  depends_on:
    mysql:
      condition: service_healthy    # 等 mysql healthcheck 通过才启动 app
    redis:
      condition: service_healthy
```

实测全新启动时 compose 日志显示 mysql/redis 先变 `Healthy`，app 才 `Started`，app 一次连接成功——从「碰运气」变「确定性」。

### 常用命令

```bash
docker compose up -d --build     # 构建并后台启动全部
docker compose ps                # 看状态（含 healthy 标记）
docker compose logs -f app       # 跟踪某服务日志
docker compose exec app alembic upgrade head   # 容器内跑迁移建表
docker compose down              # 停全部（保留卷）
docker compose config            # 校验/规范化配置（见下方查证法）
```

---

## 四、踩坑记录

1. **拉镜像超时**：国内连 `registry-1.docker.io` 超时。解法：`~/.docker/daemon.json` 配 `registry-mirrors` 国内加速器，重启 Docker Desktop。阿里云服务器上无此问题。
2. **CPU 架构**：Mac 是 arm64，阿里云多为 amd64，镜像架构不匹配会 `exec format error`。上服务器最省心办法是**在服务器上 build**（架构天然对）。
3. **PostDB 关系映射找不到**：`relationship("PostDB")` 报 `failed to locate a name 'PostDB'`。原因：app 运行时没 import 到 post_model，类没注册。解法：main.py 加 `import src.modules.posts.post_model  # noqa: F401`（为副作用而 import，勿删）。本地能跑容器炸，是因为 import 路径不同。详见 [[logging-trace-id]] 同类「初始化时机」思路。
4. **`retires` 拼写错被静默忽略**：`retries` 拼成 `retires`，compose **不报错**，当未知字段丢弃，retries 走默认值 3。靠 `docker compose config` 才发现。
5. **PID 1 信号问题**：容器里 uvicorn 是 PID 1，Ctrl+C 时抛 CancelledError 噪音（无害）。生产关乎优雅停机，可加 `init: true` 解决。（待办）

---

## 五、最大的收获：怎么自己查证，而不是记结论

> 「换个组件又不会了」的根因是记结论、没建查证路径。healthcheck 的 test 写什么，不是背的，是推的。

**把问题翻译成可查的问题：**

- 「healthcheck 字段怎么写」→ 查**官方文档**（compose 规范）。
- 「test 里放什么命令」→ 翻译成「在这个容器里敲什么能确认它活着」→ 查**镜像的 Docker Hub / 官方文档**（mysql 给了 `mysqladmin ping`；redis 就是平时验证用的 `redis-cli -a 密码 ping`）。
- 「时间参数定多少」→ 常识 + 微调（数据库启动慢给长 start_period），抄默认值跑起来再调。

**信息源优先级：** ① 官方文档 ② 镜像 Docker Hub 页面 ③ 报错信息本身（最被低估，如 PostDB 那次答案就在报错里）④ 搜索/提问。

**两个查证习惯：**
- 改完 compose 先跑 `docker compose config`，看字段有没有被认出来（防拼写被静默忽略）。
- 「没报错 ≠ 配置对」：缺省字段走默认值，关键参数要主动确认。

---

## 六、遗留待办

- `init: true` 解决 PID 1 优雅停机。
- 迁移自动化：现在要手动 `exec app alembic upgrade head`，可做成容器启动时自动跑（entrypoint 脚本）。
- 上阿里云：把 Dockerfile / compose / .dockerignore push 到 git，服务器 `git pull` 后直接 build（amd64 架构天然正确），配 .env.prod 与服务名。
- 接入 Nginx 反代 + HTTPS（见 deployment.md P0）。
