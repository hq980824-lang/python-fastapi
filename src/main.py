from contextlib import asynccontextmanager
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.common.exception import global_err_handler, http_err_handler, value_err_handler
from src.common.logger import setup_logging
from src.common.middleware import TraceIDMiddleware
from src.config.db import mysql_engine
from src.config.redis import redis_client
from src.config.settings import settings
from src.modules.health.health_controller import router as health_router
from src.modules.health.health_service import check_mysql, check_redis
from src.modules.users.user_controller import router as user_router
from src.modules.auth.auth_controller import router as auth_router

logger = logging.getLogger(__name__)

def dev():
    uvicorn.run("src.main:app", reload=True, host="0.0.0.0", port=settings.APP_PORT)

def prod():
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, workers=4, log_level="warning")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("服务正在启动，开始校验数据库、Redis连接...")

    if await check_redis():
        logger.info('Redis 连接成功')
    else:
        logger.error('Redis 连接异常，终止服务启动')
        raise SystemExit("Redis 连接异常，终止服务启动")

    if await check_mysql():
        logger.info('MySQL 数据库连接校验成功')
    else:
        logger.error('MySQL 连接异常，终止服务启动')
        raise SystemExit("MySQL 连接异常，终止服务启动")

    yield

    logger.info('服务器即将关闭，开始释放资源...')
    await redis_client.aclose()
    logger.info('Redis 连接池已释放')

    await mysql_engine.dispose()
    logger.info('MySQL 引擎已释放')

setup_logging()

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(TraceIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,   # 白名单,允许的前端域名
    allow_credentials=True,                      # 允许带 cookie/认证头
    allow_methods=["*"],                         # 允许的 HTTP 方法
    allow_headers=["*"],                         # 允许的请求头
)

app.include_router(user_router)
app.include_router(auth_router)
app.include_router(health_router)

app.add_exception_handler(HTTPException, http_err_handler)
app.add_exception_handler(ValueError, value_err_handler)
app.add_exception_handler(Exception, global_err_handler)