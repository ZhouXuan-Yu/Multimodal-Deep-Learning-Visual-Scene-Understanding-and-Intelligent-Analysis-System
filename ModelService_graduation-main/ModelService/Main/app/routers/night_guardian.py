"""
夜间保卫者系统API路由
提供视频处理、人体检测和行为识别的API接口
"""

import os
import logging
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Path
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from datetime import datetime

# 导入服务层
from app.services.night_guardian_service import NightGuardianService

# 创建路由器
router = APIRouter()

# 创建服务实例
night_guardian_service = NightGuardianService()

# 设置日志
logger = logging.getLogger(__name__)

# 模型定义
class VideoProcessRequest(BaseModel):
    """视频处理请求模型"""
    model_type: str = Field(default="OptimizedActionNetLite", description="模型类型")
    threshold: float = Field(default=0.6, description="检测阈值")
    clip_len: int = Field(default=16, description="视频片段长度")
    save_frames: bool = Field(default=False, description="是否保存关键帧")

class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str
    progress: Optional[int] = None
    results: Optional[List[Dict[str, Any]]] = None
    output_path: Optional[str] = None
    error: Optional[str] = None

@router.post("/process-video", response_model=TaskResponse)
async def process_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_type: str = Form("OptimizedActionNetLite"),
    threshold: float = Form(0.6),
    clip_len: int = Form(16),
    save_frames: bool = Form(False)
):
    """
    上传并处理视频文件，识别其中的行为
    
    - **file**: 要处理的视频文件
    - **model_type**: 使用的模型类型
    - **threshold**: 检测阈值
    - **clip_len**: 视频片段长度
    - **save_frames**: 是否保存关键帧
    """
    # 添加详细日志，记录请求接收信息
    logger.info(f"=== 收到视频处理请求 ===")
    logger.info(f"请求时间: {datetime.now().isoformat()}")
    logger.info(f"文件名: {file.filename}")
    logger.info(f"内容类型: {file.content_type}")
    logger.info(f"模型类型: {model_type}")
    logger.info(f"阈值: {threshold}")
    logger.info(f"片段长度: {clip_len}")
    logger.info(f"保存帧: {save_frames}")

    try:
        # 详细检查上传的文件
        if not file.filename:
            raise ValueError("上传的文件名为空")

        if not file.content_type.startswith('video/'):
            logger.warning(f"上传的文件类型不是视频: {file.content_type}")
            # 不严格检查内容类型，允许继续处理
            
        logger.info(f"检查文件对象: {type(file)}")
        
        # 测试文件读取功能
        try:
            # 读取少量数据测试文件可访问性
            sample_content = await file.read(1024)
            logger.info(f"成功读取文件前1KB: {len(sample_content)} 字节")
            # 重置文件指针
            await file.seek(0)
        except Exception as read_error:
            logger.error(f"读取上传文件时出错: {str(read_error)}")
            import traceback
            logger.error(f"文件读取错误详情: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"无法读取上传的文件: {str(read_error)}",
                    "details": traceback.format_exc()
                }
            )

        # 创建临时文件保存上传的视频
        try:
            logger.info("创建临时文件保存视频")
            temp_dir = tempfile.gettempdir()
            logger.info(f"系统临时目录: {temp_dir}")
            logger.info(f"临时目录是否可写: {os.access(temp_dir, os.W_OK)}")
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            temp_file_path = temp_file.name
            logger.info(f"创建临时文件: {temp_file_path}")
            temp_file.close()
            
            # 保存上传的文件
            with open(temp_file_path, "wb") as f:
                logger.info("开始复制上传的文件内容到临时文件")
                shutil.copyfileobj(file.file, f)
            
            # 检查保存的文件
            if os.path.exists(temp_file_path):
                file_size = os.path.getsize(temp_file_path)
                logger.info(f"文件已保存，大小: {file_size} 字节")
                if file_size == 0:
                    raise ValueError("保存的文件大小为0")
            else:
                raise FileNotFoundError(f"临时文件未创建成功: {temp_file_path}")
                
        except Exception as temp_file_error:
            logger.error(f"创建或写入临时文件时出错: {str(temp_file_error)}")
            import traceback
            logger.error(f"临时文件错误详情: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"创建或写入临时文件时出错: {str(temp_file_error)}",
                    "details": traceback.format_exc()
                }
            )
        
        # 测试视频文件有效性
        try:
            import cv2
            logger.info(f"测试视频文件有效性: {temp_file_path}")
            cap = cv2.VideoCapture(temp_file_path)
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {temp_file_path}")
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"视频信息: 帧数={frame_count}, FPS={fps}, 分辨率={width}x{height}")
            cap.release()
        except Exception as video_error:
            logger.error(f"视频文件无效: {str(video_error)}")
            import traceback
            logger.error(f"视频测试错误详情: {traceback.format_exc()}")
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)  # 删除临时文件
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"上传的视频文件无效: {str(video_error)}",
                    "details": traceback.format_exc()
                }
            )
        
        # 生成任务ID
        task_id = file.filename.split('.')[0] + "_" + datetime.now().strftime("%Y%m%d%H%M%S")
        logger.info(f"生成任务ID: {task_id}")
        
        # 使用后台任务处理视频
        try:
            logger.info(f"添加后台任务处理视频: {task_id}")
            background_tasks.add_task(
                night_guardian_service.process_video,
                video_path=temp_file_path,
                model_type=model_type,
                threshold=threshold,
                clip_len=clip_len,
                save_frames=save_frames,
                task_id=task_id
            )
            logger.info(f"后台任务添加成功: {task_id}")
        except Exception as task_error:
            logger.error(f"添加后台任务出错: {str(task_error)}")
            import traceback
            logger.error(f"任务添加错误详情: {traceback.format_exc()}")
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)  # 删除临时文件
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"无法启动视频处理任务: {str(task_error)}",
                    "details": traceback.format_exc()
                }
            )
        
        logger.info(f"成功处理请求，返回响应: {task_id}")
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "视频处理任务已启动，请使用任务ID查询进度"
        }
    
    except Exception as e:
        import traceback
        error_stack = traceback.format_exc()
        logger.error(f"处理视频请求时出错: {str(e)}")
        logger.error(f"错误堆栈: {error_stack}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"处理视频请求时出错: {str(e)}",
                "error_details": error_stack,
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str = Path(..., description="任务ID")):
    """
    获取视频处理任务的状态
    
    - **task_id**: 处理任务的ID
    """
    try:
        status = night_guardian_service.get_task_status(task_id)
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        return {
            "task_id": task_id,
            **status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务状态时出错: {str(e)}")

@router.get("/video/{task_id}")
async def get_processed_video(task_id: str = Path(..., description="任务ID")):
    """
    获取处理后的视频文件
    
    - **task_id**: 处理任务的ID
    """
    try:
        status = night_guardian_service.get_task_status(task_id)
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        if status.get("status") != "completed":
            return JSONResponse(
                status_code=400,
                content={"detail": f"任务 {task_id} 尚未完成，当前状态: {status.get('status')}"}
            )
        
        output_path = status.get("output_path")
        if not output_path or not os.path.exists(output_path):
            raise HTTPException(status_code=404, detail=f"处理后的视频文件不存在")
        
        # 检查文件大小
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            raise HTTPException(status_code=500, detail=f"处理后的视频文件大小为0")
            
        logger.info(f"返回处理后的视频文件: {output_path}, 大小: {file_size} 字节")
        
        # 创建改进的文件响应
        headers = {
            "Content-Disposition": f'inline; filename="processed_{task_id}.mp4"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*"
        }
        
        return FileResponse(
            path=output_path,
            media_type="video/mp4",  # 标准MP4 MIME类型
            filename=f"processed_{task_id}.mp4",
            headers=headers
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取处理后视频时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取处理后视频时出错: {str(e)}")

@router.get("/frame/{task_id}/{frame_id}")
async def get_frame(
    task_id: str = Path(..., description="任务ID"),
    frame_id: int = Path(..., description="帧ID")
):
    """
    获取特定的视频帧
    
    - **task_id**: 处理任务的ID
    - **frame_id**: 帧ID
    """
    try:
        status = night_guardian_service.get_task_status(task_id)
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        results = status.get("results", [])
        frame_path = None
        
        for result in results:
            if result.get("frame") == frame_id and "frame_path" in result:
                frame_path = result["frame_path"]
                break
        
        if not frame_path or not os.path.exists(frame_path):
            raise HTTPException(status_code=404, detail=f"帧 {frame_id} 不存在或未保存")
        
        return FileResponse(
            path=frame_path,
            media_type="image/jpeg",
            filename=f"frame_{frame_id}.jpg"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取帧时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取帧时出错: {str(e)}")

@router.get("/results/{task_id}")
async def get_results(task_id: str = Path(..., description="任务ID")):
    """
    获取视频处理结果
    
    - **task_id**: 处理任务的ID
    """
    try:
        status = night_guardian_service.get_task_status(task_id)
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        if status.get("status") != "completed":
            return {
                "task_id": task_id,
                "status": status.get("status"),
                "progress": status.get("progress", 0),
                "results": []
            }
        
        return {
            "task_id": task_id,
            "status": "completed",
            "results": status.get("results", [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取结果时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取结果时出错: {str(e)}")

# 测试端点
@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "night_guardian", "timestamp": datetime.now().isoformat()}

# 简单GET测试端点 - 用于调试
@router.get("/simple-test")
async def simple_test():
    """最简单的GET测试端点，用于调试连接问题"""
    logger.info("[测试路由] 收到简单测试请求")
    logger.info(f"[测试路由] 请求时间: {datetime.now().isoformat()}")
    
    try:
        # 尝试访问系统信息以确认环境正常
        import os
        import sys
        python_version = sys.version
        cwd = os.getcwd()
        logger.info(f"[测试路由] Python版本: {python_version}")
        logger.info(f"[测试路由] 当前工作目录: {cwd}")
        
        # 检查相关模块是否可用
        import numpy
        import imutils
        logger.info(f"[测试路由] Numpy版本: {numpy.__version__}")
        logger.info(f"[测试路由] Imutils版本: {imutils.__version__}")
        
        # 简单返回成功响应
        return {
            "status": "success",
            "message": "简单测试成功",
            "environment": {
                "python_version": python_version,
                "cwd": cwd,
                "numpy_version": numpy.__version__,
                "imutils_version": imutils.__version__
            },
            "test_id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback
        error_stack = traceback.format_exc()
        logger.error(f"[简单测试路由] 错误: {str(e)}")
        logger.error(f"[简单测试路由] 错误堆栈: {error_stack}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"简单测试错误: {str(e)}",
                "error_details": error_stack,
                "timestamp": datetime.now().isoformat()
            }
        )

# 测试文件上传端点 - 用于调试
@router.post("/test-video")
async def test_video_upload(file: UploadFile = File(...)):
    """测试文件上传功能，只返回成功响应，不处理文件"""
    logger.info(f"[测试路由] 收到文件上传测试请求: {file.filename}")
    logger.info(f"[测试路由] 请求时间: {datetime.now().isoformat()}")
    logger.info(f"[测试路由] 文件内容类型: {file.content_type}")
    
    # 缓慢执行，打印详细调试日志
    try:
        # 检查文件对象
        logger.info(f"[测试路由] 文件对象: {type(file)}")
        logger.info(f"[测试路由] 文件属性: 名称={file.filename}, 类型={file.content_type}")
        
        # 读取文件大小
        try:
            # 读取少量字节仅用于测试
            content = await file.read(1024)  # 只读取前1KB数据
            file_size = len(content)
            logger.info(f"[测试路由] 成功读取文件第一部分: {file_size} 字节")
            
            # 重置file指针位置，避免影响后续读取
            await file.seek(0)
            logger.info("[测试路由] 文件指针重置成功")
        except Exception as read_error:
            logger.error(f"[测试路由] 读取文件内容失败: {str(read_error)}")
            import traceback
            logger.error(f"[测试路由] 读取文件错误详情: {traceback.format_exc()}")
            file_size = 0
            content = b""
        
        # 测试写入临时文件
        try:
            import tempfile
            import os
            temp_dir = tempfile.gettempdir()
            logger.info(f"[测试路由] 系统临时目录: {temp_dir}")
            logger.info(f"[测试路由] 当前工作目录: {os.getcwd()}")
            logger.info(f"[测试路由] 检查临时目录是否可写: {os.access(temp_dir, os.W_OK)}")
        except Exception as temp_error:
            logger.error(f"[测试路由] 检查临时目录失败: {str(temp_error)}")
        
        # 返回成功响应
        return {
            "status": "success",
            "message": "测试文件上传成功",
            "file_name": file.filename,
            "content_type": file.content_type,
            "size_preview": file_size,
            "test_id": f"upload_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback
        error_stack = traceback.format_exc()
        logger.error(f"[测试文件上传] 错误: {str(e)}")
        logger.error(f"[测试文件上传] 错误堆栈: {error_stack}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"测试文件上传错误: {str(e)}",
                "error_details": error_stack,
                "timestamp": datetime.now().isoformat()
            }
        )
