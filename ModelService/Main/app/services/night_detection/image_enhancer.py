"""
夜间低光图像增强模块
从Night-vehicle-detection-system项目整合的图像增强功能
"""
import os
import cv2
import numpy as np
import logging
from PIL import Image, ImageEnhance

# 配置日志
logger = logging.getLogger(__name__)

# 全局默认CLAHE实例以减少重复创建开销
DEFAULT_CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

# 图像处理工具函数
def apply_clahe(img):
    """应用自适应直方图均衡化(CLAHE)增强图像对比度"""
    # 转换为LAB色彩空间
    if isinstance(img, np.ndarray):
        # 如果是NumPy数组（OpenCV格式）
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 对L通道应用CLAHE（使用全局默认实例以减少开销）
        cl = DEFAULT_CLAHE.apply(l)
        
        # 合并通道
        merged = cv2.merge((cl, a, b))
        
        # 转回原始色彩空间
        enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        return enhanced
    else:
        # 如果是PIL图像
        img_np = np.array(img)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)  # PIL是RGB格式
        enhanced = apply_clahe(img_np)  # 递归调用
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)  # 转回RGB
        return Image.fromarray(enhanced)

def denoise_image(img):
    """应用去噪算法减少图像噪点"""
    if isinstance(img, np.ndarray):
        # 对OpenCV格式的图像进行处理
        return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
    else:
        # 如果是PIL图像
        img_np = np.array(img)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)  # PIL是RGB格式
        denoised = denoise_image(img_np)  # 递归调用
        denoised = cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB)  # 转回RGB
        return Image.fromarray(denoised)

def adjust_gamma(img, gamma=1.5):
    """调整图像的gamma值提高亮度"""
    if isinstance(img, np.ndarray):
        # 创建查询表
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
        
        # 应用查询表
        return cv2.LUT(img, table)
    else:
        # 如果是PIL图像
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(gamma)

def increase_contrast(img, factor=1.5):
    """增强图像对比度"""
    if isinstance(img, np.ndarray):
        # 使用OpenCV处理
        alpha = factor  # 对比度控制
        beta = 10       # 亮度控制
        return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    else:
        # 如果是PIL图像
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(factor)

def create_night_vision_effect(img):
    """创建夜视仪效果"""
    if isinstance(img, np.ndarray):
        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 应用CLAHE增强对比度
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # 转换回彩色（绿色调）
        green_tint = np.zeros_like(img)
        green_tint[:, :, 0] = 0    # B通道
        green_tint[:, :, 1] = enhanced  # G通道
        green_tint[:, :, 2] = 0    # R通道
        
        # 增加噪点
        noise = np.zeros_like(img)
        cv2.randn(noise, 0, 25)  # 添加高斯噪声
        
        # 合并噪声和夜视效果
        result = cv2.add(green_tint, noise)
        return result
    else:
        # 如果是PIL图像
        img_np = np.array(img)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)  # PIL是RGB格式
        night_vision = create_night_vision_effect(img_np)  # 递归调用
        night_vision = cv2.cvtColor(night_vision, cv2.COLOR_BGR2RGB)  # 转回RGB
        return Image.fromarray(night_vision)

# 组合的增强函数
def enhance_image(img, method="clahe", params=None):
    """
    根据指定方法增强图像
    
    Args:
        img: 输入图像，可以是PIL.Image或numpy数组
        method: 增强方法，可选值包括
                'clahe': 自适应直方图均衡化
                'denoise': 图像去噪
                'gamma': gamma调整
                'contrast': 对比度增强
                'night_vision': 夜视效果
                'combined': 组合多种方法
        params: 方法参数，例如gamma值或对比度因子
        
    Returns:
        增强后的图像，与输入格式一致
    """
    # 确保图像格式正确
    is_pil = isinstance(img, Image.Image)
    
    # 如果是PIL图像，转换为OpenCV格式
    if is_pil:
        img_cv = np.array(img)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    else:
        img_cv = img.copy()
    
    # 应用选定的增强方法
    if method == "clahe":
        enhanced = apply_clahe(img_cv)
    elif method == "denoise":
        enhanced = denoise_image(img_cv)
    elif method == "gamma":
        gamma = params.get("gamma", 1.5) if params else 1.5
        enhanced = adjust_gamma(img_cv, gamma)
    elif method == "contrast":
        factor = params.get("factor", 1.5) if params else 1.5
        enhanced = increase_contrast(img_cv, factor)
    elif method == "night_vision":
        enhanced = create_night_vision_effect(img_cv)
    elif method == "combined":
        # 默认组合处理流程：去噪 -> CLAHE -> gamma调整 -> 对比度增强
        enhanced = denoise_image(img_cv)
        enhanced = apply_clahe(enhanced)
        enhanced = adjust_gamma(enhanced, 1.5)
        enhanced = increase_contrast(enhanced, 1.3)
    else:
        logger.warning(f"未知的增强方法: {method}，使用CLAHE作为默认方法")
        enhanced = apply_clahe(img_cv)
    
    # 转换回原始格式
    if is_pil:
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
        return Image.fromarray(enhanced)
    else:
        return enhanced
