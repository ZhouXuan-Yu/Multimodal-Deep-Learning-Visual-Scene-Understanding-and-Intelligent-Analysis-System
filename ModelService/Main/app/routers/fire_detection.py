from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Query
from fastapi.responses import JSONResponse, FileResponse, Response
from starlette.background import BackgroundTask
import numpy as np
import cv2
import logging
import os
import time
import uuid
import json
import shutil
import datetime
from typing import Optional, List, Dict
from fastapi import status
import re
from fastapi import Depends
from sqlalchemy.orm import Session

# 导入邮件通知模块
from ..utils.fire_email_notifier import fire_email_notifier

# 导入服务模块
from ..services.fire_detection.fire_detector import create_fire_detector

# 获取日志记录器
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/api/fire-detection",
    tags=["fire-detection"],
    responses={404: {"description": "Not found"}},
)

# 设置输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "output", "fire_detection")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 确保模型目录存在
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "fire_detection")
os.makedirs(MODELS_DIR, exist_ok=True)

# 初始化火灾检测器
fire_detector = None

# 模块级全局变量 - 跟踪初始化状态
FIRE_DETECTOR_INITIALIZATION_ATTEMPTS = 0
FIRE_DETECTOR_INITIALIZATION_SUCCESS = False

# 初始化函数，加载模型 - 改为延迟初始化而非启动事件
def initialize_fire_detection():
    """延迟初始化火灾检测服务的函数，包含详细调试日志"""
    global fire_detector, FIRE_DETECTOR_INITIALIZATION_ATTEMPTS, FIRE_DETECTOR_INITIALIZATION_SUCCESS
    
    # 记录初始化尝试次数
    FIRE_DETECTOR_INITIALIZATION_ATTEMPTS += 1
    
    # 调试信息
    import os
    import sys
    import threading
    import traceback
    import inspect
    
    try:
        # 获取线程和进程信息
        current_thread = threading.current_thread()
        debug_info = {
            "thread_name": current_thread.name,
            "thread_id": current_thread.ident,
            "process_id": os.getpid(),
            "module": __name__,
            "fire_detector_initialized": fire_detector is not None,
            "initialization_attempt": FIRE_DETECTOR_INITIALIZATION_ATTEMPTS,
            "initialization_success": FIRE_DETECTOR_INITIALIZATION_SUCCESS,
            "call_stack": [f.function for f in inspect.stack()[:5]]  # 只记录前5个函数调用
        }
        
        # 记录详细调试信息
        logger.info(f"\n=================== 火灾检测初始化尝试 #{FIRE_DETECTOR_INITIALIZATION_ATTEMPTS} ====================")
        logger.info(f"[调试] 进程ID: {debug_info['process_id']}, 线程: {debug_info['thread_name']}:{debug_info['thread_id']}")
        logger.info(f"[调试] 调用栈: {' -> '.join(debug_info['call_stack'])}")
        logger.info(f"[调试] fire_detector已初始化: {debug_info['fire_detector_initialized']}")
        
        # 检查环境变量
        env_vars = {k: v for k, v in os.environ.items() if k.startswith("PREVENT_") or k.startswith("RUNNING_")}
        logger.info(f"[环境变量] {env_vars}")
        
        # 只有当没有已初始化的检测器时才初始化
        if fire_detector is None:
            logger.info("开始初始化火灾检测服务...")
            fire_detector = create_fire_detector()  # 调用工厂函数创建检测器
            logger.info("✓ 火灾检测服务初始化完成")
            FIRE_DETECTOR_INITIALIZATION_SUCCESS = True
        else:
            logger.info("火灾检测器已存在，跳过初始化")
        
        logger.info("火灾检测服务初始化状态正常\n")
        
    except Exception as e:
        # 记录异常信息
        logger.error(f"[异常] 初始化火灾检测器时出错: {str(e)}")
        logger.error(f"[异常] 异常类型: {type(e).__name__}")
        logger.error(f"[异常] 堆栈跟踪:\n{traceback.format_exc()}")
        # 即使发生异常也不抛出 - 这样不会影响服务运行
    
    return fire_detector

# 读取上传的图像
async def read_image_file(file: UploadFile) -> np.ndarray:
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

# 保存处理后的图像
def save_processed_image(image: np.ndarray) -> str:
    filename = f"fire_detection_{uuid.uuid4()}.jpg"
    output_path = os.path.join(OUTPUT_DIR, filename)
    cv2.imwrite(output_path, image)
    return output_path

# 火灾检测API
@router.post("/detect")
async def detect_fire(
    file: UploadFile = File(...),
    mode: str = Form("both"),  # classification, segmentation, both
    threshold: float = Form(0.5)
):
    """
    检测图像中的火灾
    
    参数:
    - file: 上传的图像文件
    - mode: 处理模式 (classification, segmentation, both)
    - threshold: 检测阈值
    
    返回:
    - 火灾检测结果
    """
    global fire_detector
    
    # 使用延迟初始化而不是依赖于启动事件
    if fire_detector is None:
        # 如果服务未初始化，则现在初始化它
        try:
            fire_detector = initialize_fire_detection()
        except Exception as e:
            logger.error(f"初始化火灾检测服务失败: {str(e)}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"火灾检测服务初始化失败: {str(e)}")
    
    # 再次检查以确保初始化成功
    if fire_detector is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="火灾检测服务未能初始化")
        
    try:
        # 检查文件类型
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图像文件")
            
        # 读取图像
        image = await read_image_file(file)
        
        if image is None or image.size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法读取图像")
            
        # 执行火灾检测
        result = fire_detector.process_image(image, mode=mode)
        
        # 保存处理后的图像
        highlighted_path = save_processed_image(result['highlighted_image'])
        
        # 准备返回结果
        response = {
            "fire_detected": result['fire_detected'],
            "confidence": float(result['confidence']),
            "processing_time": result['processing_time'],
            "result_image_path": highlighted_path
        }
        
        # 如果有掩码，也保存
        if 'mask' in result:
            mask_path = highlighted_path.replace(".jpg", "_mask.jpg")
            cv2.imwrite(mask_path, result['mask'])
            response["mask_image_path"] = mask_path
            
        return JSONResponse(content=response)
    
    except Exception as e:
        logger.error(f"处理火灾检测请求时发生错误: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"处理请求时发生错误: {str(e)}")

# 获取处理后的图像
@router.get("/result/{image_name}")
async def get_result_image(image_name: str):
    """获取处理后的图像"""
    image_path = os.path.join(OUTPUT_DIR, image_name)
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图像不存在")
        
    return FileResponse(image_path)

# 处理视频文件
@router.post("/upload-video",
              summary="上传视频用于火灾检测",
              description="接收视频文件并开始处理",
              status_code=status.HTTP_200_OK)
async def upload_video_for_fire_detection(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    alarm_enabled: bool = Form(False, description="是否启用火灾报警"),
    alarm_email: str = Form("", description="报警接收邮箱"),
    alarm_interval: int = Form(60, description="报警间隔(秒)"),
    alarm_threshold: float = Form(0.6, description="火灾判定阈值"),
):
    """
    上传视频文件进行火灾检测
    
    此API接收视频文件，保存到服务器，然后在后台线程中进行处理，返回处理ID用于后续查询状态
    """
    logger.info(f"开始处理视频上传: 文件名={file.filename}, 内容类型={file.content_type}")
    
    try:
        # 确保火灾检测系统已初始化
        if not initialize_fire_detection():
            logger.error("火灾检测系统初始化失败，无法处理视频")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="火灾检测系统未初始化，请稍后再试"
            )
        
        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 生成处理ID
        process_id = str(uuid.uuid4())
        logger.info(f"生成处理ID: {process_id}")
        
        # 获取原始文件扩展名，如果没有则默认为.mp4
        if file.filename:
            original_extension = os.path.splitext(file.filename)[1].lower()
            if not original_extension:
                original_extension = ".mp4"
        else:
            original_extension = ".mp4"
        
        # 生成带有原始扩展名的文件名
        safe_filename = f"fire_detection_{process_id}{original_extension}"
        file_path = os.path.join(OUTPUT_DIR, safe_filename)
        logger.info(f"创建文件路径: {file_path}")
        
        # 创建进度文件
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        with open(progress_path, "w") as progress_file:
            json.dump({
                "status": "uploading",
                "progress": 0,
                "message": "正在上传视频",
                "process_id": process_id,
                "file_name": safe_filename
            }, progress_file)
        logger.info(f"创建进度文件: {progress_path}")
        
        # 使用简单的一次性读取保存文件
        try:
            # 首先，尝试直接从请求中读取所有内容
            content = await file.read()
            content_size = len(content)
            
            if content_size == 0:
                raise ValueError("上传的文件为空")
                
            # 写入文件
            with open(file_path, "wb") as buffer:
                buffer.write(content)
                
            logger.info(f"文件上传完成: 路径={file_path}, 大小={content_size/1024/1024:.2f}MB")
        except Exception as e:
            logger.error(f"写入文件时出错: {str(e)}")
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(progress_path):
                os.remove(progress_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"写入文件时出错: {str(e)}"
            )
        
        # 更新进度文件
        with open(progress_path, "w") as progress_file:
            json.dump({
                "status": "uploaded",
                "progress": 10,
                "message": "视频已上传，准备处理",
                "process_id": process_id,
                "file_name": safe_filename,
                "file_path": file_path
            }, progress_file)
        
        # 启动后台任务处理视频
        logger.info(f"启动后台任务处理视频: {file_path}")
        background_tasks.add_task(
            process_video_task,
            file_path=file_path,
            process_id=process_id,
            alarm_config={
                "enabled": alarm_enabled,
                "email": alarm_email,
                "interval": alarm_interval,
                "threshold": alarm_threshold
            }
        )
        
        return {
            "status": "success",
            "message": "视频上传成功，开始后台处理",
            "process_id": process_id,
            "file_name": safe_filename
        }
    
    except HTTPException as http_exc:
        logger.error(f"处理视频上传时HTTP异常: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"处理视频上传时发生异常: {str(e)}")
        # 记录完整的堆栈跟踪
        import traceback
        logger.error(f"堆栈跟踪: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理视频时出错: {str(e)}"
        )

@router.get("/video-status/{process_id}")
async def get_video_processing_status(process_id: str):
    """获取视频处理状态"""
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到处理ID为 {process_id} 的视频")
    
    try:
        with open(progress_path, "r") as f:
            status = json.load(f)
        
        # 确保存在key_frames字段，前端依赖此字段
        if status.get("status") == "completed" and "key_frames" not in status:
            # 收集关键帧信息
            frames_dir = status.get("frames_dir")
            if frames_dir and os.path.exists(frames_dir):
                key_frames = []
                for file in os.listdir(frames_dir):
                    if file.endswith(".jpg") or file.endswith(".png"):
                        try:
                            frame_num = int(file.split("_")[-1].split(".")[0])
                            key_frames.append({
                                "name": file,
                                "frame": frame_num,
                                "confidence": 0.8,  # 默认置信度
                                "url": f"/api/fire-detection/frame/{process_id}/{file}"
                            })
                        except Exception:
                            pass
                
                key_frames.sort(key=lambda x: x["frame"])
                status["key_frames"] = key_frames
                
                # 保存更新后的状态
                with open(progress_path, "w") as f:
                    json.dump(status, f)
        
        # 添加一些摘要信息，用于前端展示
        if "key_frames" in status and status["key_frames"]:
            status["has_fire"] = True
            status["fire_frame_count"] = len(status["key_frames"])
        else:
            status["has_fire"] = False
            status["fire_frame_count"] = 0
        
        return status
        
    except Exception as e:
        logger.error(f"获取视频处理状态时出错: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取处理状态出错: {str(e)}")

# 后台处理视频任务
async def process_video_task(file_path: str, process_id: str, alarm_config: dict, frame_skip: int = 5, save_frames: bool = True):
    """
    Background task to process video
    
    Args:
        file_path: Video file path
        process_id: Process ID
        alarm_config: Alarm configuration, including enabled, email, interval, threshold
        frame_skip: Number of frames to skip (process 1 frame every N frames)
        save_frames: Whether to save key frames
    """
    logger.info(f"Starting background video processing: {file_path}, Process ID: {process_id}, Frame skip: {frame_skip}")
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    # Determine output path based on filename
    filename = os.path.basename(file_path)
    output_path = os.path.join(OUTPUT_DIR, f"processed_{filename}")
    
    # Create frame save directory
    frames_dir = os.path.join(OUTPUT_DIR, f"frames_{process_id}")
    os.makedirs(frames_dir, exist_ok=True)
    logger.info(f"Created frames directory: {frames_dir}")
    
    # Update progress to processing
    try:
        with open(progress_path, "r") as f:
            progress_data = json.load(f)
        
        progress_data.update({
            "status": "processing",
            "progress": 10,
            "message": "Starting video processing",
            "output_path": output_path,
            "frames_dir": frames_dir,
            "frame_skip": frame_skip,
            "start_time": time.time()
        })
        
        with open(progress_path, "w") as f:
            json.dump(progress_data, f)
        
        # Call fire detector to process video
        logger.info(f"Calling fire detector to process video: {file_path}")
        try:
            result = fire_detector.process_video(
                video_path=file_path,
                output_path=output_path,
                mode="both",  # Default use both classification and segmentation
                threshold=0.5,
                save_frames=save_frames,
                frames_dir=frames_dir,
                enable_alarm=alarm_config.get("enabled", False),
                receiver_email=alarm_config.get("email", ""),
                alarm_interval=alarm_config.get("interval", 60),
                alarm_threshold=alarm_config.get("threshold", 0.6),
                frame_skip=frame_skip  # Pass frame_skip parameter
            )
            
            # Process result
            if result.get("success", False):
                logger.info(f"Video processing successful: {process_id}")
                
                # Find key frames with fire
                key_frames = []
                if save_frames and os.path.exists(frames_dir):
                    # Get all frame files
                    frame_files = os.listdir(frames_dir)
                    frame_files = [f for f in frame_files if f.endswith('.jpg') or f.endswith('.png')]
                    
                    # Log available frames for debugging
                    logger.info(f"Found {len(frame_files)} frame files in directory: {frames_dir}")
                    if len(frame_files) > 0:
                        logger.info(f"Example frame files: {frame_files[:5]}")
                    else:
                        logger.warning(f"No frame files found in directory: {frames_dir}")
                    
                    # Sort by frame number
                    frame_files.sort()
                    
                    # Create frame info
                    for i, frame_file in enumerate(frame_files):
                        # Extract frame number from filename
                        frame_number = int(re.search(r'(\d+)', frame_file).group(1)) if re.search(r'(\d+)', frame_file) else i
                        
                        # Verify frame file exists
                        frame_path = os.path.join(frames_dir, frame_file)
                        if not os.path.exists(frame_path):
                            logger.warning(f"Frame file does not exist: {frame_path}")
                            continue
                            
                        # Log frame file details for debugging
                        logger.info(f"Found frame: {frame_file}, path: {frame_path}, exists: {os.path.exists(frame_path)}")
                        
                        # Create frame info
                        frame_info = {
                            "name": frame_file,
                            "path": frame_path,
                            "frame": frame_number,
                            "confidence": float(result.get("confidences", {}).get(str(frame_number), 0.6))
                        }
                        
                        key_frames.append(frame_info)
                    
                    # Sort frames by confidence score (descending)
                    key_frames.sort(key=lambda x: x["confidence"], reverse=True)
                
                # 检查是否需要发送火灾报警邮件
                fire_detected = result.get("fire_detected", False)
                fire_confidence = result.get("confidence", 0)
                fire_percentage = result.get("fire_percentage", 0)
                
                # 处理邮件报警逻辑
                email_sent = False
                email_error = None
                
                if fire_detected and alarm_config.get("enabled", False):
                    # 检查是否超过报警阈值
                    alarm_threshold = alarm_config.get("threshold", 0.6)
                    if fire_confidence >= alarm_threshold:
                        logger.info(f"Fire detected with confidence {fire_confidence} >= threshold {alarm_threshold}, sending alarm email")
                        
                        try:
                            # 准备邮件所需信息
                            detection_details = {
                                "process_id": process_id,
                                "detection_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "video_path": file_path,
                                "fire_score": fire_confidence,
                                "fire_percentage": fire_percentage,
                                "alarm_email": alarm_config.get("email", ""),
                                "message": f"火灾检测分数: {fire_confidence:.2f}, 火灾覆盖面积百分比: {fire_percentage:.2f}%"
                            }
                            
                            # 获取最高置信度的火灾帧作为邮件附件
                            frame_path = None
                            if key_frames and len(key_frames) > 0:
                                frame_path = key_frames[0]["path"]  # 使用置信度最高的帧
                            
                            # 发送报警邮件
                            email_sent = fire_email_notifier.send_fire_alarm(
                                detection_details=detection_details,
                                frame_path=frame_path
                            )
                            
                            if email_sent:
                                logger.info(f"成功发送火灾报警邮件, 接收者: {alarm_config.get('email', '默认接收者')}")
                            else:
                                logger.warning("火灾报警邮件发送失败")
                                
                        except Exception as e:
                            email_error = str(e)
                            logger.error(f"发送火灾报警邮件时出错: {email_error}")
                    else:
                        logger.info(f"检测到火灾但置信度 {fire_confidence} < 阈值 {alarm_threshold}, 不发送报警")
                
                # Update progress file with completion info
                with open(progress_path, "w") as f:
                    completion_data = {
                        "status": "completed",
                        "progress": 100,
                        "message": "Video processing completed",
                        "process_id": process_id,
                        "output_path": output_path,
                        "frames_dir": frames_dir,
                        "key_frames": key_frames[:20],  # Limit to top 20 frames
                        "fire_detected": fire_detected,
                        "fire_percentage": fire_percentage,
                        "confidence": fire_confidence,
                        "processing_time": result.get("processing_time", 0),
                        "frames_per_second": result.get("fps", 0),
                        "frame_skip": frame_skip,
                        "end_time": time.time(),
                        "alarm_enabled": alarm_config.get("enabled", False),
                        "alarm_threshold": alarm_config.get("threshold", 0.6),
                        "alarm_email": alarm_config.get("email", ""),
                        "email_sent": email_sent,
                        "email_error": email_error
                    }
                    json.dump(completion_data, f)
            else:
                logger.error(f"Video processing failed: {process_id}, reason: {result.get('error', 'Unknown error')}")
                
                # Update progress file
                with open(progress_path, "w") as f:
                    result.update({
                        "status": "failed",
                        "progress": 0,
                        "message": f"Processing failed: {result.get('error', 'Unknown error')}",
                        "process_id": process_id,
                        "end_time": time.time()
                    })
                    json.dump(result, f)
        except Exception as e:
            logger.exception(f"Error processing video: {str(e)}")
            
            # Update progress file
            with open(progress_path, "w") as f:
                json.dump({
                    "status": "failed",
                    "progress": 0,
                    "message": f"Processing error: {str(e)}",
                    "process_id": process_id,
                    "file_path": file_path,
                    "error": str(e),
                    "end_time": time.time()
                }, f)
    except Exception as e:
        logger.exception(f"Video processing task execution failed: {str(e)}")
        
        # If progress file exists, update error info
        if os.path.exists(progress_path):
            try:
                with open(progress_path, "w") as f:
                    json.dump({
                        "status": "failed",
                        "progress": 0,
                        "message": f"Task execution failed: {str(e)}",
                        "process_id": process_id,
                        "error": str(e),
                        "end_time": time.time()
                    }, f)
            except Exception as write_err:
                logger.error(f"Error updating progress file: {str(write_err)}")

@router.get("/video-result/{process_id}")
async def get_video_result(process_id: str):
    """获取视频处理的结果信息"""
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=404, detail=f"没有找到ID为{process_id}的视频处理任务")
    
    try:
        with open(progress_path, "r") as f:
            status = json.load(f)
        
        # 根据状态返回不同的响应
        if status.get("status") == "processing":
            return {
                "status": "processing",
                "message": "视频仍在处理中",
                "progress": status.get("progress", 50)  # 返回当前进度
            }
        elif status.get("status") == "failed":
            return {
                "status": "failed",
                "message": "处理失败",
                "error": status.get("error", "未知错误")
            }
        elif status.get("status") == "completed":
            # 直接返回从进度文件中读取的信息
            return {
                "status": "completed",
                "message": "处理完成",
                "key_frames": status.get("key_frames", []),
                "processing_time": status.get("processing_time", 0),
                "frames_per_second": status.get("frames_per_second", 0),
                "total_frames": status.get("total_frames", 0),
                "frame_skip": status.get("frame_skip", 1)
            }
        else:
            return {
                "status": status.get("status", "unknown"),
                "message": f"状态: {status.get('status', '未知')}"
            }
    except Exception as e:
        logger.error(f"获取视频处理结果时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取处理结果出错: {str(e)}")

@router.get("/detection-results/{process_id}")
async def get_detection_results(process_id: str):
    """获取检测结果的详细信息"""
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=404, detail=f"没有找到ID为{process_id}的视频处理任务")
    
    try:
        with open(progress_path, "r") as f:
            status = json.load(f)
        
        # 获取帧数据
        frames = status.get("key_frames", [])
        
        # 添加完整URL
        for frame in frames:
            # 构建完整的图像URL
            frame_name = frame.get("name")
            if frame_name:
                frame["image_url"] = f"/api/fire-detection/frame/{process_id}/{frame_name}"
                frame["thumbnail_url"] = f"/api/fire-detection/frame/{process_id}/{frame_name}" 
        
        # 返回结果
        return {
            "video_id": process_id,
            "process_id": process_id,
            "status": status.get("status", "unknown"),
            "frames": frames,
            "processing_time": status.get("processing_time", 0),
            "total_frames": status.get("total_frames", 0),
            "processed_frames": status.get("frames_processed", 0),
            "frame_skip": status.get("frame_skip", 1)
        }
    except Exception as e:
        logger.error(f"获取检测结果出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取检测结果出错: {str(e)}")

@router.get("/original-video/{process_id}")
async def get_original_video(process_id: str):
    """Get original video file"""
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing record not found")
    
    # Read progress file
    with open(progress_path, "r") as f:
        progress = json.load(f)
    
    # Get original file path
    file_path = progress.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original video file not found")
    
    # Return original video
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=os.path.basename(file_path)
    )

@router.get("/video-frames/{process_id}")
async def get_video_frames(process_id: str, limit: int = Query(10, ge=1, le=100)):
    """Get key frames from video processing"""
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing record not found")
    
    # Read progress file
    with open(progress_path, "r") as f:
        progress = json.load(f)
    
    frames_dir = progress.get("frames_dir")
    if not frames_dir or not os.path.exists(frames_dir):
        return {"frames": [], "message": "No frames available"}
    
    # Get frame file list
    frame_files = []
    for file in os.listdir(frames_dir):
        if file.endswith(".jpg") or file.endswith(".png"):
            frame_path = os.path.join(frames_dir, file)
            frame_files.append({
                "name": file,
                "path": frame_path,
                "url": f"/api/fire-detection/frame/{process_id}/{file}"
            })
    
    # Sort by name and limit count
    frame_files.sort(key=lambda x: x["name"])
    frame_files = frame_files[:limit]
    
    return {"frames": frame_files, "total": len(os.listdir(frames_dir))}

@router.get("/frame/{process_id}/{frame_name}")
async def get_video_frame(process_id: str, frame_name: str):
    """Get specific key frame from video processing"""
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing record not found")
    
    # Read progress file
    with open(progress_path, "r") as f:
        progress = json.load(f)
    
    frames_dir = progress.get("frames_dir")
    if not frames_dir:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No frames directory")
    
    frame_path = os.path.join(frames_dir, frame_name)
    if not os.path.exists(frame_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified frame not found")
    
    return FileResponse(frame_path)

# 添加视频转换和预览端点
@router.post("/convert-video-for-preview")
async def convert_video_for_preview(file: UploadFile = File(...)):
    """
    接收视频文件并转换为浏览器兼容格式，用于前端预览
    """
    try:
        # 创建临时目录
        preview_dir = os.path.join(OUTPUT_DIR, "previews")
        os.makedirs(preview_dir, exist_ok=True)
        
        # 生成唯一文件名
        preview_id = str(uuid.uuid4())
        temp_input = os.path.join(preview_dir, f"temp_input_{preview_id}.mp4")
        preview_output = os.path.join(preview_dir, f"preview_{preview_id}.mp4")
        
        # 保存上传的文件
        with open(temp_input, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        logger.info(f"收到预览转换请求，文件大小: {len(content)/1024/1024:.2f}MB")
        
        # 读取文件
        try:
            cap = cv2.VideoCapture(temp_input)
            if not cap.isOpened():
                raise ValueError("无法打开视频文件")
                
            # 获取视频参数
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 如果视频过长，只预览前30秒
            max_preview_frames = min(int(fps * 30), total_frames)
            
            # 创建视频写入器 - 使用H.264编码
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            out = cv2.VideoWriter(preview_output, fourcc, fps, (width, height))
            
            # 读取帧并写入
            frame_count = 0
            while frame_count < max_preview_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # 写入帧
                out.write(frame)
                frame_count += 1
                
            # 释放资源
            cap.release()
            out.release()
            
            # 清理临时文件
            if os.path.exists(temp_input):
                os.remove(temp_input)
                
            # 返回预览视频的URL
            return {
                "success": True, 
                "preview_id": preview_id,
                "message": "视频转换成功"
            }
            
        except Exception as e:
            logger.error(f"视频转换失败: {str(e)}")
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if os.path.exists(preview_output):
                os.remove(preview_output)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"视频转换失败: {str(e)}"
            )
            
    except Exception as e:
        logger.exception(f"视频预览处理出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理预览视频时出错: {str(e)}"
        )

# 获取预览视频
@router.get("/preview-video/{preview_id}")
async def get_preview_video(preview_id: str):
    """获取预览视频"""
    preview_path = os.path.join(OUTPUT_DIR, "previews", f"preview_{preview_id}.mp4")
    
    if not os.path.exists(preview_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预览视频不存在")
    
    return FileResponse(preview_path, media_type="video/mp4")

# 添加检查完成状态的端点
@router.get("/check-completion/{process_id}")
async def check_completion(process_id: str):
    """检查视频处理任务是否完成"""
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到处理ID为 {process_id} 的视频")
    
    try:
        with open(progress_path, "r") as f:
            status_data = json.load(f)
        
        # 返回处理状态
        return {
            "status": status_data.get("status", "unknown"),
            "progress": status_data.get("progress", 0),
            "message": status_data.get("message", "未知状态"),
            "process_id": process_id
        }
    except Exception as e:
        logger.error(f"检查完成状态时出错: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"检查完成状态出错: {str(e)}")

# 添加摄像头检测API
@router.post("/detect-camera")
async def detect_camera(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    threshold: float = Form(0.5)
):
    """
    处理实时摄像头检测请求
    
    参数:
    - file: 上传的摄像头帧图像
    - session_id: 摄像头会话ID
    - threshold: 检测阈值
    
    返回:
    - 火灾检测结果
    """
    global fire_detector
    
    # 使用延迟初始化
    if fire_detector is None:
        try:
            fire_detector = initialize_fire_detection()
        except Exception as e:
            logger.error(f"初始化火灾检测服务失败: {str(e)}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"火灾检测服务初始化失败: {str(e)}")
    
    # 再次检查以确保初始化成功
    if fire_detector is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="火灾检测服务未能初始化")
    
    try:
        # 检查文件类型
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图像文件")
        
        # 读取图像
        image = await read_image_file(file)
        
        if image is None or image.size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法读取图像")
        
        # 为该会话创建输出目录
        session_dir = os.path.join(OUTPUT_DIR, f"camera_{session_id}")
        os.makedirs(session_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = int(time.time() * 1000)
        original_filename = f"camera_original_{timestamp}.jpg"
        processed_filename = f"camera_processed_{timestamp}.jpg"
        
        # 保存原始图像
        original_path = os.path.join(session_dir, original_filename)
        cv2.imwrite(original_path, image)
        
        # 执行火灾检测
        start_time = time.time()
        result = fire_detector.process_image(image, mode="both")
        processing_time = time.time() - start_time
        
        # 保存处理后的图像
        processed_path = os.path.join(session_dir, processed_filename)
        cv2.imwrite(processed_path, result.get('highlighted_image', image))
        
        # 准备返回结果
        response = {
            "fire_detected": result.get('fire_detected', False),
            "confidence": float(result.get('confidence', 0.0)),
            "fire_area_percentage": float(result.get('fire_area_percentage', 0.0)),
            "smoke_detected": result.get('smoke_detected', False),
            "smoke_area_percentage": float(result.get('smoke_area_percentage', 0.0)),
            "method": result.get('method', 'unknown'),
            "processing_time": processing_time,
            "original_image": f"/api/fire-detection/camera-image/{session_id}/{original_filename}",
            "processed_image": f"/api/fire-detection/camera-image/{session_id}/{processed_filename}",
            "timestamp": timestamp
        }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        logger.error(f"处理摄像头检测请求时发生错误: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"处理请求时发生错误: {str(e)}")

# 获取摄像头图像
@router.get("/camera-image/{session_id}/{image_name}")
async def get_camera_image(session_id: str, image_name: str):
    """获取摄像头检测的图像"""
    # 安全检查，防止目录遍历
    if ".." in image_name or not (image_name.endswith(".jpg") or image_name.endswith(".png")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的图像名称")
    
    image_path = os.path.join(OUTPUT_DIR, f"camera_{session_id}", image_name)
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图像不存在")
        
    return FileResponse(image_path)

# 测试火灾邮件功能
@router.post("/test-fire-email")
async def test_fire_email(email: str = Form("", description="接收邮件的地址，留空则使用默认配置")):
    """发送测试邮件以验证火灾邮件功能是否正常工作"""
    try:
        # 发送测试邮件
        success = fire_email_notifier.send_test_email(receiver_email=email if email else None)
        
        if success:
            return JSONResponse(content={
                "status": "success", 
                "message": "测试邮件发送成功"
            })
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error", 
                    "message": "测试邮件发送失败"
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error", 
                "message": f"测试邮件发送时出错: {str(e)}"
            }
        )

# 手动触发火灾报警邮件
@router.post("/send-fire-alarm")
async def send_fire_alarm(
    email: str = Form("", description="接收邮件的地址，留空则使用默认配置"),
    fire_score: float = Form(0.85, description="火灾检测分数"),
    message: str = Form("用户手动触发的火灾报警", description="报警消息")
):
    """手动发送火灾报警邮件"""
    try:
        # 准备邮件详细信息
        detection_details = {
            "process_id": str(uuid.uuid4()),
            "detection_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "video_path": "手动触发",
            "fire_score": fire_score,
            "fire_percentage": fire_score * 15,  # 理论上计算的火灾面积百分比
            "alarm_email": email,
            "message": message
        }
        
        # 发送报警邮件
        email_sent = fire_email_notifier.send_fire_alarm(
            detection_details=detection_details
        )
        
        if email_sent:
            return JSONResponse(content={
                "status": "success", 
                "message": "火灾报警邮件发送成功"
            })
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error", 
                    "message": "火灾报警邮件发送失败"
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error", 
                "message": f"火灾报警邮件发送时出错: {str(e)}"
            }
        )

# 转码视频为浏览器兼容格式
def convert_video_for_web(input_path: str, process_id: str) -> str:
    """
    将视频转码为网页播放兼容的格式
    根据输入视频的格式选择适当的编码方式，确保生成的视频可以在浏览器中播放
    
    Args:
        input_path: 输入视频路径
        process_id: 处理ID，用于生成输出路径
        
    Returns:
        转码后的视频路径，如果失败则返回None
    """
    if not os.path.exists(input_path):
        logger.error(f"输入视频不存在: {input_path}")
        return None
    
    # 确保输出目录存在
    web_dir = os.path.join(OUTPUT_DIR, "web_videos")
    os.makedirs(web_dir, exist_ok=True)
    
    # 根据原视频扩展名确定输出格式
    _, ext = os.path.splitext(input_path)
    ext = ext.lower()
    
    # 生成MP4和WebM两种格式，增加兼容性
    output_mp4 = os.path.join(web_dir, f"web_{process_id}.mp4")
    output_webm = os.path.join(web_dir, f"web_{process_id}.webm")
    logger.info(f"准备转码视频: {input_path} -> {output_mp4} 和 {output_webm}")
    
    try:
        # 读取源视频
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            logger.error(f"无法打开视频: {input_path}")
            return None
        
        # 获取视频参数
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"源视频信息: {width}x{height}, {fps}fps, {total_frames}帧")
        
        # 确保宽高是偶数（H.264要求）
        if width % 2 != 0:
            width -= 1
        if height % 2 != 0:
            height -= 1
        
        # 根据原视频格式选择合适的编码器
        if ext in ['.avi', '.wmv']:
            # AVI格式优先使用MJPG编码器，兼容性更好
            fourcc_mp4 = cv2.VideoWriter_fourcc(*'MJPG')
            output_path = output_mp4.replace('.mp4', '.avi')
        else:
            # 默认使用H.264编码
            fourcc_mp4 = cv2.VideoWriter_fourcc(*'avc1')
            output_path = output_mp4
        
        # 创建视频写入器
        out = cv2.VideoWriter(output_path, fourcc_mp4, fps, (width, height))
        
        if not out.isOpened():
            logger.error(f"无法创建视频写入器: {output_path}")
            # 尝试使用备用编码器
            logger.info("尝试使用备用编码器(XVID)...")
            output_path = output_mp4.replace('.mp4', '.avi')
            out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'XVID'), fps, (width, height))
            if not out.isOpened():
                return None
        
        # 逐帧转换
        frame_count = 0
        max_frames = min(total_frames, 1800)  # 最多处理30分钟视频(30fps*60s*30min)
        
        logger.info(f"开始转码视频，处理至多{max_frames}帧")
        
        # 读取所有帧以便后续处理
        frames = []
        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 如果需要，调整帧大小
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height))
            
            frames.append(frame)
            frame_count += 1
            
            # 每100帧记录一次进度
            if frame_count % 100 == 0:
                logger.info(f"读取进度: {frame_count}/{total_frames}帧")
        
        # 将帧写入主要输出格式
        for i, frame in enumerate(frames):
            out.write(frame)
            if i % 100 == 0:
                logger.info(f"写入进度: {i}/{len(frames)}帧")
        
        # 释放第一个输出
        out.release()
        
        # 检查是否需要尝试第二种格式（WebM）
        try:
            # 某些平台可能不支持WebM编码
            fourcc_webm = cv2.VideoWriter_fourcc(*'VP90')
            out_webm = cv2.VideoWriter(output_webm, fourcc_webm, fps, (width, height))
            
            if out_webm.isOpened():
                # 写入WebM格式
                for i, frame in enumerate(frames):
                    out_webm.write(frame)
                out_webm.release()
                logger.info(f"WebM格式转码成功: {output_webm}")
        except Exception as webm_error:
            logger.warning(f"WebM格式转码失败: {str(webm_error)}")
        
        # 释放资源
        cap.release()
        
        # 检查输出文件
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"视频转码成功: {output_path}, 大小: {os.path.getsize(output_path)/1024/1024:.2f}MB")
            return output_path
        else:
            logger.error(f"转码失败，输出文件无效: {output_path}")
            return None
    
    except Exception as e:
        logger.exception(f"视频转码过程中发生错误: {str(e)}")
        return None

# 获取处理后的视频文件
@router.get("/result-video/{process_id}")
async def get_result_video(process_id: str, format: str = None):
    """获取处理后的视频文件"""
    # 直接调用直接访问路由
    return await get_direct_result_video(process_id, format)

# 获取原始视频文件
@router.get("/original-video/{process_id}")
async def get_original_video_api(process_id: str):
    """获取原始视频文件"""
    # 直接调用直接访问路由
    return await get_original_video(process_id)

@router.get("/fire_detection_direct/result-video/{process_id}")
async def get_direct_result_video(process_id: str, format: str = None):
    """获取处理后的视频，支持直接访问，并允许指定格式"""
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="处理记录不存在")
    
    # 读取进度文件
    with open(progress_path, "r") as f:
        progress = json.load(f)
    
    # 检查各种可能的视频格式和路径
    web_dir = os.path.join(OUTPUT_DIR, "web_videos")
    
    # 格式优先级顺序，首先是用户指定的格式，然后是常用格式
    format_extensions = []
    if format:
        format_extensions.append(f".{format.lower()}")
    
    format_extensions.extend([".mp4", ".avi", ".webm"])
    
    # 检查每个可能的处理后视频文件
    for ext in format_extensions:
        web_video_path = os.path.join(web_dir, f"web_{process_id}{ext}")
        if os.path.exists(web_video_path) and os.path.getsize(web_video_path) > 0:
            logger.info(f"找到已处理的网页兼容视频: {web_video_path}")
            
            # 根据扩展名设置合适的媒体类型
            media_type = "video/mp4"
            if ext == ".avi":
                media_type = "video/x-msvideo"
            elif ext == ".webm":
                media_type = "video/webm"
            
            return FileResponse(
                path=web_video_path,
                media_type=media_type,
                filename=f"fire_detection_{process_id}{ext}",
                headers={
                    "Content-Disposition": f"inline; filename=fire_detection_{process_id}{ext}",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    
    # 如果没有找到已处理视频，尝试转码处理后的视频
    output_path = progress.get("output_path")
    if output_path and os.path.exists(output_path):
        logger.info(f"尝试转码处理后的视频: {output_path}")
        web_video_path = convert_video_for_web(output_path, process_id)
        
        if web_video_path and os.path.exists(web_video_path):
            # 确定正确的媒体类型
            _, ext = os.path.splitext(web_video_path)
            media_type = "video/mp4"
            if ext.lower() == ".avi":
                media_type = "video/x-msvideo"
            elif ext.lower() == ".webm":
                media_type = "video/webm"
            
            # 更新进度文件
            progress["web_video_path"] = web_video_path
            with open(progress_path, "w") as f:
                json.dump(progress, f)
            
            return FileResponse(
                path=web_video_path,
                media_type=media_type,
                filename=f"fire_detection_{process_id}{ext}",
                headers={
                    "Content-Disposition": f"inline; filename=fire_detection_{process_id}{ext}",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    
    # 如果处理后的视频不存在或转码失败，尝试转码原始视频
    file_path = progress.get("file_path")
    if file_path and os.path.exists(file_path):
        logger.info(f"尝试转码原始视频: {file_path}")
        web_video_path = convert_video_for_web(file_path, process_id)
        
        if web_video_path and os.path.exists(web_video_path):
            # 确定正确的媒体类型
            _, ext = os.path.splitext(web_video_path)
            media_type = "video/mp4"
            if ext.lower() == ".avi":
                media_type = "video/x-msvideo"
            elif ext.lower() == ".webm":
                media_type = "video/webm"
            
            # 更新进度文件
            progress["web_video_path"] = web_video_path
            with open(progress_path, "w") as f:
                json.dump(progress, f)
            
            return FileResponse(
                path=web_video_path,
                media_type=media_type,
                filename=f"fire_detection_{process_id}{ext}",
                headers={
                    "Content-Disposition": f"inline; filename=fire_detection_{process_id}{ext}",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    
    # 如果所有尝试都失败，返回错误
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="无法获取处理后的视频文件")

@router.get("/fire_detection_direct/original-video/{process_id}")
async def get_original_video(process_id: str):
    """获取原始视频，无需通过/api前缀"""
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="处理记录不存在")
        
    with open(progress_path, "r") as f:
        progress = json.load(f)
    
    # 获取原始文件路径
    file_path = progress.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="原始视频文件不存在")
    
    # 根据文件扩展名确定媒体类型
    _, ext = os.path.splitext(file_path)
    media_type = "video/mp4"
    if ext.lower() == ".avi":
        media_type = "video/x-msvideo"
    elif ext.lower() == ".webm":
        media_type = "video/webm"
    
    # 返回原始视频
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=os.path.basename(file_path),
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"inline; filename={os.path.basename(file_path)}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@router.get("/fire_detection_direct/extract-frames/{process_id}")
async def extract_frames_from_video(process_id: str, type: str = "processed", limit: int = 100):
    """
    从视频中提取帧序列，用于前端帧轮询播放
    
    Args:
        process_id: 处理任务ID
        type: 需要提取帧的视频类型，可选值：original（原始视频）, processed（处理后视频）
        limit: 最大提取帧数量
        
    Returns:
        包含帧URL列表的JSON响应
    """
    progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
    
    if not os.path.exists(progress_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="处理记录不存在")
    
    # 读取进度文件
    with open(progress_path, "r") as f:
        progress = json.load(f)
    
    # 确定要处理的视频路径
    video_path = None
    if type == "original":
        video_path = progress.get("file_path")
    else:  # processed
        video_path = progress.get("output_path")
        
        # 如果处理后的视频路径不存在，尝试查找转码后的web视频
        if not video_path or not os.path.exists(video_path):
            web_video_path = os.path.join(OUTPUT_DIR, "web_videos", f"web_{process_id}.mp4")
            if os.path.exists(web_video_path):
                video_path = web_video_path
                
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"{'原始' if type == 'original' else '处理后'}视频文件不存在"
        )
    
    # 创建帧保存目录
    frames_dir = os.path.join(OUTPUT_DIR, f"frames_sequence_{process_id}_{type}")
    os.makedirs(frames_dir, exist_ok=True)

    try:
        # 检查是否已经提取过帧
        if os.path.exists(frames_dir) and len(os.listdir(frames_dir)) > 0:
            # 已存在帧，直接返回
            frames = []
            for i, file_name in enumerate(sorted(os.listdir(frames_dir))):
                if file_name.endswith('.jpg') or file_name.endswith('.png'):
                    frames.append({
                        "index": i,
                        "name": file_name,
                        "url": f"/api/fire-detection/frame-sequence/{process_id}/{type}/{file_name}"
                    })
            
            return {"frames": frames, "total": len(frames)}
        
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"无法打开视频文件: {video_path}"
            )
        
        # 获取视频信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 确定帧采样间隔
        if total_frames <= limit:
            frame_interval = 1  # 每帧都采样
        else:
            frame_interval = total_frames // limit
        
        # 提取帧
        frames = []
        frame_index = 0
        saved_count = 0
        
        while True:
            success, frame = cap.read()
            if not success:
                break
                
            if frame_index % frame_interval == 0:
                # 为每一帧创建一个唯一的文件名
                frame_file = f"frame_{saved_count:04d}.jpg"
                frame_path = os.path.join(frames_dir, frame_file)
                
                # 保存帧
                cv2.imwrite(frame_path, frame)
                
                # 添加帧信息到结果列表
                frames.append({
                    "index": saved_count,
                    "name": frame_file,
                    "url": f"/api/fire-detection/frame-sequence/{process_id}/{type}/{frame_file}"
                })
                
                saved_count += 1
                
            frame_index += 1
            
            # 检查是否已达到限制的帧数
            if saved_count >= limit:
                break
                
        # 释放资源
        cap.release()
        
        # 返回帧信息列表
        return {
            "frames": frames,
            "total": saved_count,
            "video_info": {
                "total_frames": total_frames,
                "fps": fps,
                "duration": total_frames / fps if fps > 0 else 0
            }
        }
        
    except Exception as e:
        logger.exception(f"从视频提取帧时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"从视频提取帧时出错: {str(e)}"
        )

@router.get("/fire-detection/frame-sequence/{process_id}/{type}/{frame_name}")
async def get_frame_sequence_image(process_id: str, type: str, frame_name: str):
    """获取帧序列中的图像"""
    # 检查类型参数
    if type not in ["original", "processed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的类型参数，只能为 'original' 或 'processed'")
    
    # 验证文件名参数（安全检查）
    if ".." in frame_name or "/" in frame_name or "\\" in frame_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的文件名参数")
    
    # 构建帧图像文件路径
    frames_dir = os.path.join(OUTPUT_DIR, f"frames_sequence_{process_id}_{type}")
    frame_path = os.path.join(frames_dir, frame_name)
    
    if not os.path.exists(frame_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帧图像不存在")
    
    return FileResponse(
        path=frame_path,
        media_type="image/jpeg",
        filename=frame_name
    )
