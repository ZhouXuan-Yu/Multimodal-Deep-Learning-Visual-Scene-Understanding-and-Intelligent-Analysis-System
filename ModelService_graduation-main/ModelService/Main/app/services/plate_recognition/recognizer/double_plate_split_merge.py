'''
将双车牌图像分割成两半，然后合并
增强版会对图像进行预处理和错误处理，提高双层车牌的识别率
'''

import cv2
import numpy as np
import logging
import os.path  # 用于主函数中的文件路径处理

# 配置日志记录器
logger = logging.getLogger(__name__)

def get_split_merge(img):
    """
    将双层车牌图像分割成上下两部分，然后水平合并
    
    Args:
        img: 输入的双层车牌图像
        
    Returns:
        new_img: 处理后的图像，可用于单层车牌识别模型
    """
    try:
        # 检查输入图像
        if img is None or img.size == 0:
            logger.error("双层车牌图像为空或无效")
            return img  # 返回原始图像
        
        # 获取图像尺寸
        h, w, c = img.shape
        logger.info(f"双层车牌原始尺寸: 高={h}, 宽={w}, 通道={c}")
        
        # 图像增强预处理 - 提高对比度
        img = cv2.convertScaleAbs(img, alpha=1.2, beta=10)
        
        # 自适应分割点计算 - 根据图像特性动态调整
        upper_ratio = 5/12  # 上部分割点
        lower_ratio = 1/3   # 下部分割点
        
        # 尝试使用车牌特征更准确地定位分割点
        # 转为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 二值化
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 尝试找到分隔线 - 水平投影分析
        horizontal_proj = np.sum(thresh, axis=1)
        # 找出分隔区域 - 水平投影值较低的区域
        h_middle = h // 2
        # 在中间位置附近寻找开始分割的点
        window = int(h * 0.2)  # 搜索窗口大小
        search_start = max(0, h_middle - window)
        search_end = min(h, h_middle + window)
        
        # 在搜索区域内找到投影值最小的点作为分隔点
        sep_point = search_start + np.argmin(horizontal_proj[search_start:search_end])
        
        if sep_point > 0 and sep_point < h - 1:
            logger.info(f"检测到可能的分隔点在高度: {sep_point} (总高度的 {sep_point/h:.2f})")
            # 使用检测到的分隔点计算分割比例
            upper_ratio = (sep_point - 5) / h  # 留出一点空隙
            lower_ratio = (sep_point + 5) / h  # 留出一点空隙
        
        # 编码消息应该在上部，号码应该在下部
        img_upper = img[0:int(upper_ratio*h),:]  # 上部分(编码部分)
        img_lower = img[int(lower_ratio*h):,:]  # 下部分(号码部分)
        
        # 调整上部分的大小与下部分匹配
        if img_upper.size > 0 and img_lower.size > 0:
            img_upper = cv2.resize(img_upper, (img_lower.shape[1], img_lower.shape[0]))
            
            # 颜色增强 - 可能有助于提高识别率
            img_upper = cv2.convertScaleAbs(img_upper, alpha=1.1, beta=5)
            img_lower = cv2.convertScaleAbs(img_lower, alpha=1.1, beta=5)
            
            # 水平合并两部分
            new_img = np.hstack((img_upper, img_lower))
            logger.info(f"合并后双层车牌图像尺寸: {new_img.shape}")
            return new_img
        else:
            logger.warning("双层车牌分割后某部分为空，返回原始图像")
            return img
            
    except Exception as e:
        logger.error(f"双层车牌处理失败: {str(e)}")
        # 出错时返回原始图像
        return img

if __name__=="__main__":
    img = cv2.imread("double_plate/tmp8078.png")
    new_img =get_split_merge(img)
    cv2.imwrite("double_plate/new.jpg",new_img)
