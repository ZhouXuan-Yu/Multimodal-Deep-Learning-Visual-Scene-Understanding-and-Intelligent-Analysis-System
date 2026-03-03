"""
数据加载器模块，负责加载和预处理红外视频数据
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
import albumentations as A
from albumentations.pytorch import ToTensorV2


def get_video_files(data_root):
    """获取所有视频文件路径和对应标签"""
    video_paths = []
    labels = []
    
    # 数据组织方式为：data_root/action_category/video_files
    # 打印一下当前目录结构，帮助调试
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
            print(f"警告: 未知行为类别 '{action_name}'，将被跳过")
    
    print(f"行为类别与ID映射: {action_to_id}")
    
    # 遍历每个行为类别目录
    for action in action_dirs:
        # 跳过未知类别
        if action not in action_to_id:
            continue
            
        action_dir = os.path.join(data_root, action)
        class_id = action_to_id[action]
        
        # 查找该目录下的所有视频文件
        video_files = glob.glob(os.path.join(action_dir, '*.mp4')) + \
                      glob.glob(os.path.join(action_dir, '*.avi'))
        
        print(f"行为 '{action}' (ID: {class_id}): 找到 {len(video_files)} 个视频文件")
        
        video_paths.extend(video_files)
        labels.extend([class_id] * len(video_files))
    
    return video_paths, labels


def split_dataset(video_paths, labels):
    """划分训练、验证和测试集"""
    # 先划分训练集和临时集
    train_paths, temp_paths, train_labels, temp_labels = train_test_split(
        video_paths, labels, test_size=(VAL_SPLIT + TEST_SPLIT), 
        random_state=42, stratify=labels
    )
    
    # 再将临时集划分为验证集和测试集
    val_paths, test_paths, val_labels, test_labels = train_test_split(
        temp_paths, temp_labels, 
        test_size=TEST_SPLIT/(VAL_SPLIT + TEST_SPLIT), 
        random_state=42, stratify=temp_labels
    )
    
    return {
        'train': (train_paths, train_labels),
        'val': (val_paths, val_labels),
        'test': (test_paths, test_labels)
    }


class InfraredActionDataset(Dataset):
    """红外行为数据集"""
    
    def __init__(self, video_paths, labels, mode='train'):
        self.video_paths = video_paths
        self.labels = labels
        self.mode = mode
        
        # 设置不同模式的数据增强
        if self.mode == 'train' and USE_AUGMENTATION:
            self.transform = A.Compose([
                A.RandomResizedCrop(height=FRAME_HEIGHT, width=FRAME_WIDTH),
                A.HorizontalFlip(p=RANDOM_FLIP_PROB),
                A.RandomBrightnessContrast(
                    brightness_limit=BRIGHTNESS_CONTRAST_ADJUSTMENT,
                    contrast_limit=BRIGHTNESS_CONTRAST_ADJUSTMENT,
                    p=0.5
                ),
                # 为新版本适配高斯噪声参数
                A.GaussNoise(sigma_limit=(0, NOISE_LEVEL * 25), p=0.3),
                A.Normalize(mean=[0.45], std=[0.225]),  # 灰度图像归一化
                ToTensorV2()
            ])
        else:
            self.transform = A.Compose([
                A.Resize(height=FRAME_HEIGHT, width=FRAME_WIDTH),
                A.Normalize(mean=[0.45], std=[0.225]),
                ToTensorV2()
            ])
    
    def __len__(self):
        return len(self.video_paths)
    
    def __getitem__(self, idx):
        video_path = self.video_paths[idx]
        label = self.labels[idx]
        
        # 加载视频
        frames = self.load_video(video_path)
        
        # 如果帧数不足，使用循环填充
        if len(frames) < CLIP_LENGTH:
            frames = self.pad_frames(frames, CLIP_LENGTH)
        # 如果帧数过多，随机选择连续片段或均匀采样
        elif len(frames) > CLIP_LENGTH:
            frames = self.sample_frames(frames, CLIP_LENGTH)
            
        # 应用变换
        transformed_frames = []
        for frame in frames:
            # 确保灰度图转为3通道，因为部分预训练模型需要3通道输入
            if len(frame.shape) == 2 or frame.shape[2] == 1:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            
            # 对每一帧应用变换
            transformed = self.transform(image=frame)
            transformed_frames.append(transformed["image"])
            
        # 整合为单个张量 [C, T, H, W]
        video_tensor = torch.stack(transformed_frames, dim=1)
        
        return video_tensor, label
        
    def load_video(self, video_path):
        """加载视频文件的所有帧"""
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 红外视频通常是灰度的，但确保灰度处理
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # 转回3通道供可视化和部分模型使用
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            
            frames.append(frame)
            
        cap.release()
        return frames
    
    def pad_frames(self, frames, target_length):
        """通过循环补充帧数"""
        padded_frames = frames.copy()
        while len(padded_frames) < target_length:
            padded_frames.extend(frames)
        return padded_frames[:target_length]
    
    def sample_frames(self, frames, target_length):
        """从视频中采样指定数量的帧"""
        if self.mode == 'train':
            # 训练模式：随机选择连续片段
            max_start_idx = len(frames) - target_length
            start_idx = random.randint(0, max_start_idx)
            sampled_frames = frames[start_idx:start_idx + target_length]
        else:
            # 验证/测试模式：均匀采样
            indices = np.linspace(0, len(frames) - 1, target_length, dtype=int)
            sampled_frames = [frames[i] for i in indices]
            
        return sampled_frames


def get_dataloaders():
    """创建训练、验证和测试数据加载器"""
    # 获取所有视频文件和标签
    video_paths, labels = get_video_files(DATA_ROOT)
    
    # 划分数据集
    split_data = split_dataset(video_paths, labels)
    
    # 创建数据集
    train_dataset = InfraredActionDataset(
        split_data['train'][0], split_data['train'][1], mode='train'
    )
    val_dataset = InfraredActionDataset(
        split_data['val'][0], split_data['val'][1], mode='val'
    )
    test_dataset = InfraredActionDataset(
        split_data['test'][0], split_data['test'][1], mode='test'
    )
    
    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True, 
        num_workers=4, pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, batch_size=BATCH_SIZE, shuffle=False, 
        num_workers=4, pin_memory=True
    )
    test_loader = DataLoader(
        test_dataset, batch_size=BATCH_SIZE, shuffle=False, 
        num_workers=4, pin_memory=True
    )
    
    return train_loader, val_loader, test_loader


# 用于测试数据集加载的辅助函数
def visualize_batch(dataloader, num_samples=4):
    """可视化一个batch的数据"""
    import matplotlib.pyplot as plt
    
    # 获取一个batch
    images, labels = next(iter(dataloader))
    batch_size = min(images.size(0), num_samples)
    
    # 设置图表
    fig, axes = plt.subplots(batch_size, CLIP_LENGTH//4, figsize=(15, 3*batch_size))
    
    for i in range(batch_size):
        for j in range(CLIP_LENGTH//4):
            frame_idx = j * 4  # 每隔4帧显示一帧
            # 将张量转换回numpy数组并恢复正常范围
            frame = images[i, :, frame_idx].permute(1, 2, 0).numpy()
            frame = (frame * 0.225 + 0.45) * 255  # 反归一化
            frame = frame.astype(np.uint8)
            
            # 在灰度模式下显示
            if batch_size > 1:
                axes[i, j].imshow(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), cmap='gray')
                axes[i, j].set_title(f"Sample {i}, Frame {frame_idx}")
                axes[i, j].axis('off')
            else:
                axes[j].imshow(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), cmap='gray')
                axes[j].set_title(f"Sample {i}, Frame {frame_idx}")
                axes[j].axis('off')
    
    plt.tight_layout()
    plt.savefig('batch_visualization.png')
    plt.close()
    
    print(f"Batch visualization saved! Labels: {[list(ACTION_CATEGORIES.keys())[l] for l in labels[:batch_size].numpy()]}")

if __name__ == "__main__":
    # 测试数据加载
    train_loader, val_loader, test_loader = get_dataloaders()
    print(f"训练集大小: {len(train_loader.dataset)}")
    print(f"验证集大小: {len(val_loader.dataset)}")
    print(f"测试集大小: {len(test_loader.dataset)}")
    
    # 可视化一个batch
    visualize_batch(train_loader)
