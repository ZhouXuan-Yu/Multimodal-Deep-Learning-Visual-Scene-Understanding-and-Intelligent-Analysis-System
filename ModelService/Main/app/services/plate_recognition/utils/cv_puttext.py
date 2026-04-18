"""
在OpenCV图像上绘制中文文本的工具
提供中文字体渲染支持
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

# 获取字体文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
font_path = os.path.join(base_dir, "fonts", "platech.ttf")

# 如果字体目录不存在则创建
os.makedirs(os.path.dirname(font_path), exist_ok=True)

def cv2ImgAddText(img, text, left, top, textColor=(0, 255, 0), textSize=20, font_path=None):
    """
    在OpenCV图像上添加中文文本
    
    参数:
        img: OpenCV图像
        text: 要添加的文本
        left: 文本左上角x坐标
        top: 文本左上角y坐标
        textColor: 文本颜色，默认为绿色
        textSize: 文本大小
        font_path: 字体文件路径，如果为None则使用默认字体
        
    返回:
        添加文本后的图像
    """
    if font_path is None:
        # 使用模块中定义的默认字体路径
        font_path = os.path.join(base_dir, "fonts", "platech.ttf")
        
        # 如果默认字体文件不存在，尝试使用系统字体
        if not os.path.exists(font_path):
            # 在Windows上尝试使用系统字体
            if os.name == 'nt':
                font_path = "C:\\Windows\\Fonts\\simhei.ttf"
            # 在Linux上尝试使用系统字体
            else:
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    if isinstance(img, np.ndarray):  # 判断是否OpenCV图片类型
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    draw = ImageDraw.Draw(img)
    try:
        fontText = ImageFont.truetype(font_path, textSize, encoding="utf-8")
        draw.text((left, top), text, textColor, font=fontText)
    except Exception as e:
        # 如果加载字体失败，使用默认字体
        print(f"加载字体失败: {str(e)}，使用默认字体")
        fontText = ImageFont.load_default()
        draw.text((left, top), text, textColor, font=fontText)
    
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
