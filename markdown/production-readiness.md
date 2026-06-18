# 生产级能力建设：进度与路线图

> 对照 20 项生产级能力清单，逐项核对当前代码后标注状态。
> 状态说明：✅ 已实现 ｜ 🟡 部分实现 ｜ ⬜ 未开始

最后核对时间：2026-06-18

---

## 一、总体进度

| #  | 能力       | 状态 |
| -- | -------- | -- |
| 1  | 项目结构规范化  | 🟡 |
| 2  | 配置管理     | 🟡 |
| 3  | 数据库层     | ✅ |
| 4  | 接口 Schema | 🟡 |
| 5  | 统一响应格式   | ✅ |
| 6  | 异常处理     | 🟡 |
| 7  | 日志系统     | ⬜ |
| 8  | 认证与授权    | 🟡 |
| 9  | 安全加固     | ⬜ |
| 10 | 测试体系     | ⬜ |
| 11 | API 文档   | 🟡 |
| 12 | 健康检查     | ⬜ |
| 13 | 部署能力     | ⬜ |
| 14 | CI/CD    | ⬜ |
| 15 | 代码质量工具   | 🟡 |
| 16 | 依赖管理     | 🟡 |
| 17 | 可观测性     | ⬜ |
| 18 | 缓存与性能    | 🟡 |
| 19 | 后台任务     | ⬜ |
| 20 | 生产运维     | ⬜ |

---

## 二、已实现 / 部分实现的明细

### 3. 数据库层 ✅

- 使用 **SQLAlchemy 2.0 异步** ORM（`src/config/db.py`、`user_model.py`）
- 连接池已配置：`pool_size` / `max_overflow` / `pool_recycle` / `pool_pre_ping`，参数来自环境变量
- **Alembic** 迁移已接入（`migrations/`，已有 `create_users_table` 版本）
- 事务管理：`get_db()` 依赖里 `try/rollback/finally`，service 层 `commit` 失败回滚

### 5. 统一响应格式 ✅

- 成功响应：`ResponseModel` + `ResponseRoute` 自动包装成 `{code, msg, data}`（`response.py`、`route.py`）
- 错误响应：异常 handler 复用同一结构
- 详见 `response.md`

### 1. 项目结构规范化 🟡

- 已有 `config / common / modules` 分层，模块内按 controller / service / model / dto 拆分
- **缺口**：尚未拆出独立的 `repositories`（数据访问层），service 直接操作 db；分层边界靠约定、未强制

### 2. 配置管理 🟡

- 已区分 `dev / prod`（`.env.dev` / `.env.prod`，`settings.py` 按 `ENV` 加载）
- `.gitignore` 已排除 `.env*`、保留 `.env.example`
- **缺口**：无 `.env.test`；无 `.env.example` 模板文件；生产仍读 `.env.prod` 文件，未接入 K8s Secret / 云 Secret Manager

### 4. 接口 Schema 🟡

- 已用 Pydantic 区分 request（`UserCreate`/`UserUpdate`）/ response（`UserResp`）
- 不直接暴露 ORM 模型，靠 `response_model` 转换
- **缺口**：无统一的分页 / 排序 / 过滤 schema（`get_all` 是全表返回）

### 6. 异常处理 🟡

- 全局异常处理器已分层：`http_err_handler`（业务）/ `value_err_handler`（业务校验 400）/ `global_err_handler`（兜底 500）
- 详见 `exception-handler.md`
- **缺口**：未单独处理 FastAPI 的请求**参数校验错误**（`RequestValidationError`，目前走默认格式，与统一响应结构不一致）；无明确的**业务错误码**体系（现在只有 HTTP 状态码）

### 8. 认证与授权 🟡

- **邮箱验证码登录**已打通：`/auth/send-code` 发码（dev 直返、生产发邮件）、`/auth/login` 校验后签发 JWT
- **JWT** 已接入（`jwt_util.py`），token 的 `sub` 存 user_id；`HTTPBearer` 提取请求头 token
- **当前用户依赖**：`get_current_user`（`dependencies.py`）解码 token + 查库，鉴权失败抛 401；`/users/profile` 已用其保护
- 详见 `redis-auth.md`
- **缺口**：无密码哈希（passlib/bcrypt，目前仅验证码登录，无密码体系）；无 token 刷新 / 黑名单（登出后 token 仍有效到过期）；无 RBAC 角色权限；验证码登录遇未注册邮箱直接拒绝，无注册流程

### 18. 缓存与性能 🟡

- **Redis 已封装并落地**：连接池 + `get_redis()` 依赖 + `RedisUtil` 工具类（`config/redis.py`、`utils/redis_util.py`）
- 生命周期接入 lifespan，启动 ping 校验、关闭释放
- 已用于**验证码存储**（5 分钟过期）
- 详见 `redis-auth.md`
- **缺口**：尚未用于业务数据缓存（如热点查询）；无缓存失效策略 / 防穿透防雪崩；无查询性能优化

### 11. API 文档 🟡

- 接口已加 `response_model`，`create_router` 已设 `tags`
- **缺口**：接口缺 `summary` / `description`；未区分公开 / 内部接口

### 15. 代码质量工具 🟡

- `ruff` 已在依赖里（lint + format）
- **缺口**：无 `mypy` / `pyright` 类型检查；无 `pre-commit` hooks；ruff 规则未在 `pyproject.toml` 里配置

### 16. 依赖管理 🟡

- 用 Poetry + `requirements.txt`，版本基本锁定
- **缺口**：未区分运行依赖 / 开发依赖（dev 工具和运行库混在一起）；无依赖漏洞扫描

---

## 三、接下来的补充建议（按优先级）

按「投入产出比 + 生产必需程度」排序，越靠前越该先做。

### P0 — 上生产前的硬门槛

这几项缺了，服务上线就是裸奔，建议最先补。

1. **健康检查（#12）** — 加 `/health`（存活）和 `/ready`（含数据库连通性检查）。K8s / 负载均衡探针强依赖，工作量很小，收益立竿见影。
2. **日志系统（#7）** — 结构化 JSON 日志 + 请求 ID（Trace ID）中间件 + 日志分级。出问题能定位，是运维的最低保障。
3. **安全加固（#9）** — 至少先做 CORS 白名单、请求体大小限制、安全响应头。现在 `main.py` 一个中间件都没有，跨域和基础防护是空的。
4. **认证与授权补全（#8）** — JWT 登录与 `get_current_user` 已就绪。剩余：密码哈希（passlib/bcrypt）若要支持密码登录、token 刷新与登出黑名单（可复用已封装的 Redis）、RBAC 角色权限。

### P1 — 质量与协作的保障

5. **测试体系（#10）** — 先补 service / 接口的单元 + 集成测试，用独立测试数据库（配 `.env.test`）。当前 0 测试，重构和加功能都没有安全网。
6. **参数校验错误格式化（#6 缺口）** — 注册 `RequestValidationError` handler，让 422 也走统一 `{code,msg,data}`。工作量小，补全异常体系的最后一块。
7. **业务错误码体系（#6 缺口）** — 定义一套业务错误码枚举（如 `10001=用户名已存在`），前端按码判断而非靠 msg 文案。
8. **代码质量工具补全（#15）** — 加 `pre-commit`（ruff lint + format + mypy），把质量检查前移到提交时。
9. **依赖分组（#16）** — `pyproject.toml` 里把 dev 依赖（ruff、pytest、mypy）和运行依赖分开。

### P2 — 部署与工程化

10. **部署能力（#13）** — Dockerfile + docker-compose（app + mysql），生产用 Gunicorn + Uvicorn Worker。
11. **CI/CD（#14）** — GitHub Actions：lint → type check → test → build image。依赖 #10 和 #15。
12. **分页 / 排序 / 过滤（#4 缺口）** — 给列表接口加统一分页 schema，避免 `get_all` 全表扫描。
13. **配置管理补全（#2 缺口）** — 加 `.env.example` 模板和 `.env.test`；生产接入 Secret Manager。
14. **仓储层拆分（#1 缺口）** — 引入 `repositories` 层，把 db 操作从 service 抽离，分层更清晰（项目变大后价值才明显，现在可选）。

### P3 — 规模化阶段再做

体量上来、有真实流量后再投入，过早做是过度工程。

15. **可观测性（#17）** — Prometheus metrics + OpenTelemetry tracing + 慢查询日志。
16. **缓存与性能（#18）** — Redis 已封装并用于验证码存储，下一步扩展到业务数据缓存、查询优化、防穿透/雪崩策略。
17. **后台任务（#19）** — Celery / Dramatiq + 定时任务 + 重试 / 死信。
18. **生产运维（#20）** — 备份策略、灰度发布、回滚、监控告警、容量规划。

---

## 四、一句话路线

**先补 P0 让服务能安全上线（健康检查、日志、安全头、鉴权）→ 再用 P1 建立质量护栏（测试、错误码、pre-commit）→ 然后 P2 把部署和 CI/CD 工程化 → 最后按真实流量需要做 P3 的规模化能力。**
