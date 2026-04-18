import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time

logger = logging.getLogger(__name__)

class LargeFileHandlingMiddleware(BaseHTTPMiddleware):
    """处理大文件上传的中间件，增加超时时间和请求大小限制"""
    
    async def dispatch(self, request: Request, call_next):
        # 检查是否是上传操作
        path = request.url.path
        method = request.method
        
        is_upload = False
        if method == "POST" and any(upload_path in path for upload_path in [
            "/api/fire_detection_direct/upload-video",
            "/api/fire-detection/upload"
        ]):
            is_upload = True
            logger.info(f"大文件上传中间件: 检测到上传请求 {method} {path}")
        
        # 记录请求开始时间
        start_time = time.time()
        
        try:
            # 调用下一个中间件或路由处理函数
            response = await call_next(request)
            
            # 记录处理时间
            process_time = time.time() - start_time
            if is_upload:
                logger.info(f"大文件上传中间件: 上传请求处理完成, 耗时 {process_time:.2f} 秒")
            
            return response
        except Exception as e:
            # 记录错误
            logger.exception(f"大文件上传中间件: 处理请求时出错: {str(e)}")
            
            # 返回错误响应
            error_response = Response(
                content=f'{{"detail": "服务器处理请求时出错: {str(e)}"}}',
                status_code=500,
                media_type="application/json"
            )
            return error_response 