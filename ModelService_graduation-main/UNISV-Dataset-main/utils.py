"""
工具函数模块，包含各种辅助功能
"""

import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.utils import make_grid
import matplotlib.pyplot as plt
from config import *
import cv2


class EarlyStopping:
    """早停机制，防止过拟合"""
    
    def __init__(self, patience=EARLY_STOPPING_PATIENCE, verbose=False, delta=0, path='checkpoint.pth'):
        """
        Args:
            patience (int): 验证集损失在多少个epoch没有改善后，训练停止
            verbose (bool): 是否打印早停信息
            delta (float): 表示改善的最小值，小于这个值认为没有显著改善
            path (str): 模型保存路径
        """
        self.patience = patience
        self.verbose = verbose
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        self.val_loss_min = np.Inf
        self.delta = delta
        self.path = path

    def __call__(self, val_loss, model):
        score = -val_loss

        if self.best_score is None:
            self.best_score = score
            self.save_checkpoint(val_loss, model)
        elif score < self.best_score + self.delta:
            self.counter += 1
            if self.verbose:
                print(f'EarlyStopping counter: {self.counter} out of {self.patience}')
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.save_checkpoint(val_loss, model)
            self.counter = 0

    def save_checkpoint(self, val_loss, model):
        """保存模型"""
        if self.verbose:
            print(f'Validation loss decreased ({self.val_loss_min:.6f} --> {val_loss:.6f}). Saving model...')
        torch.save(model.state_dict(), self.path)
        self.val_loss_min = val_loss


class LabelSmoothingLoss(nn.Module):
    """标签平滑损失函数，提高模型泛化能力"""
    
    def __init__(self, num_classes, smoothing=0.1):
        super(LabelSmoothingLoss, self).__init__()
        self.confidence = 1.0 - smoothing
        self.smoothing = smoothing
        self.num_classes = num_classes

    def forward(self, pred, target):
        """
        Args:
            pred: 预测结果，shape [B, C]
            target: 目标标签，shape [B]
        """
        pred = pred.log_softmax(dim=-1)
        
        with torch.no_grad():
            # 创建平滑标签
            true_dist = torch.zeros_like(pred)
            true_dist.fill_(self.smoothing / (self.num_classes - 1))
            true_dist.scatter_(1, target.data.unsqueeze(1), self.confidence)
        
        return torch.mean(torch.sum(-true_dist * pred, dim=-1))


class FocalLoss(nn.Module):
    """Focal Loss，用于解决类别不平衡问题"""
    
    def __init__(self, gamma=2.0, alpha=None, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.gamma = gamma
        self.alpha = alpha
        self.reduction = reduction

    def forward(self, input, target):
        ce_loss = F.cross_entropy(input, target, reduction='none')
        pt = torch.exp(-ce_loss)
        loss = (1 - pt) ** self.gamma * ce_loss

        if self.alpha is not None:
            alpha_t = self.alpha[target]
            loss = alpha_t * loss

        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss


class TemporalSmoothing:
    """时序平滑类，用于稳定视频预测结果"""
    
    def __init__(self, window_size=TEMPORAL_WINDOW_SIZE, alpha=0.7):
        """
        Args:
            window_size (int): 滑动窗口大小
            alpha (float): 平滑系数，值越大越平滑
        """
        self.window_size = window_size
        self.alpha = alpha
        self.history = []

    def update(self, prediction):
        """
        更新预测历史并返回平滑后的预测结果
        
        Args:
            prediction: 当前帧的预测结果
            
        Returns:
            平滑后的预测结果
        """
        # 添加当前预测到历史记录
        self.history.append(prediction)
        
        # 保持历史记录不超过窗口大小
        if len(self.history) > self.window_size:
            self.history.pop(0)
        
        # 指数加权移动平均
        smoothed = np.copy(prediction)
        
        if len(self.history) > 1:
            for i in range(len(self.history) - 1):
                weight = self.alpha ** (len(self.history) - 1 - i)
                smoothed = (1 - weight) * smoothed + weight * self.history[i]
        
        return smoothed


def apply_alert_box(frame, detection, alert_level):
    """
    在帧上应用警报框
    
    Args:
        frame: 输入视频帧
        detection: 检测框 [x1, y1, x2, y2]
        alert_level: 警报级别 ('red', 'yellow', 'green')
        
    Returns:
        添加了警报框的帧
    """
    # 获取警报颜色
    color = ALERT_COLORS[alert_level]
    
    # 解包检测框坐标
    x1, y1, x2, y2 = detection
    
    # 绘制边界框
    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
    
    # 对于红色和黄色警报，添加文本标签
    if alert_level == 'red':
        text = 'DANGER'
        # 添加半透明的红色背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (int(x1), int(y1)-25), (int(x1)+80, int(y1)), color, -1)
        # 添加文本
        cv2.putText(overlay, text, (int(x1)+5, int(y1)-7), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        # 混合原始帧和半透明overlay
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
    elif alert_level == 'yellow':
        text = 'WARNING'
        # 添加半透明的黄色背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (int(x1), int(y1)-25), (int(x1)+100, int(y1)), color, -1)
        # 添加文本
        cv2.putText(overlay, text, (int(x1)+5, int(y1)-7), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        # 混合原始帧和半透明overlay
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    return frame


def create_alert_overlay(frame, alert_level, action_name):
    """
    创建全屏警报覆盖层
    
    Args:
        frame: 输入视频帧
        alert_level: 警报级别 ('red', 'yellow', 'green')
        action_name: 检测到的行为名称
        
    Returns:
        添加了警报覆盖层的帧
    """
    height, width = frame.shape[:2]
    overlay = frame.copy()
    
    if alert_level == 'red':
        # 红色边框
        cv2.rectangle(frame, (10, 10), (width-10, height-10), ALERT_COLORS['red'], 10)
        # 顶部警报条
        cv2.rectangle(overlay, (0, 0), (width, 60), ALERT_COLORS['red'], -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        # 添加警报文本
        cv2.putText(frame, f"DANGER! {action_name.upper()} DETECTED", (width//2-200, 40), 
                   cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
        
    elif alert_level == 'yellow':
        # 黄色边框
        cv2.rectangle(frame, (10, 10), (width-10, height-10), ALERT_COLORS['yellow'], 5)
        # 顶部警告条
        cv2.rectangle(overlay, (0, 0), (width, 50), ALERT_COLORS['yellow'], -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        # 添加警告文本
        cv2.putText(frame, f"WARNING: {action_name.upper()} DETECTED", (width//2-200, 35), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 0), 2)
    
    return frame


def show_confirm_dialog(frame, action_name):
    """
    显示确认对话框，询问是否加强管理
    
    Args:
        frame: 输入视频帧
        action_name: 检测到的行为名称
        
    Returns:
        添加了确认对话框的帧
    """
    height, width = frame.shape[:2]
    
    # 对话框区域
    dialog_width, dialog_height = 400, 150
    x1 = (width - dialog_width) // 2
    y1 = (height - dialog_height) // 2
    x2 = x1 + dialog_width
    y2 = y1 + dialog_height
    
    # 绘制半透明背景
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (240, 240, 240), -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
    
    # 绘制对话框边框
    cv2.rectangle(frame, (x1, y1), (x2, y2), (70, 70, 70), 2)
    
    # 添加标题和内容文本
    cv2.putText(frame, f"{action_name.capitalize()} 行为已检测", 
               (x1 + 20, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(frame, "是否需要加强管理?", 
               (x1 + 20, y1 + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # 添加按钮
    button_width, button_height = 80, 40
    
    # "是"按钮
    yes_x1 = x1 + 50
    yes_y1 = y2 - 60
    yes_x2 = yes_x1 + button_width
    yes_y2 = yes_y1 + button_height
    cv2.rectangle(frame, (yes_x1, yes_y1), (yes_x2, yes_y2), (0, 120, 0), -1)
    cv2.putText(frame, "是", (yes_x1 + 30, yes_y1 + 25), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    # "否"按钮
    no_x1 = x2 - 50 - button_width
    no_y1 = y2 - 60
    no_x2 = no_x1 + button_width
    no_y2 = no_y1 + button_height
    cv2.rectangle(frame, (no_x1, no_y1), (no_x2, no_y2), (0, 0, 120), -1)
    cv2.putText(frame, "否", (no_x1 + 30, no_y1 + 25), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return frame


def draw_action_label(frame, action_name, confidence, alert_level):
    """
    在帧上绘制行为标签和置信度
    
    Args:
        frame: 输入视频帧
        action_name: 行为名称
        confidence: 置信度
        alert_level: 警报级别
        
    Returns:
        带有标签的帧
    """
    height, width = frame.shape[:2]
    
    # 确定文本颜色
    if alert_level == 'red':
        color = (0, 0, 255)  # 红色
    elif alert_level == 'yellow':
        color = (0, 255, 255)  # 黄色
    else:
        color = (0, 255, 0)  # 绿色
    
    # 添加行为标签和置信度
    text = f"{action_name.capitalize()}: {confidence:.2f}"
    cv2.putText(frame, text, (10, height - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    return frame


def get_bounding_boxes(frame, model, device, tracker=None):
    """
    获取视频帧中的行为边界框
    
    Args:
        frame: 输入视频帧
        model: 行为识别模型
        device: 设备（CPU/GPU）
        tracker: 可选，目标跟踪器
        
    Returns:
        边界框列表，每个元素为 [x1, y1, x2, y2, class_id, confidence]
    """
    # 这里应该实现行为检测和定位的逻辑
    # 由于行为检测需要视频序列，而不仅仅是单帧，此函数需要维护一个帧缓冲区
    
    # 简单实现：假设整个帧是一个边界框
    height, width = frame.shape[:2]
    
    # 模拟检测结果
    box = [0, 0, width, height, 0, 0.95]  # 示例：整个帧为类别0的目标，置信度0.95
    
    return [box]
