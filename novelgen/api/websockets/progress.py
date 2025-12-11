"""
生成进度 WebSocket 路由

开发者: jamesenh
日期: 2025-12-08
"""
import json
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from novelgen.services import generation_service

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@router.websocket("/ws/projects/{name}/progress")
async def progress_websocket(websocket: WebSocket, name: str):
    """实时推送生成进度与日志"""
    await websocket.accept()
    client = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    progress_channel = f"generation_progress_channel:{name}"
    log_channel = f"generation_logs_channel:{name}"
    await pubsub.subscribe(progress_channel, log_channel)

    # 初始快照
    snapshot = generation_service.read_progress(project_name=name)
    try:
        await websocket.send_json({"type": "progress", "data": snapshot})
    except WebSocketDisconnect:
        # 客户端断开时提前退出
        await pubsub.unsubscribe(progress_channel, log_channel)
        await pubsub.close()
        await client.close()
        return

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            channel = message["channel"]
            raw = message["data"]
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw
            if channel == progress_channel:
                try:
                    await websocket.send_json({"type": "progress", "data": payload})
                except WebSocketDisconnect:
                    break
            else:
                try:
                    await websocket.send_json({"type": "log", "data": payload})
                except WebSocketDisconnect:
                    break
    except WebSocketDisconnect:
        # 客户端主动断开，忽略
        pass
    finally:
        await pubsub.unsubscribe(progress_channel, log_channel)
        await pubsub.close()
        await client.close()


