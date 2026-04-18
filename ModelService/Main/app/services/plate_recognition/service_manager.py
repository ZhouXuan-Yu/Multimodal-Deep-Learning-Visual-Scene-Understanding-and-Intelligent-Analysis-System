"""
车牌识别服务管理器
负责初始化和管理车牌识别服务的基本组件
"""
import os
import cv2
import numpy as np
import time
import torch
import logging
from typing import Dict, Any
import threading

# 导入必要组件
from .detector import load_model
from .recognizer import init_model, init_color_model, init_car_rec_model
from .config import WEIGHTS

# 配置日志
logger = logging.getLogger(__name__)

class PlateRecognitionServiceManager:
    """车牌识别服务管理器，单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PlateRecognitionServiceManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """初始化车牌识别服务管理器"""
        if self._initialized:
            return
            
        # 初始化属性
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.img_size = 640  # 默认图像尺寸
        self.models = {}  # 存储加载的模型
        self.startup_time = time.time()
        self.model_loaded = False
        self._initialized = True
        
        logger.info(f"车牌识别服务管理器初始化完成，使用设备: {self.device}")
    
    def init_service(self) -> Dict[str, Any]:
        """
        初始化车牌识别服务的所有组件
        
        返回:
            Dict[str, Any]: 初始化状态信息
        """
        try:
            logger.info("开始初始化车牌识别服务...")
            
            # 第1步：检查模型文件是否存在
            missing_models = self._check_model_files()
            if missing_models:
                logger.warning(f"部分模型文件不存在: {missing_models}")
                return {
                    "success": False,
                    "message": f"模型文件缺失: {', '.join(missing_models)}",
                    "missing_models": missing_models
                }
            
            # 第2步：加载车牌检测模型
            # 在service_manager.py的init_service方法中修改加载车牌检测模型部分
            # 第2步：加载车牌检测模型
            logger.info("加载车牌检测模型...")
            try:
                # 检测模型文件是否存在和有效
                detector_path = WEIGHTS['plate_detector']
                if not os.path.exists(detector_path):
                    logger.error(f"检测模型文件不存在: {detector_path}")
                    return {
                        "success": False,
                        "message": f"检测模型文件不存在: {detector_path}"
                    }
                
                # 使用统一的键名 'plate_detect'
                self.models['plate_detect'] = load_model(detector_path, self.device)
                
                # 验证模型是否有效并记录类别信息
                if hasattr(self.models['plate_detect'], 'names'):
                    logger.info(f"模型类别名称: {self.models['plate_detect'].names}")
                    model_classes = len(self.models['plate_detect'].names)
                    logger.info(f"模型类别数量: {model_classes}")
                    
                    # 记录一下类别ID映射，便于后续代码处理
                    self.class_mapping = {}
                    for i, name in enumerate(self.models['plate_detect'].names):
                        name = str(name).lower()
                        if "单" in name or "license" in name:
                            self.class_mapping['single_plate'] = i
                        elif "双" in name:
                            self.class_mapping['double_plate'] = i
                        elif "车" in name or "car" in name or "vehicle" in name:
                            self.class_mapping['vehicle'] = i
                            
                    logger.info(f"类别ID映射: {self.class_mapping}")
                else:
                    # 如果没有类别信息，使用默认映射
                    logger.warning("模型缺少类别名称属性，使用默认类别映射")
                    self.class_mapping = {'single_plate': 0, 'double_plate': 1, 'vehicle': 2}
                
                logger.info("车牌检测模型加载成功")
            except Exception as e:
                logger.error(f"加载车牌检测模型失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"加载车牌检测模型失败: {str(e)}"
                }
            
            # 第3步：加载车牌识别模型
            logger.info("加载车牌识别模型...")
            try:
                # 使用统一的键名 'plate_rec'
                self.models['plate_rec'] = init_model(self.device, WEIGHTS['plate_recognizer'])
                logger.info("车牌识别模型加载成功")
            except Exception as e:
                logger.error(f"加载车牌识别模型失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"加载车牌识别模型失败: {str(e)}"
                }
            
            # 第4步：加载车牌颜色识别模型
            logger.info("加载车牌颜色识别模型...")
            try:
                # 使用正确的加载函数init_color_model而非init_model
                # init_color_model创建的是MyNet_color实例，专门用于颜色识别
                self.models['plate_color'] = init_color_model(WEIGHTS['plate_color'], self.device)
                logger.info("车牌颜色识别模型加载成功")
            except Exception as e:
                logger.error(f"加载车牌颜色识别模型失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"加载车牌颜色识别模型失败: {str(e)}"
                }
            
            # 第5步：加载车辆颜色识别模型
            logger.info("加载车辆颜色识别模型...")
            try:
                # 使用统一的键名 'car_rec'
                self.models['car_rec'] = init_car_rec_model(WEIGHTS['car_color'], self.device)
                logger.info("车辆颜色识别模型加载成功")
            except Exception as e:
                logger.error(f"加载车辆颜色识别模型失败: {str(e)}")
                # 车辆颜色识别模型也是必需的
                return {
                    "success": False,
                    "message": f"加载车辆颜色识别模型失败: {str(e)}"
                }
            
            # 更新状态
            self.model_loaded = True
            logger.info("车牌识别服务初始化完成！")
            
            return {
                "success": True,
                "message": "车牌识别服务初始化成功",
                "device": str(self.device),
                "models": list(self.models.keys()),
                "startup_time": self.startup_time
            }
            
        except Exception as e:
            logger.error(f"初始化车牌识别服务过程中发生错误: {str(e)}")
            return {
                "success": False,
                "message": f"初始化错误: {str(e)}"
            }
    
    def _check_model_files(self) -> list:
        """
        检查所需的模型文件是否存在
        
        返回:
            list: 不存在的模型文件列表
        """
        missing_models = []
        
        for name, path in WEIGHTS.items():
            if not os.path.exists(path):
                missing_models.append(name)
                logger.warning(f"模型文件不存在: {name} - {path}")
        
        return missing_models
    
    def _preprocess_image(self, image):
        """
        对输入图像进行预处理，提高车牌检测率
        
        参数:
            image: OpenCV格式的图像
            
        返回:
            处理后的图像
        """
        try:
            # 检查图像是否为空
            if image is None or image.size == 0:
                logger.error("输入图像为空，无法预处理")
                return image
            
            # 创建图像副本，不修改原始图像
            processed_img = image.copy()
            
            # 1. 调整亮度和对比度
            alpha = 1.2  # 对比度增强因子
            beta = 5    # 亮度增加值
            processed_img = cv2.convertScaleAbs(processed_img, alpha=alpha, beta=beta)
            logger.debug(f"调整亮度和对比度: alpha={alpha}, beta={beta}")
            
            # 2. 应用自适应直方图均衡化 (CLAHE) - 增强图像细节
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            
            # 转换为LAB颜色空间，只对亮度通道应用CLAHE
            lab = cv2.cvtColor(processed_img, cv2.COLOR_BGR2LAB)
            lab_planes = list(cv2.split(lab))
            lab_planes[0] = clahe.apply(lab_planes[0])  # 应用于亮度通道
            lab = cv2.merge(lab_planes)
            processed_img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            logger.debug("应用CLAHE增强图像细节")
            
            # 3. 锐化处理 - 使车牌轮廓更清晰
            kernel_sharpen = np.array([[-1, -1, -1],
                                      [-1, 9, -1],
                                      [-1, -1, -1]])
            processed_img = cv2.filter2D(processed_img, -1, kernel_sharpen)
            logger.debug("应用锐化处理增强边缘")
            
            # 4. 创建多尺度版本进行尝试
            h, w = processed_img.shape[:2]
            # 创建不同缩放比例的图像
            scales = [1.0]  # 原始尺寸
            
            # 亮度图像质量较差时添加其他比例
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            
            if brightness < 100:  # 低亮度图像
                scales.extend([0.8, 1.2])  # 添加额外的缩放比例
                logger.debug(f"添加额外缩放比例处理低亮度图像 (亮度={brightness:.2f})")
            
            # 记录处理过程
            logger.info(f"图像预处理完成: 亮度={brightness:.2f}, 使用{len(scales)}个缩放比例")
            
            return processed_img
            
        except Exception as e:
            logger.error(f"图像预处理过程中出错: {str(e)}")
            return image  # 出错时返回原始图像
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取车牌识别服务状态
        
        返回:
            Dict[str, Any]: 服务状态信息
        """
        return {
            "running": self.model_loaded,
            "model_loaded": self.model_loaded,
            "device": str(self.device),
            "uptime": time.time() - self.startup_time if self.model_loaded else 0,
            "version": "1.0.0",
            "mode": "integrated",
            "models": list(self.models.keys()) if self.model_loaded else []
        }
    
    # 为兼容车牌监控功能，恢复图片识别方法
    def recognize_image(self, image, conf_thres=0.5):
        """
        识别图片中的车牌
        Args:
            image: OpenCV格式的图像
            conf_thres: 检测置信度阈值，默认为0.5
        Returns:
            字典，包含识别结果
        """
        try:
            if not self.model_loaded:
                return {
                    "success": False,
                    "message": "模型未加载",
                    "plates": []
                }
                
            # 导入检测模块
            from .detector.detector import detect_Recognition_plate, draw_result
            import cv2
            import os
            import time
            
            # 确保图像有效
            if image is None or image.size == 0:
                return {
                    "success": False,
                    "message": "无效的图像",
                    "plates": []
                }
            
            # 调用检测函数
            detect_model = self.models.get('plate_detect')
            plate_rec_model = self.models.get('plate_rec')
            car_rec_model = self.models.get('car_rec')
            
            # 检查并输出当前加载的模型情况
            logger.info(f"当前已加载模型: {list(self.models.keys())}")
            
            # 检查模型是否正确加载
            if detect_model is None:
                logger.error(f"车牌检测模型加载失败! 已加载模型: {list(self.models.keys())}")
                return {
                    "success": False,
                    "message": "车牌检测模型未加载",
                    "plates": []
                }
            
            if plate_rec_model is None:
                logger.error("车牌识别模型加载失败!")
                return {
                    "success": False,
                    "message": "车牌识别模型未加载",
                    "plates": []
                }
            
            # 图像预处理和检测
            try:
                # 记录输入图像信息
                logger.info(f"准备识别图像: shape={image.shape}, dtype={image.dtype}, range=[{image.min()}-{image.max()}]")
                
                # 记录使用的置信度阈值
                logger.info(f"使用置信度阈值: {conf_thres}")
                
                # 导入完整的函数定义，检查是否支持conf_thres参数
                import inspect
                # 进行图像预处理和增强，提高检测成功率
                processed_image = self._preprocess_image(image)
                
                detect_func_params = inspect.signature(detect_Recognition_plate).parameters
                
                # 记录图像质量信息
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                blurness = cv2.Laplacian(gray, cv2.CV_64F).var()
                logger.info(f"图像清晰度指标: {blurness:.2f} (数值越大越清晰)")
                
                # 将置信度阈值调整到0.4，平衡检测率和准确度
                lowered_conf_thres = 0.4  # 提高阈值以增加置信度
                logger.info(f"使用调整后的置信度阈值 {lowered_conf_thres} 进行检测")
                
                # 调用检测函数，使用降低的置信度阈值提高检测率
                results = []
                # 先尝试使用预处理后的图像进行检测
                if 'conf_thres' in detect_func_params:
                    results = detect_Recognition_plate(
                        detect_model, 
                        processed_image, 
                        self.device, 
                        plate_rec_model, 
                        640,
                        car_rec_model,
                        conf_thres=lowered_conf_thres
                    )
                else:
                    results = detect_Recognition_plate(
                        detect_model, 
                        processed_image, 
                        self.device, 
                        plate_rec_model, 
                        640,
                        car_rec_model
                    )
                    logger.warning("detect_Recognition_plate函数不支持conf_thres参数，使用默认置信度阈值")
                
                # 检查结果
                logger.info(f"车牌检测结果: 检测到{len(results)}个区域")
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"车牌识别时出错: {str(e)}")
                logger.debug(f"错误详情:\n{error_details}")
                return {
                    "success": False,
                    "message": f"车牌检测失败: {str(e)}",
                    "plates": []
                }
            
            if not results or len(results) == 0:
                return {
                    "success": False,
                    "message": "未检测到车牌",
                    "plates": []
                }
                
            # 格式化检测结果
            plates = []
            
            # 记录原始结果细节，帮助调试
            logger.debug(f"检测原始结果: {results}")
            
            for i, result in enumerate(results):
                # 检查结果有效性
                if 'plate_no' not in result:
                    # 只有当检测到的区域较少时才输出警告，避免过多日志
                    if len(results) <= 10:
                        logger.warning(f"第{i+1}个结果缺少车牌号码信息")
                    continue
                
                # 跳过空的或无效的车牌号码结果
                plate_no = result.get('plate_no', '')
                
                # 1. 过滤空车牌
                if not plate_no:
                    if len(results) <= 10:
                        logger.warning(f"第{i+1}个结果的车牌号码为空，跳过")
                    continue
                    
                # 2. 过滤'未知'车牌 
                if plate_no == '未知':
                    if len(results) <= 10:
                        logger.warning(f"第{i+1}个结果的车牌号码为'未知'，跳过")
                    continue
                
                # 3. 过滤短车牌
                if len(plate_no) <= 5:
                    if len(results) <= 10:
                        logger.warning(f"第{i+1}个结果的车牌号码过短 [{plate_no}](长度{len(plate_no)})，跳过")
                    continue
                    
                logger.info(f"处理第{i+1}个检测结果: 车牌={plate_no}, "
                           f"置信度={result.get('score', 0.0)}, 类型={result.get('class_type', '未知')}")
                
                # 获取车牌坐标
                box = [0, 0, 0, 0]
                if 'rect' in result:
                    rect = result['rect']
                    box = [int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])]
                    logger.debug(f"车牌坐标: [{box[0]}, {box[1]}, {box[2]}, {box[3]}]")
                
                plate_info = {
                    "plate_no": plate_no if plate_no != '未知' else "",
                    "confidence": float(result.get('score', 0.0)),
                    "box": box,
                    "color": result.get('plate_color', ''),
                    "car_color": result.get('car_color', ''),  # 增加车辆颜色字段
                    "color_confidence": float(result.get('color_confidence', 0.0))  # 增加颜色置信度
                }
                plates.append(plate_info)
            
            # 绘制结果
            visualized_img = draw_result(image.copy(), results)
            
            # 保存可视化结果
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    "static", "plate_monitoring")
            os.makedirs(output_dir, exist_ok=True)
            timestamp = int(time.time())
            output_path = os.path.join(output_dir, f"recognized_{timestamp}.jpg")
            cv2.imwrite(output_path, visualized_img)
            
            return {
                "success": True,
                "message": "识别成功",
                "plates": plates,
                "visualized_image": output_path
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"识别失败: {str(e)}\n{error_details}")
            return {
                "success": False,
                "message": f"识别失败: {str(e)}",
                "plates": []
            }
