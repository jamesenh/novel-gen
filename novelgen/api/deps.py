"""
API 依赖定义

提供 Redis 客户端与通用配置依赖，便于在路由中复用。

开发者: jamesenh
日期: 2025-12-08
"""
import os
from typing import AsyncGenerator

import redis.asyncio as redis

# 默认项目目录与 Redis 连接
PROJECTS_ROOT = os.getenv("NOVELGEN_PROJECTS_DIR", "projects")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """
    提供 Redis 异步客户端

    Returns:
        异步 Redis 连接实例
    """
    client: redis.Redis = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


