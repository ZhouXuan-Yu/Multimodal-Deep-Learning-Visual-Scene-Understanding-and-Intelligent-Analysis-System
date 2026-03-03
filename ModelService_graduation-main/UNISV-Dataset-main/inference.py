"""
推理脚本，用于实时视频处理和警报系统
"""

import os
import cv2
import torch
import numpy as np
import argparse
import time
import traceback
from datetime import datetime
from collections import deque

# 导入报警模块
from alarm import EmailSender, DEFAULT_CONFIG

from config import *
from models import get_model
# 保留相关模块的导入
from utils import TemporalSmoothing, apply_alert_box, create_alert_overlay, show_confirm_dialog, draw_action_label
# 移除未使用的导入
# from data_loader import InfraredActionDataset
# import data_loader


class ActionRecognitionSystem:
    """
    行为识别系统类，处理视频流并进行实时行为识别和警报
    """
    
    def __init__(self, model_path, device=None, conf_threshold=CONFIDENCE_THRESHOLD, 
                use_smoothing=USE_TEMPORAL_SMOOTHING, display_size=(1280, 720)):
        """
        初始化行为识别系统
        
        Args:
            model_path: 模型权重路径
            device: 运行设备（CPU/GPU）
            conf_threshold: 置信度阈值
            use_smoothing: 是否使用时序平滑
            display_size: 显示窗口大小
        """
        # 设置设备
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = device
            
        print(f"Using device: {self.device}")
        
        # 加载模型
        self.model = self._load_model(model_path)
        
        # 配置参数
        self.conf_threshold = conf_threshold
        self.use_smoothing = use_smoothing
        self.display_size = display_size
        
        # 初始化时序平滑器
        self.smoothing = TemporalSmoothing(window_size=TEMPORAL_WINDOW_SIZE)
        
        # 初始化帧缓冲区
        self.frame_buffer = deque(maxlen=CLIP_LENGTH)
        
        # 初始化结果
        self.last_prediction = None
        self.last_confidence = 0.0
        
        # 警报状态
        self.is_alert_active = False
        self.alert_start_time = None
        self.alert_duration = 30.0  # 增加冷却时间为30秒，避免过多警报
        
        # 初始化邮件发送器
        self.email_sender = EmailSender()
        
        # 中文行为名称映射
        self.action_name_chinese = {
            'pushpeople': '推人',
            'fight': '打架',
            'jogging': '慢跑',
            'shakehands': '握手',
            'embrace': '抱抱',
            'walk': '行走',
            'singlewave': '单手挥手',
            'doublewave': '双手挥手',
            'jump': '跳跃',
            'squat': '下蹲'
        }
        
        # 确认对话框状态
        self.show_dialog = False
        self.dialog_start_time = None
        self.dialog_duration = 5.0  # 对话框显示时间（秒）
        
        # 类别名称
        self.class_names = list(ACTION_CATEGORIES.keys())
        
        # 创建结果目录
        self.output_dir = os.path.join(os.path.dirname(model_path), 'results')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 录制状态
        self.is_recording = False
        self.out = None
        self.record_start_time = None
        
        # 初始化人体检测器
        self.init_human_detector()
        
        # 目标跟踪状态
        self.frame_count = 0
        self.last_detection = None  # 上一次检测到的人体坐标
        self.current_box = None  # 当前使用的方框坐标 [x1, y1, x2, y2]
        self.detection_history = deque(maxlen=5)  # 存储最近几次检测结果，用于平滑
        
    def init_human_detector(self):
        """初始化人体检测器"""
        # 首选使用HOG+SVM人体检测器（速度更快，适合推理）
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        # 备选选项：加载预训练的人体检测模型（如果HOG检测器效果不好可以替换）
        # 注释掉的是Haarcascade人体检测器，速度快但精度低
        # self.haar_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
        print("人体检测器初始化完成")
    
    def detect_humans(self, frame):
        """检测画面中的人体"""
        # 使用HOG检测器检测人体
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # 调整图像大小以提高检测速度
        height, width = frame.shape[:2]
        min_dim = min(height, width)
        scale_factor = min(1.0, 400 / min_dim)  # 最大尺寸不超过400像素
        if scale_factor < 1.0:
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            detection_frame = cv2.resize(gray, (new_width, new_height))
        else:
            detection_frame = gray
            scale_factor = 1.0
            
        # 使用HOG人体检测器 - 修复参数问题，移除finalThreshold参数
        humans, weights = self.hog.detectMultiScale(
            detection_frame, 
            winStride=(8, 8),
            padding=(16, 16),
            scale=1.05,
            hitThreshold=0.0  # 使用hitThreshold替代finalThreshold
        )
        
        # 使用置信度阈值过滤检测结果
        filtered_humans = []
        filtered_weights = []
        for (human, weight) in zip(humans, weights):
            if weight > TRACKING_CONFIDENCE:
                filtered_humans.append(human)
                filtered_weights.append(weight)
        
        humans = filtered_humans
        weights = filtered_weights
        
        # 如果找到人体，返回最大的边界框
        if len(humans) > 0:
            # 找出最大的边界框（假设最大的是主要目标）
            max_area = 0
            max_box = None
            for (x, y, w, h), confidence in zip(humans, weights):
                # 将坐标缩放回原始尺寸
                x, y, w, h = int(x/scale_factor), int(y/scale_factor), int(w/scale_factor), int(h/scale_factor)
                area = w * h
                if area > max_area:
                    max_area = area
                    # 转换为[x1, y1, x2, y2]格式
                    max_box = [x, y, x+w, y+h]
            
            return max_box
        
        # 没有检测到人体，返回None
        return None
    
    def update_tracking_box(self, frame):
        """更新跟踪框的位置"""
        height, width = frame.shape[:2]
        
        # 对每一帧都进行人体检测，确保显示检测框
        detected_box = self.detect_humans(frame)
        if detected_box is not None:
            self.detection_history.append(detected_box)
            self.last_detection = detected_box
        
        self.frame_count += 1
        
        # 如果有历史检测结果，使用平滑后的位置
        if self.last_detection is not None:
            # 首次检测到目标时初始化current_box
            if self.current_box is None:
                self.current_box = self.last_detection
            else:
                # 平滑过渡到新的位置（避免抖动）
                for i in range(4):
                    self.current_box[i] = int(BOX_SMOOTH_FACTOR * self.current_box[i] + 
                                            (1 - BOX_SMOOTH_FACTOR) * self.last_detection[i])
            
            return self.current_box
        
        # 如果未检测到人体且没有历史记录，使用默认中心区域框
        if self.current_box is None:
            # 计算默认框大小（视频中心区域）
            box_width = int(width * 0.5)
            box_height = int(height * 0.7)
            center_x = width // 2
            center_y = height // 2
            x1 = max(0, center_x - box_width // 2)
            y1 = max(0, center_y - box_height // 2)
            x2 = min(width, center_x + box_width // 2)
            y2 = min(height, center_y + box_height // 2)
            self.current_box = [x1, y1, x2, y2]
        
        return self.current_box
    
    def _load_model(self, model_path):
        """加载预训练模型"""
        model = get_model(model_type=MODEL_TYPE, num_classes=NUM_CLASSES)
        
        # 加载模型权重
        if os.path.isfile(model_path):
            checkpoint = torch.load(model_path, map_location=self.device)
            if 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                model.load_state_dict(checkpoint)
                
            print(f"Model loaded from {model_path}")
        else:
            print(f"No checkpoint found at {model_path}, using untrained model")
        
        # 设置为评估模式
        model.eval()
        model = model.to(self.device)
        
        return model
    
    def preprocess_frame(self, frame):
        """预处理单个视频帧"""
        # 确保帧是灰度的（红外视频通常是灰度的）
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # 转回3通道供模型使用
            processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        else:
            processed = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        # 调整大小
        processed = cv2.resize(processed, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # 归一化
        processed = processed.astype(np.float32) / 255.0
        processed = (processed - 0.45) / 0.225
        
        # 转换为PyTorch张量
        processed = torch.from_numpy(processed).permute(2, 0, 1)
        
        return processed
    
    def predict_action(self):
        """使用当前帧缓冲区预测行为"""
        # 准备回退选项
        if len(self.frame_buffer) < CLIP_LENGTH:
            print(f"DEBUG: 帧缓冲区长度不足 {len(self.frame_buffer)}/{CLIP_LENGTH}")
            return None, 0.0
            
        # 优化的类别特定阈值使其更准确 - 基于模型在各类别上的表现调整
        class_specific_thresholds = {
            # 红色警报类别 - 降低阈值确保能检测到危险行为
            0: 0.09,   # pushpeople（推人）- 危险行为，降低阈值确保能被检测到
            1: 0.07,   # fight（战斗）- 危险行为，降低阈值确保能被检测到
            
            # 黄色警报类别 - 适度提高阈值减少误报
            2: 0.12,   # jogging（慢跑）- 提高阈值减少误报
            3: 0.12,   # shakehands（握手）- 提高阈值减少误报
            4: 0.12,   # embrace（抱抱）- 提高阈值减少误报
            
            # 绿色标注类别 - 网络对这些需要更高阈值才更准确
            5: 0.13,   # walk（走路）- 常见动作，提高阈值保证精确度
            6: 0.12,   # singlewave（单手挥手）- 提高阈值区分与手臂运动
            7: 0.12,   # doublewave（双手挥手）- 提高阈值区分与手臂运动
            8: 0.13,   # jump（跳跃）- 提高阈值区分与离地动作
            9: 0.13,   # squat（下蹲）- 提高阈值区分与下蹲动作
        }
        
        # 阈值优化策略：
        # 1. 危险行为(fight/pushpeople)：适度提高阈值确保精确性
        # 2. 步行相关动作(walk/jogging)：使用区分度较高的阈值
        # 3. 使用活动往往具有独特的动作特征，阈值较高更好
        
        # 预处理帧缓冲区
        processed_frames = []
        for frame in self.frame_buffer:
            processed = self.preprocess_frame(frame)
            processed_frames.append(processed)
        
        print(f"DEBUG: 得到{len(processed_frames)}个处理后的帧")
        
        # 整合为单个视频片段张量
        clip = torch.stack(processed_frames, dim=1).unsqueeze(0)  # [1, C, T, H, W]
        clip = clip.to(self.device)
        
        print(f"DEBUG: 输入张量形状: {clip.shape}")
        
        # 进行预测
        with torch.no_grad():
            outputs = self.model(clip)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
            
            # 打印所有类别的概率
            probs_np = probabilities[0].cpu().numpy()
            for i, prob in enumerate(probs_np):
                class_name = self.class_names[i] if i < len(self.class_names) else f"Class {i}"
                print(f"DEBUG: 类别 {i} ({class_name}): 概率 {prob:.4f}")
        
        # 获取预测结果
        prediction = predicted.item()
        confidence = confidence.item()
        
        # 应用时序平滑
        if self.use_smoothing and self.last_prediction is not None:
            smoothed_probs = self.smoothing.update(probabilities[0].cpu().numpy())
            smoothed_prediction = np.argmax(smoothed_probs)
            smoothed_confidence = smoothed_probs[smoothed_prediction]
            
            prediction = smoothed_prediction
            confidence = smoothed_confidence
        
        # 检查置信度是否足够高
        print(f"DEBUG: 置信度阈值检查: 当前置信度={confidence:.4f}, 阈值={self.conf_threshold:.4f}")
        
        # 增强的类别特定阈值系统 - 更智能的筛选和比较机制
        valid_predictions = {}
        max_prob = 0.0
        max_class_id = -1
        confidence_gaps = {}
        
        for class_id, class_name in enumerate(self.class_names):
            if class_id < len(probabilities[0]):
                class_prob = probabilities[0][class_id].item()
                class_threshold = class_specific_thresholds.get(class_id, self.conf_threshold)
                print(f"DEBUG: 类别 {class_id} ({class_name}): 概率={class_prob:.4f}, 阈值={class_threshold:.4f}")
                
                # 记录最高概率的类别，即使未达到其阈值
                if class_prob > max_prob:
                    max_prob = class_prob
                    max_class_id = class_id
                
                # 计算每个类别与其阈值的差距
                gap = class_prob - class_threshold
                confidence_gaps[class_id] = gap
                
                # 如果超过该类别的阈值，则记录为有效预测
                if class_prob >= class_threshold:
                    valid_predictions[class_id] = class_prob
        
        # 更严格的判断策略：只有当红色警报行为超过阈值且差距显著时才优先选择
        if valid_predictions:
            danger_actions = {}
            normal_actions = {}
            
            # 分离危险行为和普通行为
            for class_id, prob in valid_predictions.items():
                if class_id in [0, 1]: # 推人或打架
                    danger_actions[class_id] = prob
                else:
                    normal_actions[class_id] = prob
            
            # 如果存在超过阈值的危险行为
            if danger_actions:
                # 找出概率最高的危险行为
                best_danger_id = max(danger_actions, key=danger_actions.get)
                best_danger_prob = danger_actions[best_danger_id]
                
                # 判断是否足够显著：必须比第二高的概率高出10%
                if normal_actions:
                    second_best_prob = max(normal_actions.values())
                    # 危险行为的概率必须足够显著(至少1.3倍于最高的其他类别概率)
                    if best_danger_prob > second_best_prob * 1.3:
                        print(f"DEBUG: 危险行为 {self.class_names[best_danger_id]} (概率: {best_danger_prob:.4f}) 显著高于其他类别 (最高普通概率: {second_best_prob:.4f})")
                        return best_danger_id, best_danger_prob
                    else:
                        print(f"DEBUG: 察觉到危险行为概率不显著高于其他普通类别，改为选择概率最高的类别")
                else:
                    # 没有其他普通行为时，使用危险行为
                    print(f"DEBUG: 选择危险行为: {self.class_names[best_danger_id]} (概率: {best_danger_prob:.4f})")
                    return best_danger_id, best_danger_prob
                    
            # 如果没有红色警报行为，才选择其他超过阈值的概率最高的
            best_class_id = max(valid_predictions, key=valid_predictions.get)
            best_prob = valid_predictions[best_class_id]
            print(f"DEBUG: 有{len(valid_predictions)}个类别超过阈值，选择概率最高的: {self.class_names[best_class_id]} (概率: {best_prob:.4f})")
            return best_class_id, best_prob
            
        # 判断策略：检查最高概率的类别是否接近其阈值
        # 如果最高概率类别接近其阈值（至少达到阈值的90%），也视为有效
        if max_class_id >= 0:
            class_threshold = class_specific_thresholds.get(max_class_id, self.conf_threshold)
            if max_prob >= class_threshold * 0.9:
                print(f"DEBUG: 最高概率类别 {self.class_names[max_class_id]} (概率: {max_prob:.4f}) 接近阈值({class_threshold:.4f})，视为有效")
                return max_class_id, max_prob
        
        # 没有类别超过其特定阈值，回退到原有预测
        if confidence < self.conf_threshold:
            print(f"DEBUG: 没有类别超过其特定阈值，且预测置信度({confidence:.4f})低于全局阈值({self.conf_threshold:.4f})")
            if self.last_prediction is None:
                print("DEBUG: 无上一次预测，返回空预测")
                return None, 0.0
            else:
                return self.last_prediction, self.last_confidence
        else:
            print(f"DEBUG: 没有类别超过其特定阈值，但预测置信度足够高，使用原始预测")
            # 使用原来的预测
        
        self.last_prediction = prediction
        self.last_confidence = confidence
        
        return prediction, confidence
    
    def process_frame(self, frame):
        """处理单个帧并返回带有标注的帧"""
        # 添加到帧缓冲区
        self.frame_buffer.append(frame.copy())
        
        # 如果帧缓冲区未满，直接返回原始帧
        if len(self.frame_buffer) < CLIP_LENGTH:
            return frame
        
        # 预测行为
        prediction, confidence = self.predict_action()
        
        # 打印调试信息
        print(f"DEBUG: 预测结果 - prediction={prediction}, confidence={confidence:.4f}")
        
        # 如果没有有效预测，返回原始帧
        if prediction is None:
            print("DEBUG: 无有效预测，返回原始帧")
            return frame
        
        # 获取行为名称和警报级别
        action_name = self.class_names[prediction]
        alert_level = ACTION_ALERT_LEVEL[prediction]
        print(f"DEBUG: 检测到行为 '{action_name}', 警报级别 '{alert_level}', 置信度 {confidence:.4f}")
        
        # 复制帧用于绘制
        output_frame = frame.copy()
        
        # 使用人体检测和跟踪更新框的位置 - 动态跟随视频中的人物
        box = self.update_tracking_box(frame)
        
        # 如果跟踪失败，使用默认中心区域
        if box is None:
            height, width = frame.shape[:2]
            box_width = int(width * 0.5)
            box_height = int(height * 0.7)
            center_x = width // 2
            center_y = height // 2
            x1 = max(0, center_x - box_width // 2)
            y1 = max(0, center_y - box_height // 2)
            x2 = min(width, center_x + box_width // 2)
            y2 = min(height, center_y + box_height // 2)
            box = [x1, y1, x2, y2]
        
        # 始终显示检测框，即使是绿色警报也显示
        # 应用警报框
        output_frame = apply_alert_box(output_frame, box, alert_level)
        
        # 增强的行为标签显示 - 显示更多有用信息
        # 绘制行为标签和附加信息
        output_frame = draw_action_label(output_frame, action_name, confidence, alert_level)
        
        # 在帧底部添加时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 获取当前帧的高度和宽度
        frame_height, frame_width = output_frame.shape[:2]
        cv2.putText(output_frame, timestamp, (10, frame_height - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 在框内底部显示更详细的置信度信息
        confidence_text = f"{action_name}: {confidence:.2f}"
        text_size = cv2.getTextSize(confidence_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(output_frame, confidence_text, 
                   (box[0] + (box[2]-box[0] - text_size[0])//2, box[3] - 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 注释掉额外的调试框，只保留警报框和标签
        # 强制显示调试框和信息的代码已移除
        
        # 处理红色警报 - 调整触发条件以确保能检测到危险行为
        if alert_level == 'red' and action_name.lower() in ['pushpeople', 'fight'] and confidence > 0.07:  # 降低红色警报阈值
            # 获取中文行为名称
            chinese_name = self.action_name_chinese.get(action_name.lower(), action_name)
            
            # 计算经过时间
            current_time = time.time()
            elapsed_time = 0.0
            if self.alert_start_time is not None:
                elapsed_time = current_time - self.alert_start_time
            
            print(f"DEBUG: 尝试触发红色警报 [{chinese_name}] - 当前状态: is_alert_active={self.is_alert_active}, 经过时间={elapsed_time:.2f}秒, 冷却时间={self.alert_duration:.1f}秒")
            
            # 仅当没有活跃警报或者超过冷却时间才发送新邮件和警报
            if not self.is_alert_active or self.alert_start_time is None or elapsed_time > self.alert_duration:
                # 重置警报状态并记录时间
                self.is_alert_active = True
                self.alert_start_time = current_time
                
                # 保存截图
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                alert_filename = os.path.join(self.output_dir, f"alert_{action_name}_{timestamp}.jpg")
                cv2.imwrite(alert_filename, frame)
                print(f"危险行为警报！检测到 [【{chinese_name}】] 行为！已保存截图: {alert_filename}")
                
                # 现在我们已经在条件判断中限定了只有推人和打架才能触发红色警报
                print(f"\n===== 正在发送危险行为邮件报警 [【{chinese_name}】]... =====")
                try:
                    subject = f"【紧急警报】检测到危险行为: {chinese_name}"
                    body = f"""尊敬的用户：

红外监控系统在 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 检测到危险行为：【{chinese_name}】。
置信度：{confidence:.4f}

请尽快查看附件截图并采取必要措施。

此自动邮件由红外监控系统发出。"""
                    
                    # 发送邮件警报 - 使用正确的参数顺序
                    EmailSender.send_email(subject, body, attachment_path=alert_filename)
                    print(f"\n===== 危险行为 [【{chinese_name}】] 邮件报警发送成功! ===== ")
                except Exception as e:
                    print(f"\n===== 邮件发送异常: {str(e)} =====")
                    print(f"\n详细错误信息: {traceback.format_exc()}")
                    print("\n请检查QQ邮箱的授权码是否正确设置在alarm.py文件中")
                
                # 开始录制
                if not self.is_recording:
                    self.start_recording(action_name)
            
            # 无论是否超过冷却时间，都显示警报覆盖层
            output_frame = create_alert_overlay(output_frame, alert_level, action_name)
            
        # 处理黄色警报
        elif alert_level == 'yellow' and confidence > 0.09:  # 大幅降低黄色警报阈值
            # 获取中文行为名称
            chinese_name = self.action_name_chinese.get(action_name.lower(), action_name)
            
            # 计算经过时间
            current_time = time.time()
            elapsed_time = 0.0
            if self.alert_start_time is not None:
                elapsed_time = current_time - self.alert_start_time
            
            print(f"DEBUG: 尝试触发黄色警报 [{chinese_name}] - 当前状态: is_alert_active={self.is_alert_active}, 经过时间={elapsed_time:.2f}秒, 冷却时间={self.alert_duration:.1f}秒")
            
            # 判断是否超过冷却时间
            if not self.is_alert_active or self.alert_start_time is None or elapsed_time > self.alert_duration:
                # 重置状态
                self.is_alert_active = True
                self.alert_start_time = current_time
                self.dialog_start_time = current_time  # 设置对话框显示时间
                self.show_dialog = True
                
                # 保存截图
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                alert_filename = os.path.join(self.output_dir, f"alert_{action_name}_{timestamp}.jpg")
                cv2.imwrite(alert_filename, frame)
                print(f"异常行为警报！检测到 [【{chinese_name}】] 行为！已保存截图: {alert_filename}")
                
                # 黄色警报不发送邮件，只在控制台显示信息
                print(f"\n===== 检测到异常行为 [【{chinese_name}】]，但不发送邮件 =====")
            
            # 无论是否超过冷却时间，都添加警报覆盖层
            output_frame = create_alert_overlay(output_frame, alert_level, action_name)
            
            # 如果对话框状态有效，显示对话框
            if self.show_dialog and self.dialog_start_time is not None and (current_time - self.dialog_start_time) <= self.dialog_duration:
                output_frame = show_confirm_dialog(output_frame, action_name)
        
        # 如果没有警报，采用渐进式重置状态
        else:
            current_time = time.time()
            
            # 如果警报处于活跃状态，检查是否超过冷却时间
            if self.is_alert_active and self.alert_start_time is not None:
                elapsed_time = current_time - self.alert_start_time
                # 冷却时间结束后自动重置警报状态
                if elapsed_time > self.alert_duration:
                    print(f"DEBUG: 重置警报状态 - 冷却时间结束 ({elapsed_time:.2f} > {self.alert_duration:.1f}秒)")
                    self.is_alert_active = False
                    self.show_dialog = False
            
            # 对话框相关逻辑
            if self.show_dialog and self.dialog_start_time is not None:
                dialog_elapsed_time = current_time - self.dialog_start_time
                if dialog_elapsed_time > self.dialog_duration:
                    print(f"DEBUG: 关闭对话框 - 显示时间结束 ({dialog_elapsed_time:.2f} > {self.dialog_duration:.1f}秒)")
                    self.show_dialog = False
            
            # 录制相关逻辑
            if self.is_recording and self.record_start_time is not None:
                record_elapsed_time = current_time - self.record_start_time
                if record_elapsed_time > 10.0:  # 10秒后停止录制
                    print(f"DEBUG: 停止录制 - 录制时间超过10秒 ({record_elapsed_time:.2f} > 10.0秒)")
                    self.stop_recording()
        
        return output_frame
    
    def start_recording(self, action_name):
        """开始录制视频"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = os.path.join(self.output_dir, f"record_{action_name}_{timestamp}.mp4")
        
        # 获取第一帧的尺寸
        height, width = self.frame_buffer[0].shape[:2]
        
        # 创建VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(video_filename, fourcc, 20.0, (width, height))
        
        # 更新录制状态
        self.is_recording = True
        self.record_start_time = time.time()
        
        print(f"开始录制视频: {video_filename}")
    
    def stop_recording(self):
        """停止录制视频"""
        if self.out is not None:
            self.out.release()
            self.out = None
        
        self.is_recording = False
        print("停止录制视频")
    
    def process_video(self, video_path=None, camera_id=0, save_output=False, no_gui=False):
        """
        处理视频文件或摄像头流
        
        Args:
            video_path: 视频文件路径，如果为None则使用摄像头
            camera_id: 摄像头ID，仅在video_path为None时使用
            save_output: 是否保存输出视频
            no_gui: 是否使用无GUI模式（不显示视频窗口）
        """
        # 打开视频文件或摄像头
        if video_path is not None:
            cap = cv2.VideoCapture(video_path)
            print(f"正在处理视频文件: {video_path}")
        else:
            cap = cv2.VideoCapture(camera_id)
            print(f"正在使用摄像头 ID: {camera_id}")
        
        if not cap.isOpened():
            print("无法打开视频源")
            return
        
        # 获取视频属性
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 设置输出视频
        output_video = None
        if save_output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"output_{timestamp}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            output_video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            print(f"输出视频将保存至: {output_path}")
        
        # 处理视频帧
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                if video_path is not None:
                    print("视频处理完成")
                else:
                    print("无法从摄像头获取帧")
                break
            
            # 处理帧
            processed_frame = self.process_frame(frame)
            
            # 测试帧处理进度 
            if frame_count % 20 == 0:
                print(f"\n处理帧: {frame_count}")
                print(f"当前时间: {datetime.now().strftime('%H:%M:%S')}")
                print(f"处理速度: {frame_count / (time.time() - start_time):.2f} FPS")
                
            # 显示帧（如果不是无GUI模式）
            if not no_gui:
                try:
                    display_frame = cv2.resize(processed_frame, self.display_size) if self.display_size else processed_frame
                    cv2.imshow('Infrared Action Recognition', display_frame)
                except Exception as e:
                    print(f"警告: 无法显示视频窗口: {str(e)}")
                    no_gui = True  # 如果显示失败，切换到无GUI模式
            
            # 保存到输出视频
            if output_video is not None:
                output_video.write(processed_frame)
            
            # 如果正在录制，记录当前帧
            if self.is_recording and self.out is not None:
                self.out.write(frame)
            
            # 按ESC键退出（仅在GUI模式下）
            if not no_gui:
                try:
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:
                        break
                except Exception as e:
                    print(f"警告: 键盘交互失败: {str(e)}")
            
            frame_count += 1
            
        # 计算FPS
        elapsed_time = time.time() - start_time
        if frame_count > 0 and elapsed_time > 0:
            processed_fps = frame_count / elapsed_time
            print(f"处理速度: {processed_fps:.2f} FPS")
        
        # 释放资源
        cap.release()
        if output_video is not None:
            output_video.release()
        if self.is_recording and self.out is not None:
            self.out.release()
        
        # 视频处理结束后强制测试邮件功能
        if save_output and video_path is not None and "Fight" in video_path:
            print("\n\n========== 视频处理完成，开始测试邮件功能... ==========\n")
            try:
                # 查找已生成的警报截图作为测试用途
                existing_images = [f for f in os.listdir(self.output_dir) if f.startswith('alert_') and f.endswith('.jpg')]
                
                if existing_images:
                    # 使用最新生成的警报截图
                    test_filename = os.path.join(self.output_dir, existing_images[-1])
                    print(f"\n使用现有警报截图: {test_filename}")
                else:
                    # 如果没有警报截图，手动创建一个空白图像
                    test_filename = os.path.join(self.output_dir, "test_alert.jpg")
                    print(f"\n创建空白图像用于测试: {test_filename}")
                    # 创建一个320x240的空白图像
                    blank_image = np.ones((240, 320, 3), np.uint8) * 255
                    # 添加文字
                    cv2.putText(blank_image, "Fight Detection Test", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.imwrite(test_filename, blank_image)
                
                if not os.path.exists(test_filename):
                    print(f"\n错误: 无法找到或创建测试图像: {test_filename}")
                    test_filename = None  # 如果图像不存在，则不使用附件
                
                from alarm import send_red_alert, EmailSender, QQ_CONFIG, GMAIL_CONFIG
                
                # 直接测试不带附件的邮件发送
                print("1. 测试QQ邮箱直接发送(无附件)...")
                EmailSender.send_email("红外监控系统测试邮件", "这是一封测试邮件(无附件)", QQ_CONFIG)
                
                if test_filename and os.path.exists(test_filename):
                    # 带附件测试
                    print(f"2. 测试QQ邮箱发送(带附件)...")
                    EmailSender.send_email("红外监控系统测试邮件", "这是一封测试邮件(带附件)", QQ_CONFIG, test_filename)
                
                # 尝试Gmail
                try:
                    print("3. 测试Gmail直接发送...")
                    EmailSender.send_email("红外监控系统 Gmail 测试邮件", "这是一封来自Gmail的测试邮件", GMAIL_CONFIG, None)
                except Exception as gmail_error:
                    print(f"Gmail发送失败: {str(gmail_error)}")
                
                # 测试警报函数
                print("4. 测试红色警报函数...")
                if test_filename and os.path.exists(test_filename):
                    send_red_alert("Fight", 0.99, test_filename)
                else:
                    send_red_alert("Fight", 0.99, None)
                
                print("\n========== 邮件功能测试完成 ==========\n")
            except Exception as e:
                print(f"\n========== 邮件功能测试出错: {str(e)} ==========\n")
        
        cv2.destroyAllWindows()
    
    def run_real_time_demo(self, camera_id=0):
        """运行实时演示，使用摄像头"""
        self.process_video(video_path=None, camera_id=camera_id, save_output=False)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="红外监控视频行为识别系统")
    parser.add_argument('--model', type=str, required=True, help='模型权重路径')
    parser.add_argument('--video', type=str, default=None, help='视频文件路径，不提供则使用摄像头')
    parser.add_argument('--camera', type=int, default=0, help='摄像头ID，仅在未提供视频文件时使用')
    parser.add_argument('--save', action='store_true', help='保存输出视频')
    parser.add_argument('--device', type=str, default=None, help='运行设备，如 "cuda" 或 "cpu"')
    parser.add_argument('--no-gui', action='store_true', help='无GUI模式，不显示视频窗口')
    parser.add_argument('--conf', type=float, default=CONFIDENCE_THRESHOLD, help='置信度阈值')
    parser.add_argument('--no-smooth', action='store_true', help='禁用时序平滑')
    parser.add_argument('--display-width', type=int, default=1280, help='显示窗口宽度')
    parser.add_argument('--display-height', type=int, default=720, help='显示窗口高度')
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 初始化行为识别系统
    system = ActionRecognitionSystem(model_path=args.model, device=args.device)
    
    # 处理视频
    if args.video or args.camera is not None:
        system.process_video(
            video_path=args.video,
            camera_id=args.camera,
            save_output=args.save,
            no_gui=args.no_gui
        )
    else:
        print("请指定视频文件路径或摄像头ID")


if __name__ == "__main__":
    main()
