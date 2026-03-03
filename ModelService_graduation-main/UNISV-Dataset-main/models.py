"""
模型定义模块，包含用于红外视频行为识别的网络架构
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models.video import r3d_18, R3D_18_Weights
from torch.hub import load_state_dict_from_url
from config import *


class AttentionModule(nn.Module):
    """空间-时间注意力模块，增强对关键动作特征的关注"""
    
    def __init__(self, in_channels):
        super(AttentionModule, self).__init__()
        self.spatial_attention = nn.Sequential(
            nn.Conv3d(in_channels, 1, kernel_size=1),
            nn.Sigmoid()
        )
        
        self.temporal_attention = nn.Sequential(
            nn.AdaptiveAvgPool3d((None, 1, 1)),
            nn.Conv3d(in_channels, in_channels, kernel_size=1),
            nn.ReLU(),
            nn.Conv3d(in_channels, in_channels, kernel_size=1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        spatial_weights = self.spatial_attention(x)
        spatial_attention = x * spatial_weights
        
        temporal_weights = self.temporal_attention(x)
        temporal_attention = x * temporal_weights
        
        return spatial_attention + temporal_attention


class InfraredI3D(nn.Module):
    """为红外视频行为识别调整的I3D模型"""
    
    def __init__(self, num_classes=NUM_CLASSES, dropout_prob=DROPOUT_PROB, pretrained=PRETRAINED):
        super(InfraredI3D, self).__init__()
        
        # 从R3D_18加载预训练权重
        if pretrained:
            self.base_model = r3d_18(weights=R3D_18_Weights.DEFAULT)
            # 修改第一个卷积层以处理灰度输入图像（复制权重的平均值）
            original_weight = self.base_model.stem[0].weight.data
            new_weight = original_weight.mean(dim=1, keepdim=True).repeat(1, 3, 1, 1, 1)
            self.base_model.stem[0].weight.data = new_weight
        else:
            self.base_model = r3d_18(weights=None)
            # 修改第一个卷积层以直接处理灰度图像（1通道输入）
            self.base_model.stem[0] = nn.Conv3d(3, 64, kernel_size=(3, 7, 7), 
                                               stride=(1, 2, 2), padding=(1, 3, 3), 
                                               bias=False)
        
        # 特征提取器
        self.features = nn.Sequential(*list(self.base_model.children())[:-2])
        
        # 添加注意力模块
        self.attention = AttentionModule(512)  # R3D_18的最后一层有512个通道
        
        # 全局池化
        self.avgpool = nn.AdaptiveAvgPool3d((1, 1, 1))
        
        # 分类器
        self.classifier = nn.Sequential(
            nn.Dropout3d(dropout_prob),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_prob),
            nn.Linear(256, num_classes)
        )
        
        # 初始化新加入的层
        self._initialize_weights()
        
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
        # x的预期形状: [batch_size, channels, num_frames, height, width]
        
        # 特征提取
        x = self.features(x)
        
        # 应用注意力机制
        x = self.attention(x)
        
        # 全局池化
        x = self.avgpool(x)
        
        # 展平
        x = x.flatten(1)
        
        # 分类
        x = self.classifier(x)
        
        return x


class SlowFastNetwork(nn.Module):
    """SlowFast网络，结合慢路径和快路径特征，适用于行为识别"""
    
    def __init__(self, num_classes=NUM_CLASSES, dropout_prob=DROPOUT_PROB):
        super(SlowFastNetwork, self).__init__()
        
        # 慢路径 - 捕获空间语义信息
        self.slow_pathway = nn.Sequential(
            nn.Conv3d(3, 64, kernel_size=(1, 7, 7), stride=(1, 2, 2), padding=(0, 3, 3), bias=False),
            nn.BatchNorm3d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool3d(kernel_size=(1, 3, 3), stride=(1, 2, 2), padding=(0, 1, 1)),
            self._make_layer_slow(64, 128, 2),
            self._make_layer_slow(128, 256, 2),
            self._make_layer_slow(256, 512, 2),
        )
        
        # 快路径 - 捕获时间动态信息
        self.fast_pathway = nn.Sequential(
            nn.Conv3d(3, 32, kernel_size=(5, 7, 7), stride=(1, 2, 2), padding=(2, 3, 3), bias=False),
            nn.BatchNorm3d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool3d(kernel_size=(1, 3, 3), stride=(1, 2, 2), padding=(0, 1, 1)),
            self._make_layer_fast(32, 64, 2),
            self._make_layer_fast(64, 128, 2),
            self._make_layer_fast(128, 256, 2),
        )
        
        # 路径融合
        self.fusion = nn.Sequential(
            nn.Conv3d(512 + 256, 512, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm3d(512),
            nn.ReLU(inplace=True)
        )
        
        # 注意力机制
        self.attention = AttentionModule(512)
        
        # 全局池化
        self.avgpool = nn.AdaptiveAvgPool3d((1, 1, 1))
        
        # 分类器
        self.classifier = nn.Sequential(
            nn.Dropout(dropout_prob),
            nn.Linear(512, num_classes)
        )
        
    def _make_layer_slow(self, in_channels, out_channels, blocks):
        layers = []
        # 第一个块可能需要下采样
        layers.append(nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=(1, 3, 3), 
                     stride=(1, 2, 2), padding=(0, 1, 1), bias=False),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True)
        ))
        
        # 添加剩余块
        for _ in range(1, blocks):
            layers.append(nn.Sequential(
                nn.Conv3d(out_channels, out_channels, kernel_size=(1, 3, 3), 
                         stride=1, padding=(0, 1, 1), bias=False),
                nn.BatchNorm3d(out_channels),
                nn.ReLU(inplace=True)
            ))
            
        return nn.Sequential(*layers)
    
    def _make_layer_fast(self, in_channels, out_channels, blocks):
        layers = []
        # 第一个块可能需要下采样
        layers.append(nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=(3, 3, 3), 
                     stride=(1, 2, 2), padding=(1, 1, 1), bias=False),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True)
        ))
        
        # 添加剩余块
        for _ in range(1, blocks):
            layers.append(nn.Sequential(
                nn.Conv3d(out_channels, out_channels, kernel_size=(3, 3, 3), 
                         stride=1, padding=(1, 1, 1), bias=False),
                nn.BatchNorm3d(out_channels),
                nn.ReLU(inplace=True)
            ))
            
        return nn.Sequential(*layers)
    
    def forward(self, x):
        # 慢路径处理
        slow_features = self.slow_pathway(x)
        
        # 快路径处理
        fast_features = self.fast_pathway(x)
        
        # 调整时间维度以匹配
        if slow_features.shape[2] != fast_features.shape[2]:
            slow_features = F.interpolate(
                slow_features, 
                size=(fast_features.shape[2], slow_features.shape[3], slow_features.shape[4]),
                mode='nearest'
            )
        
        # 融合特征
        fused_features = torch.cat([slow_features, fast_features], dim=1)
        fused_features = self.fusion(fused_features)
        
        # 应用注意力
        features = self.attention(fused_features)
        
        # 全局池化
        features = self.avgpool(features)
        
        # 展平
        features = features.flatten(1)
        
        # 分类
        output = self.classifier(features)
        
        return output


class X3DModel(nn.Module):
    """X3D模型，轻量级但高效的视频识别架构"""
    
    def __init__(self, num_classes=NUM_CLASSES, dropout_prob=DROPOUT_PROB):
        super(X3DModel, self).__init__()
        
        # 特征提取主干网络
        self.conv1 = nn.Conv3d(3, 24, kernel_size=(3, 3, 3), stride=(1, 2, 2), padding=(1, 1, 1), bias=False)
        self.bn1 = nn.BatchNorm3d(24)
        self.relu = nn.ReLU(inplace=True)
        
        # X3D块
        self.layer1 = self._make_layer(24, 24, 2, stride=1)
        self.layer2 = self._make_layer(24, 48, 3, stride=2)
        self.layer3 = self._make_layer(48, 96, 4, stride=2)
        self.layer4 = self._make_layer(96, 192, 3, stride=2)
        
        # SE模块
        self.se = SEModule(192)
        
        # 全局平均池化
        self.avgpool = nn.AdaptiveAvgPool3d((1, 1, 1))
        
        # 分类头
        self.fc1 = nn.Linear(192, 432)
        self.fc_relu = nn.ReLU(inplace=True)
        self.fc2 = nn.Linear(432, num_classes)
        self.dropout = nn.Dropout(dropout_prob)
        
    def _make_layer(self, in_channels, out_channels, blocks, stride):
        layers = []
        
        # 第一个块可能需要下采样
        layers.append(X3DBlock(in_channels, out_channels, stride=stride))
        
        # 添加剩余块
        for _ in range(1, blocks):
            layers.append(X3DBlock(out_channels, out_channels, stride=1))
            
        return nn.Sequential(*layers)
    
    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        
        x = self.se(x)
        
        x = self.avgpool(x)
        x = x.flatten(1)
        
        x = self.fc1(x)
        x = self.fc_relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x


class X3DBlock(nn.Module):
    """X3D架构的基本构建块"""
    
    def __init__(self, in_channels, out_channels, stride=1):
        super(X3DBlock, self).__init__()
        
        self.conv1 = nn.Conv3d(in_channels, in_channels, kernel_size=(3, 1, 1),
                              stride=(1, 1, 1), padding=(1, 0, 0), bias=False, groups=in_channels)
        self.bn1 = nn.BatchNorm3d(in_channels)
        self.conv2 = nn.Conv3d(in_channels, in_channels, kernel_size=(1, 3, 3),
                              stride=(1, stride, stride), padding=(0, 1, 1), bias=False, groups=in_channels)
        self.bn2 = nn.BatchNorm3d(in_channels)
        self.conv3 = nn.Conv3d(in_channels, out_channels, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm3d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        
        # SE模块
        self.se = SEModule(out_channels)
        
        # 残差连接
        self.downsample = None
        if stride != 1 or in_channels != out_channels:
            self.downsample = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size=1, stride=(1, stride, stride), bias=False),
                nn.BatchNorm3d(out_channels)
            )
            
    def forward(self, x):
        identity = x
        
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)
        
        out = self.conv3(out)
        out = self.bn3(out)
        
        out = self.se(out)
        
        if self.downsample is not None:
            identity = self.downsample(x)
            
        out += identity
        out = self.relu(out)
        
        return out


class SEModule(nn.Module):
    """Squeeze-and-Excitation模块，增强特征通道间的依赖关系"""
    
    def __init__(self, channels, reduction=4):
        super(SEModule, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool3d((1, 1, 1))
        self.fc1 = nn.Conv3d(channels, channels // reduction, kernel_size=1)
        self.relu = nn.ReLU(inplace=True)
        self.fc2 = nn.Conv3d(channels // reduction, channels, kernel_size=1)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        module_input = x
        x = self.avg_pool(x)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.sigmoid(x)
        
        return module_input * x


def get_model(model_type=MODEL_TYPE, num_classes=NUM_CLASSES, **kwargs):
    """根据指定的模型类型获取相应模型实例"""
    if model_type == 'I3D':
        return InfraredI3D(num_classes=num_classes, **kwargs)
    elif model_type == 'SlowFast':
        return SlowFastNetwork(num_classes=num_classes, **kwargs)
    elif model_type == 'X3D':
        return X3DModel(num_classes=num_classes, **kwargs)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
