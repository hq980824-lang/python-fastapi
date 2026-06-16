# 数据库连接与迁移说明

## 技术栈

- **SQLAlchemy**：ORM 框架，负责定义表结构和执行 SQL
- **aiomysql**：异步 MySQL 驱动
- **Alembic**：数据库迁移工具，追踪表结构变更

---



## 一、数据库连接（`src/config/db.py`）

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

mysql_engine = create_async_engine(
    settings.mysql_url,   # 连接串来自环境变量
    pool_size=...,
    max_overflow=...,
    pool_recycle=...,
    pool_pre_ping=...,
)

AsyncSessionLocal = async_sessionmaker(bind=mysql_engine, ...)

Base = declarative_base()   # 所有 Model 继承这个 Base
```

**关键对象说明：**


| 对象                  | 作用                                              |
| ------------------- | ----------------------------------------------- |
| `mysql_engine`      | 全局异步引擎，管理连接池                                    |
| `AsyncSessionLocal` | 工厂，每次请求创建一个 Session                             |
| `Base`              | 所有 Model 的父类，持有 `metadata`（表结构信息）               |
| `get_db()`          | FastAPI 依赖注入函数，yield 一个 Session 供 controller 使用 |


---

## 二、定义表结构（Model）

以 `src/modules/users/user_model.py` 为例：

```python
from src.config.db import Base

class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    create_time = Column(DateTime, server_default=func.now())
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

继承 `Base` 后，这张表的结构会被注册进 `Base.metadata`，Alembic 才能感知到它。

---

## 三、Alembic 迁移

### 初始化（只做一次）

```bash
alembic init -t async migrations
```

`-t async` 使用异步模板，生成 `migrations/` 目录和 `alembic.ini`。

### 配置 `migrations/env.py`

需要做三件事：

1. 从 `settings` 读取数据库 URL
2. 把 `Base.metadata` 传给 Alembic 作为对比基准
3. **手动 import 所有 Model**，否则 `Base.metadata` 为空，Alembic 检测不到任何表

```python
from src.config.settings import settings
from src.config.db import Base
import src.modules.users.user_model  # noqa  ← 必须显式导入

target_metadata = Base.metadata
```

因为项目用异步引擎，迁移执行方式也要用异步：

```python
async def run_async_migrations():
    engine = create_async_engine(settings.mysql_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()
```

### 每次修改 Model 后的操作流程

```bash
# 1. 生成迁移文件（Alembic 对比 Model 和数据库，自动生成 SQL 差异）
alembic revision --autogenerate -m "描述本次变更"

# 2. 执行迁移，同步到数据库
alembic upgrade head
```

生成的迁移文件保存在 `migrations/versions/` 下，例如：

```
migrations/versions/178922d0b0ba_create_users_table.py
```

---

## 四、在接口中使用数据库

通过 FastAPI 的依赖注入，把 Session 传入 controller：

```python
# controller
@router.post("")
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create(db, payload)
```

```python
# service
async def create(self, db: AsyncSession, payload: UserCreate):
    new_user = UserDB(**payload.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
```

每次请求结束后，`get_db()` 的 `finally` 块会自动关闭 Session，无需手动管理。

---

## 五、常用 Alembic 命令


| 命令                     | 作用        |
| ---------------------- | --------- |
| `alembic upgrade head` | 升级到最新版本   |
| `alembic downgrade -1` | 回退一个版本    |
| `alembic current`      | 查看数据库当前版本 |
| `alembic history`      | 查看所有迁移历史  |


