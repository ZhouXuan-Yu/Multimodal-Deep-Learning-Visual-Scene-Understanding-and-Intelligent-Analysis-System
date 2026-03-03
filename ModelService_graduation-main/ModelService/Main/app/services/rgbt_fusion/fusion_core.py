"""
RGBT图像融合核心模块
从RGBT-Tiny项目整合的图像融合功能
"""
import os
import cv2
import numpy as np
import logging
import time
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)

class RGBTFusion:
    """RGBT图像融合类，用于融合可见光和热成像图像"""
    
    def __init__(self):
        """初始化图像融合类"""
        self.logger = logging.getLogger(__name__ + ".RGBTFusion")
        self.logger.info("初始化RGBT图像融合模块")
    
    def preprocess_images(self, rgb_image, thermal_image):
        """
        预处理RGB和热成像图像，确保它们具有相同的尺寸和通道数
        
        Args:
            rgb_image: 可见光图像 (numpy数组)
            thermal_image: 热成像图像 (numpy数组)
            
        Returns:
            预处理后的RGB和热成像图像
        """
        # 确保图像是numpy数组
        if not isinstance(rgb_image, np.ndarray):
            rgb_image = np.array(rgb_image)
        if not isinstance(thermal_image, np.ndarray):
            thermal_image = np.array(thermal_image)
            
        # 确保RGB图像是3通道
        if len(rgb_image.shape) == 2:
            rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_GRAY2BGR)
        elif rgb_image.shape[2] == 4:  # 处理带alpha通道的图像
            rgb_image = rgb_image[:, :, :3]
            
        # 确保热成像图像是单通道
        if len(thermal_image.shape) == 3:
            if thermal_image.shape[2] == 3:
                thermal_image = cv2.cvtColor(thermal_image, cv2.COLOR_BGR2GRAY)
            elif thermal_image.shape[2] == 4:
                thermal_image = cv2.cvtColor(thermal_image[:, :, :3], cv2.COLOR_BGR2GRAY)
                
        # 确保两张图像尺寸相同
        if rgb_image.shape[:2] != thermal_image.shape[:2]:
            # 调整热成像图像大小以匹配RGB图像
            thermal_image = cv2.resize(thermal_image, (rgb_image.shape[1], rgb_image.shape[0]))
            
        # 将热成像图像归一化到0-255
        if thermal_image.dtype != np.uint8:
            thermal_min = np.min(thermal_image)
            thermal_max = np.max(thermal_image)
            if thermal_min != thermal_max:
                thermal_image = ((thermal_image - thermal_min) / (thermal_max - thermal_min) * 255).astype(np.uint8)
            else:
                thermal_image = np.zeros_like(thermal_image, dtype=np.uint8)
                
        return rgb_image, thermal_image
        
    def simple_average_fusion(self, rgb_image, thermal_image, alpha=0.5):
        """
        简单的加权平均融合方法
        
        Args:
            rgb_image: 预处理后的RGB图像
            thermal_image: 预处理后的热成像图像
            alpha: RGB图像的权重 (0-1)
            
        Returns:
            融合后的图像
        """
        # 将热成像图像转换为3通道
        thermal_colored = cv2.applyColorMap(thermal_image, cv2.COLORMAP_JET)
        
        # 加权融合
        fused = cv2.addWeighted(rgb_image, alpha, thermal_colored, 1-alpha, 0)
        
        return fused
        
    def wavelet_fusion(self, rgb_image, thermal_image):
        """
        使用小波变换的图像融合方法
        
        Args:
            rgb_image: 预处理后的RGB图像
            thermal_image: 预处理后的热成像图像
            
        Returns:
            融合后的图像
        """
        # 注意：这需要PyWavelets包，如果不可用，将返回简单融合
        try:
            import pywt
        except ImportError:
            self.logger.warning("PyWavelets包不可用，使用简单融合代替")
            return self.simple_average_fusion(rgb_image, thermal_image)
            
        # 转换RGB图像为灰度，用于小波变换
        rgb_gray = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2GRAY)
        
        # 对两幅图像进行小波分解
        coeffs_rgb = pywt.wavedec2(rgb_gray, 'db1', level=2)
        coeffs_thermal = pywt.wavedec2(thermal_image, 'db1', level=2)
        
        # 融合系数
        # 低频部分取平均值
        fused_coeffs = [((coeffs_rgb[0] + coeffs_thermal[0]) / 2)]
        
        # 高频部分取最大值
        for i in range(1, len(coeffs_rgb)):
            fused_detail = []
            for j in range(len(coeffs_rgb[i])):
                # 取最大绝对值
                fused_detail.append(np.where(
                    np.abs(coeffs_rgb[i][j]) > np.abs(coeffs_thermal[i][j]),
                    coeffs_rgb[i][j],
                    coeffs_thermal[i][j]
                ))
            fused_coeffs.append(tuple(fused_detail))
            
        # 逆小波变换
        fused_gray = pywt.waverec2(fused_coeffs, 'db1')
        
        # 裁剪到原始大小
        fused_gray = fused_gray[:rgb_gray.shape[0], :rgb_gray.shape[1]]
        
        # 归一化到0-255
        fused_gray = np.uint8(np.clip(fused_gray, 0, 255))
        
        # 将热成像图像上色
        thermal_colored = cv2.applyColorMap(thermal_image, cv2.COLORMAP_JET)
        
        # 结合灰度融合图和彩色RGB图像
        # 用HSV空间替换亮度通道
        hsv = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2HSV)
        hsv[:, :, 2] = fused_gray
        fused_color = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        # 再与热成像彩色图进行轻微融合
        final_fused = cv2.addWeighted(fused_color, 0.7, thermal_colored, 0.3, 0)
        
        return final_fused
    
    def guided_filter_fusion(self, rgb_image, thermal_image, radius=5, eps=0.01):
        """
        使用引导滤波的图像融合方法
        
        Args:
            rgb_image: 预处理后的RGB图像
            thermal_image: 预处理后的热成像图像
            radius: 滤波半径
            eps: 正则化参数
            
        Returns:
            融合后的图像
        """
        # 转换RGB图像为灰度，用作引导图像
        guide = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2GRAY)
        
        # 使用引导滤波
        filtered = cv2.ximgproc.guidedFilter(guide, thermal_image, radius, eps)
        
        # 将热成像图像转为伪彩色
        thermal_colored = cv2.applyColorMap(thermal_image, cv2.COLORMAP_JET)
        filtered_colored = cv2.applyColorMap(filtered, cv2.COLORMAP_JET)
        
        # 融合原始RGB和滤波后的热成像
        fused = cv2.addWeighted(rgb_image, 0.6, filtered_colored, 0.4, 0)
        
        return fused
        
    def fusion_with_mask(self, rgb_image, thermal_image, mask=None):
        """
        基于掩码的图像融合，突出热成像中的高温区域
        
        Args:
            rgb_image: 预处理后的RGB图像
            thermal_image: 预处理后的热成像图像
            mask: 可选，用于指定哪些区域突出热成像，如果为None则自动基于热成像生成
            
        Returns:
            融合后的图像
        """
        # 如果未提供掩码，根据热成像生成掩码（提取高温区域）
        if mask is None:
            # 阈值化找出高温区域
            _, mask = cv2.threshold(thermal_image, 200, 255, cv2.THRESH_BINARY)
            
            # 轻微膨胀以确保覆盖完整区域
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)
            
        # 创建彩色热成像图
        thermal_colored = cv2.applyColorMap(thermal_image, cv2.COLORMAP_JET)
        
        # 基于掩码融合
        # 创建3通道掩码
        mask_3ch = cv2.merge([mask, mask, mask]) / 255.0
        
        # 在掩码区域使用热成像，在其他区域使用RGB图像
        fused = rgb_image * (1 - mask_3ch) + thermal_colored * mask_3ch
        
        return fused.astype(np.uint8)
    
    def advanced_fusion(self, rgb_image, thermal_image, method="guided"):
        """
        执行高级图像融合
        
        Args:
            rgb_image: 原始RGB图像
            thermal_image: 原始热成像图像
            method: 融合方法，可选值为"average", "wavelet", "guided", "mask"
            
        Returns:
            融合后的图像
        """
        # 预处理图像
        rgb_proc, thermal_proc = self.preprocess_images(rgb_image, thermal_image)
        
        # 根据指定方法执行融合
        start_time = time.time()
        self.logger.info(f"使用 {method} 方法融合图像")
        
        if method == "average":
            fused = self.simple_average_fusion(rgb_proc, thermal_proc)
        elif method == "wavelet":
            fused = self.wavelet_fusion(rgb_proc, thermal_proc)
        elif method == "guided":
            fused = self.guided_filter_fusion(rgb_proc, thermal_proc)
        elif method == "mask":
            fused = self.fusion_with_mask(rgb_proc, thermal_proc)
        else:
            self.logger.warning(f"未知的融合方法: {method}，使用引导滤波代替")
            fused = self.guided_filter_fusion(rgb_proc, thermal_proc)
            
        elapsed = time.time() - start_time
        self.logger.info(f"融合完成，耗时: {elapsed:.2f}秒")
        
        return fused

# 图像融合工厂函数
def create_fusion_processor():
    """创建RGBT图像融合处理器"""
    return RGBTFusion()
