import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV = os.getenv("ENV", "dev")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{ENV}"), env_file_encoding="utf-8", extra="ignore"
    )

    ENV: str = "dev"

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

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_DB: int
    REDIS_MAX_CONNECTIONS: int

    CORS_ALLOW_ORIGINS: str = ""

    HE_FENG_API_HOST: str
    HE_FENG_KID: str
    HE_FENG_SID: str
    HE_FENG_ALGORITHM: str

    @property
    def mysql_url(self):
        # mysql+aiomysql://用户名:密码@地址:端口/数据库名?charset=utf8mb4
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            f"?charset={self.MYSQL_CHARSET}"
        )

    @property
    def redis_url(self):
        # redis://:password@host:port/db
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def cors_origins(self) -> list[str]:
        if not self.CORS_ALLOW_ORIGINS:
            return []
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",")]

    @property
    def he_feng_bem(self):
        return "/Users/huangqiang/fj-app-pc/python-fastapi/weather/ed25519-private.pem"

    @property
    def he_feng_api_prefix(self):
        return f"https://{self.HE_FENG_API_HOST}/"

settings = Settings()
