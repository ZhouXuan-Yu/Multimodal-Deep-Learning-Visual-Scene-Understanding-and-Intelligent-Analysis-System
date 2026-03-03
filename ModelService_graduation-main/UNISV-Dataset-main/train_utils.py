"""
针对RTX 3050优化的训练工具函数
用于支持train_optimized.py中的训练过程
"""

import os
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import _LRScheduler
from config import *


def set_random_seed(seed=42):
    """设置随机种子以确保可重复性"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def get_free_gpu_memory():
    """获取可用的GPU显存(MB)"""
    if not torch.cuda.is_available():
        return 0
    
    torch.cuda.synchronize()
    return torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 - torch.cuda.memory_allocated(0) / 1024 / 1024


class GradualWarmupScheduler(_LRScheduler):
    """
    学习率预热调度器
    先逐渐提高学习率，再使用指定的调度器
    """
    def __init__(self, optimizer, multiplier, warmup_epochs, after_scheduler=None):
        self.multiplier = multiplier
        self.warmup_epochs = warmup_epochs
        self.after_scheduler = after_scheduler
        self.finished = False
        super().__init__(optimizer)
        
    def get_lr(self):
        if self.last_epoch > self.warmup_epochs:
            if self.after_scheduler:
                if not self.finished:
                    self.after_scheduler.base_lrs = [base_lr * self.multiplier for base_lr in self.base_lrs]
                    self.finished = True
                return self.after_scheduler.get_lr()
            return [base_lr * self.multiplier for base_lr in self.base_lrs]
        
        return [base_lr * ((self.multiplier - 1.) * self.last_epoch / self.warmup_epochs + 1.) for base_lr in self.base_lrs]
    
    def step(self, epoch=None):
        if self.finished and self.after_scheduler:
            if epoch is None:
                self.after_scheduler.step(None)
            else:
                self.after_scheduler.step(epoch - self.warmup_epochs)
        else:
            return super(GradualWarmupScheduler, self).step(epoch)


class MaxAccuracyLoss(nn.Module):
    """
    针对提高准确率优化的损失函数
    结合交叉熵损失和自定义加权，特别关注危险行为的识别
    """
    def __init__(self, num_classes=NUM_CLASSES, danger_weight=3.0, smooth_factor=0.1, gamma=2.0):
        super(MaxAccuracyLoss, self).__init__()
        
        # 基础损失函数 - 标签平滑交叉熵
        self.ce_loss = nn.CrossEntropyLoss(reduction='none')
        self.smooth_factor = smooth_factor
        self.num_classes = num_classes
        self.gamma = gamma  # Focal Loss焦点系数
        
        # 危险行为权重
        self.danger_classes = [ACTION_CATEGORIES['pushpeople'], ACTION_CATEGORIES['fight']] 
        self.danger_weight = danger_weight
        
        # 创建类别权重
        self.class_weights = torch.ones(num_classes)
        for danger_class in self.danger_classes:
            self.class_weights[danger_class] = danger_weight
    
    def forward(self, inputs, targets):
        """计算损失
        
        Args:
            inputs: 模型输出 [batch_size, num_classes]
            targets: 真实标签 [batch_size]
        
        Returns:
            loss: 加权损失
        """
        if self.training:
            # 在训练时使用标签平滑
            with torch.no_grad():
                # 为每个标签创建平滑标签
                targets_one_hot = torch.zeros_like(inputs)
                targets_one_hot.scatter_(1, targets.unsqueeze(1), 1)
                targets_smooth = targets_one_hot * (1 - self.smooth_factor) + self.smooth_factor / self.num_classes
            
            # 计算交叉熵损失
            log_probs = torch.nn.functional.log_softmax(inputs, dim=1)
            loss = -(targets_smooth * log_probs).sum(dim=1)
            
            # Focal Loss部分 - 降低易分类样本的权重
            probs = torch.exp(log_probs)
            p_t = torch.gather(probs, 1, targets.unsqueeze(1)).squeeze(1)
            focal_weight = (1 - p_t) ** self.gamma
            
            # 应用Focal权重
            loss = loss * focal_weight
        else:
            # 测试时使用标准交叉熵
            loss = self.ce_loss(inputs, targets)
        
        # 应用危险类别权重
        weights = torch.ones_like(targets, dtype=torch.float)
        
        # 如果是危险类别，增加权重
        for danger_class in self.danger_classes:
            weights = torch.where(targets == danger_class, 
                                 torch.tensor(self.danger_weight, device=targets.device),
                                 weights)
        
        # 最终损失 = 加权平均
        weighted_loss = (loss * weights).mean()
        
        return weighted_loss


class AdaptiveBatchSize:
    """
    基于显存使用情况动态调整批量大小
    """
    def __init__(self, initial_batch_size=4, min_batch_size=1, max_batch_size=16, 
                 memory_threshold=500, scale_factor=0.8):
        self.current_batch_size = initial_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.memory_threshold = memory_threshold  # MB
        self.scale_factor = scale_factor
    
    def update(self, free_memory=None):
        """根据可用显存更新批量大小"""
        if free_memory is None and torch.cuda.is_available():
            free_memory = get_free_gpu_memory()
        elif free_memory is None:
            return self.current_batch_size
        
        if free_memory < self.memory_threshold and self.current_batch_size > self.min_batch_size:
            # 显存不足，减小批量大小
            new_batch_size = max(self.min_batch_size, 
                                int(self.current_batch_size * self.scale_factor))
            if new_batch_size != self.current_batch_size:
                self.current_batch_size = new_batch_size
                return self.current_batch_size, True
        
        elif free_memory > self.memory_threshold * 3 and self.current_batch_size < self.max_batch_size:
            # 显存充足，增加批量大小
            new_batch_size = min(self.max_batch_size, 
                               int(self.current_batch_size / self.scale_factor))
            if new_batch_size != self.current_batch_size:
                self.current_batch_size = new_batch_size
                return self.current_batch_size, True
        
        return self.current_batch_size, False


def freeze_bn(model):
    """冻结BatchNorm层以节省显存"""
    for module in model.modules():
        if isinstance(module, nn.BatchNorm3d):
            module.eval()


def get_optimized_training_config(device, force_cpu=False):
    """
    根据设备性能获取优化的训练配置
    
    Args:
        device: 训练设备('cuda'或'cpu')
        force_cpu: 是否强制使用CPU训练
        
    Returns:
        config: 优化的训练配置字典
    """
    if device == 'cuda' and torch.cuda.is_available() and not force_cpu:
        # GPU配置
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
        
        print(f"检测到GPU: {gpu_name}，显存: {gpu_memory:.2f}GB")
        
        # 针对不同性能的GPU调整配置
        if 'RTX 3050' in gpu_name or ('GTX' in gpu_name and gpu_memory <= 4.5):
            # RTX 3050或其他4GB显存的GPU
            config = {
                'batch_size': 2,  # 小批量大小，减少显存占用
                'grad_accumulation': 8,  # 梯度累积，增大等效批量大小
                'use_amp': True,  # 使用自动混合精度
                'dynamic_batch_size': True,  # 动态调整批量大小
                'optimizer': 'Adam',  # 使用Adam优化器，显存占用较小
                'model_type': 'OptimizedActionNetLite',  # 使用轻量级模型
                'optimizer_kwargs': {'lr': 0.0002, 'weight_decay': 1e-5},
                'warmup_epochs': 3,  # 学习率预热轮数
                'num_epochs': 40,  # 训练轮数
            }
        elif 'RTX' in gpu_name and gpu_memory <= 6.5:
            # 6GB显存的GPU (RTX 2060等)
            config = {
                'batch_size': 4,
                'grad_accumulation': 4,
                'use_amp': True,
                'dynamic_batch_size': True,
                'optimizer': 'AdamW',
                'model_type': 'OptimizedInfraredActionNet',
                'optimizer_kwargs': {'lr': 0.0003, 'weight_decay': 1e-5},
                'warmup_epochs': 2,
                'num_epochs': 35,
            }
        else:
            # 显存充足的高性能GPU
            config = {
                'batch_size': 8,
                'grad_accumulation': 2,
                'use_amp': True,
                'dynamic_batch_size': False,
                'optimizer': 'AdamW',
                'model_type': 'EnsembleOptimizedNet',  # 使用集成模型
                'optimizer_kwargs': {'lr': 0.0005, 'weight_decay': 1e-5},
                'warmup_epochs': 1,
                'num_epochs': 30,
            }
    else:
        # CPU配置
        print("使用CPU训练，性能将显著降低")
        config = {
            'batch_size': 1,
            'grad_accumulation': 16,
            'use_amp': False,  # CPU不支持自动混合精度
            'dynamic_batch_size': False,
            'optimizer': 'Adam',
            'model_type': 'OptimizedActionNetLite',  # 使用轻量级模型
            'optimizer_kwargs': {'lr': 0.0001, 'weight_decay': 1e-6},
            'warmup_epochs': 1,
            'num_epochs': 20,  # 减少训练轮数以加快训练
        }
    
    return config


def create_optimizer(model, config):
    """
    根据配置创建优化器
    
    Args:
        model: 模型
        config: 训练配置字典
        
    Returns:
        optimizer: 优化器
    """
    optim_name = config.get('optimizer', 'AdamW')
    optim_kwargs = config.get('optimizer_kwargs', {'lr': 0.0003, 'weight_decay': 1e-5})
    
    if optim_name == 'AdamW':
        optimizer = optim.AdamW(model.parameters(), **optim_kwargs)
    elif optim_name == 'Adam':
        optimizer = optim.Adam(model.parameters(), **optim_kwargs)
    elif optim_name == 'SGD':
        sgd_kwargs = optim_kwargs.copy()
        sgd_kwargs.setdefault('momentum', 0.9)
        optimizer = optim.SGD(model.parameters(), **sgd_kwargs)
    else:
        # 默认使用Adam
        optimizer = optim.Adam(model.parameters(), **optim_kwargs)
    
    return optimizer


def create_scheduler(optimizer, config, train_loader_len):
    """
    创建学习率调度器
    
    Args:
        optimizer: 优化器
        config: 训练配置字典
        train_loader_len: 训练数据加载器长度
        
    Returns:
        scheduler: 学习率调度器
    """
    scheduler_name = config.get('scheduler', 'OneCycleLR')
    num_epochs = config.get('num_epochs', 30)
    warmup_epochs = config.get('warmup_epochs', 0)
    
    if scheduler_name == 'OneCycleLR':
        # 一周期学习率
        steps_per_epoch = train_loader_len // config.get('grad_accumulation', 1)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=optimizer.param_groups[0]['lr'] * 10,
            steps_per_epoch=steps_per_epoch,
            epochs=num_epochs,
            pct_start=0.3,
            div_factor=25,
            final_div_factor=1000
        )
    elif scheduler_name == 'CosineAnnealingLR':
        # 余弦退火学习率
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=num_epochs,
            eta_min=optimizer.param_groups[0]['lr'] / 100
        )
    else:
        # 默认使用余弦退火
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=num_epochs,
            eta_min=optimizer.param_groups[0]['lr'] / 100
        )
    
    # 添加预热
    if warmup_epochs > 0:
        scheduler = GradualWarmupScheduler(
            optimizer,
            multiplier=1.0,
            warmup_epochs=warmup_epochs,
            after_scheduler=scheduler
        )
    
    return scheduler
