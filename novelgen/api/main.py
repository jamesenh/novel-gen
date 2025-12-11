"""
FastAPI 应用入口

开发者: jamesenh
日期: 2025-12-08
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from novelgen.api.routes import content, export, generation, projects, rollback
from novelgen.api.websockets import progress as progress_ws

app = FastAPI(title="NovelGen Web API", version="0.1.0")


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    """统一 HTTP 异常格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": "HTTP_ERROR"},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """兜底异常处理"""
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "error_code": "SERVER_ERROR"},
    )


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


# 注册路由
app.include_router(projects.router)
app.include_router(generation.router)
app.include_router(content.router)
app.include_router(export.router)
app.include_router(rollback.router)
app.include_router(progress_ws.router)


