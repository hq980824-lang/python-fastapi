# 环境变量配置说明

## 文件结构

```
.env          # 所有环境共用的默认值
.env.dev      # 开发环境覆盖值
.env.prod     # 生产环境覆盖值
```

> 以上文件均已加入 `.gitignore`，不会提交到 git。

## 加载机制

通过系统环境变量 `ENV` 决定加载哪套配置，默认值为 `dev`。

```python
# src/config/settings.py
ENV = os.getenv("ENV", "dev")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=('.env', f".env.{ENV}")  # 先读 .env，再读 .env.{ENV}，后者覆盖前者
    )
```

加载顺序：`.env` → `.env.dev` 或 `.env.prod`，后面的值覆盖前面的。

## 切换环境

```bash
# 开发环境（默认）
poetry run dev

# 生产环境
ENV=prod poetry run prod
```

## 配置项说明

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `app_name` | str | FastAPI 应用名称 |
| `port` | int | 服务端口，默认 8000 |
| `MYSQL_HOST` | str | 数据库地址 |
| `MYSQL_PORT` | int | 数据库端口 |
| `MYSQL_USER` | str | 数据库用户名 |
| `MYSQL_PASSWORD` | str | 数据库密码 |
| `MYSQL_DB` | str | 数据库名 |
| `MYSQL_CHARSET` | str | 字符集，通常为 `utf8mb4` |
| `DB_POOL_SIZE` | int | 连接池大小 |
| `DB_MAX_OVERFLOW` | int | 连接池最大溢出数 |
| `DB_POOL_RECYCLE` | int | 连接回收时间（秒） |
| `DB_POOL_PRE_PING` | bool | 是否在使用前检测连接存活 |

## 使用位置

| 文件 | 用途 |
|------|------|
| `src/main.py` | `settings.app_name` 设置 FastAPI 的 title |
| `src/config/db.py` | `settings.mysql_url` 及连接池配置创建数据库引擎 |
| `migrations/env.py` | `settings.mysql_url` 供 Alembic 连接数据库做迁移 |

## 数据库连接串

`mysql_url` 是 `settings.py` 中的 `@property`，自动拼接：

```
mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset={MYSQL_CHARSET}
```

## `settings` 单例

`settings.py` 底部执行 `settings = Settings()`，全局实例化一次。其他模块直接导入使用：

```python
from src.config.settings import settings
```
