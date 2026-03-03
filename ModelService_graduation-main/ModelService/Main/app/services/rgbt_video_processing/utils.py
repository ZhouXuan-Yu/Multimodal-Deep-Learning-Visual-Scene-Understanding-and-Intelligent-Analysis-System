"""
RGBT视频处理工具函数

提供视频处理相关的工具函数，包括格式验证、路径处理等
"""

import os
import cv2
import logging
import uuid
from typing import Tuple, Dict, Any, List, Optional
from datetime import datetime

# 设置日志记录器
logger = logging.getLogger(__name__)

# 支持的视频格式
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mkv', '.mov']

def is_valid_video_format(filename: str) -> bool:
    """
    验证文件是否为支持的视频格式
    
    参数:
        filename: 文件名
        
    返回:
        是否为有效的视频格式
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in SUPPORTED_VIDEO_FORMATS

def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    获取视频文件的基本信息
    
    参数:
        video_path: 视频文件路径
        
    返回:
        视频信息字典，包含宽度、高度、FPS、总帧数等
    """
    try:
        # 打开视频文件
        video = cv2.VideoCapture(video_path)
        
        if not video.isOpened():
            logger.error(f"无法打开视频文件: {video_path}")
            return {
                "success": False,
                "error": "无法打开视频文件"
            }
        
        # 获取视频信息
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        # 释放视频对象
        video.release()
        
        return {
            "success": True,
            "width": width,
            "height": height,
            "fps": fps,
            "frame_count": frame_count,
            "duration": duration,
            "format": os.path.splitext(video_path)[1].lower()
        }
    except Exception as e:
        logger.error(f"获取视频信息失败: {str(e)}")
        return {
            "success": False,
            "error": f"获取视频信息失败: {str(e)}"
        }

def generate_output_path(input_path: str, output_dir: str, suffix: str = "_processed") -> str:
    """
    生成处理后的视频输出路径
    
    参数:
        input_path: 输入视频路径
        output_dir: 输出目录
        suffix: 添加到文件名的后缀
        
    返回:
        输出视频路径
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取文件名和扩展名
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    
    # 生成带唯一ID的新文件名
    unique_id = str(uuid.uuid4())[:8]
    new_filename = f"{name}{suffix}_{unique_id}{ext}"
    
    # 返回完整路径
    return os.path.join(output_dir, new_filename)

def create_task_record(task_id: str, rgb_video_path: str, thermal_video_path: Optional[str] = None) -> Dict[str, Any]:
    """
    创建视频处理任务记录
    
    参数:
        task_id: 任务ID
        rgb_video_path: RGB视频路径
        thermal_video_path: 热成像视频路径（可选）
        
    返回:
        任务记录字典
    """
    return {
        "task_id": task_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "rgb_video": {
            "path": rgb_video_path,
            "info": get_video_info(rgb_video_path)
        },
        "thermal_video": {
            "path": thermal_video_path,
            "info": get_video_info(thermal_video_path) if thermal_video_path else None
        },
        "progress": 0,
        "output": {
            "rgb_processed": "",
            "thermal_processed": "",
            "combined": ""
        },
        "error": None
    }
