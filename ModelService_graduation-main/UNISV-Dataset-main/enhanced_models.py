"""
增强型模型架构，专为红外视频行为识别设计，特别优化了危险行为检测的准确率
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models.video import r3d_18, R3D_18_Weights, mvit_v2_s, MViT_V2_S_Weights
from torchvision.models.video import swin3d_s, Swin3D_S_Weights
from torchvision.models import efficientnet_v2_s, EfficientNet_V2_S_Weights
from torch.hub import load_state_dict_from_url
import math
from config import *


class MultiScaleTemporalAttention(nn.Module):
    """
    多尺度时间注意力模块，捕捉不同时间尺度的动作特征
    """
    def __init__(self, in_channels, reduction=8):
        super(MultiScaleTemporalAttention, self).__init__()
        self.in_channels = in_channels
        
        # 不同长度的时间卷积核，捕捉不同时间尺度的模式
        self.conv1 = nn.Conv3d(in_channels, in_channels//reduction, kernel_size=(3, 1, 1), padding=(1, 0, 0))
        self.conv2 = nn.Conv3d(in_channels, in_channels//reduction, kernel_size=(5, 1, 1), padding=(2, 0, 0))
        self.conv3 = nn.Conv3d(in_channels, in_channels//reduction, kernel_size=(7, 1, 1), padding=(3, 0, 0))
        
        # 注意力权重生成
        self.attention = nn.Sequential(
            nn.AdaptiveAvgPool3d((None, 1, 1)),
            nn.Conv3d(in_channels//reduction*3, in_channels, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv3d(in_channels, in_channels, kernel_size=1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        # 多尺度时间特征提取
        feat1 = self.conv1(x)
        feat2 = self.conv2(x)
        feat3 = self.conv3(x)
        
        # 拼接多尺度特征
        multi_scale_feat = torch.cat([feat1, feat2, feat3], dim=1)
        
        # 生成注意力权重
        weights = self.attention(multi_scale_feat)
        
        # 加权原始特征
        enhanced_feat = x * weights
        
        return enhanced_feat


class MotionFocusBlock(nn.Module):
    """
    运动聚焦模块，专注于捕捉帧间运动模式，对危险行为（如推人、打架）特别敏感
    """
    def __init__(self, in_channels):
        super(MotionFocusBlock, self).__init__()
        
        # 计算相邻帧差异的卷积
        self.motion_conv = nn.Conv3d(in_channels, in_channels, kernel_size=(2, 3, 3), 
                                    stride=(1, 1, 1), padding=(0, 1, 1), groups=in_channels)
        self.bn = nn.BatchNorm3d(in_channels)
        self.relu = nn.ReLU(inplace=True)
        
        # 产生运动权重
        self.motion_gate = nn.Sequential(
            nn.AdaptiveAvgPool3d((None, 1, 1)),
            nn.Conv3d(in_channels, in_channels//4, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv3d(in_channels//4, in_channels, kernel_size=1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        # 提取运动特征
        motion_features = self.motion_conv(x)
        motion_features = self.bn(motion_features)
        motion_features = self.relu(motion_features)
        
        # 运动门控
        motion_weights = self.motion_gate(motion_features)
        
        # 将运动信息与原始特征结合
        # 先处理尺寸差异（时间维度可能不同）
        if motion_features.shape[2] < x.shape[2]:
            motion_features = F.pad(motion_features, (0, 0, 0, 0, 0, x.shape[2]-motion_features.shape[2]))
            motion_weights = F.pad(motion_weights, (0, 0, 0, 0, 0, x.shape[2]-motion_weights.shape[2]))
            
        enhanced = x + (motion_features * motion_weights)
        return enhanced


class DangerActionDetectionHead(nn.Module):
    """
    危险行为检测专用头，专门优化推人、打架等危险行为的识别
    """
    def __init__(self, in_channels, num_classes=NUM_CLASSES):
        super(DangerActionDetectionHead, self).__init__()
        
        self.avgpool = nn.AdaptiveAvgPool3d((1, 1, 1))
        self.danger_classes = [ACTION_CATEGORIES['pushpeople'], ACTION_CATEGORIES['fight']]
        
        # 创建危险行为专用分类器
        self.danger_classifier = nn.Sequential(
            nn.Linear(in_channels, in_channels//2),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(in_channels//2, len(self.danger_classes)),
            nn.Sigmoid()  # 使用Sigmoid而非Softmax，以获得更独立的危险行为概率
        )
        
        # 常规分类器处理所有类别
        self.general_classifier = nn.Sequential(
            nn.Linear(in_channels, in_channels//2),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(in_channels//2, num_classes)
        )
        
    def forward(self, x, return_features=False):
        # 全局池化
        pooled = self.avgpool(x)
        features = pooled.flatten(1)
        
        # 危险行为专用预测
        danger_preds = self.danger_classifier(features)
        
        # 常规分类预测
        general_preds = self.general_classifier(features)
        
        # 将危险行为专用预测合并到常规预测中
        # 为危险行为类别使用专用分类器的结果，因为它被优化得更好
        final_preds = general_preds.clone()
        for i, danger_class in enumerate(self.danger_classes):
            # 使用危险行为专用分类器的输出增强常规分类器对危险类别的预测
            # 这种方法的目的是保持原始格式的输出同时提高危险类的准确率
            final_preds[:, danger_class] = final_preds[:, danger_class] * 0.3 + danger_preds[:, i] * 0.7
            
        if return_features:
            return final_preds, features
        return final_preds


class PositionalEncoding3D(nn.Module):
    """
    3D位置编码，帮助模型更好地理解视频中的时空位置信息
    """
    def __init__(self, channels, temporal_length=CLIP_LENGTH, spatial_size=(FRAME_HEIGHT//4, FRAME_WIDTH//4)):
        super(PositionalEncoding3D, self).__init__()
        
        t, h, w = temporal_length, spatial_size[0], spatial_size[1]
        position_t = torch.arange(0, t, dtype=torch.float).unsqueeze(1).unsqueeze(1)
        position_h = torch.arange(0, h, dtype=torch.float).unsqueeze(0).unsqueeze(2)
        position_w = torch.arange(0, w, dtype=torch.float).unsqueeze(0).unsqueeze(0)
        
        div_term = torch.exp(torch.arange(0, channels//6, 2, dtype=torch.float) * (-math.log(10000.0) / channels))
        
        # 创建时间位置编码
        pe_t = torch.zeros(1, channels//3, t, 1, 1)
        pe_t[0, 0::2, :, 0, 0] = torch.sin(position_t * div_term)
        pe_t[0, 1::2, :, 0, 0] = torch.cos(position_t * div_term)
        
        # 创建空间高度位置编码
        pe_h = torch.zeros(1, channels//3, 1, h, 1)
        pe_h[0, 0::2, 0, :, 0] = torch.sin(position_h * div_term)
        pe_h[0, 1::2, 0, :, 0] = torch.cos(position_h * div_term)
        
        # 创建空间宽度位置编码
        pe_w = torch.zeros(1, channels//3, 1, 1, w)
        pe_w[0, 0::2, 0, 0, :] = torch.sin(position_w * div_term)
        pe_w[0, 1::2, 0, 0, :] = torch.cos(position_w * div_term)
        
        # 扩展到整个空间
        pe_t = pe_t.expand(-1, -1, -1, h, w)
        pe_h = pe_h.expand(-1, -1, t, -1, -1)
        pe_w = pe_w.expand(-1, -1, t, h, -1)
        
        # 将三个位置编码连接
        self.register_buffer('pe', torch.cat([pe_t, pe_h, pe_w], dim=1))
        
    def forward(self, x):
        # 将位置编码添加到输入中
        return x + self.pe[:, :x.size(1), :x.size(2), :x.size(3), :x.size(4)]


class EnhancedTemporalBlock(nn.Module):
    """增强的时序块，更好地捕捉动作特征"""
    
    def __init__(self, in_channels, out_channels):
        super(EnhancedTemporalBlock, self).__init__()
        
        # 时间卷积分支
        self.temp_conv = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=(3, 1, 1), padding=(1, 0, 0)),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        # 空间卷积分支
        self.spat_conv = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=(1, 3, 3), padding=(0, 1, 1)),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        # 融合卷积
        self.fusion = nn.Sequential(
            nn.Conv3d(out_channels*2, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        # 注意力模块
        self.attention = nn.Sequential(
            nn.AdaptiveAvgPool3d((1, 1, 1)),
            nn.Conv3d(out_channels, out_channels//4, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv3d(out_channels//4, out_channels, kernel_size=1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        # 时间和空间特征提取
        temp_feat = self.temp_conv(x)
        spat_feat = self.spat_conv(x)
        
        # 特征融合
        fused = torch.cat([temp_feat, spat_feat], dim=1)
        fused = self.fusion(fused)
        
        # 应用注意力
        att = self.attention(fused)
        out = fused * att
        
        return out


class InfraredActionNet(nn.Module):
    """
    专为红外视频行为识别优化的高精度网络，特别加强了对危险行为的识别能力
    """
    def __init__(self, num_classes=NUM_CLASSES, dropout_prob=0.5):
        super(InfraredActionNet, self).__init__()
        
        # 使用高性能视频主干网络 - 多种骨干网络集成
        # MViT V2 作为主要特征提取器
        self.mvit = mvit_v2_s(weights=MViT_V2_S_Weights.DEFAULT)
        # 移除分类头
        self.mvit_features = nn.Sequential(*list(self.mvit.children())[:-1])
        
        # 集成 Swin Transformer 特征 - 它在捕获长范围依赖关系方面表现良好
        self.swin = swin3d_s(weights=Swin3D_S_Weights.DEFAULT)
        # 移除分类头
        self.swin_features = nn.Sequential(*list(self.swin.children())[:-1])
        
        # 使用 R3D_18 作为辅助骨干
        self.r3d = r3d_18(weights=R3D_18_Weights.DEFAULT)
        self.r3d_features = nn.Sequential(*list(self.r3d.children())[:-1])
        
        # 创建特征适配层，统一各个骨干网络的输出维度
        # MViT输出通道为768
        # Swin输出通道为768
        # R3D输出通道为512
        self.mvit_adapter = nn.Conv3d(768, 512, kernel_size=1)
        self.swin_adapter = nn.Conv3d(768, 512, kernel_size=1)
        
        # 添加位置编码增强空间感知
        self.pos_encoding = PositionalEncoding3D(512)
        
        # 多尺度时间注意力增强动作识别
        self.temporal_attention = MultiScaleTemporalAttention(512)
        
        # 运动聚焦模块专注捕捉帧间变化
        self.motion_focus = MotionFocusBlock(512)
        
        # 时间特征增强
        self.temporal_enhance = EnhancedTemporalBlock(512, 512)
        
        # 危险行为特化处理模块
        self.danger_action_block = nn.Sequential(
            nn.Conv3d(512, 256, kernel_size=3, padding=1),
            nn.BatchNorm3d(256),
            nn.ReLU(inplace=True),
            nn.Conv3d(256, 512, kernel_size=3, padding=1),
            nn.BatchNorm3d(512),
            nn.ReLU(inplace=True)
        )
        
        # 权重生成网络，学习如何融合不同骨干特征
        self.weight_net = nn.Sequential(
            nn.AdaptiveAvgPool3d((1, 1, 1)),
            nn.Conv3d(512*3, 3, kernel_size=1),
            nn.Softmax(dim=1)
        )
        
        # 深度特征提取器
        self.deep_feature = nn.Sequential(
            nn.Conv3d(512, 512, kernel_size=3, padding=1),
            nn.BatchNorm3d(512),
            nn.ReLU(inplace=True),
            nn.Conv3d(512, 512, kernel_size=3, padding=1),
            nn.BatchNorm3d(512),
            nn.ReLU(inplace=True)
        )
        
        # 危险行为检测专用头
        self.detection_head = DangerActionDetectionHead(512, num_classes)
        
        # 辅助分类器 - 使用多任务学习进一步提高性能
        self.aux_classifier = nn.Sequential(
            nn.AdaptiveAvgPool3d((1, 1, 1)),
            nn.Flatten(),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_prob),
            nn.Linear(256, num_classes)
        )
        
        # 初始化权重
        self._initialize_weights()
        
    def _initialize_weights(self):
        """初始化新添加层的权重"""
        for m in self.modules():
            if isinstance(m, nn.Conv3d) or isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm3d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        """前向传播"""
        # 特征提取 - 获取三个不同骨干网络的特征
        mvit_feat = self.mvit_features(x)
        swin_feat = self.swin_features(x)
        r3d_feat = self.r3d_features(x)
        
        # 调整特征维度一致
        mvit_feat = self.mvit_adapter(mvit_feat)
        swin_feat = self.swin_adapter(swin_feat)
        
        # 动态特征融合 - 生成权重并加权融合三个骨干特征
        # 首先调整尺寸一致
        min_t = min(mvit_feat.shape[2], swin_feat.shape[2], r3d_feat.shape[2])
        min_h = min(mvit_feat.shape[3], swin_feat.shape[3], r3d_feat.shape[3])
        min_w = min(mvit_feat.shape[4], swin_feat.shape[4], r3d_feat.shape[4])
        
        mvit_feat = F.adaptive_avg_pool3d(mvit_feat, (min_t, min_h, min_w))
        swin_feat = F.adaptive_avg_pool3d(swin_feat, (min_t, min_h, min_w))
        r3d_feat = F.adaptive_avg_pool3d(r3d_feat, (min_t, min_h, min_w))
        
        # 拼接特征用于生成权重
        concat_feat = torch.cat([mvit_feat, swin_feat, r3d_feat], dim=1)
        weights = self.weight_net(concat_feat)  # 输出形状(B, 3, 1, 1, 1)
        
        # 加权融合特征
        fused_feat = (mvit_feat * weights[:, 0:1, :, :, :] + 
                      swin_feat * weights[:, 1:2, :, :, :] + 
                      r3d_feat * weights[:, 2:3, :, :, :])
        
        # 添加位置编码
        pos_feat = self.pos_encoding(fused_feat)
        
        # 应用时序注意力
        temp_feat = self.temporal_attention(pos_feat)
        
        # 运动聚焦增强
        motion_feat = self.motion_focus(temp_feat)
        
        # 危险行为特化处理
        danger_feat = self.danger_action_block(motion_feat)
        
        # 时序特征增强
        enhanced_feat = self.temporal_enhance(danger_feat)
        
        # 深度特征提取
        deep_feat = self.deep_feature(enhanced_feat)
        
        # 计算辅助损失(训练时)，预测最终结果
        aux_out = self.aux_classifier(motion_feat)
        main_out = self.detection_head(deep_feat)
        
        if self.training:
            return main_out, aux_out
        else:
            return main_out


class InfraredActionNetLite(nn.Module):
    """
    InfraredActionNet的轻量版本，在保持高准确率的同时降低计算开销
    适合在边缘设备和实时系统中部署
    """
    def __init__(self, num_classes=NUM_CLASSES, dropout_prob=0.5):
        super(InfraredActionNetLite, self).__init__()
        
        # 轻量级视频特征提取主干网络 - R3D_18 基础上优化
        self.base_model = r3d_18(weights=R3D_18_Weights.DEFAULT)
        self.features = nn.Sequential(*list(self.base_model.children())[:-2])
        
        # EfficientNet V2作为辅助特征提取
        self.efficient_net = efficientnet_v2_s(weights=EfficientNet_V2_S_Weights.DEFAULT)
        # 移除分类头
        self.efficient_features = nn.Sequential(*list(self.efficient_net.children())[:-1])
        
        # 特征提取增强
        self.temporal_attention = MultiScaleTemporalAttention(512, reduction=16)
        self.motion_focus = MotionFocusBlock(512)
        
        # 空间特征处理
        self.spatial_processor = nn.Sequential(
            nn.Conv3d(512, 256, kernel_size=(1, 3, 3), padding=(0, 1, 1)),
            nn.BatchNorm3d(256),
            nn.ReLU(inplace=True),
            nn.Conv3d(256, 512, kernel_size=1),
            nn.BatchNorm3d(512),
            nn.ReLU(inplace=True)
        )
        
        # 危险行为检测头
        self.detection_head = DangerActionDetectionHead(512, num_classes)
        
        # 初始化权重
        self._initialize_weights()
        
    def _initialize_weights(self):
        """初始化新添加层的权重"""
        for m in self.modules():
            if isinstance(m, nn.Conv3d) or isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm3d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def _process_2d_features(self, x, efficient_features):
        """处理2D特征并转换为3D特征"""
        b, c, t, h, w = x.shape
        
        # 提取中间帧作为关键帧
        mid_frame = x[:, :, t//2, :, :]
        
        # 通过EfficientNet提取特征
        efficient_feat = self.efficient_features(mid_frame)  # (B, 1280, H/32, W/32)
        
        # 调整为3D特征图
        efficient_feat = efficient_feat.unsqueeze(2)  # 添加时间维度
        efficient_feat = efficient_feat.repeat(1, 1, 1, 1, 1)  # 只使用一个时间步长
        
        # 特征维度调整
        efficient_feat = F.adaptive_avg_pool3d(efficient_feat, (1, h//16, w//16))
        
        return efficient_feat
                
    def forward(self, x):
        """前向传播"""
        # 3D特征提取
        r3d_feat = self.features(x)
        
        # 应用时序注意力
        attended_feat = self.temporal_attention(r3d_feat)
        
        # 运动聚焦
        motion_feat = self.motion_focus(attended_feat)
        
        # 空间特征处理
        spatial_feat = self.spatial_processor(motion_feat)
        
        # 分类
        out = self.detection_head(spatial_feat)
        
        return out


def get_enhanced_model(model_type="InfraredActionNet", num_classes=NUM_CLASSES, **kwargs):
    """
    获取增强型模型实例
    
    Args:
        model_type: 模型类型，可选 "InfraredActionNet" 或 "InfraredActionNetLite"
        num_classes: 类别数量
        **kwargs: 其他参数
        
    Returns:
        模型实例
    """
    if model_type == "InfraredActionNet":
        return InfraredActionNet(num_classes=num_classes, **kwargs)
    elif model_type == "InfraredActionNetLite":
        return InfraredActionNetLite(num_classes=num_classes, **kwargs)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}，请使用 'InfraredActionNet' 或 'InfraredActionNetLite'")
