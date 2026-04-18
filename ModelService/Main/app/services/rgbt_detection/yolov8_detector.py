"""
YOLOv8检测器模块，用于RGBT微小目标检测
"""
import os
import logging
import cv2
import numpy as np
import torch
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class YOLOv8Detector:
    """YOLOv8检测器类，用于微小目标检测"""
    
    def __init__(self, model_path: str, conf_thres: float = 0.15, iou_thres: float = 0.45):
        """
        初始化YOLOv8检测器
        
        参数:
            model_path: YOLOv8模型文件路径
            conf_thres: 置信度阈值，降低此值可检测更多目标 (默认0.15，比标准0.25要低)
            iou_thres: IOU阈值，用于非极大值抑制 (默认0.45，标准通常为0.5)
        """
        self.logger = logging.getLogger("YOLOv8Detector")
        self.model_path = model_path
        self.model = None
        # 检测配置参数
        self.conf_thres = conf_thres  # 置信度阈值
        self.iou_thres = iou_thres    # NMS的IOU阈值
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.load_model()
        
    def load_model(self):
        """加载YOLOv8模型"""
        try:
            from ultralytics import YOLO
            
            if not os.path.exists(self.model_path):
                self.logger.error(f"模型文件不存在: {self.model_path}")
                return False
                
            self.logger.info(f"加载YOLOv8模型: {self.model_path}")
            self.model = YOLO(self.model_path)
            self.model.to(self.device)
            self.logger.info(f"YOLOv8模型加载成功，使用设备: {self.device}")
            return True
        except Exception as e:
            self.logger.error(f"加载YOLOv8模型失败: {str(e)}")
            return False
    
    def detect(self, rgb_img: np.ndarray, thermal_img: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
        """
        检测图像中的目标
        
        参数:
            rgb_img: RGB图像
            thermal_img: 热成像图像（可选）
            
        返回:
            检测到的目标列表
        """
        detected_objects = []
        
        if self.model is None:
            self.logger.error("模型未加载")
            return detected_objects
            
        try:
            # RGB图像检测 - 使用配置的置信度和IOU阈值
            rgb_results = self.model(rgb_img, conf=self.conf_thres, iou=self.iou_thres, verbose=False)
            self.logger.info(f"使用检测参数 - 置信度阈值: {self.conf_thres}, IOU阈值: {self.iou_thres}")
            
            # 处理RGB检测结果
            for i, result in enumerate(rgb_results):
                boxes = result.boxes
                for j, box in enumerate(boxes):
                    # 获取边界框坐标
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    # 计算宽度和高度
                    w = x2 - x1
                    h = y2 - y1
                    # 获取置信度和类别
                    conf = float(box.conf.cpu().numpy()[0])
                    cls = int(box.cls.cpu().numpy()[0])
                    cls_name = result.names[cls]
                    
                    detected_objects.append({
                        "id": len(detected_objects) + 1,
                        "type": cls_name,
                        "size": f"{int(w)}x{int(h)}",
                        "confidence": conf,
                        "bbox": [int(x1), int(y1), int(w), int(h)],
                        "source": "rgb"
                    })
            
            # 如果有热成像图像，也进行检测，但使用更低的置信度阈值
            if thermal_img is not None:
                # 为热成像图像使用更低的置信度阈值，因为热成像目标通常信号较弱
                thermal_conf_thres = max(0.08, self.conf_thres * 0.6)  # 热成像置信度阈值为普通阈值的60%，但不低于0.08
                thermal_iou_thres = max(0.35, self.iou_thres * 0.8)  # 热成像 IOU 阈值也略低
                
                self.logger.info(f"对热成像图像进行检测 - 特殊置信度阈值: {thermal_conf_thres}, IOU阈值: {thermal_iou_thres}")
                thermal_results = self.model(thermal_img, conf=thermal_conf_thres, iou=thermal_iou_thres, verbose=False)
                
                # 处理热成像检测结果
                for i, result in enumerate(thermal_results):
                    boxes = result.boxes
                    for j, box in enumerate(boxes):
                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        # 计算宽度和高度
                        w = x2 - x1
                        h = y2 - y1
                        # 获取置信度和类别
                        conf = float(box.conf.cpu().numpy()[0]) 
                        cls = int(box.cls.cpu().numpy()[0])
                        cls_name = result.names[cls]
                        
                        detected_objects.append({
                            "id": len(detected_objects) + 1,
                            "type": cls_name,
                            "size": f"{int(w)}x{int(h)}",
                            "confidence": conf,
                            "bbox": [int(x1), int(y1), int(w), int(h)],
                            "source": "thermal"
                        })
            
            self.logger.info(f"检测到 {len(detected_objects)} 个目标")
            return detected_objects
            
        except Exception as e:
            self.logger.error(f"YOLOv8检测失败: {str(e)}")
            return detected_objects
    
    def preprocess_thermal_image(self, thermal_img: np.ndarray) -> np.ndarray:
        """
        预处理热成像图像，增强对比度和可见性
        
        参数:
            thermal_img: 原始热成像图像
            
        返回:
            处理后的热成像图像
        """
        try:
            # 保存原始图像副本
            processed_img = thermal_img.copy()
            
            # 1. 转换为灰度图像
            if len(processed_img.shape) == 3 and processed_img.shape[2] == 3:
                gray_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2GRAY)
            else:
                gray_img = processed_img.copy()
            
            # 2. 应用CLAHE（对比度受限自适应直方图均衡化）
            clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
            enhanced_img = clahe.apply(gray_img)
            
            # 3. 归一化到 0-255 范围
            norm_img = cv2.normalize(enhanced_img, None, 0, 255, cv2.NORM_MINMAX)
            
            # 4. 转换回3通道图像
            enhanced_thermal = cv2.cvtColor(norm_img, cv2.COLOR_GRAY2BGR)
            
            self.logger.info("热成像图像预处理完成")
            return enhanced_thermal
        except Exception as e:
            self.logger.error(f"热成像预处理失败: {str(e)}")
            return thermal_img  # 如果处理失败，返回原始图像
    
    def process_images(self, rgb_img: np.ndarray, thermal_img: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
        """
        处理RGB和热成像图像，返回处理后的图像和检测结果
        
        参数:
            rgb_img: RGB图像
            thermal_img: 热成像图像
            
        返回:
            处理后的RGB图像, 处理后的热成像图像, 检测结果列表
        """
        # 预处理热成像图像
        enhanced_thermal = self.preprocess_thermal_image(thermal_img)
        
        # 复制原始图像用于绘制
        rgb_result = rgb_img.copy()
        thermal_result = enhanced_thermal.copy()  # 使用增强后的热成像进行绘制
        
        # 使用增强后的热成像进行检测
        objects = self.detect(rgb_img, enhanced_thermal)
        
        # 在图像上绘制检测结果
        for obj in objects:
            bbox = obj["bbox"]
            source = obj["source"]
            
            # 使用置信度来调整颜色强度
            confidence = obj["confidence"]  # 使用confidence而非conf，以匹配字典键名
            thickness = max(1, int(confidence * 5))  # 根据置信度调整线条粗细
            
            # 确定颜色 - RGB检测用绿色，热成像检测用红色
            if source == "rgb":
                color = (0, 255, 0)  # 绿色
            else:  # thermal
                color = (0, 0, 255)  # 红色
            
            # 在相应图像上绘制边界框，不添加文字标签
            if source == "rgb":
                # 仅绘制边界框，不添加文字
                cv2.rectangle(rgb_result, 
                              (bbox[0], bbox[1]), 
                              (bbox[0] + bbox[2], bbox[1] + bbox[3]), 
                              color, thickness)
            else:
                # 在热成像上仅绘制边界框，不添加文字
                cv2.rectangle(thermal_result, 
                             (bbox[0], bbox[1]), 
                             (bbox[0] + bbox[2], bbox[1] + bbox[3]), 
                             color, thickness)
        
        return rgb_result, thermal_result, objects
