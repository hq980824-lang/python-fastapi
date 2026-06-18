from contextlib import asynccontextmanager
from sqlalchemy import text
import uvicorn
from fastapi import FastAPI, HTTPException
from src.common.exception import global_err_handler, http_err_handler, value_err_handler
from src.config.db import mysql_engine
from src.config.redis import redis_client
from src.config.settings import settings
from src.modules.users.user_controller import router as user_router
from src.modules.auth.auth_controller import router as auth_router



def dev():
    uvicorn.run("src.main:app", reload=True, host="0.0.0.0", port=settings.APP_PORT)

def prod():
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, workers=4, log_level="warning")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("服务正在启动，开始校验数据库、Redis连接...")

    try:
        ping_result = await redis_client.ping()
        if ping_result:
            print("Redis 连接成功")
    except Exception as e:
        print(f"Redis 连接失败：{str(e)}")
        raise

    try:
        async with mysql_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print('MySQL 数据库连接校验成功')
    except Exception as e:
        print(f"MySQL 数据库连接校验失败：{str(e)}")
        await redis_client.aclose()
        await mysql_engine.dispose()
        raise SystemExit('MySQL连接异常，终止服务启动')

    yield

    print('服务器即将关闭，开始释放资源...')
    await redis_client.aclose()
    print('Redis 连接池已释放')

    await mysql_engine.dispose()
    print('MySQL 引擎已释放')

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.include_router(user_router)
app.include_router(auth_router)

app.add_exception_handler(HTTPException, http_err_handler)
app.add_exception_handler(ValueError, value_err_handler)
app.add_exception_handler(Exception, global_err_handler)