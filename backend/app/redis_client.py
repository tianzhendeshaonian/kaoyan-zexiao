from redis.asyncio import Redis

from .config import settings


redis_client: Redis = Redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
)


async def redis_ping() -> bool:
    try:
        return await redis_client.ping()
    except Exception:
        return False
