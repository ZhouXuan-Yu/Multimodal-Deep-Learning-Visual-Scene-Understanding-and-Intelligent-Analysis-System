"""
路由追踪中间件
用于记录所有API请求和响应信息
"""

import time
from typing import Callable, Dict, Any
import logging
import json
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

# 创建日志记录器
logger = logging.getLogger("api.routes")

class RouteTrackerMiddleware(BaseHTTPMiddleware):
    """路由追踪中间件，记录API请求和响应"""
    
    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 跳过不需要记录的路径
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # 记录请求开始
        start_time = time.time()
        
        # 请求ID（用于关联请求和响应）
        request_id = f"{int(start_time * 1000)}"
        
        # 提取请求信息
        client_host = request.client.host if request.client else "unknown"
        method = request.method
        url = str(request.url)
        headers = dict(request.headers)
        query_params = dict(request.query_params)

        # 记录请求体 (如果有)
        request_body = ""
        if method in ["POST", "PUT", "PATCH"]:
            try:
                raw_body = await request.body()
                request.scope["_body"] = raw_body  # 保存请求体供后续使用
                try:
                    request_body = raw_body.decode("utf-8")
                except UnicodeDecodeError:
                    request_body = "[二进制数据]"
            except Exception as e:
                request_body = f"[无法读取请求体: {str(e)}]"

        # 打印请求信息
        logger.info(f"┌── API请求 [{request_id}] ──────────────────────────────")
        logger.info(f"│ 📤 {method} {url} - 客户端: {client_host}")
        if query_params:
            logger.info(f"│ 📝 查询参数: {json.dumps(query_params, ensure_ascii=False)}")
        if request_body and len(request_body) < 500:  # 只打印较短的请求体
            logger.info(f"│ 📄 请求体: {request_body}")
        logger.info(f"└─────────────────────────────────────────────────")

        try:
            # 调用下一个中间件/路由处理器
            response = await call_next(request)
            
            # 计算请求处理时间
            process_time = time.time() - start_time
            process_time_ms = round(process_time * 1000)
            
            # 记录响应信息
            status_code = response.status_code
            
            # 只有对文本类型响应才尝试获取响应体
            response_body = ""
            if "content-type" in response.headers and "json" in response.headers["content-type"]:
                # 保存原始响应
                original_response_body = b""
                async for chunk in response.body_iterator:
                    original_response_body += chunk
                
                # 创建新的响应
                response = Response(
                    content=original_response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
                # 尝试解析响应体
                try:
                    response_body = original_response_body.decode("utf-8")
                    if len(response_body) > 500:  # 截断过长的响应
                        response_body = response_body[:500] + "... [截断]"
                except UnicodeDecodeError:
                    response_body = "[二进制数据]"
            
            # 根据状态码确定响应类型
            status_symbol = "✅" if status_code < 400 else "⚠️" if status_code < 500 else "❌"
            
            # 打印响应信息
            logger.info(f"┌── API响应 [{request_id}] ──────────────────────────────")
            logger.info(f"│ 📥 {method} {url} - 状态: {status_code} {status_symbol} - 用时: {process_time_ms}ms")
            if response_body:
                logger.info(f"│ 📄 响应体: {response_body}")
            logger.info(f"└─────────────────────────────────────────────────")
            
            # 添加处理时间和请求ID到响应头
            response.headers["X-Process-Time"] = str(process_time_ms)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # 记录错误
            process_time = time.time() - start_time
            process_time_ms = round(process_time * 1000)
            
            logger.error(f"┌── API错误 [{request_id}] ──────────────────────────────")
            logger.error(f"│ ❌ {method} {url} - 错误: {str(e)}")
            logger.error(f"│ ⏱️ 用时: {process_time_ms}ms")
            logger.exception(e)
            logger.error(f"└─────────────────────────────────────────────────")
            
            # 返回JSON错误响应
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal Server Error",
                    "message": str(e),
                    "request_id": request_id
                }
            )


class ErrorHandler:
    """统一错误处理类"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        
        # 注册异常处理器
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            """全局异常处理"""
            # 记录错误
            logger.error(f"全局异常: {str(exc)}")
            logger.exception(exc)
            
            # 提取请求路径
            path = request.url.path
            method = request.method
            
            # 构建错误响应
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": str(exc),
                    "path": path,
                    "method": method,
                    "timestamp": time.time(),
                    "type": exc.__class__.__name__
                }
            )


def setup_route_tracking(app: FastAPI) -> None:
    """为FastAPI应用设置路由追踪"""
    # 添加路由追踪中间件
    app.add_middleware(RouteTrackerMiddleware)
    
    # 设置错误处理
    ErrorHandler(app)
    
    logger.info("✅ 路由追踪和错误处理已设置")
