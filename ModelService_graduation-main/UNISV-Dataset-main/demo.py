"""
红外视频行为识别系统演示脚本
展示针对危险行为（推人和打架）的检测效果
"""

import os
import time
import argparse
import numpy as np
import torch
import torch.nn.functional as F
import cv2
from tqdm import tqdm
from collections import deque
import datetime
import imutils
from imutils.object_detection import non_max_suppression

# 导入项目模块
from config import *
from enhanced_models import InfraredActionNet
from optimized_models import OptimizedInfraredActionNet, OptimizedActionNetLite
from train_utils import set_random_seed

# 导入报警模块
from alarm import send_red_alert, send_yellow_alert

# 定义图像预处理函数
def preprocess_frame(frame, target_size=(224, 224)):
    # 调整大小
    if frame.shape[0] != target_size[0] or frame.shape[1] != target_size[1]:
        frame = cv2.resize(frame, target_size)
    
    # 转换为灰度图
    if len(frame.shape) == 3 and frame.shape[2] == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 添加通道维度（如果是灰度图）
    if len(frame.shape) == 2:
        frame = np.expand_dims(frame, axis=2)
        # 转回3通道供可视化和部分模型使用
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    
    # 归一化
    frame = frame.astype(np.float32) / 255.0
    
    return frame
# 设置随机种子以确保可重复性
set_random_seed(42)

# 定义命令行参数
parser = argparse.ArgumentParser(description='红外视频行为识别系统演示')
parser.add_argument('--video_path', type=str, default=None, help='输入视频路径，不填则使用摄像头')
parser.add_argument('--model_path', type=str, default='./saved_models/best_model.pth', help='模型权重路径')
parser.add_argument('--model_type', type=str, default='OptimizedActionNetLite', 
                    choices=['InfraredActionNet', 'OptimizedInfraredActionNet', 'OptimizedActionNetLite'],
                    help='模型类型')
parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu', 
                    help='运行设备 (cuda/cpu)')
parser.add_argument('--clip_len', type=int, default=16, help='视频片段长度')
parser.add_argument('--output_path', type=str, default=None, help='输出视频路径，不填则直接显示')
parser.add_argument('--threshold', type=float, default=0.6, help='危险行为检测阈值')
parser.add_argument('--show_fps', action='store_true', help='显示FPS')
parser.add_argument('--enable_alarm', action='store_true', help='启用邮件报警功能')
parser.add_argument('--save_frames', action='store_true', help='保存关键帧图像')
args = parser.parse_args()


def get_model(model_type, num_classes=NUM_CLASSES):
    """获取模型实例"""
    if model_type == 'InfraredActionNet':
        return InfraredActionNet(num_classes=num_classes)
    elif model_type == 'OptimizedInfraredActionNet':
        return OptimizedInfraredActionNet(num_classes=num_classes)
    elif model_type == 'OptimizedActionNetLite':
        return OptimizedActionNetLite(num_classes=num_classes)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")


def load_model(model_path, model_type, device):
    """加载预训练模型"""
    print(f"加载模型 {model_type} 从 {model_path}")
    
    # 获取模型实例
    model = get_model(model_type)
    
    # 加载权重
    if os.path.exists(model_path):
        checkpoint = torch.load(model_path, map_location=device)
        
        # 处理不同格式的checkpoint
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
            
        print(f"成功加载模型权重")
    else:
        print(f"警告: 模型权重文件 {model_path} 不存在，使用随机初始化的模型")
    
    # 将模型移至设备并设置为评估模式
    model = model.to(device)
    model.eval()
    
    return model


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
        
        # 最后一次报警时间
        self.last_red_alert_time = 0
        self.last_yellow_alert_time = 0
        
        # 报警冷却时间（秒）
        self.red_alert_cooldown = 10    # 红色警报冷却时间
        self.yellow_alert_cooldown = 30 # 黄色警报冷却时间
    
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
            
            # 检查危险行为的概率
            danger_prob = sum(avg_probs[i] for i in self.danger_indices)
        else:
            smoothed_prediction = prediction
            smoothed_confidence = confidence
            danger_prob = sum(all_probs[i] for i in self.danger_indices)
        
        # 确定警报级别 - 增强对危险行为的检测能力
        # 如果当前预测类别是危险行为，即使置信度低也考虑为红色警报
        if smoothed_prediction in self.danger_indices and smoothed_confidence > 0.1:  # 阈值降低到 0.1
            alert_level = 'red'  # 危险
        # 如果危险行为的总概率超过阈值
        elif danger_prob > self.threshold * 0.7:  # 降低门槛到阈值的30%
            alert_level = 'red'  # 危险
        # 中等风险行为
        elif smoothed_prediction in [ACTION_CATEGORIES['jogging'], ACTION_CATEGORIES['shakehands'], ACTION_CATEGORIES['embrace']]:
            alert_level = 'yellow'  # 中等
        else:
            alert_level = 'green'  # 正常
        
        action_name = self.action_names[smoothed_prediction]
        
        return action_name, smoothed_confidence, alert_level
    
    
def process_video(video_path, model, output_path=None, show_fps=False, enable_alarm=False, save_frames=False):
    """处理视频文件或摄像头流"""
    # 设置视频源
    if video_path is None:
        print("使用摄像头作为输入源")
        cap = cv2.VideoCapture(0)
    else:
        print(f"处理视频文件: {video_path}")
        cap = cv2.VideoCapture(video_path)
    
    # 检查视频是否成功打开
    if not cap.isOpened():
        print("错误: 无法打开视频源")
        return
    
    # 获取视频信息
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30  # 默认FPS
    
    # 创建输出目录
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # 为保存的帧创建目录
    frames_dir = os.path.join(output_dir, 'frames')
    if save_frames:
        os.makedirs(frames_dir, exist_ok=True)
    
    # 设置输出视频
    if output_path is None:
        # 如果未指定输出路径，则在output目录中创建一个带时间戳的视频文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f'processed_{timestamp}.mp4')
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    print(f"处理后的视频将保存到: {output_path}")
    
    # 创建行为识别器
    recognizer = ActionRecognizer(
        model=model,
        device=args.device,
        clip_len=args.clip_len,
        threshold=args.threshold
    )
    
    frame_count = 0
    start_time = time.time()
    processing_times = []
    
    print("开始处理视频...")
    
    # 主循环
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_start_time = time.time()
        
        # 创建原始帧的副本用于显示
        display_frame = frame.copy()
        
        # 使用改进的人物检测方法
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)  # 直方图均衡化提高对比度
        gray = cv2.GaussianBlur(gray, (5, 5), 0)  # 高斯模糊减少噪声
        
        # 尝试使用更敏感的检测参数
        try:
            # 先尝试常规参数
            people, weights = recognizer.hog.detectMultiScale(
                gray, 
                winStride=(8, 8),
                padding=(16, 16),
                scale=1.05
            )
            
            # 如果没有检测到人物，尝试第二组更敏感的参数
            if len(people) == 0:
                people, weights = recognizer.hog.detectMultiScale(
                    gray, 
                    winStride=(4, 4),  # 更小的步长
                    padding=(8, 8),   # 更小的填充
                    scale=1.02        # 更小的缩放系数，提高检测精度
                )
        except Exception as e:
            print(f"人物检测错误: {str(e)}")
            people = np.array([])
            weights = np.array([])
        
        print(f"检测到 {len(people)} 个人物")
        
        # 如果没有检测到人物，添加默认检测框
        if len(people) == 0:
            print("没有检测到人物，添加默认检测框")
            # 添加默认框（比原来的小很多，更合理的大小）
            h, w = frame.shape[:2]
            # 计算一个更合理的框大小，大约是图片高度的30%
            box_height = int(h * 0.3)
            box_width = int(box_height * 0.5)  # 保持人形的大致宽高比
            
            # 在画面中间偏下位置添加一个框
            center_x = w // 2
            center_y = int(h * 0.6)  # 偏下位置，更符合人物通常出现的位置
            
            # 计算左上角和右下角坐标
            x1 = center_x - box_width // 2
            y1 = center_y - box_height // 2
            x2 = x1 + box_width
            y2 = y1 + box_height
            
            # 绘制默认框，使用青色而不是绿色，便于区分
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 255, 0), 2)  # 黄色框       
        # 更新帧缓冲区
        recognizer.update_buffer(frame)
        
        # 获取预测结果
        action, confidence, alert_level = recognizer.get_prediction()
        
        frame_count += 1
        
        # 计算处理时间
        frame_processing_time = time.time() - frame_start_time
        processing_times.append(frame_processing_time)
        
        # 计算平均FPS
        elapsed_time = time.time() - start_time
        current_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
        
        # 在帧上绘制信息
        if action is not None:
            # 绘制边框，颜色基于警报级别
            color = recognizer.alert_colors[alert_level]
            cv2.rectangle(display_frame, (10, 10), (frame_width - 10, frame_height - 10), color, 2)
            
            # 框选检测到的人物
            for (x, y, w, h) in people:
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                # 在人物框上添加行为标签
                cv2.putText(display_frame, action.upper(), (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # 绘制行为信息
            text = f"{action.upper()}: {confidence:.2f}"
            cv2.putText(display_frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            # 绘制警报级别
            alert_text = f"警报级别: {alert_level.upper()}"
            cv2.putText(display_frame, alert_text, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            # 处理警报 - 红色警报（危险行为）
            if enable_alarm and alert_level == 'red':
                current_time = time.time()
                if current_time - recognizer.last_red_alert_time > recognizer.red_alert_cooldown:
                    # 保存关键帧
                    if save_frames:
                        frame_path = os.path.join(frames_dir, f"danger_{action}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                        cv2.imwrite(frame_path, display_frame)
                        print(f"保存危险行为关键帧: {frame_path}")
                    
                    # 发送报警邮件
                    print(f"检测到危险行为: {action}，发送红色警报...")
                    try:
                        # 确保邮件参数顺序正确
                        if save_frames:
                            # 按照新的 send_red_alert 函数参数顺序传递
                            # action_name, confidence, image_path
                            send_red_alert(action, confidence, frame_path)
                        else:
                            # 如果没有图像路径，不传附件
                            send_red_alert(action, confidence, None)
                    except Exception as e:
                        print(f"发送报警邮件失败: {str(e)}")
                        print("尝试不使用任何附件发送")
                        try:
                            # 简化调用，减少可能的错误
                            send_red_alert(action, confidence, None)
                        except Exception as e2:
                            print(f"再次失败: {str(e2)}")
                    recognizer.last_red_alert_time = current_time
            
            # 处理警报 - 黄色警报（中等风险行为）
            elif enable_alarm and alert_level == 'yellow':
                current_time = time.time()
                if current_time - recognizer.last_yellow_alert_time > recognizer.yellow_alert_cooldown:
                    # 保存关键帧
                    if save_frames:
                        frame_path = os.path.join(frames_dir, f"warning_{action}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                        cv2.imwrite(frame_path, display_frame)
                        print(f"保存警告行为关键帧: {frame_path}")
                    
                    # 发送警告邮件
                    print(f"检测到警告行为: {action}，发送黄色警报...")
                    try:
                        # 按正确参数顺序发送黄色警报
                        if save_frames:
                            send_yellow_alert(action, confidence, frame_path)  # 使用保存的帧路径
                        else:
                            send_yellow_alert(action, confidence, None)
                    except Exception as e:
                        print(f"发送警告邮件失败: {str(e)}")
                        print("尝试不使用任何附件发送")
                        try:
                            send_yellow_alert(action, confidence, None)
                        except Exception as e2:
                            print(f"再次失败: {str(e2)}")
                    recognizer.last_yellow_alert_time = current_time
        
        # 显示FPS信息
        if show_fps:
            fps_text = f"FPS: {current_fps:.2f}"
            cv2.putText(display_frame, fps_text, (frame_width - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 写入输出视频
        out.write(display_frame)
        
        # 显示帧
        cv2.imshow('红外视频行为识别', display_frame)
        
        # 检查退出条件
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # 计算统计信息
    if processing_times:
        avg_processing_time = sum(processing_times) / len(processing_times)
        print(f"平均每帧处理时间: {avg_processing_time*1000:.2f} ms")
        print(f"平均FPS: {1/avg_processing_time:.2f}")
    
    # 释放资源
    cap.release()
    if out is not None:
        out.write(frame)
        out.release()
    cv2.destroyAllWindows()


def main():
    # 加载模型
    model = load_model(args.model_path, args.model_type, args.device)
    
    # 处理视频
    process_video(
        video_path=args.video_path,
        model=model,
        output_path=args.output_path,
        show_fps=args.show_fps,
        enable_alarm=args.enable_alarm,
        save_frames=args.save_frames
    )


if __name__ == "__main__":
    main()
