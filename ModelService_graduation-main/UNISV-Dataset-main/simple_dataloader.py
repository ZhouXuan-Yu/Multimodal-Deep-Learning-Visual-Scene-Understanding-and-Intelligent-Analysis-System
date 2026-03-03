"""
简化版数据加载器，避免依赖复杂的第三方库
专注于红外视频危险行为（推人和打架）识别的准确率提升
"""

import os
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import random
from sklearn.model_selection import train_test_split
import glob
from config import *

# 定义危险行为类别索引常量
DANGER_ACTIONS = ['pushpeople', 'fight']

def get_video_files(data_root):
    """获取所有视频文件路径和对应标签"""
    video_paths = []
    labels = []
    
    # 数据组织方式为：data_root/action_category/video_files
    print(f"搜索视频文件，数据根目录: {data_root}")
    
    # 检查目录是否存在
    if not os.path.exists(data_root):
        print(f"警告: 数据目录 {data_root} 不存在!")
        return video_paths, labels
    
    # 排除这些非行为目录
    excluded_dirs = ['checkpoints', 'logs', '__pycache__']
    
    # 列出所有行为类别目录（排除非行为目录）
    action_dirs = [d for d in os.listdir(data_root) 
                  if os.path.isdir(os.path.join(data_root, d)) and d not in excluded_dirs]
    print(f"找到的行为类别目录: {action_dirs}")
    
    # 从配置创建反向映射（小写类别名称 -> 类别ID）
    lowercase_to_id = {k.lower(): v for k, v in ACTION_CATEGORIES.items()}
    
    # 为每个行为类别分配一个ID
    action_to_id = {}
    for action_name in action_dirs:
        # 将目录名称转换为小写，匹配配置中的类别名称
        lower_name = action_name.lower()
        # 检查是否在预定义的类别中
        if lower_name in lowercase_to_id:
            action_to_id[action_name] = lowercase_to_id[lower_name]
        else:
            # 如果不在预定义类别中，分配新ID
            action_to_id[action_name] = len(action_to_id)
        
    print(f"行为类别与ID映射: {action_to_id}")
    
    # 遍历每个行为类别目录，获取视频文件
    for action_name in action_dirs:
        action_dir = os.path.join(data_root, action_name)
        action_id = action_to_id[action_name]
        
        # 获取所有视频文件
        video_files = []
        for ext in ['*.mp4', '*.avi', '*.mkv', '*.mov']:
            video_files.extend(glob.glob(os.path.join(action_dir, '**', ext), recursive=True))
        
        # 添加到总列表
        for video_file in video_files:
            video_paths.append(video_file)
            labels.append(action_id)
        
        print(f"行为 '{action_name}' (ID: {action_id}): 找到 {len(video_files)} 个视频文件")
    
    return video_paths, labels


def split_dataset(video_paths, labels):
    """划分训练、验证和测试集，确保危险行为在每个集合中都有足够样本"""
    # 先分离出危险行为样本
    danger_paths = []
    danger_labels = []
    normal_paths = []
    normal_labels = []
    
    # 危险行为（推人和打架）的类别ID
    danger_ids = [ACTION_CATEGORIES[action.lower()] for action in DANGER_ACTIONS]
    
    # 分离危险行为和普通行为
    for path, label in zip(video_paths, labels):
        if label in danger_ids:
            danger_paths.append(path)
            danger_labels.append(label)
        else:
            normal_paths.append(path)
            normal_labels.append(label)
    
    # 分割危险行为数据 - 使用较多比例用于测试，提高泛化能力
    d_train_paths, d_temp_paths, d_train_labels, d_temp_labels = train_test_split(
        danger_paths, danger_labels, test_size=VAL_SPLIT + TEST_SPLIT, random_state=42, stratify=danger_labels
    )
    d_val_paths, d_test_paths, d_val_labels, d_test_labels = train_test_split(
        d_temp_paths, d_temp_labels, test_size=TEST_SPLIT/(VAL_SPLIT + TEST_SPLIT), random_state=42, stratify=d_temp_labels
    )
    
    # 分割普通行为数据
    n_train_paths, n_temp_paths, n_train_labels, n_temp_labels = train_test_split(
        normal_paths, normal_labels, test_size=VAL_SPLIT + TEST_SPLIT, random_state=42, stratify=normal_labels
    )
    n_val_paths, n_test_paths, n_val_labels, n_test_labels = train_test_split(
        n_temp_paths, n_temp_labels, test_size=TEST_SPLIT/(VAL_SPLIT + TEST_SPLIT), random_state=42, stratify=n_temp_labels
    )
    
    # 合并数据
    train_paths = d_train_paths + n_train_paths
    train_labels = d_train_labels + n_train_labels
    val_paths = d_val_paths + n_val_paths
    val_labels = d_val_labels + n_val_labels
    test_paths = d_test_paths + n_test_paths
    test_labels = d_test_labels + n_test_labels
    
    # 打乱顺序
    train_data = list(zip(train_paths, train_labels))
    val_data = list(zip(val_paths, val_labels))
    test_data = list(zip(test_paths, test_labels))
    
    random.shuffle(train_data)
    random.shuffle(val_data)
    random.shuffle(test_data)
    
    train_paths, train_labels = zip(*train_data)
    val_paths, val_labels = zip(*val_data)
    test_paths, test_labels = zip(*test_data)
    
    return {
        'train': (train_paths, train_labels),
        'val': (val_paths, val_labels),
        'test': (test_paths, test_labels)
    }


class SimpleInfraredDataset(Dataset):
    """简化的红外视频数据集类，专注于危险行为识别"""
    def __init__(self, video_paths, labels, mode='train'):
        self.video_paths = video_paths
        self.labels = labels
        self.mode = mode
        
        # 定义危险行为ID
        self.danger_ids = [ACTION_CATEGORIES[action.lower()] for action in DANGER_ACTIONS]
    
    def __len__(self):
        return len(self.video_paths)
    
    def __getitem__(self, idx):
        video_path = self.video_paths[idx]
        label = self.labels[idx]
        
        # 加载视频帧
        frames = self.load_video(video_path)
        
        # 确保帧数满足要求
        if len(frames) < CLIP_LENGTH:
            # 通过循环复制帧补充
            frames = self.pad_frames(frames, CLIP_LENGTH)
        elif len(frames) > CLIP_LENGTH:
            # 如果帧太多，则均匀采样
            frames = self.sample_frames(frames, CLIP_LENGTH)
        
        # 数据增强和预处理
        processed_frames = self.preprocess_frames(frames, is_danger=(label in self.danger_ids))
        
        # 转换为PyTorch张量，格式为 [C, T, H, W]
        video_tensor = torch.FloatTensor(processed_frames)
        label_tensor = torch.LongTensor([label])[0]  # 单个标签
        
        return video_tensor, label_tensor
    
    def load_video(self, video_path):
        """加载视频帧"""
        frames = []
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"无法打开视频: {video_path}")
            # 返回一个空帧序列，会在后续被补充
            return frames
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 转换为灰度图像（红外视频通常是单通道）
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # 转回3通道以兼容模型输入
                frame = np.stack([gray, gray, gray], axis=2)
            
            frames.append(frame)
        
        cap.release()
        return frames
    
    def pad_frames(self, frames, target_length):
        """通过循环复制帧来补充至指定长度"""
        if len(frames) == 0:
            # 如果没有帧，创建一个全零帧
            empty_frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
            frames = [empty_frame]
        
        # 不断循环添加帧，直到达到目标长度
        while len(frames) < target_length:
            frames.append(frames[len(frames) % len(frames)])
            
        return frames
    
    def sample_frames(self, frames, target_length):
        """均匀采样指定数量的帧"""
        # 计算采样间隔
        indices = np.linspace(0, len(frames) - 1, target_length, dtype=int)
        sampled_frames = [frames[i] for i in indices]
        return sampled_frames
    
    def preprocess_frames(self, frames, is_danger=False):
        """
        预处理视频帧
        对危险行为样本进行更强的数据增强以提高准确率
        """
        processed_frames = []
        
        for frame in frames:
            # 调整大小
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            
            # 数据增强 - 仅在训练模式下进行
            if self.mode == 'train':
                # 水平翻转
                if random.random() < RANDOM_FLIP_PROB:
                    frame = cv2.flip(frame, 1)
                
                # 随机亮度和对比度调整
                if random.random() < 0.5:
                    alpha = 1.0 + random.uniform(-BRIGHTNESS_CONTRAST_ADJUSTMENT, BRIGHTNESS_CONTRAST_ADJUSTMENT)
                    beta = random.uniform(-BRIGHTNESS_CONTRAST_ADJUSTMENT * 10, BRIGHTNESS_CONTRAST_ADJUSTMENT * 10)
                    frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
                
                # 随机噪声 - 对危险行为样本增加更多噪声以提高鲁棒性
                if random.random() < 0.3:
                    noise_level = NOISE_LEVEL * (1.5 if is_danger else 1.0)
                    noise = np.random.normal(0, noise_level * 255, frame.shape).astype(np.int16)
                    frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                # 对危险行为样本进行额外处理 - 增强时间差异
                if is_danger and random.random() < 0.5:
                    # 随机调整部分区域的亮度，模拟动作焦点
                    h, w = frame.shape[:2]
                    center_x, center_y = random.randint(w//4, 3*w//4), random.randint(h//4, 3*h//4)
                    radius = random.randint(min(h, w)//8, min(h, w)//4)
                    
                    # 创建圆形掩码
                    y, x = np.ogrid[-center_y:h-center_y, -center_x:w-center_x]
                    mask = x*x + y*y <= radius*radius
                    
                    # 增强区域
                    frame_enhanced = frame.copy()
                    frame_enhanced[mask] = np.clip(frame_enhanced[mask] * 1.3, 0, 255).astype(np.uint8)
                    frame = frame_enhanced
            
            # 归一化
            frame = frame.astype(np.float32) / 255.0
            
            # 标准化 (使用ImageNet均值和标准差)
            mean = np.array([0.45, 0.45, 0.45])
            std = np.array([0.225, 0.225, 0.225])
            frame = (frame - mean) / std
            
            # 转置为 [C, H, W] 格式
            frame = np.transpose(frame, (2, 0, 1))
            
            processed_frames.append(frame)
        
        # 将帧列表转换为 [C, T, H, W] 格式的numpy数组
        processed_frames = np.array(processed_frames)
        processed_frames = np.transpose(processed_frames, (1, 0, 2, 3))
        
        return processed_frames


def get_simple_dataloaders(batch_size=None, num_workers=2):
    """创建简化的数据加载器，更加关注危险行为样本
    
    Args:
        batch_size: 可选的批量大小，如果不指定则使用配置文件中的BATCH_SIZE
        num_workers: 数据加载器使用的工作线程数
    """
    # 使用传入的batch_size或使用默认值
    if batch_size is None:
        batch_size = BATCH_SIZE
    print(f"数据加载器使用批量大小: {batch_size}")
    
    # 获取所有视频文件和标签
    video_paths, labels = get_video_files(DATA_ROOT)
    
    # 划分数据集 - 确保危险行为在每个集合中都有足够样本
    split_data = split_dataset(video_paths, labels)
    
    # 创建数据集 - 使用简化的数据集类
    train_dataset = SimpleInfraredDataset(
        split_data['train'][0], split_data['train'][1], mode='train'
    )
    val_dataset = SimpleInfraredDataset(
        split_data['val'][0], split_data['val'][1], mode='val'
    )
    test_dataset = SimpleInfraredDataset(
        split_data['test'][0], split_data['test'][1], mode='test'
    )
    
    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, 
        num_workers=num_workers, pin_memory=True  # 减少工作线程以降低内存占用
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False, 
        num_workers=num_workers, pin_memory=True
    )
    test_loader = DataLoader(
        test_dataset, batch_size=batch_size, shuffle=False, 
        num_workers=num_workers, pin_memory=True
    )
    
    return train_loader, val_loader, test_loader


if __name__ == "__main__":
    # 测试数据加载
    train_loader, val_loader, test_loader = get_simple_dataloaders()
    print(f"训练集大小: {len(train_loader.dataset)}")
    print(f"验证集大小: {len(val_loader.dataset)}")
    print(f"测试集大小: {len(test_loader.dataset)}")
    
    # 统计危险行为样本比例
    danger_ids = [ACTION_CATEGORIES[action.lower()] for action in DANGER_ACTIONS]
    danger_count = sum(1 for _, label in train_loader.dataset if label.item() in danger_ids)
    print(f"训练集中危险行为样本比例: {danger_count/len(train_loader.dataset)*100:.2f}%")
    
    # 检查一个批次的数据形状
    for inputs, labels in train_loader:
        print(f"批次输入形状: {inputs.shape}")  # 应为 [batch_size, channels, time, height, width]
        print(f"批次标签形状: {labels.shape}")  # 应为 [batch_size]
        print(f"批次标签: {labels}")
        break
