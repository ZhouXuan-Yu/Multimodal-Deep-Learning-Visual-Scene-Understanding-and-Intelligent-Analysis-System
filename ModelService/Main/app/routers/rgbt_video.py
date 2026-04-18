"""
RGBT视频处理API路由

提供视频上传、处理和结果获取的API接口
"""

import os
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
# 导入数据模型
from app.models.rgbt_video import (
    VideoUploadResponse,
    VideoProcessResponse,
    TaskStatusResponse,
    VideoResultResponse
    # VideoTaskCreate 不再使用，已移除
)

# 导入自定义服务
from app.services.rgbt_video_processing import RGBTVideoProcessor
from app.services.rgbt_video_processing.utils import is_valid_video_format

# 设置日志记录器
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="",  # 不使用前缀，因为main.py中已经设置了前缀/api/rgbt-video
    tags=["RGBT视频处理"],
    responses={404: {"description": "Not found"}},
)

# 设置视频存储位置
UPLOAD_DIR = os.path.join(os.getcwd(), "static", "rgbt_video", "uploads")
OUTPUT_DIR = os.path.join(os.getcwd(), "static", "rgbt_video", "outputs")

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 初始化模板引擎
templates = Jinja2Templates(directory="app/templates")

# 初始化视频处理器
video_processor = RGBTVideoProcessor(output_dir=OUTPUT_DIR)

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    video_type: str = Form(...),  # "rgb" 或 "thermal"
    video_file: UploadFile = File(...)
):
    """
    上传视频文件
    
    参数:
        video_type: 视频类型，"rgb"表示可见光视频，"thermal"表示热成像视频
        video_file: 视频文件
    
    返回:
        包含上传状态和视频路径的响应
    """
    try:
        # 检查视频类型是否有效
        if video_type not in ["rgb", "thermal"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "无效的视频类型", "error": "视频类型必须是'rgb'或'thermal'"}
            )
        
        # 检查视频格式是否支持
        if not is_valid_video_format(video_file.filename):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "不支持的视频格式", 
                    "error": "只支持MP4、AVI、MKV和MOV格式"
                }
            )
        
        # 为上传的视频生成唯一文件名
        file_extension = os.path.splitext(video_file.filename)[1]
        unique_filename = f"{video_type}_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # 保存上传的视频
        with open(file_path, "wb") as f:
            content = await video_file.read()
            f.write(content)
        
        logger.info(f"视频上传成功: {file_path}")
        
        # 返回成功响应
        return {
            "success": True,
            "message": "视频上传成功",
            "video_path": file_path
        }
    
    except Exception as e:
        logger.error(f"视频上传失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "视频上传失败", "error": str(e)}
        )

@router.post("/process", response_model=VideoProcessResponse)
async def process_video(request: Request):
    """
    处理视频
    
    参数:
        request_data: 请求体，包含如下参数:
            - rgb_video_path: RGB视频路径
            - thermal_video_path: 热成像视频路径（可选）
    
    返回:
        任务ID和状态
    """
    try:
        # 直接解析JSON请求体
        request_data = await request.json()
        logger.info(f"接收到请求数据: {request_data}")
        
        # 从字典中提取视频路径
        rgb_video_path = request_data.get("rgb_video_path")
        thermal_video_path = request_data.get("thermal_video_path")
        
        # 记录请求参数
        logger.info(f"请求参数: rgb_video_path={rgb_video_path}, thermal_video_path={thermal_video_path}")
        
        # 检查是否提供RGB视频路径
        if not rgb_video_path:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "需要提供RGB视频路径", 
                    "error": "rgb_video_path参数缺失"
                }
            )
        
        # 检查视频文件是否存在
        if not os.path.exists(rgb_video_path):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "RGB视频文件不存在", 
                    "error": f"未找到视频: {rgb_video_path}"
                }
            )
        
        if thermal_video_path and not os.path.exists(thermal_video_path):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "热成像视频文件不存在", 
                    "error": f"未找到视频: {thermal_video_path}"
                }
            )
        
        # 创建处理任务
        task_result = video_processor.create_task(rgb_video_path, thermal_video_path)
        
        if not task_result["success"]:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False, 
                    "message": "创建视频处理任务失败", 
                    "error": task_result.get("error", "未知错误")
                }
            )
        
        # 获取任务ID
        task_id = task_result["task_id"]
        
        # 启动异步处理任务
        process_result = video_processor.process_video_async(task_id)
        
        if not process_result["success"]:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False, 
                    "message": "启动视频处理任务失败", 
                    "error": process_result.get("error", "未知错误")
                }
            )
        
        # 返回任务ID和状态
        return {
            "success": True,
            "task_id": task_id,
            "message": "视频处理任务已启动"
        }
    
    except Exception as e:
        logger.error(f"视频处理请求失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "视频处理请求失败", "error": str(e)}
        )

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    参数:
        task_id: 任务ID
    
    返回:
        任务状态信息
    """
    try:
        # 获取任务状态
        status_result = video_processor.get_task_status(task_id)
        
        if not status_result["success"]:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False, 
                    "message": "获取任务状态失败", 
                    "error": status_result.get("error", "未知错误")
                }
            )
        
        # 提取任务信息
        task = status_result["task"]
        
        # 返回状态响应
        return {
            "success": True,
            "status": task["status"],
            "progress": task["progress"]
        }
    
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "获取任务状态失败", "error": str(e)}
        )

@router.get("/result/{task_id}", response_model=VideoResultResponse)
async def get_task_result(task_id: str):
    """
    获取任务结果
    
    参数:
        task_id: 任务ID
    
    返回:
        任务结果信息
    """
    # 确保输出目录存在
    uploads_dir = os.path.join(os.getcwd(), "static", "rgbt_video", "uploads")
    outputs_dir = os.path.join(os.getcwd(), "static", "rgbt_video", "outputs")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)
    
    logger.debug(f"获取任务结果: {task_id}, 上传目录: {uploads_dir}, 输出目录: {outputs_dir}")
    try:
        # 获取任务状态
        status_result = video_processor.get_task_status(task_id)
        
        if not status_result["success"]:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False, 
                    "message": "获取任务结果失败", 
                    "error": status_result.get("error", "未知错误")
                }
            )
        
        # 提取任务信息
        task = status_result["task"]
        
        # 检查任务是否完成
        if task["status"] != "completed":
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "任务尚未完成", 
                    "error": f"当前任务状态: {task['status']}, 进度: {task['progress']}%"
                }
            )
        
        # 返回结果信息
        # 处理安全的时间计算 - 始终保证返回浮点数或None
        processing_time = None
        try:
            if task.get("completed_at") and task.get("started_at"):
                # 如果是时间对象，尝试转换为浮点数
                if isinstance(task["completed_at"], datetime) and isinstance(task["started_at"], datetime):
                    # 计算时间差在秒数
                    time_diff = (task["completed_at"] - task["started_at"]).total_seconds()
                    processing_time = float(time_diff)
                elif isinstance(task["completed_at"], (int, float)) and isinstance(task["started_at"], (int, float)):
                    processing_time = float(task["completed_at"] - task["started_at"])
                # 如果是字符串或其他类型，不进行计算，返回None
                else:
                    logger.warning(f"不支持的时间格式，无法计算处理时间: {type(task['completed_at'])} - {type(task['started_at'])}")
        except Exception as e:
            logger.error(f"计算处理时间失败: {str(e)}")
            processing_time = None
            
        # 记录完整的任务数据，帮助调试
        logger.debug(f"任务详情: {task}")
        
        # 确保所有路径正确性
        rgb_original = None
        rgb_processed = None
        thermal_original = None
        thermal_processed = None
        combined_video = None
        
        # 检查RGB视频路径
        if task.get('rgb_video', {}).get('path'):
            rgb_path = task['rgb_video']['path']
            rgb_original = f"/static/rgbt_video/uploads/{os.path.basename(rgb_path)}"
            logger.debug(f"RGB原始视频路径: {rgb_path}, 生成URL: {rgb_original}")
        
        # 检查RGB处理结果路径
        if task.get('output', {}).get('rgb_processed'):
            rgb_proc_path = task['output']['rgb_processed']
            rgb_processed = f"/static/rgbt_video/outputs/{os.path.basename(rgb_proc_path)}"
            logger.debug(f"RGB处理后视频路径: {rgb_proc_path}, 生成URL: {rgb_processed}")
            # 验证文件是否存在
            full_path = os.path.join(os.getcwd(), "static", "rgbt_video", "outputs", os.path.basename(rgb_proc_path))
            if not os.path.exists(full_path):
                logger.warning(f"RGB处理后视频文件不存在: {full_path}")
        
        # 检查热成像视频路径
        if task.get('thermal_video', {}).get('path'):
            thermal_path = task['thermal_video']['path']
            thermal_original = f"/static/rgbt_video/uploads/{os.path.basename(thermal_path)}"
            logger.debug(f"热成像原始视频路径: {thermal_path}, 生成URL: {thermal_original}")
        
        # 检查热成像处理结果路径
        if task.get('output', {}).get('thermal_processed'):
            thermal_proc_path = task['output']['thermal_processed']
            thermal_processed = f"/static/rgbt_video/outputs/{os.path.basename(thermal_proc_path)}"
            logger.debug(f"热成像处理后视频路径: {thermal_proc_path}, 生成URL: {thermal_processed}")
            # 验证文件是否存在
            full_path = os.path.join(os.getcwd(), "static", "rgbt_video", "outputs", os.path.basename(thermal_proc_path))
            if not os.path.exists(full_path):
                logger.warning(f"热成像处理后视频文件不存在: {full_path}")
        
        # 检查组合视频路径
        if task.get('output', {}).get('combined'):
            combined_path = task['output']['combined']
            combined_video = f"/static/rgbt_video/outputs/{os.path.basename(combined_path)}"
            logger.debug(f"组合视频路径: {combined_path}, 生成URL: {combined_video}")
        
        # 确保所有模型要求的字段都被包含，即使它们是空值
        return {
            "success": True,
            "task_id": task_id,
            "status": task["status"],
            "created_at": task["created_at"],
            "completed_at": task.get("completed_at"),  # 使用get避免KeyError
            "processing_time": processing_time,
            "rgb_video": {
                "original": rgb_original,
                "processed": rgb_processed
            },
            "thermal_video": {
                "original": thermal_original,
                "processed": thermal_processed
            },
            "combined_video": combined_video,
            "detection_stats": task.get("detection_stats", {}),  # 添加detection_stats字段
            "error": task.get("error")  # 添加error字段
        }
    
    except Exception as e:
        logger.error(f"获取任务结果失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "获取任务结果失败", "error": str(e)}
        )

@router.get("/view/{task_id}", response_class=HTMLResponse)
async def view_video_result(request: Request, task_id: str):
    """
    查看视频处理结果页面
    
    参数:
        task_id: 任务ID
    
    返回:
        HTML页面
    """
    try:
        # 获取任务状态
        status_result = video_processor.get_task_status(task_id)
        
        if not status_result["success"]:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error_message": "获取任务失败",
                    "error_detail": status_result.get("error", "未知错误")
                }
            )
        
        # 提取任务信息
        task = status_result["task"]
        
        # 检查任务是否完成
        if task["status"] != "completed":
            return templates.TemplateResponse(
                "processing.html",
                {
                    "request": request,
                    "task_id": task_id,
                    "status": task["status"],
                    "progress": task["progress"]
                }
            )
        
        # 准备模板数据
        template_data = {
            "request": request,
            "task_id": task_id,
            "status": task["status"],
            "created_at": task["created_at"],
            "completed_at": task["completed_at"],
            "processing_time": (
                (task["completed_at"] - task["started_at"]).total_seconds()
                if task["completed_at"] and task["started_at"] else None
            ),
            "rgb_video": {
                "original": f"/static/rgbt_video/uploads/{os.path.basename(task['rgb_video']['path'])}",
                "processed": f"/static/rgbt_video/outputs/{os.path.basename(task['output']['rgb_processed'])}"
            },
            "detection_stats": task.get("detection_stats")
        }
        
        # 添加热成像视频信息（如果存在）
        if task.get("thermal_video", {}).get("path"):
            template_data["thermal_video"] = {
                "original": f"/static/rgbt_video/uploads/{os.path.basename(task['thermal_video']['path'])}",
                "processed": (
                    f"/static/rgbt_video/outputs/{os.path.basename(task['output']['thermal_processed'])}"
                    if task["output"].get("thermal_processed") else None
                )
            }
        
        # 添加融合视频信息（如果存在）
        if task["output"].get("combined"):
            template_data["combined_video"] = f"/static/rgbt_video/outputs/{os.path.basename(task['output']['combined'])}"
        
        # 渲染模板
        return templates.TemplateResponse("video_results.html", template_data)
    
    except Exception as e:
        logger.error(f"渲染视频结果页面失败: {str(e)}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": "渲染视频结果页面失败",
                "error_detail": str(e)
            }
        )

@router.get("/download/{video_type}/{task_id}")
async def download_video(video_type: str, task_id: str):
    """
    下载处理后的视频
    
    参数:
        video_type: 视频类型，"rgb"、"thermal"或"combined"
        task_id: 任务ID
    
    返回:
        视频文件
    """
    try:
        # 检查视频类型是否有效
        if video_type not in ["rgb", "thermal", "combined"]:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "无效的视频类型", 
                    "error": "视频类型必须是'rgb'、'thermal'或'combined'"
                }
            )
        
        # 获取任务状态
        status_result = video_processor.get_task_status(task_id)
        
        if not status_result["success"]:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False, 
                    "message": "获取任务失败", 
                    "error": status_result.get("error", "未知错误")
                }
            )
        
        # 提取任务信息
        task = status_result["task"]
        
        # 检查任务是否完成
        if task["status"] != "completed":
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "任务尚未完成", 
                    "error": f"当前任务状态: {task['status']}, 进度: {task['progress']}%"
                }
            )
        
        # 根据视频类型获取视频路径
        video_path = None
        if video_type == "rgb":
            video_path = task["output"]["rgb_processed"]
        elif video_type == "thermal":
            video_path = task["output"]["thermal_processed"]
        elif video_type == "combined":
            video_path = task["output"]["combined"]
        
        # 检查视频是否存在
        if not video_path or not os.path.exists(video_path):
            return JSONResponse(
                status_code=404,
                content={
                    "success": False, 
                    "message": f"{video_type}视频不存在", 
                    "error": "请求的视频文件不存在"
                }
            )
        
        # 返回视频文件
        return FileResponse(
            path=video_path,
            filename=os.path.basename(video_path),
            media_type="video/mp4"
        )
    
    except Exception as e:
        logger.error(f"下载视频失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "下载视频失败", "error": str(e)}
        )
