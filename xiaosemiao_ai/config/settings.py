"""应用全局配置（支持 .env 文件与环境变量覆盖）"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 应用
    APP_NAME: str = "萧瑟喵AI工作台"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    # 数据库（MySQL，异步驱动 aiomysql）
    DATABASE_URL: str = "mysql+aiomysql://root:123456@localhost:3306/xiaosemiao_ai"

    # Redis 缓存
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True

    # JWT 鉴权
    JWT_SECRET: str = "xiaosemiao-ai-v1-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    # Ollama 本地大模型
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_TIMEOUT: float = 120.0

    # 对话上下文窗口（携带最近 N 条消息）
    CONTEXT_MESSAGE_COUNT: int = 20

    # 缓存有效期（秒）
    CACHE_CHAT_DETAIL_TTL: int = 3600      # chat:detail:{chat_id} 1 小时
    CACHE_CHAT_LIST_TTL: int = 1800        # chat:list:{user_id}:{page}:{size} 30 分钟
    CACHE_HISTORY_LIST_TTL: int = 3600     # history:list:{user_id} 1 小时
    CACHE_FAVORITE_LIST_TTL: int = 1800    # favorite:list:{user_id}:{page}:{size} 30 分钟
    CACHE_USER_TOKEN_TTL: int = 604800     # user:token:{user_id} 7 天
    CACHE_CHAT_CONTEXT_TTL: int = 7200     # chat:context:{chat_id} 2 小时

    # CORS
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()