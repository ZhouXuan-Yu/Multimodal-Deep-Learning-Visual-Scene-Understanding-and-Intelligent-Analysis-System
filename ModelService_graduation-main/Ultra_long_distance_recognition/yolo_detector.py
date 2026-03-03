#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YOLOv8检测器模块
提供YOLOv8检测器的创建和使用功能
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path

def create_yolov8_detector():
    """
    创建YOLOv8检测器
    
    Returns:
        object: YOLOv8检测器对象，失败返回None
    """
    try:
        # 检查是否已安装ultralytics
        try:
            from ultralytics import YOLO
        except ImportError:
            print("未找到ultralytics包，正在安装...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])
            from ultralytics import YOLO
            print("ultralytics安装成功")
        
        # 检测模型路径
        model_dir = Path(__file__).parent / "models" / "yolo"
        os.makedirs(model_dir, exist_ok=True)
        
        # 查找已下载的模型文件
        model_files = list(model_dir.glob("*.pt"))
        
        if model_files:
            # 使用找到的第一个模型文件
            model_path = str(model_files[0])
            print(f"使用已下载的模型: {model_path}")
            
            # 获取文件大小
            file_size_mb = round(os.path.getsize(model_path) / (1024 * 1024), 2)
            print(f"模型大小: {file_size_mb} MB")
            
            # 加载模型
            model = YOLO(model_path)
            
            # 设置检测参数
            model.conf = 0.25  # 置信度阈值，可以根据需要调整
            model.iou = 0.45   # IoU阈值
            model.agnostic = False  # 是否进行类别无关的NMS
            model.multi_label = False  # 是否允许每个框有多个类别
            model.max_det = 1000  # 最大检测数量
            
            print("YOLOv8检测器初始化成功")
            return model
        else:
            # 如果没有找到模型文件，尝试使用名称加载（会自动下载）
            print("未找到本地模型文件，尝试使用ultralytics默认模型...")
            
            # 尝试多个不同大小的模型，从小到大
            for model_name in ['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt', 'yolov8l.pt', 'yolov8x.pt']:
                try:
                    print(f"尝试加载模型: {model_name}")
                    model = YOLO(model_name)
                    
                    # 设置检测参数
                    model.conf = 0.25  # 置信度阈值
                    model.iou = 0.45   # IoU阈值
                    
                    print(f"成功加载模型: {model_name}")
                    return model
                except Exception as e:
                    print(f"加载模型 {model_name} 失败: {str(e)}")
                    continue
            
            print("所有模型加载尝试均失败")
            return None
    except Exception as e:
        print(f"初始化YOLOv8检测器时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def detect_with_yolov8(detector, img):
    """
    使用YOLOv8检测图像中的对象
    
    Args:
        detector: YOLOv8检测器对象
        img: 输入图像，OpenCV格式(BGR)
        
    Returns:
        list: 检测结果列表，每个元素为[x1, y1, x2, y2, class_id, confidence]
    """
    try:
        # 确保图像是RGB格式（YOLOv8期望RGB而不是BGR）
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 执行检测
        results = detector(img_rgb, verbose=False)  # 关闭详细输出
        
        # 转换为标准格式 [x1, y1, x2, y2, class_id, confidence]
        detections = []
        
        # 处理检测结果
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # 获取坐标
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # 获取置信度和类别
                conf = box.conf[0].cpu().numpy().item()
                cls = int(box.cls[0].cpu().numpy().item())
                
                # 添加到检测列表
                detections.append([float(x1), float(y1), float(x2), float(y2), cls, conf])
        
        # 打印检测到的对象数量
        print(f"检测到 {len(detections)} 个对象")
        
        return detections
    except Exception as e:
        print(f"YOLOv8检测过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

# 测试模块
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    # 创建检测器
    detector = create_yolov8_detector()
    
    if detector is not None:
        # 加载测试图像
        test_img_path = Path(__file__).parent / "data" / "RGBT-Tiny" / "images" / "DJI_0022_1" / "00" / "00001.jpg"
        
        if test_img_path.exists():
            img = cv2.imread(str(test_img_path))
            
            # 执行检测
            detections = detect_with_yolov8(detector, img)
            
            # 打印检测结果
            print(f"检测结果: {detections}")
            
            # 显示检测结果
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            plt.figure(figsize=(10, 8))
            plt.imshow(img_rgb)
            
            # 绘制边界框
            for det in detections:
                x1, y1, x2, y2, cls, conf = det
                plt.gca().add_patch(plt.Rectangle((x1, y1), x2-x1, y2-y1, fill=False, edgecolor='red', linewidth=2))
                plt.text(x1, y1-10, f'Class: {cls}, Conf: {conf:.2f}', color='white', backgroundcolor='red')
            
            plt.axis('off')
            plt.title('YOLOv8 检测结果')
            plt.show()
        else:
            print(f"测试图像不存在: {test_img_path}")
    else:
        print("YOLOv8检测器初始化失败")
