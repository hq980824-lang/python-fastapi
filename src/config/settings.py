import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV = os.getenv("ENV", "dev")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=('.env', f".env.{ENV}"), env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str
    APP_PORT: int

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str

    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str
    MYSQL_CHARSET: str

    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    DB_POOL_RECYCLE: int
    DB_POOL_PRE_PING: bool

    @property
    def mysql_url(self):
        # mysql+aiomysql://用户名:密码@地址:端口/数据库名?charset=utf8mb4
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            f"?charset={self.MYSQL_CHARSET}"
        )


settings = Settings()