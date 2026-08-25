from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # runtime
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # mysql
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "kyzx"
    DB_PASSWORD: str = "kyzx_dev_pass"
    DB_NAME: str = "kaoyan_zexiao"
    DB_ECHO: bool = False

    # redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # jwt
    JWT_SECRET_KEY: str = "change_me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TTL_MIN: int = 120
    JWT_REFRESH_TTL_DAY: int = 7

    # wechat
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""

    # rate limit
    RL_GLOBAL_IP_PER_MIN: int = 60
    RL_LOGIN_IP_PER_MIN: int = 10
    RL_RECOMMEND_FREE_PER_DAY: int = 3
    RL_REPORT_PER_DAY: int = 5

    # crawler local-test
    CRAWLER_DELAY_MIN_SEC: float = 2.0
    CRAWLER_DELAY_MAX_SEC: float = 5.0
    CRAWLER_RETRY_MAX: int = 3
    CRAWLER_DOMAIN_WHITELIST: str = "edu.cn"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def crawler_whitelist_domains(self) -> list[str]:
        return [d.strip() for d in self.CRAWLER_DOMAIN_WHITELIST.split(",") if d.strip()]


settings = Settings()
