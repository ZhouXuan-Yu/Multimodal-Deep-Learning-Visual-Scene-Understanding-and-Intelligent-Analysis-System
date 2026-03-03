"""
针对RTX 3050 4GB显存优化的红外视频行为识别模型
特别专注于推人和打架等危险行为的高精度识别
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import math
from config import *
import torch.amp as torch_amp

class EfficientAttention(nn.Module):
    """
    高效注意力机制，显著降低显存占用同时提高模型性能
    """
    def __init__(self, in_channels, reduction_ratio=8):
        super(EfficientAttention, self).__init__()
        self.in_channels = in_channels
        self.reduced_channels = max(in_channels // reduction_ratio, 32)
        
        # 特征降维以减少计算成本
        self.q_conv = nn.Conv3d(in_channels, self.reduced_channels, kernel_size=1, bias=False)
        self.k_conv = nn.Conv3d(in_channels, self.reduced_channels, kernel_size=1, bias=False)
        self.v_conv = nn.Conv3d(in_channels, self.reduced_channels, kernel_size=1, bias=False)
        
        # 输出投影
        self.output_conv = nn.Conv3d(self.reduced_channels, in_channels, kernel_size=1, bias=False)
        
        # 初始化
        for m in self.modules():
            if isinstance(m, nn.Conv3d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                
    def forward(self, x):
        # 原始输入形状: [B, C, T, H, W]
        batch_size, _, t, h, w = x.shape
        
        # 查询、键、值投影
        q = self.q_conv(x)  # [B, C', T, H, W]
        k = self.k_conv(x)  # [B, C', T, H, W]
        v = self.v_conv(x)  # [B, C', T, H, W]
        
        # 记录原始形状用于重塑
        
        # 重塑形状用于高效注意力计算
        q = q.reshape(batch_size, self.reduced_channels, -1)  # [B, C', T*H*W]
        k = k.reshape(batch_size, self.reduced_channels, -1)  # [B, C', T*H*W]
        v = v.reshape(batch_size, self.reduced_channels, -1)  # [B, C', T*H*W]
        
        # 确保k的形状与q的permute后形状兼容 
        # q_perm将是[B, T*H*W, C']，所以k需要是[B, C', T*H*W]
        # 注意：我们不再转置k，而是在bmm操作中调整
        
        # 计算注意力图 - 修正了bmm操作以确保维度匹配
        q_perm = q.permute(0, 2, 1)  # [B, T*H*W, C']
        attn = torch.bmm(q_perm, k)  # [B, T*H*W, T*H*W]  
        attn = F.softmax(attn / math.sqrt(self.reduced_channels), dim=2)
        
        # 应用注意力权重，这里需要调整形状以适配矩阵乘法
        # attn形状为[B, T*H*W, T*H*W]  
        # 我们需要将其转置为[B, T*H*W, T*H*W]的转置，但其实这里已经是正确形状
        attn_adj = attn.permute(0, 2, 1)  # [B, T*H*W, T*H*W] -> [B, T*H*W, T*H*W]
        out = torch.bmm(v, attn_adj)  # [B, C', T*H*W]
        
        # 重塑回原始形状
        out = out.reshape(batch_size, self.reduced_channels, t, h, w)
        
        # 投影回原始通道数
        out = self.output_conv(out)
        
        # 残差连接
        return x + out


class MemoryEfficientBlock(nn.Module):
    """
    显存高效的残差块，使用分组卷积和深度可分离卷积降低参数量和计算量
    """
    def __init__(self, in_channels, out_channels, stride=1, groups=8, reduction_ratio=4):
        super(MemoryEfficientBlock, self).__init__()
        
        # 使用组卷积降低参数量
        self.conv1 = nn.Conv3d(in_channels, in_channels, kernel_size=(1, 3, 3),
                             stride=(1, stride, stride), padding=(0, 1, 1), 
                             groups=groups, bias=False)
        self.bn1 = nn.BatchNorm3d(in_channels)
        
        # 时序卷积
        self.conv2 = nn.Conv3d(in_channels, in_channels, kernel_size=(3, 1, 1),
                             stride=(1, 1, 1), padding=(1, 0, 0), 
                             groups=groups, bias=False)
        self.bn2 = nn.BatchNorm3d(in_channels)
        
        # 通道注意力
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool3d((1, 1, 1)),
            nn.Conv3d(in_channels, in_channels // reduction_ratio, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv3d(in_channels // reduction_ratio, in_channels, kernel_size=1),
            nn.Sigmoid()
        )
        
        # 输出投影
        self.conv3 = nn.Conv3d(in_channels, out_channels, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm3d(out_channels)
        
        # 残差连接
        self.downsample = None
        if stride != 1 or in_channels != out_channels:
            self.downsample = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size=1, 
                        stride=(1, stride, stride), bias=False),
                nn.BatchNorm3d(out_channels)
            )
        
        self.relu = nn.ReLU(inplace=True)
        
    def forward(self, x):
        residual = x
        
        # 空间卷积
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        
        # 时序卷积
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)
        
        # 通道注意力
        out = out * self.se(out)
        
        # 输出投影
        out = self.conv3(out)
        out = self.bn3(out)
        
        # 残差连接
        if self.downsample is not None:
            residual = self.downsample(x)
        
        out += residual
        out = self.relu(out)
        
        return out


class LowRankConv3D(nn.Module):
    """
    低秩卷积层，通过分解3D卷积为三个单轴卷积显著降低参数量和显存需求
    """
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0):
        super(LowRankConv3D, self).__init__()
        
        # 分解为三个单轴卷积
        self.conv_t = nn.Conv3d(in_channels, in_channels, 
                              kernel_size=(kernel_size[0], 1, 1),
                              stride=(stride if isinstance(stride, int) else stride[0], 1, 1),
                              padding=(padding if isinstance(padding, int) else padding[0], 0, 0),
                              groups=in_channels,
                              bias=False)
        
        self.conv_h = nn.Conv3d(in_channels, in_channels, 
                              kernel_size=(1, kernel_size[1], 1),
                              stride=(1, stride if isinstance(stride, int) else stride[1], 1),
                              padding=(0, padding if isinstance(padding, int) else padding[1], 0),
                              groups=in_channels,
                              bias=False)
        
        self.conv_w = nn.Conv3d(in_channels, in_channels, 
                              kernel_size=(1, 1, kernel_size[2]),
                              stride=(1, 1, stride if isinstance(stride, int) else stride[2]),
                              padding=(0, 0, padding if isinstance(padding, int) else padding[2]),
                              groups=in_channels,
                              bias=False)
        
        # 点卷积做通道投影
        self.conv_p = nn.Conv3d(in_channels, out_channels, kernel_size=1, bias=True)
        
    def forward(self, x):
        x = self.conv_t(x)
        x = self.conv_h(x)
        x = self.conv_w(x)
        x = self.conv_p(x)
        return x


class DangerActionFocusModule(nn.Module):
    """
    危险行为专注模块，特别针对推人和打架等危险行为的特征提取
    """
    def __init__(self, in_channels, mid_channels=None):
        super(DangerActionFocusModule, self).__init__()
        
        if mid_channels is None:
            mid_channels = in_channels // 2
            
        # 专注于快速动作的时间特征提取
        self.rapid_motion_branch = nn.Sequential(
            nn.Conv3d(in_channels, mid_channels, kernel_size=(3, 1, 1), 
                     stride=(1, 1, 1), padding=(1, 0, 0), bias=False),
            nn.BatchNorm3d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv3d(mid_channels, mid_channels, kernel_size=(3, 3, 3), 
                     stride=(1, 1, 1), padding=(1, 1, 1), bias=False),
            nn.BatchNorm3d(mid_channels),
            nn.ReLU(inplace=True)
        )
        
        # 专注于人体交互的空间特征提取
        self.interaction_branch = nn.Sequential(
            nn.Conv3d(in_channels, mid_channels, kernel_size=(1, 3, 3), 
                     stride=(1, 1, 1), padding=(0, 1, 1), bias=False),
            nn.BatchNorm3d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv3d(mid_channels, mid_channels, kernel_size=(1, 5, 5), 
                     stride=(1, 1, 1), padding=(0, 2, 2), bias=False),
            nn.BatchNorm3d(mid_channels),
            nn.ReLU(inplace=True)
        )
        
        # 注意力聚焦机制
        self.attention = EfficientAttention(mid_channels * 2, reduction_ratio=4)
        
        # 输出投影
        self.fusion = nn.Sequential(
            nn.Conv3d(mid_channels * 2, in_channels, kernel_size=1, bias=False),
            nn.BatchNorm3d(in_channels),
            nn.ReLU(inplace=True)
        )
        
    def forward(self, x):
        # 快速动作特征
        motion_feats = self.rapid_motion_branch(x)
        
        # 人体交互特征
        interaction_feats = self.interaction_branch(x)
        
        # 合并两种特征
        combined = torch.cat([motion_feats, interaction_feats], dim=1)
        
        # 应用注意力
        focused = self.attention(combined)
        
        # 投影回原始通道数
        output = self.fusion(focused)
        
        # 残差连接
        return x + output


class HighPrecisionClassifier(nn.Module):
    """
    高精度分类器，使用分层分类提高对危险行为的识别准确率
    """
    def __init__(self, in_features, num_classes, dropout_rate=0.5):
        super(HighPrecisionClassifier, self).__init__()
        
        # 危险动作类别(推人、打架)的索引
        self.danger_indices = [ACTION_CATEGORIES['pushpeople'], ACTION_CATEGORIES['fight']]
        
        # 二级分类器 - 首先判断是否为危险行为
        self.danger_classifier = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(in_features, in_features // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate / 2),
            nn.Linear(in_features // 2, 1),
            nn.Sigmoid()
        )
        
        # 具体危险行为分类器 - 推人 vs 打架
        self.specific_danger_classifier = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(in_features, in_features // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate / 2),
            nn.Linear(in_features // 2, len(self.danger_indices)),
            nn.Softmax(dim=1)
        )
        
        # 常规行为分类器 - 分类所有可能的行为
        self.general_classifier = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(in_features, in_features // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate / 2),
            nn.Linear(in_features // 2, num_classes)
        )
        
    def forward(self, x):
        # 判断是否为危险行为
        is_danger = self.danger_classifier(x)
        
        # 如果是危险行为，进一步判断具体是哪种危险行为
        danger_probs = self.specific_danger_classifier(x)
        
        # 获取通用分类结果
        general_logits = self.general_classifier(x)
        outputs = general_logits.clone()
        
        # 根据危险行为分类结果调整最终输出
        batch_size = x.size(0)
        
        # 构建一个权重因子，当is_danger值高时，更信任specific_danger_classifier的结果
        danger_weight = is_danger.view(-1, 1)  # 形状变为[B, 1]
        
        # 遍历每种危险行为
        for i, danger_idx in enumerate(self.danger_indices):
            # 获取该危险行为的概率
            danger_prob = danger_probs[:, i].view(-1, 1)  # 形状变为[B, 1]
            
            # 只有在样本被判定为危险行为时，才用specific_danger_classifier的结果
            # 调整对应危险行为的logits以增强其识别能力，同时保持其他类别不变
            mask = torch.zeros_like(outputs)
            mask[:, danger_idx] = 1.0
            
            # 通过提高危险行为的logits来提高其概率
            # 当is_danger接近1时，提升效果最强
            danger_logit_boost = danger_prob * danger_weight * 10.0  # 10.0是提升系数
            outputs = outputs + mask * danger_logit_boost
            
        return outputs


class OptimizedInfraredActionNet(nn.Module):
    """
    针对RTX 3050 4GB显存优化的红外视频行为识别网络
    在保证高准确率的同时最小化显存占用
    """
    def __init__(self, num_classes=NUM_CLASSES, dropout_rate=0.5, fine_tune=True):
        super(OptimizedInfraredActionNet, self).__init__()
        
        # 使用高效的预训练模型作为骨干
        self.base_model = models.video.r3d_18(pretrained=True)
        
        # 微调策略 - 冻结前面的层以节省显存
        if not fine_tune:
            for param in self.base_model.parameters():
                param.requires_grad = False
            
            # 只微调最后几层
            for param in self.base_model.layer4.parameters():
                param.requires_grad = True
        
        # 修改第一个卷积层以处理灰度输入图像
        original_conv = self.base_model.stem[0]
        # 通过平均权重将3通道的卷积层权重转换为1通道的权重
        avg_weight = original_conv.weight.data.mean(dim=1, keepdim=True).repeat(1, 3, 1, 1, 1)
        self.base_model.stem[0].weight.data = avg_weight
        
        # 提取特征部分
        self.features = nn.Sequential(*list(self.base_model.children())[:-1])
        
        # 危险动作关注模块
        self.danger_focus = DangerActionFocusModule(512)
        
        # 时空特征增强，使用内存高效的组件
        self.feature_enhancer = nn.Sequential(
            MemoryEfficientBlock(512, 512),
            MemoryEfficientBlock(512, 512)
        )
        
        # 全局池化
        self.global_pool = nn.AdaptiveAvgPool3d((1, 1, 1))
        
        # 高精度分类器
        self.classifier = HighPrecisionClassifier(512, num_classes, dropout_rate)
        
        # 降低精度但保持准确性的混合精度训练辅助函数
        self.use_amp = True  # 自动混合精度，降低显存需求
        
    def forward(self, x):
        with torch_amp.autocast(device_type='cuda' if torch.cuda.is_available() else 'cpu'):
            # 特征提取
            features = self.features(x)
            
            # 危险行为关注
            focused = self.danger_focus(features)
            
            # 特征增强
            enhanced = self.feature_enhancer(focused)
            
            # 全局池化
            pooled = self.global_pool(enhanced)
            pooled = pooled.view(pooled.size(0), -1)
            
            # 分类
            outputs = self.classifier(pooled)
            
            return outputs


class EnsembleOptimizedNet(nn.Module):
    """
    集成多个优化模型，通过投票提高准确率
    使用知识蒸馏减少显存占用
    """
    def __init__(self, num_classes=NUM_CLASSES, num_models=3, dropout_rate=0.5, fine_tune=True):
        super(EnsembleOptimizedNet, self).__init__()
        
        # 使用略微不同的配置创建多个基础模型
        self.models = nn.ModuleList([
            OptimizedInfraredActionNet(num_classes, dropout_rate, fine_tune)
            for _ in range(num_models)
        ])
        
        # 创建用于模型蒸馏的学生模型
        self.student = OptimizedInfraredActionNet(num_classes, dropout_rate, fine_tune)
        
        # 集成权重
        self.weights = nn.Parameter(torch.ones(num_models) / num_models)
        
        # 集成激活函数
        self.alpha = nn.Parameter(torch.tensor(1.0))
        
        # 是否使用蒸馏模式
        self.distillation_mode = False
        
    def set_distillation_mode(self, mode=True):
        """设置蒸馏模式"""
        self.distillation_mode = mode
        
        # 在蒸馏模式下冻结教师模型参数
        for model in self.models:
            for param in model.parameters():
                param.requires_grad = not mode
                
        # 学生模型始终可训练
        for param in self.student.parameters():
            param.requires_grad = True
    
    def forward(self, x):
        with torch_amp.autocast(device_type='cuda' if torch.cuda.is_available() else 'cpu'):
            if self.distillation_mode:
                # 蒸馏模式 - 只使用学生模型进行前向传播
                return self.student(x)
            
            # 集成模式 - 各模型前向传播
            outputs = []
            for model in self.models:
                outputs.append(model(x))
            
            # 加权平均
            weights = F.softmax(self.weights * self.alpha, dim=0)
            ensemble_output = 0
            for i, output in enumerate(outputs):
                ensemble_output += output * weights[i]
            
            return ensemble_output
    
    def get_teacher_outputs(self, x):
        """获取教师模型的输出，用于蒸馏损失计算"""
        outputs = []
        with torch.no_grad():
            for model in self.models:
                outputs.append(model(x))
            
            # 加权平均
            weights = F.softmax(self.weights * self.alpha, dim=0)
            ensemble_output = 0
            for i, output in enumerate(outputs):
                ensemble_output += output * weights[i]
            
            return ensemble_output
    
    def get_student_output(self, x):
        """获取学生模型输出，用于蒸馏损失计算"""
        return self.student(x)


class OptimizedActionNetLite(nn.Module):
    """
    极轻量级模型，适合在显存受限设备上运行
    牺牲一定准确率来显著降低显存占用，适合推理阶段使用
    """
    def __init__(self, num_classes=NUM_CLASSES, dropout_rate=0.5):
        super(OptimizedActionNetLite, self).__init__()
        
        # 使用轻量级3D卷积架构
        self.conv1 = LowRankConv3D(3, 32, kernel_size=(3, 7, 7), stride=(1, 2, 2), padding=(1, 3, 3))
        self.bn1 = nn.BatchNorm3d(32)
        self.relu = nn.ReLU(inplace=True)
        self.pool = nn.MaxPool3d(kernel_size=(1, 3, 3), stride=(1, 2, 2), padding=(0, 1, 1))
        
        # 高效残差块
        self.layer1 = self._make_layer(32, 64, blocks=2, stride=1)
        self.layer2 = self._make_layer(64, 128, blocks=2, stride=2)
        self.layer3 = self._make_layer(128, 256, blocks=2, stride=2)
        
        # 危险行为专注模块
        self.danger_focus = DangerActionFocusModule(256, 128)
        
        # 全局池化
        self.global_pool = nn.AdaptiveAvgPool3d((1, 1, 1))
        
        # 高效分类器
        self.classifier = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate / 2),
            nn.Linear(128, num_classes)
        )
        
        # 初始化权重
        self._initialize_weights()
        
    def _make_layer(self, in_channels, out_channels, blocks, stride=1):
        layers = []
        
        # 第一个块可能改变通道数和分辨率
        layers.append(MemoryEfficientBlock(in_channels, out_channels, stride))
        
        # 其余的块保持通道数和分辨率不变
        for _ in range(1, blocks):
            layers.append(MemoryEfficientBlock(out_channels, out_channels))
            
        return nn.Sequential(*layers)
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv3d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm3d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        with torch_amp.autocast(device_type='cuda' if torch.cuda.is_available() else 'cpu'):
            x = self.conv1(x)
            x = self.bn1(x)
            x = self.relu(x)
            x = self.pool(x)
            
            x = self.layer1(x)
            x = self.layer2(x)
            x = self.layer3(x)
            
            x = self.danger_focus(x)
            
            x = self.global_pool(x)
            x = x.view(x.size(0), -1)
            
            x = self.classifier(x)
            
            return x


def get_optimized_model(model_type="OptimizedInfraredActionNet", num_classes=NUM_CLASSES, **kwargs):
    """
    获取针对RTX 3050优化的模型
    
    Args:
        model_type: 模型类型，可选值:
            - "OptimizedInfraredActionNet": 针对高精度优化的完整模型
            - "EnsembleOptimizedNet": 集成多个模型，准确率更高但训练更慢
            - "OptimizedActionNetLite": 轻量级模型，显存占用低但准确率稍低
        num_classes: 类别数量
        **kwargs: 其他参数
        
    Returns:
        模型实例
    """
    if model_type == "OptimizedInfraredActionNet":
        return OptimizedInfraredActionNet(num_classes=num_classes, **kwargs)
    elif model_type == "EnsembleOptimizedNet":
        return EnsembleOptimizedNet(num_classes=num_classes, **kwargs)
    elif model_type == "OptimizedActionNetLite":
        return OptimizedActionNetLite(num_classes=num_classes, **kwargs)
    else:
        raise ValueError(f"未支持的模型类型: {model_type}")
