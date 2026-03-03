"""
夜间车辆检测模块
从Night-vehicle-detection-system项目整合的车辆检测功能
"""
import os
import cv2
import numpy as np
import torch
import logging
import time
from PIL import Image, ImageDraw
from pathlib import Path

# 尝试导入YOLOv8，如果不可用则提供替代方案
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# 配置日志
logger = logging.getLogger(__name__)

# 模型路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))))
MODEL_PATH = os.path.join(BASE_DIR, "ModelService", "Main", "models", "yolov8n.pt")
if not os.path.exists(MODEL_PATH):
    # 尝试查找上级目录中的模型
    alt_model_path = os.path.join(BASE_DIR, "yolov8n.pt")
    if os.path.exists(alt_model_path):
        MODEL_PATH = alt_model_path
        logger.info(f"使用替代模型路径: {MODEL_PATH}")
    else:
        logger.warning(f"无法找到YOLOv8模型: {MODEL_PATH}")
        MODEL_PATH = None

# 模型类
class VehicleDetector:
    """夜间车辆检测器类"""
    
    def __init__(self, model_path=None):
        """
        初始化车辆检测器
        
        Args:
            model_path: 可选，YOLOv8模型路径，如果未提供将使用默认路径
        """
        self.model = None
        self.model_path = model_path or MODEL_PATH
        self.logger = logging.getLogger(__name__ + ".VehicleDetector")
        
        # 尝试加载模型
        self._load_model()
    
    def _load_model(self):
        """加载YOLOv8模型"""
        if not YOLO_AVAILABLE:
            self.logger.warning("未找到ultralytics包，无法加载YOLOv8模型")
            return False
            
        if not self.model_path or not os.path.exists(self.model_path):
            self.logger.error(f"模型文件不存在: {self.model_path}")
            return False
            
        try:
            start_time = time.time()
            self.logger.info(f"正在加载模型: {self.model_path}")
            self.model = YOLO(self.model_path)
            
            # 强制使用CPU以避免GPU内存问题
            self.model.to('cpu')
            
            elapsed = time.time() - start_time
            self.logger.info(f"模型加载完成，耗时: {elapsed:.2f}秒")
            return True
        except Exception as e:
            self.logger.error(f"加载模型时发生错误: {str(e)}")
            return False
    
    def detect(self, image, conf_threshold=0.25, classes=None, enhance=False):
        """
        执行车辆检测
        
        Args:
            image: 输入图像（PIL.Image或numpy数组）
            conf_threshold: 置信度阈值，默认0.25
            classes: 可选，要检测的类别ID列表，默认检测所有
            enhance: 是否在检测前增强图像
            
        Returns:
            检测结果列表，每个结果包含bbox、类别和置信度
        """
        if self.model is None:
            self.logger.error("模型未加载，无法执行检测")
            return []
            
        # 确保图像格式正确
        is_pil = isinstance(image, Image.Image)
        if is_pil:
            # 如果是PIL图像，转换为numpy数组
            image_np = np.array(image)
        else:
            image_np = image.copy()
            
        if enhance:
            # 导入图像增强模块
            from .image_enhancer import enhance_image
            image_np = enhance_image(image_np, method="combined")
        
        try:
            # 执行检测
            self.logger.info("开始执行车辆检测")
            start_time = time.time()
            
            # 设置检测参数
            results = self.model(image_np, conf=conf_threshold, classes=classes)
            
            elapsed = time.time() - start_time
            self.logger.info(f"检测完成，耗时: {elapsed:.2f}秒")
            
            # 解析结果
            detections = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    b = box.xyxy[0].tolist()  # 边界框坐标 (x1, y1, x2, y2)
                    c = int(box.cls)          # 类别ID
                    s = float(box.conf)       # 置信度
                    
                    # 获取类别名称
                    class_name = r.names[c] if hasattr(r, 'names') and c in r.names else f"class_{c}"
                    
                    detections.append({
                        'bbox': b,
                        'class': class_name,
                        'confidence': s
                    })
            
            self.logger.info(f"检测到 {len(detections)} 个物体")
            return detections
            
        except Exception as e:
            self.logger.error(f"执行检测时发生错误: {str(e)}")
            return []
    
    def draw_detections(self, image, detections):
        """
        在图像上绘制检测结果
        
        Args:
            image: 输入图像（PIL.Image或numpy数组）
            detections: 检测结果列表
            
        Returns:
            绘制了检测框的图像，与输入格式一致
        """
        # 确保图像格式正确
        is_pil = isinstance(image, Image.Image)
        if is_pil:
            # 如果是PIL图像
            img_draw = image.copy()
            draw = ImageDraw.Draw(img_draw)
            
            from PIL import ImageFont
            font = ImageFont.load_default()
            for det in detections:
                bbox = det['bbox']
                label = f"{det['class']} {det['confidence']:.2f}"
                
                # 绘制边界框
                draw.rectangle(bbox, outline=(0, 255, 0), width=2)
                
                # 绘制带背景的标签，提升可读性
                text_size = draw.textsize(label, font=font)
                text_x = max(bbox[0], 0)
                text_y = max(bbox[1] - text_size[1] - 4, 0)
                background_box = [text_x, text_y, text_x + text_size[0] + 6, text_y + text_size[1] + 4]
                draw.rectangle(background_box, fill=(0, 255, 0))
                draw.text((text_x + 3, text_y + 2), label, fill=(0, 0, 0), font=font)
            
            return img_draw
        else:
            # 如果是numpy数组
            img_draw = image.copy()
            
            for det in detections:
                bbox = det['bbox']
                x1, y1, x2, y2 = map(int, bbox)
                label = f"{det['class']} {det['confidence']:.2f}"
                
                # 绘制边界框
                cv2.rectangle(img_draw, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # 绘制带背景的标签，提升可读性
                (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                bg_tl = (x1, max(y1 - text_h - 8, 0))
                bg_br = (x1 + text_w + 6, y1)
                cv2.rectangle(img_draw, bg_tl, bg_br, (0, 255, 0), -1)
                cv2.putText(img_draw, label, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            return img_draw
            
# 创建一个简单的替代检测器，当YOLOv8不可用时使用
class DummyVehicleDetector:
    """简单的车辆检测器替代实现，当YOLOv8不可用时使用"""
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__ + ".DummyVehicleDetector")
        self.logger.warning("使用替代车辆检测器")
    
    def detect(self, image, conf_threshold=0.25, classes=None, enhance=False):
        """
        使用传统CV方法执行简单的车辆检测（只是演示用）
        """
        self.logger.info("使用替代检测方法")
        
        # 确保图像格式正确
        is_pil = isinstance(image, Image.Image)
        if is_pil:
            # 如果是PIL图像，转换为numpy数组
            image_np = np.array(image)
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        else:
            image_np = image.copy()
            
        # 转换为灰度图
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        
        # 应用高斯模糊
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 使用Canny边缘检测
        edges = cv2.Canny(blur, 50, 150)
        
        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤小轮廓
        min_area = 1000
        large_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
        
        # 模拟检测结果
        detections = []
        for i, cnt in enumerate(large_contours):
            x, y, w, h = cv2.boundingRect(cnt)
            
            # 检查纵横比来识别可能的车辆
            aspect_ratio = float(w) / h
            if 0.8 <= aspect_ratio <= 3.0:  # 车辆通常有这个纵横比范围
                # 创建虚拟检测结果
                detections.append({
                    'bbox': [float(x), float(y), float(x+w), float(y+h)],
                    'class': '汽车' if i % 2 == 0 else '卡车',  # 随机分配类别
                    'confidence': 0.7 + (i % 3) * 0.1  # 随机置信度
                })
        
        self.logger.info(f"检测到 {len(detections)} 个可能的车辆")
        return detections
    
    def draw_detections(self, image, detections):
        """
        在图像上绘制检测结果
        """
        # 与主类相同的绘制函数
        is_pil = isinstance(image, Image.Image)
        if is_pil:
            img_draw = image.copy()
            draw = ImageDraw.Draw(img_draw)
            
            for det in detections:
                bbox = det['bbox']
                label = f"{det['class']} {det['confidence']:.2f}"
                
                draw.rectangle(bbox, outline=(0, 255, 0), width=2)
                draw.text((bbox[0], bbox[1] - 10), label, fill=(0, 255, 0))
            
            return img_draw
        else:
            img_draw = image.copy()
            
            for det in detections:
                bbox = det['bbox']
                x1, y1, x2, y2 = map(int, bbox)
                label = f"{det['class']} {det['confidence']:.2f}"
                
                cv2.rectangle(img_draw, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img_draw, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            return img_draw

# 工厂函数，根据可用性创建适当的检测器
def create_detector(model_path=None):
    """创建车辆检测器实例"""
    if YOLO_AVAILABLE:
        return VehicleDetector(model_path)
    else:
        logger.warning("YOLOv8不可用，使用替代检测器")
        return DummyVehicleDetector()
