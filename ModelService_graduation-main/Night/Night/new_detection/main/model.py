import torch
import torch.nn as nn
import numpy  as np
from PIL import Image,ImageTk
from loss import LossFunction
from ultralytics import YOLO

class EnhanceNetwork(nn.Module):
    def __init__(self, layers, channels):
        super(EnhanceNetwork, self).__init__()

        # 增加内核尺寸和通道数以提取更多细节
        kernel_size = 3
        dilation = 1
        padding = int((kernel_size - 1) / 2) * dilation
        
        # 增加输入通道，提高特征提取能力
        self.in_conv = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=32, kernel_size=kernel_size, stride=1, padding=padding),
            nn.ReLU()
        )
        
        # 添加更深层次的卷积层
        self.down_conv = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=kernel_size, stride=2, padding=padding),
            nn.BatchNorm2d(64),
            nn.ReLU()
        )
        
        # 中间处理层
        self.middle_conv = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=kernel_size, stride=1, padding=padding),
            nn.BatchNorm2d(64),
            nn.ReLU()
        )
        
        # 上采样层
        self.up_conv = nn.Sequential(
            nn.ConvTranspose2d(in_channels=64, out_channels=32, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU()
        )
        
        # 标准卷积块
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=kernel_size, stride=1, padding=padding),
            nn.BatchNorm2d(32),
            nn.ReLU()
        )

        # 残差块
        self.blocks = nn.ModuleList()
        for i in range(layers):
            self.blocks.append(self.conv)
            
        # 注意力机制层
        self.attention = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=1, kernel_size=1, stride=1, padding=0),
            nn.Sigmoid()
        )

        # 输出层，增加对比度和亮度控制
        self.out_conv = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=3, kernel_size=3, stride=1, padding=1),
            nn.Sigmoid()
        )

    def forward(self, input):
        # 初始特征提取
        fea = self.in_conv(input)
        
        # 保存初始特征用于跳跃连接
        initial_fea = fea
        
        # 下采样
        down_fea = self.down_conv(fea)
        
        # 中间处理
        middle_fea = down_fea
        for _ in range(3):  # 增加中间层处理次数
            middle_fea = self.middle_conv(middle_fea) + middle_fea  # 添加残差连接
        
        # 上采样
        up_fea = self.up_conv(middle_fea)
        
        # 结合初始特征（跳跃连接）
        combined_fea = up_fea + initial_fea
        
        # 残差块处理
        res_fea = combined_fea
        for conv in self.blocks:
            res_fea = res_fea + conv(res_fea)  # 残差连接
        
        # 注意力机制
        attention_map = self.attention(res_fea)
        attended_fea = res_fea * attention_map
        
        # 生成输出
        out_fea = self.out_conv(attended_fea)
        
        # 增强照明
        illu = out_fea + input
        illu = torch.clamp(illu, 0.0001, 1)
        
        return illu

class Network(nn.Module):

    def __init__(self, weights):
        super(Network, self).__init__()
        # 增加层数和通道数
        self.enhance = EnhanceNetwork(layers=3, channels=32)
        self._criterion = LossFunction()

        try:
            base_weights = torch.load(weights)
            pretrained_dict = base_weights
            model_dict = self.state_dict()
            # 过滤掉不匹配的键(由于我们修改了网络结构)
            pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict and v.shape == model_dict[k].shape}
            print(f'成功加载 {len(pretrained_dict)} 个预训练参数')
            model_dict.update(pretrained_dict)
            self.load_state_dict(model_dict)
        except Exception as e:
            print(f'加载权重时出错: {e}')
            print('使用随机初始化权重')

    def weights_init(self, m):
        if isinstance(m, nn.Conv2d):
            m.weight.data.normal_(0, 0.02)
            m.bias.data.zero_()

        if isinstance(m, nn.BatchNorm2d):
            m.weight.data.normal_(1., 0.02)

    def forward(self, input, night_vision_mode=False):
        # 增强图像
        i = self.enhance(input)
        
        if night_vision_mode:
            # 如果启用夜视模式，应用特殊处理
            # 提取亮度信息
            r = input / (i + 0.0001)  # 防止除以零
            r = torch.clamp(r, 0, 1)
            
            # 转换为灰度图像并提高对比度
            gray = 0.299 * r[:, 0, :, :] + 0.587 * r[:, 1, :, :] + 0.114 * r[:, 2, :, :]
            gray = gray.unsqueeze(1).repeat(1, 3, 1, 1)  # 恢复为3通道
            
            # 应用高对比度和轻微绿色调
            contrast = 2.5
            brightness = 0.15
            green_tint = torch.zeros_like(gray)
            green_tint[:, 1, :, :] = 0.1  # 轻微绿色调
            
            night_vision = contrast * gray + brightness + green_tint
            night_vision = torch.clamp(night_vision, 0, 1)
            
            # 添加噪点效果
            noise = torch.randn_like(night_vision) * 0.05
            night_vision = torch.clamp(night_vision + noise, 0, 1)
            
            # 转换为PIL图像
            image_numpy = night_vision[0].cpu().float().numpy()
            image_numpy = (np.transpose(image_numpy, (1, 2, 0)))
            im = Image.fromarray(np.clip(image_numpy * 255.0, 0, 255.0).astype('uint8'))
        else:
            # 标准增强处理
            r = input / (i + 0.0001)  # 防止除以零
            r = torch.clamp(r, 0, 1)

            image_numpy = r[0].cpu().float().numpy()
            image_numpy = (np.transpose(image_numpy, (1, 2, 0)))
            im = Image.fromarray(np.clip(image_numpy * 255.0, 0, 255.0).astype('uint8'))

        return im


    def _loss(self, input):
        i, r = self(input)
        loss = self._criterion(input, i)
        return loss
