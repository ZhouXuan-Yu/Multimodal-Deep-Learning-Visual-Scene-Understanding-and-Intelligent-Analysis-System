"""
RGBT视频处理器核心模块

提供视频处理的核心功能，包括RGBT视频的帧提取、处理和结果生成
"""

import os
import cv2
import time
import uuid
import logging
import threading
from typing import Dict, Any, Optional
from datetime import datetime

# 导入RGBT检测器 - 复用已有的YOLOv8检测器
from app.services.rgbt_detection import YOLOv8Detector
from .utils import get_video_info

# 设置日志记录器
logger = logging.getLogger(__name__)

# 定义任务状态常量
TASK_STATUS = {
    "PENDING": "pending",       # 等待处理
    "PROCESSING": "processing", # 处理中
    "COMPLETED": "completed",   # 处理完成
    "FAILED": "failed"          # 处理失败
}

class RGBTVideoProcessor:
    """RGBT视频处理器类，用于处理RGB和热成像视频"""
    
    def __init__(self, output_dir: str, model_path: str = None):
        """
        初始化RGBT视频处理器
        
        参数:
            output_dir: 输出目录
            model_path: 模型路径，如未指定则使用默认路径
        """
        self.logger = logging.getLogger("RGBTVideoProcessor")
        self.output_dir = output_dir
        self.tasks = {}  # 保存所有任务的状态和信息
        
        # 确保输出目录结构完整存在
        # 主输出目录
        os.makedirs(output_dir, exist_ok=True)
        self.logger.info(f"确保输出主目录存在: {output_dir}")
        
        # 创建上传和处理结果子目录
        uploads_dir = os.path.join(os.path.dirname(output_dir), "uploads")
        outputs_dir = os.path.join(os.path.dirname(output_dir), "outputs")
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(outputs_dir, exist_ok=True)
        self.logger.info(f"创建上传目录: {uploads_dir}")
        self.logger.info(f"创建输出目录: {outputs_dir}")
        
        # 初始化YOLOv8检测器 - 使用与图像处理相同的模型和参数
        try:
            if model_path is None:
                # 用与图像处理相同的模型路径查找逻辑
                app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                model_dir = os.path.join(app_root, "models", "rgbt_fusion")
                
                # 按优先级尝试找模型
                model_candidates = [
                    os.path.join(model_dir, "best.pt"),
                    os.path.join(model_dir, "yolov8x.pt"),
                    os.path.join(model_dir, "yolov8x-seg.pt")
                ]
                
                for candidate in model_candidates:
                    if os.path.exists(candidate):
                        model_path = candidate
                        break
            
            if model_path and os.path.exists(model_path):
                self.logger.info(f"使用YOLOv8模型进行视频处理: {model_path}")
                self.detector = YOLOv8Detector(model_path, conf_thres=0.15, iou_thres=0.45)
                if self.detector.model is None:
                    self.logger.error("YOLOv8模型加载失败")
            else:
                self.logger.error("未找到有效的YOLOv8模型文件")
        except Exception as e:
            self.logger.error(f"初始化YOLOv8检测器失败: {str(e)}")
    
    def create_task(self, rgb_video_path: str, thermal_video_path: Optional[str] = None) -> Dict[str, Any]:
        """
        创建视频处理任务
        
        参数:
            rgb_video_path: RGB视频路径
            thermal_video_path: 热成像视频路径（可选）
            
        返回:
            任务信息，包含任务ID
        """
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 检查文件是否存在
        if not os.path.exists(rgb_video_path):
            return {"success": False, "error": f"RGB视频文件不存在: {rgb_video_path}"}
        
        if thermal_video_path and not os.path.exists(thermal_video_path):
            return {"success": False, "error": f"热成像视频文件不存在: {thermal_video_path}"}
        
        # 创建任务记录
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": TASK_STATUS["PENDING"],
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "rgb_video": {
                "path": rgb_video_path,
                "info": get_video_info(rgb_video_path)
            },
            "thermal_video": {
                "path": thermal_video_path,
                "info": get_video_info(thermal_video_path) if thermal_video_path else None
            },
            "progress": 0,
            "processed_frames": 0,
            "total_frames": 0,
            "fps": 0,
            "output": {
                "rgb_processed": "",
                "thermal_processed": "",
                "combined": ""
            },
            "error": None
        }
        
        # 返回任务信息
        return {
            "success": True,
            "task_id": task_id,
            "status": self.tasks[task_id]["status"]
        }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        参数:
            task_id: 任务ID
            
        返回:
            任务状态信息
        """
        if task_id not in self.tasks:
            return {"success": False, "error": f"任务不存在: {task_id}"}
        
        return {
            "success": True,
            "task": self.tasks[task_id]
        }
    
    def process_video_async(self, task_id: str) -> Dict[str, Any]:
        """
        异步处理视频
        
        参数:
            task_id: 任务ID
            
        返回:
            任务启动结果
        """
        if task_id not in self.tasks:
            return {"success": False, "error": f"任务不存在: {task_id}"}
        
        if self.tasks[task_id]["status"] != TASK_STATUS["PENDING"]:
            return {
                "success": False, 
                "error": f"任务状态不是等待处理，当前状态: {self.tasks[task_id]['status']}"
            }
        
        # 更新任务状态为处理中
        self.tasks[task_id]["status"] = TASK_STATUS["PROCESSING"]
        self.tasks[task_id]["started_at"] = datetime.now().isoformat()
        
        # 启动处理线程
        thread = threading.Thread(
            target=self._process_video_thread,
            args=(task_id,)
        )
        thread.daemon = True
        thread.start()
        
        return {
            "success": True,
            "task_id": task_id,
            "status": self.tasks[task_id]["status"]
        }
    
    def _process_video_thread(self, task_id: str) -> None:
        """
        视频处理线程
        
        参数:
            task_id: 任务ID
        """
        try:
            # 获取任务信息
            task = self.tasks[task_id]
            rgb_video_path = task["rgb_video"]["path"]
            thermal_video_path = task["thermal_video"]["path"] if task["thermal_video"] else None
            
            # 创建输出目录
            outputs_dir = os.path.join(os.path.dirname(self.output_dir), "outputs")
            os.makedirs(outputs_dir, exist_ok=True)
            self.logger.info(f"创建处理结果目录: {outputs_dir}")
            
            # 生成输出文件路径
            rgb_output_path = os.path.join(outputs_dir, f"rgb_processed_{task_id}.mp4")
            thermal_output_path = os.path.join(outputs_dir, f"thermal_processed_{task_id}.mp4") if thermal_video_path else None
            
            # 处理RGB视频
            self.logger.info(f"开始处理RGB视频: {rgb_video_path} -> {rgb_output_path}")
            rgb_result = self._process_single_video(
                task_id, 
                rgb_video_path, 
                rgb_output_path,
                is_thermal=False
            )
            
            # 如果有热成像视频，也进行处理
            thermal_result = None
            if thermal_video_path and thermal_output_path:
                self.logger.info(f"开始处理热成像视频: {thermal_video_path} -> {thermal_output_path}")
                thermal_result = self._process_single_video(
                    task_id,
                    thermal_video_path,
                    thermal_output_path,
                    is_thermal=True
                )
            
            # 更新任务状态
            self.tasks[task_id]["status"] = TASK_STATUS["COMPLETED"]
            self.tasks[task_id]["completed_at"] = datetime.now().isoformat()
            self.tasks[task_id]["output"]["rgb_processed"] = rgb_result["output_path"] if rgb_result else ""
            if thermal_result:
                self.tasks[task_id]["output"]["thermal_processed"] = thermal_result["output_path"]
                
            # 检查并记录输出文件是否存在
            if os.path.exists(rgb_output_path):
                self.logger.info(f"已生成RGB处理视频: {rgb_output_path}")
            else:
                self.logger.error(f"RGB处理视频文件未生成: {rgb_output_path}")
                
            if thermal_output_path and os.path.exists(thermal_output_path):
                self.logger.info(f"已生成热成像处理视频: {thermal_output_path}")
            elif thermal_output_path:
                self.logger.error(f"热成像处理视频文件未生成: {thermal_output_path}")
            
            self.logger.info(f"任务完成: {task_id}, 输出路径: {self.tasks[task_id]['output']}")
            
        except Exception as e:
            self.logger.error(f"视频处理失败: {str(e)}")
            self.tasks[task_id]["status"] = TASK_STATUS["FAILED"]
            self.tasks[task_id]["error"] = str(e)
    
    def _process_single_video(
        self, 
        task_id: str, 
        video_path: str, 
        output_path: str,
        is_thermal: bool = False
    ) -> Dict[str, Any]:
        """
        处理单个视频
        
        参数:
            task_id: 任务ID
            video_path: 视频路径
            output_path: 输出路径
            is_thermal: 是否为热成像视频
            
        返回:
            处理结果
        """
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        self.logger.info(f"处理视频 - 输出目录: {output_dir}")
        self.logger.info(f"处理视频 - {'(热成像)' if is_thermal else '(可见光)'} 输入: {video_path} -> 输出: {output_path}")
        
        # 检查源视频是否存在
        if not os.path.exists(video_path):
            error_msg = f"视频文件不存在: {video_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            error_msg = f"无法打开视频: {video_path}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # 获取视频信息
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 更新任务信息
        if is_thermal:
            self.tasks[task_id]["thermal_video"]["info"]["frame_count"] = total_frames
            self.tasks[task_id]["thermal_video"]["info"]["fps"] = fps
        else:
            self.tasks[task_id]["rgb_video"]["info"]["frame_count"] = total_frames
            self.tasks[task_id]["rgb_video"]["info"]["fps"] = fps
            self.tasks[task_id]["total_frames"] = total_frames
            self.tasks[task_id]["fps"] = fps
        
        # 创建视频写入器 - 使用H.264编码器提高浏览器兼容性
        try:
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if not out.isOpened():
                # 如果avc1不可用，退回到h264
                self.logger.warning("avc1编码器不可用，尝试h264")
                fourcc = cv2.VideoWriter_fourcc(*'H264')
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 如果仍然不可用，尝试mp4v
            if not out.isOpened():
                self.logger.warning("H264编码器不可用，尝试mp4v")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                
            # 记录最终使用的编码器
            self.logger.info(f"视频编码器: {chr(fourcc&0xFF)} {chr((fourcc>>8)&0xFF)} {chr((fourcc>>16)&0xFF)} {chr((fourcc>>24)&0xFF)}")
            
        except Exception as e:
            self.logger.error(f"创建视频写入器失败: {str(e)}")
            # 退回到最基本的mp4v编码器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # 每隔n帧处理一次以提高速度（可选）
        process_every_n_frames = 1  # 处理每一帧，可以根据需要调整
        
        processed_frames = 0
        start_time = time.time()
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # 只处理满足条件的帧
            if processed_frames % process_every_n_frames == 0:
                try:
                    # 使用YOLOv8检测器处理帧
                    if is_thermal:
                        # 热成像图像先进行预处理增强
                        enhanced_frame = self.detector.preprocess_thermal_image(frame)
                        # 使用更低的置信度阈值进行热成像检测
                        thermal_conf_thres = max(0.08, self.detector.conf_thres * 0.6)
                        thermal_iou_thres = max(0.35, self.detector.iou_thres * 0.8)
                        results = self.detector.model(enhanced_frame, conf=thermal_conf_thres, iou=thermal_iou_thres, verbose=False)
                        # 使用增强后的热成像绘制
                        processed_frame = enhanced_frame.copy()
                    else:
                        # RGB图像直接使用标准参数检测
                        results = self.detector.model(frame, conf=self.detector.conf_thres, iou=self.detector.iou_thres, verbose=False)
                        processed_frame = frame.copy()
                    
                    # 在图像上绘制检测结果
                    for result in results:
                        boxes = result.boxes
                        for box in boxes:
                            # 获取边界框坐标
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            # 获取置信度和类别
                            conf = float(box.conf.cpu().numpy()[0])
                            cls = int(box.cls.cpu().numpy()[0])
                            # 获取类别名称作为调试信息
                            class_name = result.names[cls]
                            self.logger.debug(f"检测到目标: 类别={class_name}, 置信度={conf:.2f}, 坐标=({int(x1)},{int(y1)})-({int(x2)},{int(y2)})")
                            
                            # 确定颜色 - RGB检测用绿色，热成像检测用红色
                            color = (0, 255, 0) if not is_thermal else (0, 0, 255)
                            # 根据置信度调整线条粗细
                            thickness = max(1, int(conf * 5))
                            
                            # 添加类别标签（带背景以提升可读性）
                            label = f"{class_name} {conf:.2f}"
                            (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                            bg_tl = (int(x1), max(int(y1) - text_h - 8, 0))
                            bg_br = (int(x1) + text_w + 6, int(y1))
                            cv2.rectangle(processed_frame, bg_tl, bg_br, color, -1)
                            cv2.putText(processed_frame, label, (int(x1) + 3, int(y1) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)
                            
                            # 绘制边界框
                            cv2.rectangle(
                                processed_frame,
                                (int(x1), int(y1)),
                                (int(x2), int(y2)),
                                color,
                                thickness
                            )
                    
                    # 写入处理后的帧
                    out.write(processed_frame)
                except Exception as e:
                    self.logger.error(f"处理帧失败: {str(e)}")
                    # 如果处理失败，写入原始帧
                    out.write(frame)
            else:
                # 不处理的帧直接写入
                out.write(frame)
            
            # 更新进度
            processed_frames += 1
            if total_frames > 0:
                progress = int((processed_frames / total_frames) * 100)
                self.tasks[task_id]["progress"] = progress
                self.tasks[task_id]["processed_frames"] = processed_frames
            
            # 每100帧记录一次进度
            if processed_frames % 100 == 0:
                elapsed = time.time() - start_time
                frames_per_second = processed_frames / elapsed if elapsed > 0 else 0
                self.logger.info(f"进度: {progress}%, 已处理{processed_frames}/{total_frames}帧, {frames_per_second:.2f}帧/秒")
        
        # 释放资源
        cap.release()
        out.release()
        
        return {
            "success": True,
            "output_path": output_path,
            "processed_frames": processed_frames,
            "total_frames": total_frames
        }
