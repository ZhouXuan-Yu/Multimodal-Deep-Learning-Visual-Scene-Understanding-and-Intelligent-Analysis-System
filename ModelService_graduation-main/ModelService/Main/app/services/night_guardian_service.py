"""
夜间保卫者系统服务层
负责视频处理、人体检测和行为识别的核心功能
"""

import os
import time
import uuid
import cv2
import torch
import numpy as np
import torch.nn.functional as F
from collections import deque
import asyncio
from datetime import datetime
from imutils.object_detection import non_max_suppression
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

# 导入模型相关模块
from app.models.night_guardian.config import (
    ACTION_CATEGORIES, 
    ACTION_ALERT_LEVEL, 
    ALERT_COLORS,
    FRAME_WIDTH,
    FRAME_HEIGHT
)
from app.models.night_guardian.enhanced_models import InfraredActionNet
from app.models.night_guardian.optimized_models import OptimizedInfraredActionNet, OptimizedActionNetLite
from app.models.night_guardian.train_utils import set_random_seed

# 设置日志
logger = logging.getLogger(__name__)

class NightGuardianService:
    """夜间保卫者服务类，负责视频处理和行为检测"""
    
    # 使用类变量存储任务状态，确保所有实例共享任务数据
    tasks = {}
    
    def __init__(self):
        # 打印日志确认初始化
        logger.info("初始化夜间保卫者服务实例")
        
        # 设置基础路径
        self.base_path = Path(os.path.dirname(os.path.abspath(__file__))).parent
        self.upload_dir = self.base_path / "data" / "night_guardian" / "uploads"
        self.output_dir = self.base_path / "data" / "night_guardian" / "outputs"
        self.model_dir = self.base_path / "models" / "night_guardian" / "checkpoints"
        
        # 确保目录存在
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置随机种子以确保可重复性
        set_random_seed(42)
        
        # 打印当前任务记录
        logger.info(f"当前任务记录数量: {len(type(self).tasks)}")
        
    async def process_video(self, 
                     video_path: str, 
                     model_type: str = "OptimizedActionNetLite",
                     threshold: float = 0.6,
                     clip_len: int = 16,
                     save_frames: bool = False,
                     task_id: str = None) -> Dict[str, Any]:
        """
        异步处理视频并进行行为检测
        
        Args:
            video_path: 视频文件路径
            model_type: 模型类型
            threshold: 检测阈值
            clip_len: 视频片段长度
            save_frames: 是否保存关键帧
            task_id: 任务ID，如不提供则自动生成
            
        Returns:
            处理结果信息
        """
        import traceback
        
        logger.info(f"[处理视频] 开始处理视频: {video_path}")
        logger.info(f"[处理视频] 参数: 模型={model_type}, 阈值={threshold}, 片段长度={clip_len}, 保存帧={save_frames}")
        
        # 生成任务ID或使用提供的ID
        if task_id is None:
            task_id = str(uuid.uuid4())
        logger.info(f"[处理视频] 任务ID: {task_id}")
        
        # 创建任务记录 - 使用类变量而非实例变量
        tasks = type(self).tasks
        tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "video_path": video_path,
            "model_type": model_type,
            "threshold": threshold,
            "start_time": time.time(),
            "output_path": None,
            "results": []
        }
        logger.info(f"[处理视频] 创建任务记录: {task_id}, 当前任务数: {len(tasks)}")
        logger.info(f"[处理视频] 现有任务: {list(tasks.keys())}")
        
        try:
            # 检查视频文件是否存在
            if not os.path.exists(video_path):
                error_msg = f"视频文件不存在: {video_path}"
                logger.error(f"[处理视频] {error_msg}")
                self.tasks[task_id].update({
                    "status": "error",
                    "error": error_msg
                })
                raise FileNotFoundError(error_msg)
            
            # 检查文件是否可读
            try:
                file_size = os.path.getsize(video_path)
                logger.info(f"[处理视频] 文件大小: {file_size} 字节")
                if file_size == 0:
                    error_msg = f"视频文件大小为0: {video_path}"
                    logger.error(f"[处理视频] {error_msg}")
                    self.tasks[task_id].update({
                        "status": "error",
                        "error": error_msg
                    })
                    raise ValueError(error_msg)
            except Exception as file_error:
                error_msg = f"读取文件信息时出错: {str(file_error)}"
                logger.exception(f"[处理视频] {error_msg}")
                self.tasks[task_id].update({
                    "status": "error",
                    "error": error_msg
                })
                raise
            
            # 测试打开视频文件
            try:
                logger.info(f"[处理视频] 测试打开视频文件: {video_path}")
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    error_msg = f"无法打开视频文件: {video_path}"
                    logger.error(f"[处理视频] {error_msg}")
                    self.tasks[task_id].update({
                        "status": "error",
                        "error": error_msg
                    })
                    raise ValueError(error_msg)
                
                # 获取视频信息
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                logger.info(f"[处理视频] 视频信息: 帧数={frame_count}, FPS={fps}, 分辨率={width}x{height}")
                
                # 释放视频文件
                cap.release()
            except Exception as video_error:
                error_msg = f"测试视频文件时出错: {str(video_error)}"
                logger.exception(f"[处理视频] {error_msg}")
                self.tasks[task_id].update({
                    "status": "error",
                    "error": error_msg
                })
                raise
            
            # 加载模型
            try:
                logger.info(f"[处理视频] 加载模型: {model_type}")
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                logger.info(f"[处理视频] 使用设备: {device}")
                model = self._load_model(model_type, device)
                logger.info(f"[处理视频] 模型加载成功: {model_type}")
            except Exception as model_error:
                error_msg = f"加载模型时出错: {str(model_error)}"
                logger.exception(f"[处理视频] {error_msg}")
                self.tasks[task_id].update({
                    "status": "error",
                    "error": error_msg
                })
                raise
            
            # 处理视频
            logger.info(f"[处理视频] 开始处理视频文件: {video_path}")
            try:
                output_path, results = await self._process_video_file(
                    task_id=task_id,
                    video_path=video_path,
                    model=model,
                    device=device,
                    threshold=threshold,
                    clip_len=clip_len,
                    save_frames=save_frames
                )
                logger.info(f"[处理视频] 处理成功, 输出路径: {output_path}, 结果数量: {len(results)}")
            except Exception as process_error:
                error_msg = f"处理视频文件时出错: {str(process_error)}"
                error_trace = traceback.format_exc()
                logger.exception(f"[处理视频] {error_msg}")
                logger.error(f"[处理视频] 错误堆栈: {error_trace}")
                self.tasks[task_id].update({
                    "status": "error",
                    "error": error_msg,
                    "traceback": error_trace
                })
                raise
            
            # 更新任务状态
            logger.info(f"[处理视频] 更新任务状态: {task_id}")
            tasks = type(self).tasks
            tasks[task_id].update({
                "status": "completed",
                "progress": 100,
                "end_time": time.time(),
                "output_path": output_path,
                "results": results,
                "detection_count": len(results)
            })
            logger.info(f"[处理视频] 任务完成: {task_id}, 检测到 {len(results)} 个结果")
            
            return {
                "task_id": task_id,
                "status": "completed",
                "output_path": output_path,
                "results": results
            }
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.exception(f"[处理视频] 处理视频时发生错误: {str(e)}")
            logger.error(f"[处理视频] 错误堆栈: {error_trace}")
            
            # 确保任务记录更新了错误状态
            if task_id in self.tasks and self.tasks[task_id].get("status") != "error":
                self.tasks[task_id].update({
                    "status": "error",
                    "error": str(e),
                    "traceback": error_trace,
                    "end_time": time.time()
                })
            
            # 抛出异常以便上层处理
            raise
            
        except Exception as e:
            logger.error(f"处理视频时出错: {str(e)}")
            self.tasks[task_id].update({
                "status": "failed",
                "error": str(e)
            })
            raise
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务处理状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        # 使用类变量存储任务信息
        tasks = type(self).tasks
        logger.info(f"获取任务状态: {task_id}, 当前任务数: {len(tasks)}")
        
        if task_id not in tasks:
            logger.warning(f"找不到任务: {task_id}, 现有任务: {list(tasks.keys())}")
            return {"status": "not_found"}
        
        logger.info(f"找到任务: {task_id}, 状态: {tasks[task_id]['status']}")
        return tasks[task_id]
    
    def _get_model(self, model_type: str, num_classes: int = 10):
        """获取模型实例"""
        if model_type == 'InfraredActionNet':
            return InfraredActionNet(num_classes=num_classes)
        elif model_type == 'OptimizedInfraredActionNet':
            return OptimizedInfraredActionNet(num_classes=num_classes)
        elif model_type == 'OptimizedActionNetLite':
            return OptimizedActionNetLite(num_classes=num_classes)
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
    
    def _load_model(self, model_type: str, device: str, model_name: str = "best_model.pth"):
        """加载预训练模型"""
        logger.info(f"加载模型 {model_type} 从 {model_name}")
        
        # 获取模型实例
        model = self._get_model(model_type)
        
        # 检查模型权重
        model_path = self.model_dir / model_name
        
        # 如果指定模型不存在，尝试使用默认模型
        if not model_path.exists() and model_name != "best_model.pth":
            logger.warning(f"指定的模型权重文件 {model_name} 不存在，尝试使用默认模型")
            model_path = self.model_dir / "best_model.pth"
        
        # 加载权重（如果存在）
        if model_path.exists():
            try:
                checkpoint = torch.load(str(model_path), map_location=device)
                
                # 处理不同格式的checkpoint
                if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                    model.load_state_dict(checkpoint['model_state_dict'])
                else:
                    model.load_state_dict(checkpoint)
                    
                logger.info("成功加载模型权重")
            except Exception as e:
                logger.error(f"加载模型权重时出错: {str(e)}")
                logger.warning("使用随机初始化的模型继续")
        else:
            logger.warning(f"警告: 模型权重文件 {model_path} 不存在，使用随机初始化的模型")
        
        # 将模型移至设备并设置为评估模式
        model = model.to(device)
        model.eval()
        
        return model
    
    async def _process_video_file(self,
                           task_id: str,
                           video_path: str,
                           model,
                           device: str,
                           threshold: float = 0.6,
                           clip_len: int = 16,
                           save_frames: bool = False) -> Tuple[str, List[Dict]]:
        """
        处理视频文件
        
        Args:
            task_id: 任务ID
            video_path: 视频文件路径
            model: 加载的模型
            device: 运行设备
            threshold: 检测阈值
            clip_len: 视频片段长度
            save_frames: 是否保存关键帧
            
        Returns:
            输出视频路径和检测结果列表
        """
        # 创建行为识别器
        recognizer = ActionRecognizer(model, device, clip_len, threshold)
        
        # 打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 创建输出视频文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(self.output_dir / f"processed_{task_id}.mp4")
        
        # 使用H.264编码 - 更兼容浏览器
        try:
            # 先尝试H.264编码
            fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264编码
            out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
            
            # 验证视频写入器是否正确初始化
            if not out.isOpened():
                logger.warning("H.264 (avc1) 编码初始化失败，尝试使用mp4v")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
                
                if not out.isOpened():
                    logger.warning("mp4v 编码初始化失败，尝试使用divx")
                    fourcc = cv2.VideoWriter_fourcc(*'DIVX')
                    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        except Exception as e:
            logger.error(f"创建视频写入器失败: {str(e)}，尝试使用mp4v")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        # 创建帧保存目录（如果需要）
        frames_dir = None
        if save_frames:
            frames_dir = self.output_dir / "frames" / timestamp
            frames_dir.mkdir(parents=True, exist_ok=True)
        
        # 处理结果记录
        results = []
        
        # 帧计数和处理时间
        frame_count = 0
        processing_start = time.time()
        
        # 逐帧处理视频
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 更新进度
                progress = int((frame_count / total_frames) * 100)
                self.tasks[task_id]["progress"] = progress
                
                # 转为可处理的格式（适应模型输入）
                # 更新行为识别器的缓冲区
                recognizer.update_buffer(frame)
                
                # 检测人物
                person_boxes = recognizer.detect_persons(frame)
                
                # 获取行为预测
                action_name, confidence, alert_level = recognizer.get_prediction()
                
                # 在框中添加行为标签和置信度
                if action_name:
                    # 记录结果
                    result = {
                        "frame": frame_count,
                        "timestamp": frame_count / fps,
                        "action": action_name,
                        "confidence": confidence,
                        "alert_level": alert_level
                    }
                    results.append(result)
                    
                    # 保存关键帧（如果启用且是危险行为）
                    if save_frames and alert_level == 'red':
                        frame_path = str(frames_dir / f"frame_{frame_count:06d}.jpg")
                        cv2.imwrite(frame_path, frame)
                        result["frame_path"] = frame_path
                    
                    for box in person_boxes:
                        # 根据警报级别选择颜色
                        color = ALERT_COLORS.get(alert_level, (0, 255, 0))
                        
                        # 绘制边框
                        x, y, w, h = box
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        
                        # 添加文本标签
                        label = f"{action_name}: {confidence:.2f}"
                        cv2.putText(frame, label, (x, y - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # 写入输出视频
                out.write(frame)
                
                # 更新帧计数
                frame_count += 1
                
                # 每处理100帧让出控制权，使异步函数不阻塞
                if frame_count % 100 == 0:
                    await asyncio.sleep(0.001)
        
        finally:
            # 释放资源
            cap.release()
            out.release()
        
        # 计算处理统计信息
        processing_time = time.time() - processing_start
        fps_processing = frame_count / processing_time if processing_time > 0 else 0
        
        logger.info(f"视频处理完成: {frame_count} 帧, {processing_time:.2f} 秒, {fps_processing:.2f} FPS")
        
        return output_path, results


class ActionRecognizer:
    """行为识别器类"""
    def __init__(self, model, device, clip_len=16, threshold=0.6):
        self.model = model
        self.device = device
        self.clip_len = clip_len
        self.threshold = threshold
        
        # 初始化帧缓冲区
        self.frames_buffer = deque(maxlen=clip_len)
        
        # 初始化平滑器 - 使用过去5个预测的平均值
        self.prediction_history = deque(maxlen=5)
        
        # 类别信息
        self.action_names = {v: k for k, v in ACTION_CATEGORIES.items()}
        
        # 危险行为索引
        self.danger_indices = [ACTION_CATEGORIES['pushpeople'], ACTION_CATEGORIES['fight']]
        
        # 警告行为索引
        self.warning_indices = [ACTION_CATEGORIES['jogging'], ACTION_CATEGORIES['shakehands'], ACTION_CATEGORIES['embrace']]
        
        # 警告级别颜色
        self.alert_colors = {
            'red': (0, 0, 255),     # 危险行为 (BGR格式)
            'yellow': (0, 255, 255), # 中等风险
            'green': (0, 255, 0)     # 正常行为
        }
        
        # 加载人体检测模型 (使用OpenCV内置的HOG行人检测器)
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
    def preprocess_frame(self, frame):
        """预处理单个帧"""
        # 调整大小
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # 灰度化处理 (红外视频通常是单通道)
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # 转回3通道以兼容模型输入
            frame = np.stack([gray, gray, gray], axis=2)
        
        # 数值归一化
        frame = frame / 255.0
        
        return frame
    
    def update_buffer(self, frame):
        """更新帧缓冲区"""
        processed_frame = self.preprocess_frame(frame)
        self.frames_buffer.append(processed_frame)
    
    def detect_persons(self, frame):
        """
        检测图像中的人物
        
        Args:
            frame: 输入帧
            
        Returns:
            人物边界框列表 [(x, y, w, h), ...]
        """
        # 调整帧大小以加快处理速度
        width = 400
        height = int(frame.shape[0] * (width / frame.shape[1]))
        resized = cv2.resize(frame, (width, height))
        
        # 预处理以提高检测质量
        if len(resized.shape) == 3:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = resized
            
        # 提高对比度
        gray = cv2.equalizeHist(gray)
        
        # 应用高斯模糊减少噪声
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 人物检测
        boxes, weights = self.hog.detectMultiScale(
            gray, 
            winStride=(8, 8),
            padding=(4, 4),
            scale=1.05
        )
        
        # 处理检测结果
        if len(boxes) > 0:
            # 应用非最大值抑制减少重叠的边界框
            boxes = non_max_suppression(boxes, probs=None, overlapThresh=0.65)
            
            # 调整回原始帧尺寸
            scale_x = frame.shape[1] / width
            scale_y = frame.shape[0] / height
            
            adjusted_boxes = []
            for (x, y, w, h) in boxes:
                x_orig = int(x * scale_x)
                y_orig = int(y * scale_y)
                w_orig = int(w * scale_x)
                h_orig = int(h * scale_y)
                adjusted_boxes.append((x_orig, y_orig, w_orig, h_orig))
                
            return adjusted_boxes
        else:
            # 如果没有检测到人物，添加一个默认检测框（视频中心区域）
            center_x = frame.shape[1] // 4
            center_y = frame.shape[0] // 4
            width = frame.shape[1] // 2
            height = frame.shape[0] // 2
            return [(center_x, center_y, width, height)]
        
    def get_prediction(self):
        """获取当前缓冲区的行为预测"""
        if len(self.frames_buffer) < self.clip_len:
            # 缓冲区未满
            return None, None, None
        
        # 准备输入张量
        clip = np.array(list(self.frames_buffer))
        clip = np.transpose(clip, (3, 0, 1, 2))  # [C, T, H, W]
        clip = torch.from_numpy(clip).unsqueeze(0).float().to(self.device)
        
        # 推理
        with torch.no_grad():
            outputs = self.model(clip)
            probs = F.softmax(outputs, dim=1)
            
            # 获取预测和置信度
            confidence, prediction = torch.max(probs, 1)
            confidence = confidence.item()
            prediction = prediction.item()
            
            # 所有类别的概率
            all_probs = probs[0].cpu().numpy()
        
        # 将当前预测添加到历史记录
        self.prediction_history.append(all_probs)
        
        # 计算平均预测结果以平滑输出
        if len(self.prediction_history) > 0:
            avg_probs = np.mean(np.array(self.prediction_history), axis=0)
            smoothed_prediction = np.argmax(avg_probs)
            smoothed_confidence = avg_probs[smoothed_prediction]
            
            # 获取行为名称和警报级别
            action_name = self.action_names.get(smoothed_prediction, "未知")
            alert_level = ACTION_ALERT_LEVEL.get(smoothed_prediction, "green")
            
            return action_name, smoothed_confidence, alert_level
        
        return None, None, None
