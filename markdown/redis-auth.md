# Redis 封装与验证码登录鉴权说明

## 技术栈

- **redis-py（redis.asyncio）**：官方异步 Redis 客户端，与项目全异步风格一致
- **PyJWT**：生成、解析 JWT token
- **FastAPI HTTPBearer**：从请求头提取 `Authorization: Bearer <token>`

---

## 一、Redis 封装

整体复用了 MySQL 的封装思路：`settings` 配置 → `redis.py` 建连接池 + 依赖 → `main.py` 生命周期管理 → `redis_util` 工具类。

### 1. 配置（`src/config/settings.py`）

新增 5 个 `REDIS_*` 字段，从 `.env` 读取，并提供 `redis_url` 拼接属性：

```python
REDIS_HOST: str
REDIS_PORT: int
REDIS_PASSWORD: str
REDIS_DB: int
REDIS_MAX_CONNECTIONS: int

@property
def redis_url(self):
    # 密码为空时不拼 :password@，避免 redis://:@host 的歧义
    auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
    return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
```

### 2. 连接池与依赖（`src/config/redis.py`）

```python
from redis.asyncio import ConnectionPool, Redis

redis_pool = ConnectionPool.from_url(
    url=settings.redis_url,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True,   # 取值自动解码为 str，无需手动 decode
)
redis_client = Redis(connection_pool=redis_pool)

async def get_redis() -> AsyncGenerator[Redis, None]:
    yield redis_client       # 全局共享，不每请求开关
```

| 对象             | 作用                                    |
| -------------- | ------------------------------------- |
| `redis_pool`   | 全局连接池，基于 `redis_url` 创建               |
| `redis_client` | 全局客户端，整个应用共用一个                        |
| `get_redis()`  | FastAPI 依赖，yield 全局 client 供路由注入      |

> **要点**：与 `get_db()` 不同，Redis 依赖不需要 `async with` 或手动 close —— 连接池自己管理连接，每请求 close 反而会关掉共享客户端。连通性校验与释放都放在 `main.py` 的 lifespan 里。

### 3. 生命周期（`src/main.py`）

用 `lifespan` 在启动时 ping 校验、关闭时释放：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.ping()                 # 启动校验
    async with mysql_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    await redis_client.aclose()               # 释放（aclose，close 已废弃）
    await mysql_engine.dispose()
```

### 4. 工具类（`src/utils/redis_util.py`）

沿用项目 `XxxUtil` + `@staticmethod` 风格，client 作为参数传入：

```python
class RedisUtil:
    @staticmethod
    async def set_value(client: Redis, key: str, value, expire: int | None = None):
        await client.set(key, value, ex=expire)   # 过期用关键字 ex，按秒

    @staticmethod
    async def get_value(client: Redis, key: str) -> str | None:
        return await client.get(key)

    @staticmethod
    async def delete_value(client: Redis, key: str):
        return await client.delete(key)

    @staticmethod
    async def exists(client: Redis, key: str) -> int:
        return await client.exists(key)
```

---

## 二、验证码登录

逻辑拆分到 `auth_service.py`，controller 只负责注入依赖与组织返回，与 user 模块分层一致。

### 1. 发送验证码

```python
async def send_code(self, redis: Redis, email: str) -> str:
    code = EmailUtil.generate_code()
    if settings.ENV != 'dev':                        # dev 跳过真实发送
        try:
            await asyncio.to_thread(EmailUtil.send_verify_code, email, code)
        except Exception:
            raise ValueError("验证码发送失败，请稍后重试")
    await RedisUtil.set_value(redis, self._code_key(email), code, expire=5 * 60)
    return code
```

- **dev 环境直接返回明文 code**，方便调试；生产返回提示语，不泄露。
- 邮件发送是同步阻塞的 `smtplib`，用 `asyncio.to_thread` 丢到线程池，避免卡住事件循环。注意传函数和参数（`to_thread(fn, a, b)`），不要带括号直接调用。
- 验证码写入 Redis 并设 5 分钟过期，与邮件提示一致。

### 2. 校验并登录

```python
async def verify_and_login(self, redis: Redis, dto: EmailLoginDto, db: AsyncSession) -> str:
    code = await RedisUtil.get_value(redis, self._code_key(dto.email))
    if code is None:
        raise ValueError("请先获取邮箱验证码")
    if code != dto.code:
        raise ValueError("验证码错误")

    user = await UserService().get_by_email(db, email=dto.email)
    if user is None:
        raise ValueError("用户不存在")

    token = JwtUtil.create_access_token(subject=user.id)   # token 存 user_id
    await RedisUtil.delete_value(redis, self._code_key(dto.email))
    return token
```

- service 层只抛 `ValueError`，由全局 `value_err_handler` 统一转 400，**不依赖 fastapi**。
- 校验通过后删除验证码，防止一码多用。
- **token 的 `sub` 存 user_id（int）**，与 `decode_access_token` 的 `int(sub)` 闭环一致。

---

## 三、Token 鉴权

### 1. 当前用户依赖（`src/common/dependencies.py`）

```python
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials                  # 属性，不是方法
    user_id = JwtUtil.decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="登录已失效，请重新登录")
    user = await UserService().get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="用户不存在")
    return user
```

- `HTTPBearer` 自动解析 `Authorization: Bearer xxx`，并在 Swagger 提供 Authorize 按钮。
- 鉴权失败抛 **401 HTTPException**（协议层语义），区别于 service 的业务 `ValueError`。

### 2. 获取用户信息接口（`src/modules/users/user_controller.py`）

```python
@router.get("/profile", response_model=UserResp)
async def get_profile(current_user: UserDB = Depends(get_current_user)):
    return current_user
```

- 脏活都在依赖里做完，路由体只需返回对象（`UserResp` 配了 `from_attributes=True`）。
- **路由顺序**：`/profile` 必须定义在 `/{user_id}` 之前，否则会被当成 user_id 匹配走。

---

## 四、踩坑记录

| 现象 | 原因 | 修正 |
| --- | --- | --- |
| 启动报 `ValidationError: REDIS_* Field required` | `.env` 缺字段或字段名大小写不符 | 补全 `.env`，名字与 settings 大写一致 |
| `redis://:@host` 连接异常 | 密码为空仍拼了 `:@` | `redis_url` 判断密码为空时不拼 auth 段 |
| 请求 `/send-code` 一直转圈 | SMTP 端口/加密不匹配，且无 timeout 永久等待 | 465 用 SMTP_SSL、587 用 STARTTLS；加 timeout |
| `'str' object is not callable` | `credentials.credentials()` 多了括号 | 它是属性，去掉 `()` |
| `'UserDB' object is not callable` | `current_user()` 多了括号 | 它是数据对象，去掉 `()` |
| 实例方法当类方法调报错 | `UserService.get_by_id(...)` 漏了实例 | 改 `UserService().get_by_id(...)` |
| 登录报"用户不存在" | 该 email 未在 users 表注册（B 方案：不自动注册） | 用已注册邮箱，或先建用户 |

---

## 五、完整调用链

```
POST /auth/send-code   → AuthService.send_code   → 生成码 → (生产)发邮件 → 写 Redis(5min)
POST /auth/login       → AuthService.verify_and_login → 校验码 → 查 user → 用 id 签 token → 删码
GET  /users/profile    → get_current_user 依赖   → 取 token → 解码 → 查 user → 返回
```
