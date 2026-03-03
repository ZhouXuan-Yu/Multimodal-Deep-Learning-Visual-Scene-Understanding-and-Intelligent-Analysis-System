"""
火灾检测服务模块
从Fire-Detection-UAV项目整合的火灾检测功能
"""
import os
import cv2
import time
import logging
import traceback
import numpy as np
from datetime import datetime
import shutil

# 导入报警模块
from app.services.fire_detection.fire_alarm import FireAlarmManager

# 尝试导入PyTorch和YOLOv8
TORCH_AVAILABLE = False
YOLO_AVAILABLE = False
try:
    import torch
    TORCH_AVAILABLE = True
    # 我们在函数内部导入YOLO以避免未使用的导入警告
    # 但这里检查导入是否可用
    import importlib.util
    if importlib.util.find_spec("ultralytics") is not None:
        YOLO_AVAILABLE = True
except ImportError:
    pass

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入PyTorch
try:
    import torch
    TORCH_AVAILABLE = True
    
    # 设置GPU
    if torch.cuda.is_available():
        DEVICE = 'cuda'
        logger.info(f"Found GPU device: {torch.cuda.get_device_name()}")
    else:
        DEVICE = 'cpu'
        logger.info("No GPU device found, using CPU")
        
except ImportError:
    TORCH_AVAILABLE = False
    DEVICE = 'cpu'
    logger.warning("PyTorch not available, will use alternative methods for fire detection")

# 模型路径
# 当前文件位于: .../ModelService/Main/app/services/fire_detection/fire_detector.py
# 只需向上回溯 3 级到 Main 目录，再进入 models/fire_detection
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))  # 指向 Main 目录
MODEL_DIR = os.path.join(BASE_DIR, "models", "fire_detection")

# 确保模型目录存在，便于你直接把权重文件放到这个目录
os.makedirs(MODEL_DIR, exist_ok=True)

# 模型路径配置
# 分类模型路径 (YOLOv8格式)
CLASSIFICATION_MODEL_PATH = os.path.join(MODEL_DIR, "fire_classification_model.h5.pt")

# 分割模型路径 (YOLOv8格式)
SEGMENTATION_MODEL_PATH = os.path.join(MODEL_DIR, "fire_segmentation_model.h5.pt")

# 旧版 YOLOv5 烟雾/火焰检测模型路径
SMOKE_YOLOV5_MODEL_PATH = os.path.join(MODEL_DIR, "smoke.pt")

# 统一的 Fire + Smoke 检测模型权重路径
# 你可以把自己的 YOLO 权重文件（如 best.pt、yolov5s_best.pt 等）
# 放在 Main/models/fire_detection 目录下，名称任选，我们会自动检测
#
# 优先顺序：
# 1. 环境变量 FIRE_SMOKE_MODEL_PATH 显式指定
# 2. Main/models/fire_detection 目录下按下面列表依次查找
FIRE_SMOKE_CANDIDATE_NAMES = [
    #"yolov5s_best.pt",   # 你之前使用的名称
    #"best.pt",           # 常见默认名称
    "fire_smoke_v11.pt"  # 另一种可能的命名
]

# 为了向后兼容保留这两个变量（实际不再直接使用）
FIRE_SMOKE_MODEL_DEFAULT_PATH = os.path.join(MODEL_DIR, "fire_smoke_v11.pt")
FIRE_SMOKE_MODEL_ALT_PATH = FIRE_SMOKE_MODEL_DEFAULT_PATH

# 兼容旧代码
TENSORFLOW_AVAILABLE = False

# 图像处理配置
CLASSIFICATION_IMG_SIZE = (224, 224)  # 分类模型输入尺寸
SEGMENTATION_IMG_SIZE = (256, 256)    # 分割模型输入尺寸

# YOLOv8模型配置
# 我们不需要手动定义模型架构，因为YOLOv8已经有内置的模型架构

# YOLOv8适配器 - 集成自UAV火灾检测项目
class YOLOModelAdapter:
    """YOLOv8模型适配器，使其与现有系统兼容"""
    
    def __init__(self, model_path, model_type="detection", confidence_threshold=0.25):
        """
        初始化YOLOv8模型适配器
        
        Args:
            model_path: YOLO模型文件路径
            model_type: 模型类型，可以是"detection"、"classification"或"segmentation"
            confidence_threshold: 置信度阈值（默认 0.25，对应你的 detect.py 示例）
        """
        self.model_path = model_path
        self.model_type = model_type
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.logger = logging.getLogger(__name__ + ".YOLOModelAdapter")
        
        # 检查模型文件是否存在
        if not os.path.exists(model_path):
            self.logger.error(f"YOLO model file not found: {model_path}")
            raise FileNotFoundError(f"YOLO model file not found: {model_path}")
        
        # 加载YOLO模型
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.logger.info(f"Successfully loaded YOLO model: {model_path}, using device: {DEVICE}")
            # 将模型移至指定设备
            self.model.to(DEVICE)
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def predict(self, img_array, verbose=0):
        """
        使用YOLOv8模型进行预测，输出格式与原火灾检测系统兼容
        
        Args:
            img_array: 输入图像数组
            verbose: 详细程度
        
        Returns:
            预测结果，格式取决于模型类型
        """
        if self.model is None:
            raise ValueError("Model not loaded, cannot predict")
        
        # 确保输入格式正确
        if img_array.max() <= 1.0 and img_array.dtype == np.float32:
            img_array = (img_array * 255).astype(np.uint8)
        
        # 从批量数组中提取单张图像
        if len(img_array.shape) == 4:
            img = img_array[0]  # (height, width, 3)
        else:
            img = img_array  # 已经是单张图像
        
        # 根据模型类型进行预测
        if self.model_type == "detection" or self.model_type == "classification":
            # 目标检测模式
            results = self.model(img, verbose=False)
            return self._process_detection_results(results)
        
        elif self.model_type == "segmentation":
            # 分割模式
            results = self.model(img, verbose=False)
            return self._process_segmentation_results(results, img.shape[:2])
        
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def _process_detection_results(self, results):
        """
        处理YOLOv8目标检测/分类结果，转换为与原系统兼容的格式
        
        Args:
            results: YOLOv8检测结果
        
        Returns:
            兼容格式的检测结果
        """
        result = results[0]  # 获取第一张图像的结果
        
        # 检查是否是分类结果（有probs属性）
        if hasattr(result, 'probs') and result.probs is not None:
            # 这是分类结果
            probs = result.probs
            # 在二分类中，通常索引1是正类（火灾），索引0是负类（非火灾）
            if len(probs.data) >= 2:
                fire_prob = float(probs.data[1])
                no_fire_prob = float(probs.data[0])
            else:
                # 单类判断（仅火灾）
                fire_prob = float(probs.data[0])
                no_fire_prob = 1.0 - fire_prob
                
            return np.array([[no_fire_prob, fire_prob]])
        
        # 如果是目标检测结果
        if hasattr(result, 'boxes'):
            boxes = result.boxes
            
            # 查找与火/烟雾有关的检测结果
            fire_confidence = 0.0
            fire_detected = False
            
            # 只保留 fire / flame / smoke 且满足置信度阈值的框
            for box in boxes:
                try:
                    # 获取类别ID和置信度
                    cls_id = int(box.cls.item())
                    conf = float(box.conf.item())
                    # 获取类别名称
                    class_name = str(result.names[cls_id]).lower()
                except Exception:
                    continue
                
                # 置信度过滤
                if conf < self.confidence_threshold:
                    continue
                
                # 只保留 fire / flame / smoke 相关类别
                if not any(k in class_name for k in ["fire", "flame", "smoke"]):
                    continue
                
                if conf > fire_confidence:
                    fire_confidence = conf
                    fire_detected = True
            
            # 创建与分类模型输出兼容的格式
            if fire_detected:
                # 返回格式: [[no_fire_prob, fire_prob]]
                return np.array([[1.0 - fire_confidence, fire_confidence]])
            else:
                # 未检测到火灾或置信度太低
                return np.array([[1.0, 0.0]])
        
        # 如果既没有分类结果也没有检测结果，返回默认值
        return np.array([[1.0, 0.0]])
    
    def _process_segmentation_results(self, results, original_shape):
        """
        处理YOLOv8分割结果，转换为与原系统兼容的格式
        
        Args:
            results: YOLOv8分割结果
            original_shape: 原始图像形状(height, width)
        
        Returns:
            兼容格式的分割掩码
        """
        result = results[0]  # 获取第一张图像的结果
        
        # 创建空白掩码
        height, width = original_shape
        fire_mask = np.zeros((height, width, 1), dtype=np.float32)
        
        # 如果有分割掩码
        if hasattr(result, 'masks') and result.masks is not None:
            masks = result.masks
            boxes = result.boxes
            
            for i, (mask, box) in enumerate(zip(masks.data, boxes)):
                # 获取类别ID和置信度
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                
                # 获取类别名称
                class_name = result.names[cls_id]
                
                # 只处理与火相关的类别
                if ("fire" in class_name.lower() or 
                    "flame" in class_name.lower() or 
                    "smoke" in class_name.lower()) and conf >= self.confidence_threshold:
                    
                    # 调整掩码大小至原始图像尺寸
                    mask_np = mask.cpu().numpy()  # 转换为numpy数组
                    mask_np = cv2.resize(mask_np, (width, height))
                    
                    # 将掩码添加到综合火灾掩码中
                    fire_mask = np.maximum(fire_mask, mask_np[:,:,np.newaxis] * conf)
        
        # 返回与分割模型输出兼容的格式
        return fire_mask  # 形状为 (height, width, 1)
    
    def load_weights(self, weights_path):
        """为了与原系统接口兼容而提供的方法"""
        # YOLO模型已在初始化时加载，此方法仅为兼容API
        self.logger.info("YOLO model already loaded, no need to load weights separately")
        return True

    def to(self, device):
        """将模型移至指定设备"""
        if self.model is not None:
            self.model.to(device)
            return True
        return False


class SmokeYoloV5Detector:
    """
    基于旧版 YOLOv5 的烟雾/火焰检测模型封装
    参考 `models/fire_detection/1.py` 中的 `Smoke_File_Detector` 实现，
    去除 argparse 依赖，直接在代码中指定权重与参数。
    """

    def __init__(self, weights_path):
        # 延迟导入 YOLOv5 相关模块，避免环境中没有这些模块时直接导入失败
        try:
            from utils import torch_utils
            from models.experimental import attempt_load
            from utils.general import non_max_suppression, scale_coords
            from utils.datasets import letterbox
        except Exception as e:
            raise ImportError(f"加载 YOLOv5 依赖失败，请确认已将 YOLOv5 代码放入 Python 路径中: {e}")

        self.attempt_load = attempt_load
        self.non_max_suppression = non_max_suppression
        self.scale_coords = scale_coords
        self.letterbox = letterbox
        self.torch_utils = torch_utils

        # 与 1.py 中 argparse 参数保持一致的默认值
        self.weights = weights_path
        self.img_size = 640
        self.conf_thres = 0.25
        self.iou_thres = 0.45
        self.device_str = ""
        self.classes = None
        self.agnostic_nms = False
        self.augment = False

        # 初始化设备
        self.device = self.torch_utils.select_device(self.device_str)
        # half 精度仅在 CUDA 下可用
        self.half = self.device.type != "cpu"

        # 加载模型
        self.model = self.attempt_load(self.weights, map_location=self.device)
        # 确保输入尺寸是步长的倍数
        self.imgsz = int(self.img_size)
        if self.half:
            self.model.half()

        # 类别名称
        self.names = self.model.module.names if hasattr(self.model, "module") else self.model.names

    def detect(self, img):
        """
        对单张图像进行检测，返回与 1.py 相同风格的结果:
        [{'bbox': [x1, y1, x2, y2], 'label': str, 'conf': float}, ...]
        """
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            return []

        im0 = img
        # 仿照 1.py 中的预处理流程
        img_resized = self.letterbox(im0, new_shape=self.imgsz)[0]
        img_resized = img_resized[:, :, ::-1].transpose(2, 0, 1)  # BGR -> RGB, HWC -> CHW
        img_resized = np.ascontiguousarray(img_resized)

        import torch  # 局部导入，确保与主项目 torch 一致

        img_tensor = torch.from_numpy(img_resized).to(self.device)
        img_tensor = img_tensor.half() if self.half else img_tensor.float()  # uint8 -> fp16/32
        img_tensor /= 255.0
        if img_tensor.ndimension() == 3:
            img_tensor = img_tensor.unsqueeze(0)

        # 推理
        pred = self.model(img_tensor, augment=self.augment)[0]

        # NMS
        pred = self.non_max_suppression(
            pred,
            self.conf_thres,
            self.iou_thres,
            classes=self.classes,
            agnostic=self.agnostic_nms,
        )

        results = []
        det = pred[0]
        if det is not None and len(det):
            # 将坐标从推理尺寸缩放回原图尺寸
            det[:, :4] = self.scale_coords(img_tensor.shape[2:], det[:, :4], im0.shape).round()

            # 转到 CPU / numpy
            det = det.cuda().data.cpu().numpy()
            for *xyxy, conf, cls in det:
                label = self.names[int(cls)] if self.names is not None else str(int(cls))
                results.append(
                    {
                        "bbox": xyxy,  # [x1, y1, x2, y2]
                        "label": label,
                        "conf": float(conf),
                    }
                )

        return results

# 辅助函数，创建分类和分割模型适配器
def make_yolo_classification_model(model_path, confidence_threshold=0.5):
    """创建用于分类的YOLO模型适配器"""
    return YOLOModelAdapter(model_path, model_type="classification", confidence_threshold=confidence_threshold)

def make_yolo_segmentation_model(model_path, confidence_threshold=0.5):
    """创建用于分割的YOLO模型适配器"""
    return YOLOModelAdapter(model_path, model_type="segmentation", confidence_threshold=confidence_threshold)

class FireDetectionColorAnalysis:
    """
    基于颜色分析的火灾检测替代实现
    当TensorFlow/模型不可用时使用
    增强版支持火焰和烟雾检测
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".FireDetectionColorAnalysis")
        self.logger.info("Initializing color-based fire detector")
        # 初始化记录环境亮度的字典，用于环境适应性阈值调整
        self.env_brightness_history = []
        self.max_history_size = 10
        self.adaptive_threshold_enabled = True
    
    def detect_fire(self, image):
        """
        增强版火灾检测 - 使用多种颜色空间和形态学操作检测火灾和烟雾
        
        Args:
            image: 输入图像 (BGR格式的numpy数组)
            
        Returns:
            火灾检测结果和置信度分数
        """
        # 转换为BGR图像（如果是PIL图像）
        if not isinstance(image, np.ndarray):
            image = np.array(image)
            
        # 确保图像是BGR格式
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:
            image = image[:, :, :3]
            
        # 记录环境亮度，用于环境适应性阈值调整
        avg_brightness = np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        self.env_brightness_history.append(avg_brightness)
        if len(self.env_brightness_history) > self.max_history_size:
            self.env_brightness_history.pop(0)
            
        # 计算环境亮度自适应阈值
        if self.adaptive_threshold_enabled and len(self.env_brightness_history) > 3:
            avg_env_brightness = np.mean(self.env_brightness_history)
            brightness_factor = 1.0
            # 亮度补偿，使检测在不同亮度环境下都有好结果
            if avg_env_brightness < 50:  # 暗场景
                brightness_factor = 1.4  # 提高敏感度
            elif avg_env_brightness > 200:  # 非常亮的场景
                brightness_factor = 0.8  # 降低敏感度
        else:
            brightness_factor = 1.0
            
        # 增强图像对比度，使火源更明显
        adjusted = image.copy()
        adjusted = cv2.convertScaleAbs(adjusted, alpha=1.2, beta=10)
        
        # 转换为各种颜色空间
        hsv = cv2.cvtColor(adjusted, cv2.COLOR_BGR2HSV)
        ycrcb = cv2.cvtColor(adjusted, cv2.COLOR_BGR2YCrCb)
        lab = cv2.cvtColor(adjusted, cv2.COLOR_BGR2LAB)
        
        # 提取各通道
        h, s, v = cv2.split(hsv)
        y, cr, cb = cv2.split(ycrcb)
        lab_l, a, b_comp = cv2.split(lab)
        blue, green, red = cv2.split(adjusted)
        
        # 1. 火焰检测 - 增强版多规则火焰检测
        # 火焰具有红色/橙色分量高于绿色和蓝色
        rule1 = np.logical_and(red > green + 20, red > blue + 20)
        
        # 在HSV中的火焰条件：红-橙-黄色系
        # 红色范围 (0-30 或 150-180)
        rule2_h1 = np.logical_and(h >= 0, h <= 30)  # 红色到橙色
        rule2_h2 = np.logical_and(h >= 150, h <= 180)  # 粉红色
        rule2_h = np.logical_or(rule2_h1, rule2_h2)  
        
        # 饱和度和亮度都较高
        rule2_s = s > 100  # 饱和度阈值
        rule2_v = v > 150  # 亮度阈值
        
        rule2 = np.logical_and(rule2_h, np.logical_or(rule2_s, rule2_v))
        
        # 使用YCrCb的Cr分量识别红色区域
        rule3 = cr > 135
        
        # 使用LAB空间的a分量检测红色
        rule4 = a > 130  # a表示红色-绿色分量
        
        # 组合规则 - 更宽松的组合方式
        # 满足以下条件之一即可：颜色特征和HSV特征，或者YCrCb特征和LAB特征
        fire_pixels_strict = np.logical_and(np.logical_and(rule1, rule2), np.logical_or(rule3, rule4))
        fire_pixels_loose = np.logical_or(np.logical_and(rule1, rule2), np.logical_and(rule3, rule4))
        
        # 组合严格和宽松条件 
        fire_pixels = np.logical_or(fire_pixels_strict, fire_pixels_loose)
        
        # 2. 烟雾检测 - 新增功能
        # 烟雾通常是灰色/白色，饱和度低，与周围区域对比度低
        
        # 灰度图像进行高斯滤波减少噪声
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 自适应阈值，查找潜在的烟雾区域
        binary = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        
        # 烟雾颜色特征 - 灰色/白色，低饱和度
        smoke_rule1 = s < 40  # 低饱和度
        smoke_rule2 = v > 150  # 高亮度
        smoke_rule3 = np.logical_and(blue > 100, np.logical_and(green > 100, red > 100))  # 灰白色
        smoke_rule4 = np.abs(blue.astype(np.int32) - red.astype(np.int32)) < 30  # 颜色通道差异小
        
        # 组合烟雾规则
        smoke_pixels = np.logical_and(
            np.logical_and(smoke_rule1, smoke_rule2),
            np.logical_and(smoke_rule3, smoke_rule4)
        )
        
        # 应用动态阈值调整
        if self.adaptive_threshold_enabled:
            if brightness_factor != 1.0:
                # 调整火灾和烟雾像素的检测阈值
                kernel_size = 5 if brightness_factor > 1.0 else 3  # 暗场景使用更大的核
                fire_pixels = fire_pixels.astype(np.uint8) * 255
                fire_pixels = cv2.dilate(fire_pixels, np.ones((kernel_size, kernel_size), np.uint8))
                fire_pixels = fire_pixels > 128
                
                smoke_pixels = smoke_pixels.astype(np.uint8) * 255
                smoke_pixels = cv2.dilate(smoke_pixels, np.ones((kernel_size, kernel_size), np.uint8))
                smoke_pixels = smoke_pixels > 128
        
        # 3. 构建最终火灾掩码
        # 将火焰和烟雾结合
        combined_mask = np.logical_or(fire_pixels, smoke_pixels)
        
        # 计算火灾百分比
        fire_percentage_strict = np.mean(fire_pixels_strict) * 100 * brightness_factor
        fire_percentage_loose = np.mean(fire_pixels_loose) * 100 * brightness_factor
        smoke_percentage = np.mean(smoke_pixels) * 100 * brightness_factor * 0.7  # 烟雾置信度权重低于火焰
        
        # 加权计算火灾像素百分比
        fire_percentage = max(fire_percentage_strict * 1.5, 
                             fire_percentage_loose * 0.8, 
                             smoke_percentage * 0.5)  # 火焰>宽松火焰>烟雾的权重
        
        # 判断火灾 - 使用自适应阈值
        # 注意: fire_percentage 是「百分比」(0-100)，之前这里用 0.5 导致阈值只有 0.5%，
        # 实际效果就是几乎任何一点火/亮色都会被判为有火，误报非常严重。
        # 这里将基础阈值提升到 3%，并保留暗场景稍微更敏感、亮场景更保守的特性。
        base_threshold = 3.0  # 基础阈值: 至少有 3% 像素满足火/烟规则才认为有火
        if self.adaptive_threshold_enabled:
            # 暗场景 (brightness_factor > 1.0) -> 阈值略降低；亮场景 (brightness_factor < 1.0) -> 阈值略升高
            adaptive_threshold = base_threshold / brightness_factor
        else:
            adaptive_threshold = base_threshold
        fire_detected = fire_percentage > adaptive_threshold
        
        # 计算最终置信度
        # 将 fire_percentage 从「面积比例」映射到 0-1 之间的置信度，并适度放大但不过饱和
        # 比如 fire_percentage=3% -> ~0.3, 10% -> ~0.8, >=15% -> 接近 1.0
        confidence = min(fire_percentage / 3.5, 1.0)
        
        # 创建火灾掩码（分割结果）和烟雾掩码
        fire_mask = np.zeros_like(image[:, :, 0], dtype=np.uint8)
        fire_mask[fire_pixels] = 255
        
        smoke_mask = np.zeros_like(image[:, :, 0], dtype=np.uint8)
        smoke_mask[smoke_pixels] = 255
        
        # 组合掩码
        combined_mask_uint8 = np.zeros_like(image[:, :, 0], dtype=np.uint8)
        combined_mask_uint8[combined_mask] = 255
        
        # 应用形态学操作去除噪点并连接碎片区域
        kernel = np.ones((3, 3), np.uint8)  # 较小的核，保留更多细节
        fire_mask = cv2.morphologyEx(fire_mask, cv2.MORPH_OPEN, kernel)  # 去除噪点
        smoke_mask = cv2.morphologyEx(smoke_mask, cv2.MORPH_OPEN, kernel)  # 去除噪点
        
        kernel = np.ones((7, 7), np.uint8)  # 较大的核，连接区域
        fire_mask = cv2.morphologyEx(fire_mask, cv2.MORPH_CLOSE, kernel)  # 连接临近区域
        smoke_mask = cv2.morphologyEx(smoke_mask, cv2.MORPH_CLOSE, kernel)  # 连接临近区域
        combined_mask_uint8 = cv2.morphologyEx(combined_mask_uint8, cv2.MORPH_CLOSE, kernel)
        
        # 创建可视化结果用于调试
        fire_highlighted = adjusted.copy()
        fire_highlighted[fire_pixels] = [0, 0, 255]  # 红色标记火灾区域
        fire_highlighted[smoke_pixels] = [255, 255, 0]  # 青色标记烟雾区域
        
        # 查找火区/烟雾边界框（只返回框，不再依赖掩膜可视化）
        fire_regions = []
        frame_area = float(image.shape[0] * image.shape[1]) if image.size > 0 else 1.0
        # 动态面积阈值，过滤掉非常小的噪声框
        min_fire_region_ratio = 0.003  # 火焰区域至少占整幅图的 0.3%
        min_smoke_region_ratio = 0.005  # 烟雾区域至少占整幅图的 0.5%
        min_fire_area = max(300.0, frame_area * min_fire_region_ratio)
        min_smoke_area = max(500.0, frame_area * min_smoke_region_ratio)

        # 查找火区边界框
        if np.any(fire_pixels):
            fire_contours, _ = cv2.findContours(fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in fire_contours:
                area = cv2.contourArea(contour)
                # 过滤掉太小的火焰区域，避免出现大量小碎片框
                if area < min_fire_area:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                area_percentage = (area / frame_area) * 100
                fire_regions.append({
                    'bbox': (x, y, w, h),
                    'type': 'fire',
                    'confidence': confidence,
                    'area_percentage': area_percentage
                })
        
        # 查找烟雾边界框
        if np.any(smoke_pixels):
            smoke_contours, _ = cv2.findContours(smoke_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in smoke_contours:
                area = cv2.contourArea(contour)
                # 烟雾区域要求更大一些，同样过滤掉小噪声
                if area < min_smoke_area:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                area_percentage = (area / frame_area) * 100
                fire_regions.append({
                    'bbox': (x, y, w, h),
                    'type': 'smoke',
                    'confidence': smoke_percentage / 100.0,
                    'area_percentage': area_percentage
                })
        
        self.logger.info(f"Fire detection: detected={fire_detected}, confidence={confidence:.2f}, percentage={fire_percentage:.2f}%, smoke={smoke_percentage:.2f}%")
        
        return {
            'fire_detected': fire_detected,
            'confidence': confidence,
            'mask': combined_mask_uint8,
            'fire_mask': fire_mask,
            'smoke_mask': smoke_mask,
            'fire_area_percentage': fire_percentage / 100.0,
            'smoke_area_percentage': smoke_percentage / 100.0,
            'highlighted_image': fire_highlighted,
            'method': 'color_analysis_enhanced',
            'fire_regions': fire_regions,
            'env_brightness': avg_brightness
        }
        
    def highlight_fire(self, image, mask, smoke_mask=None, alpha=0.5):
        """
        在原始图像上突出显示火灾和烟雾区域
        
        Args:
            image: 原始图像
            mask: 火灾掩码
            smoke_mask: 烟雾掩码（可选）
            alpha: 混合因子
            
        Returns:
            突出显示火灾区域的图像
        """
        # 确保图像是BGR格式
        if not isinstance(image, np.ndarray):
            image = np.array(image)
        
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:
            image = image[:, :, :3]
            
        # 创建高亮图像
        highlighted = image.copy()
        
        # 如果有火灾掩码，用红色高亮火灾区域
        if mask is not None and np.any(mask):
            red_overlay = np.zeros_like(image)
            red_overlay[:, :, 2] = mask  # 红色通道
            highlighted = cv2.addWeighted(highlighted, 1.0, red_overlay, alpha, 0)
        
        # 如果有烟雾掩码，用蓝色高亮烟雾区域
        if smoke_mask is not None and np.any(smoke_mask):
            blue_overlay = np.zeros_like(image)
            blue_overlay[:, :, 0] = smoke_mask  # 蓝色通道
            highlighted = cv2.addWeighted(highlighted, 1.0, blue_overlay, alpha * 0.6, 0)  # 烟雾的透明度稍低
        
        return highlighted

class FireDetector:
    """火灾检测器，使用YOLOv8模型进行火灾检测和分割"""
    
    def __init__(self):
        """初始化火灾检测器，使用错误捕获和日志记录以提高稳定性"""
        # 初始化基本属性
        self.logger = logging.getLogger(__name__)
        self.classification_model = None
        self.segmentation_model = None
        self.models_loaded = False
        # 统一的 YOLO 火焰 + 烟雾 检测模型
        self.yolo_model = None
        # 旧版 YOLOv5 烟雾/火焰检测模型
        self.smoke_detector = None
        # 默认置信度阈值（适当调高，减少低置信度乱框）
        # 想要更灵敏可以在实例化后修改 self.yolo_conf_threshold
        self.yolo_conf_threshold = 0.5
        
        # 初始化结果字典
        self.result_template = {
            'fire_detected': False,
            'confidence': 0.0,
            'highlighted_image': None,
            'mask': None,
            'method': 'none'
        }
        
        # 初始化颜色分析器（作为模型不可用时的后备方案）
        self.color_analyzer = FireDetectionColorAnalysis()
        
        # 使用try-except包裹初始化代码以捕获所有可能的异常
        try:
            self.logger.info("Starting to initialize fire detector...")
            
            # 检查是否有GPU可用
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
                self.logger.info(f"Found GPU device: {torch.cuda.get_device_name()}")
            else:
                self.device = torch.device('cpu')
                self.logger.info("No GPU device found, using CPU")
            
            # 初始化模型变量
            self.classification_model = None
            self.segmentation_model = None
            
            # 模型是否可用的标志
            self.classification_available = False
            self.segmentation_available = False
            
            # 模型配置
            self.classification_model_path = CLASSIFICATION_MODEL_PATH
            self.segmentation_model_path = SEGMENTATION_MODEL_PATH
            
            # 检查模型文件是否存在
            if os.path.exists(self.segmentation_model_path):
                self.logger.info(f"Found segmentation model file: {self.segmentation_model_path}, size: {os.path.getsize(self.segmentation_model_path) / (1024*1024):.2f} MB")
                self.segmentation_available = True
            else:
                self.logger.warning(f"Segmentation model file not found: {self.segmentation_model_path}")
                
            if os.path.exists(self.classification_model_path):
                self.logger.info(f"Found classification model file: {self.classification_model_path}, size: {os.path.getsize(self.classification_model_path) / (1024*1024):.2f} MB")
                self.classification_available = True
            else:
                self.logger.warning(f"Classification model file not found: {self.classification_model_path}")

            # 检查PyTorch和YOLO是否可用
            if TORCH_AVAILABLE and YOLO_AVAILABLE:
                self.logger.info("PyTorch and YOLO available - trying to preload models")

                # 1) 优先加载单一的 Fire + Smoke YOLO 检测模型（Roboflow Universe best.pt 等）
                try:
                    from ultralytics import YOLO
                    env_path = os.environ.get("FIRE_SMOKE_MODEL_PATH")
                    candidate_paths = []
                    load_errors = []

                    # 1. 明确指定的环境变量路径（最高优先级）
                    if env_path:
                        candidate_paths.append(env_path)

                    # 2. 自动在模型目录下按常见文件名进行扫描
                    for name in FIRE_SMOKE_CANDIDATE_NAMES:
                        candidate_paths.append(os.path.join(MODEL_DIR, name))

                    loaded_path = None
                    for model_path in candidate_paths:
                        if model_path and os.path.exists(model_path):
                            self.logger.info(f"Loading unified fire+smoke YOLO model from: {model_path}")
                            try:
                                model = YOLO(model_path)
                                model.to(DEVICE)
                            except Exception as e:
                                err = str(e)
                                load_errors.append(f"{model_path}: {err}")
                                # 常见：某些 YOLOv5/自定义训练权重在 pickle 反序列化时依赖训练代码里的模块路径
                                # 例如：No module named 'utilss.autoanchor'（模块名拼写/路径不一致）
                                if "utilss.autoanchor" in err:
                                    self.logger.error(
                                        "Detected incompatible YOLO weights format: "
                                        f"{model_path} requires module 'utilss.autoanchor'. "
                                        "This usually means the .pt was saved with custom code/modules and cannot be "
                                        "loaded by Ultralytics YOLO in this environment. "
                                        "Try using another weight file (e.g. best.pt) or re-export weights."
                                    )
                                self.logger.error(
                                    f"Failed to load unified fire+smoke YOLO model from {model_path}: {err}"
                                )
                                continue

                            self.yolo_model = model
                            loaded_path = model_path
                            break

                    if self.yolo_model is not None:
                        self.logger.info(f"Unified fire+smoke YOLO model loaded successfully from {loaded_path}")
                    else:
                        if load_errors:
                            self.logger.error(
                                "Unified fire+smoke YOLO model weights were found but failed to load.\n"
                                f"  - Checked directory: {MODEL_DIR}\n"
                                f"  - Candidate file names: {', '.join(FIRE_SMOKE_CANDIDATE_NAMES)}\n"
                                "  - Load errors (first few):\n"
                                + "\n".join([f"    - {x}" for x in load_errors[:5]])
                            )
                        else:
                            self.logger.error(
                                "Unified fire+smoke YOLO model not found.\n"
                                f"  - Checked directory: {MODEL_DIR}\n"
                                f"  - Candidate file names: {', '.join(FIRE_SMOKE_CANDIDATE_NAMES)}\n"
                                "  - You can either:\n"
                                "    1) Put your YOLO weights into this directory with one of the above names, or\n"
                                "    2) Set environment variable FIRE_SMOKE_MODEL_PATH to the full path of your .pt file."
                            )
                except Exception as e:
                    self.logger.error(f"Failed to load unified fire+smoke YOLO model: {str(e)}")

                # 2) 兼容旧的分割模型预加载逻辑（如果仍然存在）
                if self.segmentation_available:
                    try:
                        self._load_segmentation_yolo_model()
                        self.logger.info("Successfully preloaded segmentation model")
                    except Exception as e:
                        self.logger.error(f"Failed to preload segmentation model: {str(e)}")
            else:
                self.logger.warning("PyTorch or YOLO not available, will use color analysis method")

            # 无论 YOLOv8 是否可用，尽量尝试加载旧版 smoke.pt YOLOv5 模型，作为优先生效的模型
            if os.path.exists(SMOKE_YOLOV5_MODEL_PATH):
                try:
                    self.logger.info(f"尝试加载旧版 YOLOv5 烟雾/火焰模型: {SMOKE_YOLOV5_MODEL_PATH}")
                    self.smoke_detector = SmokeYoloV5Detector(SMOKE_YOLOV5_MODEL_PATH)
                    self.logger.info("旧版 YOLOv5 烟雾/火焰模型加载成功，将优先用于火灾/烟雾检测")
                except Exception as e:
                    self.logger.error(
                        f"加载旧版 YOLOv5 烟雾/火焰模型失败: {str(e)}，将继续使用其它检测方式（若可用）"
                    )
            else:
                self.logger.warning(
                    f"未找到旧版 YOLOv5 模型文件 smoke.pt，期望路径: {SMOKE_YOLOV5_MODEL_PATH}"
                )

            self.logger.info("Fire detector initialization completed")
        except Exception as e:
            self.logger.error(f"Error initializing fire detector: {str(e)}")
            stack_trace = traceback.format_exc()
            self.logger.error(f"Stack trace:\n{stack_trace}")
            # 不抛出异常，允许对象创建，但功能可能受限
            if not YOLO_AVAILABLE:
                self.logger.warning("YOLOv8 library not available, will use color-based fire detection method")
            if not TORCH_AVAILABLE:
                self.logger.warning("PyTorch not available, will use color-based fire detection method")

        # 初始化完成后，如果 YOLO 模型依然为空，给出一次性明确错误日志
        if getattr(self, "yolo_model", None) is None:
            self.logger.error(
                "FireDetector initialized but YOLO model is NOT loaded.\n"
                f"  - Expected directory: {MODEL_DIR}\n"
                f"  - Candidate file names: {', '.join(FIRE_SMOKE_CANDIDATE_NAMES)}\n"
                "  - Or set FIRE_SMOKE_MODEL_PATH to your weight file path.\n"
                "  => YOLO 火焰/烟雾检测将不可用（会尝试回退到颜色/分类/分割流水线，如果已启用）。"
            )
            
        # 视频处理参数
        self.last_frame_time = 0
        self.frame_count = 0
        self.fps = 0
        
        # 报警系统
        self.alarm_manager = None

    def _load_classification_yolo_model(self):
        """加载YOLOv8火灾分类模型"""
        try:
            self.logger.info(f"Starting to load YOLOv8 classification model: {self.classification_model_path}")
            
            # 使用适配器加载YOLOv8模型
            self.classification_model = make_yolo_classification_model(
                self.classification_model_path, 
                confidence_threshold=0.3  # 降低阈值以增加检测灵敏度
            )
            
            self.logger.info(f"YOLOv8 classification model loaded successfully, using device: {DEVICE}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load YOLOv8 classification model: {str(e)}")
            self.classification_model = None
            return False
            
    def _load_segmentation_yolo_model(self):
        """加载YOLOv8火灾分割模型"""
        try:
            self.logger.info(f"Starting to load YOLOv8 segmentation model: {self.segmentation_model_path}")
            
            # 使用适配器加载YOLOv8分割模型
            self.segmentation_model = make_yolo_segmentation_model(
                self.segmentation_model_path,
                confidence_threshold=0.2  # 降低阈值以增加检测灵敏度
            )
            
            self.logger.info(f"YOLOv8 segmentation model loaded successfully, using device: {DEVICE}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load YOLOv8 segmentation model: {str(e)}")
            self.segmentation_model = None
            return False

    def process_video(self, video_path, output_path=None, mode="both", display=False, 
                      threshold=0.5, save_frames=False, frames_dir=None, 
                      enable_alarm=False, receiver_email=None, alarm_interval=60, alarm_threshold=0.6,
                      frame_skip=5):  # Frame skip parameter, default is 5, process 1 frame every 5 frames
        """
        Process video file
        
        Args:
            video_path: Video file path
            output_path: Output video path, default None (don't save)
            mode: Processing mode, can be "classification", "segmentation", "both"
            display: Whether to display processing (disabled in server environment)
            threshold: Detection threshold
            save_frames: Whether to save key frames
            frames_dir: Frame save directory
            enable_alarm: Whether to enable alarm
            receiver_email: Alarm receiving email
            alarm_interval: Alarm interval (seconds)
            alarm_threshold: Alarm threshold
            frame_skip: Number of frames to skip (process 1 frame every N frames)
            
        Returns:
            Dictionary of processing results
        """
        if not os.path.exists(video_path):
            self.logger.error(f"Video file not found: {video_path}")
            return {"success": False, "error": "Video file not found"}
        
        # Basic validation of the video file
        try:
            # Get file size
            file_size = os.path.getsize(video_path)
            self.logger.info(f"Video file size: {file_size/1024/1024:.2f}MB")
            
            # Check if file is empty
            if file_size == 0:
                self.logger.error("Video file is empty")
                return {"success": False, "error": "Video file is empty"}
        except Exception as e:
            self.logger.error(f"Video file validation failed: {str(e)}")
            return {"success": False, "error": f"Video file validation failed: {str(e)}"}
            
        # Open video file
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.logger.error(f"Failed to open video: {video_path}")
                return {"success": False, "error": "Failed to open video file, possibly format not supported"}
        except Exception as e:
            self.logger.error(f"Failed to open video: {str(e)}")
            return {"success": False, "error": f"Failed to open video: {str(e)}"}
            
        # Get video information
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Validate video properties
            if fps <= 0 or frame_width <= 0 or frame_height <= 0 or total_frames <= 0:
                self.logger.error(f"Video format exception: fps={fps}, width={frame_width}, height={frame_height}, total frames={total_frames}")
                cap.release()
                return {"success": False, "error": "Video format exception, please provide standard MP4 or AVI format video file"}
                
            self.logger.info(f"Video information: {frame_width}x{frame_height}, {fps}fps, {total_frames} frames")
        except Exception as e:
            self.logger.error(f"Failed to get video information: {str(e)}")
            cap.release()
            return {"success": False, "error": f"Failed to get video information: {str(e)}"}
        
        # Prepare output video
        video_writer = None
        if output_path:
            try:
                # Ensure output directory exists
                output_dir = os.path.dirname(output_path)
                os.makedirs(output_dir, exist_ok=True)
                
                # 优化视频编码器选择以提高浏览器兼容性
                # 首先检查输出路径的文件扩展名
                _, ext = os.path.splitext(output_path)
                ext = ext.lower()
                
                # 根据文件扩展名选择合适的编码器
                if ext == '.mp4':
                    # 优先尝试的编码器列表 - MP4容器
                    codecs_to_try = ['avc1', 'H264', 'mp4v']
                elif ext == '.avi':
                    # AVI容器优先尝试MJPG或XVID编码器
                    codecs_to_try = ['MJPG', 'XVID']
                else:
                    # 默认使用MP4和H.264
                    codecs_to_try = ['avc1', 'H264', 'mp4v']
                    # 确保输出文件扩展名为.mp4
                    if not output_path.lower().endswith('.mp4'):
                        output_path = os.path.splitext(output_path)[0] + '.mp4'
                
                # 如果宽度或高度不是偶数，调整为偶数（H.264要求）
                if frame_width % 2 != 0:
                    frame_width -= 1
                if frame_height % 2 != 0:
                    frame_height -= 1
                
                # 计算有效的帧率（跳帧后）
                effective_fps = max(fps / frame_skip, 1)  # 确保最低1fps
                self.logger.info(f"设置输出视频参数: {frame_width}x{frame_height}, {effective_fps}fps, 编码器优先级: {codecs_to_try}")
                
                # 尝试不同的编码器
                video_writer_created = False
                
                # 尝试每个编码器
                for codec in codecs_to_try:
                    try:
                        fourcc = cv2.VideoWriter_fourcc(*codec)
                        
                        # 为每个编码器创建特定的临时输出路径
                        if codec == codecs_to_try[0]:  # 第一个编码器尝试直接使用指定的输出路径
                            tmp_output = output_path
                        else:
                            # 其他编码器使用临时文件
                            base, ext = os.path.splitext(output_path)
                            tmp_output = f"{base}_tmp_{codec}{ext}"
                        
                        # 创建视频写入器
                        self.logger.info(f"尝试使用编码器 {codec} 创建视频: {tmp_output}")
                        video_writer = cv2.VideoWriter(
                            tmp_output, fourcc, effective_fps, (frame_width, frame_height)
                        )
                        
                        if video_writer.isOpened():
                            self.logger.info(f"成功创建输出视频，使用编码器: {codec}")
                            output_path = tmp_output  # 更新返回的输出路径
                            video_writer_created = True
                            break
                        else:
                            self.logger.warning(f"无法打开编码器 {codec} 的视频写入器")
                    except Exception as codec_error:
                        self.logger.warning(f"使用编码器 {codec} 创建视频写入器失败: {str(codec_error)}")
                
                if not video_writer_created:
                    self.logger.error("所有编码器都无法创建视频写入器，将不保存处理后的视频")
                    video_writer = None
            except Exception as e:
                self.logger.error(f"创建视频写入器失败: {str(e)}")
                video_writer = None
        
        # Prepare frame save directory
        if save_frames:
            try:
                if not frames_dir:
                    frames_dir = os.path.join(os.path.dirname(output_path or video_path), "frames", 
                                            os.path.basename(video_path).split('.')[0])
                
                # Ensure frame save directory exists
                os.makedirs(frames_dir, exist_ok=True)
                self.logger.info(f"Frame save directory created: {frames_dir}")
            except Exception as e:
                self.logger.error(f"Failed to create frame save directory: {str(e)}")
                self.logger.exception(e)
                # If frame directory creation fails, disable frame saving
                save_frames = False
        
        # Initialize alarm manager
        alarm_list = []
        if enable_alarm:
            self.logger.info(f"Enabled fire alarm feature, receiving email: {receiver_email}")
            self.alarm_manager = FireAlarmManager(
                receiver_email=receiver_email,
                alarm_interval=alarm_interval,
                alarm_threshold=alarm_threshold
            )
        else:
            self.alarm_manager = None
            
        # Processing statistics
        frame_count = 0
        processed_count = 0
        fire_frames = 0
        results_log = []
        start_time = time.time()
        
        # Start processing
        self.logger.info(f"Starting to process video: {video_path}")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_count += 1
                
                # Skip frames according to frame_skip parameter
                if frame_count % frame_skip != 0:
                    continue
                    
                processed_count += 1
                
                # Process current frame
                result = self.process_image(frame, mode=mode)
                
                # Get fire information
                has_fire = result.get("fire_detected", False)
                fire_confidence = result.get("confidence", 0)
                fire_area_percentage = result.get("fire_area_percentage", 0)
                
                # Update statistics
                if has_fire and fire_confidence >= threshold:
                    fire_frames += 1
                    
                    # Save key frames
                    if save_frames:
                        try:
                            # Verify frames directory exists
                            if not frames_dir:
                                self.logger.warning("No frames directory specified, cannot save key frames")
                                continue
                            
                            # Create frames directory if needed
                            os.makedirs(frames_dir, exist_ok=True)
                            
                            # Get frame with fire marked
                            if "output_image" in result:
                                highlighted_frame = result["output_image"]
                            elif "highlighted_image" in result:
                                highlighted_frame = result["highlighted_image"]
                            else:
                                # If no processed image, manually add fire warning
                                highlighted_frame = frame.copy()
                                # Add red border and fire warning
                                cv2.rectangle(highlighted_frame, (0, 0), (frame_width, frame_height), (0, 0, 255), 3)
                                cv2.putText(highlighted_frame, "FIRE DETECTED!", (int(frame_width/2)-100, 50), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                            
                            # Create frame file name
                            frame_name = f"fire_frame_{processed_count:04d}.jpg"
                            frame_path = os.path.join(frames_dir, frame_name)
                            
                            # Ensure frame is valid
                            if highlighted_frame is None or highlighted_frame.size == 0:
                                self.logger.error(f"Invalid frame image to save: {frame_path}")
                                continue
                                
                            # Verify frame shape and type
                            if len(highlighted_frame.shape) != 3 or highlighted_frame.shape[2] != 3:
                                self.logger.error(f"Invalid frame format: shape={highlighted_frame.shape}")
                                continue
                                
                            # Save frame
                            cv2.imwrite(frame_path, highlighted_frame)
                            
                            # Log frame info
                            self.logger.info(f"Saved fire frame: {frame_path}, confidence: {fire_confidence:.2f}")
                        except Exception as e:
                            self.logger.error(f"Error saving frame: {str(e)}")
                
                # Add result to log
                results_log.append({
                    "frame": frame_count,
                    "processed_frame": processed_count,
                    "fire_detected": has_fire,
                    "confidence": fire_confidence,
                    "fire_area_percentage": fire_area_percentage
                })
                
                # Send alarm if needed
                if self.alarm_manager and has_fire and fire_confidence >= alarm_threshold:
                    alarm_file = None
                    if save_frames:
                        # 使用最近保存的关键帧作为报警图像
                        alarm_file = frame_path if 'frame_path' in locals() else None
                    
                    alarm_result = self.alarm_manager.check_and_send_alarm(
                        fire_confidence=fire_confidence,
                        fire_area=fire_area_percentage,
                        image_file=alarm_file
                    )
                    
                    if alarm_result.get("alarm_sent", False):
                        alarm_list.append({
                            "timestamp": time.time(),
                            "frame": frame_count,
                            "confidence": fire_confidence,
                            "message": alarm_result.get("message", "")
                        })
                
                # Write to output video
                if video_writer is not None:
                    try:
                        # 获取需要写入的帧
                        output_frame = result.get("highlighted_image", frame)
                        
                        # 确保帧大小符合视频写入器的要求
                        if output_frame.shape[1] != frame_width or output_frame.shape[0] != frame_height:
                            output_frame = cv2.resize(output_frame, (frame_width, frame_height))
                        
                        # 写入帧
                        video_writer.write(output_frame)
                    except Exception as write_error:
                        self.logger.error(f"Error writing frame to video: {str(write_error)}")
                
                # Display progress
                if processed_count % 10 == 0:
                    elapsed_time = time.time() - start_time
                    fps_processing = processed_count / elapsed_time if elapsed_time > 0 else 0
                    percent_done = (frame_count / total_frames * 100) if total_frames > 0 else 0
                    self.logger.info(f"Processing: {percent_done:.1f}% (frame {frame_count}/{total_frames}), "
                                    f"fire frames: {fire_frames}, "
                                    f"FPS: {fps_processing:.2f}")
            
            # Processing complete
            self.logger.info(f"Video processing completed, processed {processed_count} frames, "
                            f"detected fire in {fire_frames} frames")
            
            # Calculate processing statistics
            elapsed_time = time.time() - start_time
            fps_processing = processed_count / elapsed_time if elapsed_time > 0 else 0
            fire_percentage = (fire_frames / processed_count * 100) if processed_count > 0 else 0
            
            # 关闭视频写入器
            if video_writer is not None:
                video_writer.release()
                
                # 如果使用了临时文件，现在转换并移动到最终位置
                if '_tmp_' in output_path:
                    tmp_output = output_path.replace(".mp4", f"_tmp_{codec}.mp4")
                    if os.path.exists(tmp_output) and os.path.getsize(tmp_output) > 0:
                        try:
                            # 复制到最终输出文件
                            shutil.copy2(tmp_output, output_path)
                            self.logger.info(f"临时视频复制到最终位置: {output_path}")
                            
                            # 如果复制成功，删除临时文件
                            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                                os.remove(tmp_output)
                                self.logger.info(f"删除临时视频文件: {tmp_output}")
                        except Exception as e:
                            self.logger.error(f"移动临时视频文件失败: {str(e)}")
                            # 如果移动失败但临时文件存在，使用临时文件作为输出
                            if os.path.exists(tmp_output):
                                output_path = tmp_output
                                self.logger.info(f"使用临时文件作为最终输出: {output_path}")
            
            # 确保输出视频是有效的
            video_valid = False
            if output_path and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size > 0:
                    try:
                        # 尝试打开生成的视频进行验证
                        test_cap = cv2.VideoCapture(output_path)
                        if test_cap.isOpened():
                            video_valid = True
                            test_cap.release()
                            self.logger.info(f"输出视频验证成功: {output_path}, 大小: {file_size/1024/1024:.2f}MB")
                        else:
                            self.logger.error(f"输出视频无法打开: {output_path}")
                    except Exception as e:
                        self.logger.error(f"验证输出视频时出错: {str(e)}")
                else:
                    self.logger.error(f"输出视频文件大小为零: {output_path}")
            else:
                self.logger.warning(f"没有找到输出视频文件: {output_path}")
            
            # Create result object
            result = {
                "success": True,
                "fire_detected": fire_frames > 0,
                "fire_frames": fire_frames,
                "processed_frames": processed_count,
                "total_frames": total_frames,
                "fire_percentage": fire_percentage,
                "output_path": output_path if video_valid else None,
                "frames_dir": frames_dir if save_frames else None,
                "processing_time": elapsed_time,
                "fps": fps_processing,
                "alarms": alarm_list
            }
            
            # Close video capture
            cap.release()
            
            # Return result
            return result
            
        except Exception as e:
            # Processing error
            self.logger.error(f"Error processing video: {str(e)}")
            self.logger.exception(e)
            
            # Close resources
            cap.release()
            if video_writer is not None:
                video_writer.release()
            
            # Return error result
            return {
                "success": False,
                "error": str(e),
                "fire_frames": fire_frames,
                "processed_frames": processed_count,
                "total_frames": total_frames
            }

    def process_image(self, image, mode="both"):
        """
        处理单一图像，检测火灾
        
        Args:
            image: 输入图像
            mode: 处理模式，可选 "color", "classification", "segmentation", "both"
            
        Returns:
            处理结果和可视化图像
        """
        # 记录开始时间
        start_time = time.time()

        # 检查图像有效性
        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            self.logger.error("[FIRE_DEBUG] process_image received invalid input image")
            return {"success": False, "error": "Invalid input image"}
        
        # 保存原始图像
        original_image = image.copy()
        result_image = image.copy()

        try:
            img_shape = original_image.shape
        except Exception:
            img_shape = "unknown"

        # 精简日志：如需详细调试可将本行改回 info 级别
        self.logger.debug(
            f"[FIRE_DEBUG] process_image called: "
            f"mode={mode}, shape={img_shape}, "
            f"yolo_loaded={getattr(self, 'yolo_model', None) is not None}, "
            f"smoke_v5_loaded={getattr(self, 'smoke_detector', None) is not None}"
        )
        
        # 初始化返回结果
        result = {
            "success": True,
            "fire_detected": False,
            "confidence": 0.0,
            "fire_area_percentage": 0.0,
            "smoke_detected": False,
            "smoke_area_percentage": 0.0,
            "processing_time": 0.0,
            "method": "none",
            "fire_regions": []
        }

        # 1) 优先使用旧版 YOLOv5 smoke.pt 模型进行火焰/烟雾检测
        if getattr(self, "smoke_detector", None) is not None:
            try:
                smoke_result = self.detect_fire_smoke_with_smoke_model(image)
                result["fire_detected"] = smoke_result.get("fire_detected", False)
                result["smoke_detected"] = smoke_result.get("smoke_detected", False)
                result["confidence"] = smoke_result.get("confidence", 0.0)
                result["fire_area_percentage"] = smoke_result.get("fire_area_percentage", 0.0)
                result["smoke_area_percentage"] = smoke_result.get("smoke_area_percentage", 0.0)
                result["method"] = smoke_result.get("method", "yolov5-smoke")
                result["fire_regions"] = smoke_result.get("fire_regions", [])
            except Exception as e:
                self.logger.error(
                    f"[FIRE_DEBUG] YOLOv5 smoke.pt 检测失败，将尝试使用其余检测流水线: {str(e)}"
                )
        # 2) 如果没有 smoke.pt 模型，退回到 Ultralytics YOLOv8 火焰/烟雾检测模型
        elif getattr(self, "yolo_model", None) is not None:
            try:
                yolo_result = self.detect_fire_smoke_with_yolo(
                    image,
                    conf_threshold=self.yolo_conf_threshold
                )
                result["fire_detected"] = yolo_result.get("fire_detected", False)
                result["smoke_detected"] = yolo_result.get("smoke_detected", False)
                result["confidence"] = yolo_result.get("confidence", 0.0)
                result["fire_area_percentage"] = yolo_result.get("fire_area_percentage", 0.0)
                result["smoke_area_percentage"] = yolo_result.get("smoke_area_percentage", 0.0)
                result["method"] = yolo_result.get("method", "yolo-fire-smoke")
                result["fire_regions"] = yolo_result.get("fire_regions", [])
            except Exception as e:
                self.logger.error(
                    f"[FIRE_DEBUG] YOLO fire/smoke detection failed, "
                    f"falling back to legacy pipeline: {str(e)}"
                )
        
        # 如果没有可用的 YOLO 模型，则回退到原有颜色/分类/分割流水线
        # 根据模式选择处理方法（仅用于检测，不再做掩膜高亮，只用矩形框展示）
        if getattr(self, "yolo_model", None) is None and getattr(self, "smoke_detector", None) is None:
            # 避免视频逐帧处理时刷屏：只提示一次
            if not getattr(self, "_yolo_missing_warned", False):
                self.logger.warning(
                    "YOLO model is not loaded; falling back to legacy fire detection pipeline "
                    "(color/classification/segmentation if available)."
                )
                self._yolo_missing_warned = True
                
        # 深度学习分类（如果可用）
        if getattr(self, "yolo_model", None) is None and mode in ["classification", "both"] and hasattr(self, 'classification_model') and self.classification_model is not None:
            # 检查分类模型可用
            try:
                # 使用分类模型检测
                class_result = self.detect_with_classification_model(image)
                class_detected = class_result.get("fire_detected", False)
                class_confidence = class_result.get("confidence", 0.0)
                
                # 更新结果
                if class_detected:
                    result["fire_detected"] = True
                    # 如果分类置信度更高，更新置信度和方法
                    if class_confidence > result["confidence"]:
                        result["confidence"] = class_confidence
                        result["method"] = class_result.get("method", "classification")
                        
                    # 如果分类检测到火灾但颜色分析未检测到，创建一个标记
                    if not result.get("fire_area_percentage", 0) > 0:
                        # 创建红色透明遮罩
                        overlay = original_image.copy()
                        cv2.rectangle(overlay, (0, 0), (image.shape[1], image.shape[0]), (0, 0, 255), -1)
                        # 仅当使用分类方法时才应用此效果
                        if result["method"] == "classification" and result_image is original_image:
                            result_image = cv2.addWeighted(overlay, 0.2, result_image, 0.8, 0)
                        
            except Exception as e:
                self.logger.error(f"Failed to detect fire with classification model: {str(e)}")
                
        # 分割模型检测（如果可用）
        if getattr(self, "yolo_model", None) is None and mode in ["segmentation", "both"] and hasattr(self, 'segmentation_model') and self.segmentation_model is not None:
            # 检查分割模型可用
            try:
                # 使用分割模型检测
                seg_result = self.detect_with_segmentation_model(image)
                seg_detected = seg_result.get("fire_detected", False)
                seg_confidence = seg_result.get("confidence", 0.0)
                seg_mask = seg_result.get("mask", None)
                
                # 更新结果
                if seg_detected:
                    result["fire_detected"] = True
                    # 如果分割置信度更高，更新置信度和方法
                    if seg_confidence > result["confidence"]:
                        result["confidence"] = seg_confidence
                        result["method"] = seg_result.get("method", "segmentation")
                    
                    # 如果有分割掩码，计算火焰区域百分比（不再做掩膜高亮）
                    if seg_mask is not None and np.any(seg_mask):
                        fire_area = np.sum(seg_mask > 0)
                        total_area = seg_mask.shape[0] * seg_mask.shape[1]
                        result["fire_area_percentage"] = max(result["fire_area_percentage"], (fire_area / total_area))
                
                    # 从分割结果中提取区域信息
                    if seg_mask is not None and np.any(seg_mask > 0):
                        # 转换掩码为二值图像
                        binary_mask = (seg_mask > 128).astype(np.uint8) * 255
                        # 找到轮廓
                        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        # 提取边界框
                        for contour in contours:
                            if cv2.contourArea(contour) > 100:  # 过滤掉太小的区域
                                x, y, w, h = cv2.boundingRect(contour)
                                area_percentage = (cv2.contourArea(contour) / (image.shape[0] * image.shape[1])) * 100
                                result["fire_regions"].append({
                                    'bbox': (x, y, w, h),
                                    'type': 'fire',
                                    'confidence': seg_confidence,
                                    'area_percentage': area_percentage
                                })
                
            except Exception as e:
                self.logger.error(f"Failed to detect fire with segmentation model: {str(e)}")
        
        # 计算处理时间
        result["processing_time"] = time.time() - start_time

        # 输出最终调试信息：降为 debug 级别，避免视频逐帧处理时大量输出
        try:
            self.logger.debug(
                "[FIRE_DEBUG] process_image result summary: "
                f"fire={result['fire_detected']}, "
                f"smoke={result['smoke_detected']}, "
                f"conf={result['confidence']:.3f}, "
                f"method={result['method']}, "
                f"fire_area={result['fire_area_percentage']:.4f}, "
                f"smoke_area={result['smoke_area_percentage']:.4f}, "
                f"regions={len(result.get('fire_regions', []))}, "
                f"time={result['processing_time']:.3f}s"
            )
        except Exception as log_err:
            self.logger.debug(f"[FIRE_DEBUG] Failed to log process_image summary: {log_err}")
        
        # 添加可视化元素
        enhanced_visualization = self.create_enhanced_visualization(
            result_image, 
            result,
            fire_regions=result.get("fire_regions", [])
        )
        
        # 添加输出图像到结果
        result["output_image"] = enhanced_visualization
        result["highlighted_image"] = enhanced_visualization  # 保持兼容性
        
        return result

    def create_enhanced_visualization(self, image, result, fire_regions=None):
        """
        创建增强的可视化效果，包括火灾和烟雾区域的标注
        
        Args:
            image: 输入图像
            result: 检测结果字典
            fire_regions: 火灾区域列表
            
        Returns:
            增强可视化效果的图像
        """
        vis_image = image.copy()
        
        # 标记火灾区域
        if fire_regions:
            for region in fire_regions:
                region_type = region.get("type", "fire")
                x, y, w, h = region["bbox"]
                conf = region.get("confidence", 0.5)
                
                # 根据区域类型选择颜色
                if region_type == "fire":
                    color = (0, 0, 255)  # 红色表示火焰
                    label = f"fire {conf:.2f}"
                elif region_type == "smoke":
                    color = (255, 200, 0)  # 蓝色表示烟雾
                    label = f"smoke {conf:.2f}"
                else:
                    color = (255, 0, 255)  # 洋红色表示其他类型
                    label = f"{region_type} {conf:.2f}"
                
                # 绘制边界框 - 简洁风格
                cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 2)
                
                # 添加简洁的标签
                cv2.putText(vis_image, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 如果火灾检测为真但没有区域信息，添加一个小型警告标志
        if result.get("fire_detected", False) and (not fire_regions or len(fire_regions) == 0):
            height, width = vis_image.shape[:2]
            # 添加一个小的火灾标记在右上角
            confidence = result.get("confidence", 0.0)
            cv2.putText(vis_image, f"FIRE: {confidence:.2f}", (width - 120, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 添加简单的帧信息到右下角
        height, width = vis_image.shape[:2]
        cv2.putText(vis_image, f"Fire Detection", (10, height - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return vis_image

    def detect_fire_smoke_with_yolo(self, image, conf_threshold=0.4):
        """
        使用单一的 Ultralytics YOLO 检测模型（如 YOLOv11）同时检测火焰和烟雾。
        模型通常来自 Roboflow Universe 上的 Fire + Smoke 数据集（best.pt）。
        """
        start = time.time()

        if self.yolo_model is None:
            return {
                "fire_detected": False,
                "smoke_detected": False,
                "confidence": 0.0,
                "fire_area_percentage": 0.0,
                "smoke_area_percentage": 0.0,
                "method": "no-yolo-model",
                "fire_regions": [],
                "processing_time": 0.0,
            }

        # 确保图像为 numpy 数组（BGR）
        if not isinstance(image, np.ndarray):
            image = np.array(image)

        if image is None or image.size == 0:
            raise ValueError("Invalid image for YOLO detection")

        height, width = image.shape[:2]
        total_area = float(height * width) if height > 0 and width > 0 else 1.0
        # YOLO 检测框的最小面积阈值，进一步抑制乱框（按整幅图面积的比例计算）
        min_box_area_ratio = 0.001  # 单个框至少占 0.1% 画面
        min_box_area = max(200.0, total_area * min_box_area_ratio)

        # 根据模型的类别名称，预先计算出 fire/smoke 相关的类别 ID，只让 YOLO 输出这些类别
        classes_filter = None
        treat_all_classes_as_fire = False
        try:
            model_names = getattr(self.yolo_model, "names", None)
            if isinstance(model_names, dict) and model_names:
                # 仅在 debug 级别记录一次模型类别信息，避免刷屏
                if not hasattr(self, "_yolo_logged_class_names"):
                    self.logger.debug(f"[FIRE_DEBUG][YOLO] model.names: {model_names}")
                    self._yolo_logged_class_names = True

                fire_keywords = ("fire", "flame", "smoke")
                classes_filter = [
                    cid for cid, name in model_names.items()
                    if any(k in str(name).lower() for k in fire_keywords)
                ]
                # 如果没有任何类别名包含 fire/flame/smoke，说明这个权重的类别名可能是 0/1/2 或者中文
                # 这种情况下我们退化为「认为所有类别都是火/烟」，避免因为名字不匹配导致完全检测不到
                if not classes_filter:
                    self.logger.debug(
                        "[FIRE_DEBUG][YOLO] No classes matched keywords (fire/flame/smoke); "
                        "treating ALL classes as fire/smoke for this model."
                    )
                    classes_filter = None
                    treat_all_classes_as_fire = True
        except Exception as e:
            self.logger.debug(f"[FIRE_DEBUG][YOLO] Failed to build classes filter: {e}")
            classes_filter = None
            treat_all_classes_as_fire = False

        # 运行 YOLO 检测（只保留 fire/smoke 相关类别），仅在 debug 级别输出详细信息
        self.logger.debug(
            f"[FIRE_DEBUG][YOLO] Running YOLO fire/smoke detection "
            f"with conf_threshold={conf_threshold}, classes_filter={classes_filter}"
        )
        if classes_filter:
            results = self.yolo_model(image, conf=conf_threshold, classes=classes_filter, verbose=False)
        else:
            # 回退：不显式限制类别，但后处理仍然只保留 fire/smoke 相关框
            results = self.yolo_model(image, conf=conf_threshold, verbose=False)
        if not results:
            return {
                "fire_detected": False,
                "smoke_detected": False,
                "confidence": 0.0,
                "fire_area_percentage": 0.0,
                "smoke_area_percentage": 0.0,
                "method": "yolo-fire-smoke",
                "fire_regions": [],
                "processing_time": time.time() - start,
            }

        result0 = results[0]
        # 如需查看原始框统计，可将下面这段日志改为 info 级别；默认保持在 debug 以免刷屏
        debug_frame_idx = getattr(self, "_yolo_debug_frame_idx", 0)
        debug_this_frame = debug_frame_idx < 5
        if debug_this_frame and hasattr(result0, "boxes") and result0.boxes is not None:
            try:
                raw_boxes = result0.boxes
                self.logger.debug(
                    f"[FIRE_DEBUG][YOLO] raw boxes count: {len(raw_boxes)} "
                    f"(before any fire/smoke filtering)"
                )
                names_dbg = getattr(result0, "names", {}) or {}
                for i, box in enumerate(raw_boxes[:5]):
                    try:
                        cls_id_dbg = int(box.cls.item())
                        conf_dbg = float(box.conf.item())
                        cname_dbg = str(names_dbg.get(cls_id_dbg, cls_id_dbg))
                        self.logger.debug(
                            f"[FIRE_DEBUG][YOLO] box#{i}: cls={cls_id_dbg}({cname_dbg}), conf={conf_dbg:.3f}"
                        )
                    except Exception:
                        continue
            except Exception as dbg_err:
                self.logger.debug(f"[FIRE_DEBUG][YOLO] failed to log raw boxes: {dbg_err}")
        if debug_this_frame:
            self._yolo_debug_frame_idx = debug_frame_idx + 1

        fire_detected = False
        smoke_detected = False
        best_fire_conf = 0.0
        best_smoke_conf = 0.0
        fire_area_px = 0.0
        smoke_area_px = 0.0
        fire_regions = []

        if hasattr(result0, "boxes") and result0.boxes is not None:
            boxes = result0.boxes
            names = getattr(result0, "names", {}) or {}

            for box in boxes:
                try:
                    cls_id = int(box.cls.item())
                    conf = float(box.conf.item())
                    class_name = str(names.get(cls_id, "")).lower()
                except Exception:
                    continue

                # 二次置信度过滤，确保低于阈值的框被剔除
                if conf < conf_threshold:
                    continue

                # 只关心与火焰或烟雾相关的类别；如果 treat_all_classes_as_fire=True，则不过滤
                if not treat_all_classes_as_fire:
                    if not any(k in class_name for k in ["fire", "flame", "smoke"]):
                        continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                w_box = max(0, x2 - x1)
                h_box = max(0, y2 - y1)
                area = float(w_box * h_box)

                # 过滤掉非常小的框，避免 YOLO 在复杂背景上产生大量噪声框
                if area < min_box_area:
                    continue

                region_type = "fire"
                if "smoke" in class_name:
                    region_type = "smoke"
                    smoke_detected = True
                    best_smoke_conf = max(best_smoke_conf, conf)
                    smoke_area_px += area
                else:
                    # 火焰 / 火光
                    fire_detected = True
                    best_fire_conf = max(best_fire_conf, conf)
                    fire_area_px += area

                fire_regions.append({
                    "bbox": (x1, y1, w_box, h_box),
                    "type": region_type,
                    "confidence": conf,
                    "area_percentage": (area / total_area) * 100.0 if total_area > 0 else 0.0,
                })

        confidence = max(best_fire_conf, best_smoke_conf)
        fire_area_percentage = fire_area_px / total_area if total_area > 0 else 0.0
        smoke_area_percentage = smoke_area_px / total_area if total_area > 0 else 0.0

        # 调试日志：输出YOLO检测摘要（默认不在 info 级别刷屏）
        try:
            self.logger.debug(
                "[FIRE_DEBUG][YOLO] Detection summary: "
                f"fire={fire_detected}, smoke={smoke_detected}, "
                f"conf={confidence:.3f}, "
                f"fire_area={fire_area_percentage:.4f}, "
                f"smoke_area={smoke_area_percentage:.4f}, "
                f"boxes={len(fire_regions)}"
            )
        except Exception as log_err:
            self.logger.warning(f"[FIRE_DEBUG][YOLO] Failed to log YOLO summary: {log_err}")

        return {
            "fire_detected": fire_detected,
            "smoke_detected": smoke_detected,
            "confidence": confidence,
            "fire_area_percentage": fire_area_percentage,
            "smoke_area_percentage": smoke_area_percentage,
            "method": "yolo-fire-smoke",
            "fire_regions": fire_regions,
            "processing_time": time.time() - start,
        }

    def detect_fire_smoke_with_smoke_model(self, image):
        """
        使用旧版 YOLOv5 smoke.pt 模型进行火焰/烟雾检测。
        该模型参考 `models/fire_detection/1.py`，我们将其输出转换为统一结果格式。
        """
        start = time.time()

        if self.smoke_detector is None:
            return {
                "fire_detected": False,
                "smoke_detected": False,
                "confidence": 0.0,
                "fire_area_percentage": 0.0,
                "smoke_area_percentage": 0.0,
                "method": "no-smoke-model",
                "fire_regions": [],
                "processing_time": 0.0,
            }

        if not isinstance(image, np.ndarray) or image is None or image.size == 0:
            raise ValueError("Invalid image for smoke.pt YOLOv5 detection")

        height, width = image.shape[:2]
        total_area = float(height * width) if height > 0 and width > 0 else 1.0

        detections = self.smoke_detector.detect(image)

        fire_detected = False
        smoke_detected = False
        best_conf = 0.0
        fire_area_px = 0.0
        smoke_area_px = 0.0
        fire_regions = []

        for det in detections:
            xyxy = det.get("bbox", [])
            if len(xyxy) != 4:
                continue
            x1, y1, x2, y2 = map(int, xyxy)
            w_box = max(0, x2 - x1)
            h_box = max(0, y2 - y1)
            area = float(w_box * h_box)
            if area <= 0:
                continue

            label = str(det.get("label", "")).lower()
            conf = float(det.get("conf", 0.0))

            region_type = "fire"
            if "smoke" in label:
                region_type = "smoke"
                smoke_detected = True
                smoke_area_px += area
            else:
                fire_detected = True
                fire_area_px += area

            if conf > best_conf:
                best_conf = conf

            fire_regions.append(
                {
                    "bbox": (x1, y1, w_box, h_box),
                    "type": region_type,
                    "confidence": conf,
                    "area_percentage": (area / total_area) * 100.0 if total_area > 0 else 0.0,
                }
            )

        fire_area_percentage = fire_area_px / total_area if total_area > 0 else 0.0
        smoke_area_percentage = smoke_area_px / total_area if total_area > 0 else 0.0

        return {
            "fire_detected": fire_detected or smoke_detected,
            "smoke_detected": smoke_detected,
            "confidence": best_conf,
            "fire_area_percentage": fire_area_percentage,
            "smoke_area_percentage": smoke_area_percentage,
            "method": "yolov5-smoke",
            "fire_regions": fire_regions,
            "processing_time": time.time() - start,
        }

    def detect_with_segmentation_model(self, image):
        """
        使用YOLOv8分割模型检测图像中的火灾
        
        Args:
            image: 输入图像
            
        Returns:
            分割结果字典，包含火灾掩码、置信度和检测结果
        """
        try:
            # 如果分割模型可用，则使用深度学习检测
            if self.segmentation_model is not None:
                # 简单检查图像是否有效
                if image is None or not isinstance(image, np.ndarray):
                    raise ValueError("无效的图像输入")
                    
                # 使用YOLO模型进行分割
                results = self.segmentation_model.predict(image, verbose=False)
                
                # 解析检测结果
                result = results[0]  # 智能输入支持单张或批量图像，这里我们只处理一张
                
                # 检查是否有分割掩码
                if hasattr(result, 'masks') and result.masks is not None and len(result.masks) > 0:
                    # 获取最佳分割掩码
                    masks = result.masks
                    
                    # 获取置信度
                    if hasattr(result, 'boxes') and result.boxes is not None and len(result.boxes) > 0:
                        confidences = result.boxes.conf.cpu().numpy()
                        confidence = float(np.max(confidences)) if len(confidences) > 0 else 0.8  # 如果没有置信度，使用默认值
                    else:
                        confidence = 0.8  # 分割模型可能没有返回置信度，使用默认值
                    
                    # 假定检测到火灾（分割模型的目的就是找到火灾区域）
                    fire_detected = True
                    
                    # 获取分割掩码
                    mask_tensor = masks.data[0]  # 获取第一个掩码
                    mask = mask_tensor.cpu().numpy()
                    
                    # 调整掩码尺寸以匹配输入图像
                    if mask.shape[:2] != image.shape[:2]:
                        mask = cv2.resize(mask, (image.shape[1], image.shape[0]))
                    
                    return {
                        "fire_detected": fire_detected,
                        "confidence": confidence,
                        "mask": mask,
                        "method": "yolov8-segmentation"
                    }
                else:
                    # 没有检测到火灾
                    return {
                        "fire_detected": False,
                        "confidence": 0.0,
                        "mask": None,
                        "method": "yolov8-segmentation"
                    }
            else:
                return {
                    "fire_detected": False,
                    "confidence": 0.0,
                    "mask": None,
                    "method": "no-model"
                }
        except Exception as e:
            self.logger.error(f"Failed to detect fire with segmentation model: {str(e)}")
            # 使用更安全的方式处理异常情况
            # 对于测试图像，我们可以返回一个默认的结果
            # 为了防止整个流程中断，我们不会将错误传播出去
            return {
                "fire_detected": False,
                "confidence": 0.0,
                "mask": None,
                "method": "error",
                "error": str(e)
            }

    def detect_with_classification_model(self, image):
        """
        使用YOLOv8分类模型检测图像中的火灾
        
        Args:
            image: 输入图像
            
        Returns:
            分类结果字典，包含火灾置信度和检测结果
        """
        try:
            # 如果分类模型可用，则使用深度学习检测
            if self.classification_model is not None:
                # 简单检查图像是否有效
                if image is None or not isinstance(image, np.ndarray):
                    raise ValueError("无效的图像输入")
                    
                # 使用YOLO模型进行分类
                results = self.classification_model.predict(image, verbose=False)
                
                # 解析检测结果
                result = results[0]  # 智能输入支持单张或批量图像，这里我们只处理一张
                probs = result.probs  # 分类概率
                
                # 对于分类模型，如果是二分类，通常索引 1 对应"火灾"类别
                # 这可能需要根据实际训练模型进行调整
                if probs is not None:
                    fire_class_idx = 1  # 假设索引 1 是火灾类别
                    confidence = float(probs.data[fire_class_idx]) if len(probs.data) > fire_class_idx else float(probs.data[0])
                    fire_detected = confidence > 0.5  # 如果置信度大于0.5，判定为有火灾
                    
                    return {
                        "fire_detected": fire_detected,
                        "confidence": confidence,
                        "method": "yolov8-classification"
                    }
                else:
                    # 如果模型没有返回概率，可能是目标检测模型而非分类模型
                    # 检查是否有目标框
                    if hasattr(result, 'boxes') and len(result.boxes) > 0:
                        boxes = result.boxes
                        # 获取置信度最高的检测结果
                        confidences = boxes.conf.cpu().numpy()
                        confidence = float(np.max(confidences)) if len(confidences) > 0 else 0.0
                        fire_detected = confidence > 0.5
                    else:
                        # 没有目标框也没有概率，返回低置信度
                        confidence = 0.0
                        fire_detected = False
                    
                    return {
                        "fire_detected": fire_detected,
                        "confidence": confidence,
                        "method": "yolov8-classification"
                    }
            else:
                return {
                    "fire_detected": False,
                    "confidence": 0.0,
                    "method": "no-model"
                }
        except Exception as e:
            self.logger.error(f"Failed to detect fire with classification model: {str(e)}")
            return {
                "fire_detected": False,
                "confidence": 0.0,
                "method": "error",
                "error": str(e)
            }

    def preprocess_image(self, image, target_size=None):
        """
        预处理输入图像，为模型推理做准备
        
        Args:
            image: 输入图像，可以是文件路径或图像数组
            target_size: 目标尺寸，对于YOLOv8模型可以为None，模型会自动调整
            
        Returns:
            预处理后的图像和原始图像
        """
        # 如果是字符串路径，先加载图像
        if isinstance(image, str):
            try:
                image = cv2.imread(image)
            except Exception as e:
                self.logger.error(f"Failed to load image: {str(e)}")
                return None, None
        
        # 确保图像是有效的numpy数组
        if image is None or not isinstance(image, np.ndarray):
            self.logger.error("无效的图像输入")
            return None, None
            
        # 保存原始图像
        original_image = image.copy()
        
        # 调整图像尺寸（如果需要）
        if target_size is not None:
            resized_image = cv2.resize(image, target_size)
        else:
            # 如果没有指定尺寸，使用原始图像
            # YOLOv8模型会自动调整图像尺寸
            resized_image = image
        
        return resized_image, original_image
    
    def classify_image(self, image):
        """
        分类图像是否包含火灾
        
        Args:
            image: 输入图像
            
        Returns:
            包含分类结果和置信度的字典
        """
        # 如果分类模型未加载，检查模型文件并尝试加载
        if self.classification_model is None:
            self.logger.info(f"First use of model, checking model file: {self.classification_model_path}")
            # 检查模型是否存在
            if os.path.exists(self.classification_model_path):
                self.logger.info(f"Model file exists, size: {os.path.getsize(self.classification_model_path)/1024/1024:.2f} MB")
                # 加载模型
                self._load_classification_yolo_model()
            else:
                self.logger.warning(f"Model file not found: {self.classification_model_path}")
        
        # 使用分类模型检测火灾
        result = self.detect_with_classification_model(image)
        
        # 返回分类结果
        return {
            'fire_detected': result['fire_detected'],
            'confidence': result['confidence'],
            'method': result['method']
        }
        
    def segment_fire(self, image):
        """
        对图像中的火灾区域进行分割
        
        Args:
            image: 输入图像
            
        Returns:
            包含分割结果的字典
        """
        # 首次运行时尝试加载模型
        if self.segmentation_model is None and TORCH_AVAILABLE and YOLO_AVAILABLE:
            # 检查文件是否存在
            if os.path.exists(self.segmentation_model_path):
                # 加载模型
                self._load_segmentation_yolo_model()
        
        # 使用分割模型检测与分割
        result = self.detect_with_segmentation_model(image)
        
        return {
            'fire_detected': result['fire_detected'],
            'confidence': result['confidence'],
            'mask': result['mask'],
            'method': result['method']
        }

# 添加模块级导出函数
def create_fire_detector():
    """创建并返回一个火灾检测器实例
    
    Returns:
        FireDetector: 配置好的火灾检测器实例
    """
    try:
        detector = FireDetector()
        return detector
    except Exception as e:
        logger.error(f"创建火灾检测器时出错: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 创建一个最小化的检测器，返回空结果但不会导致整个系统崩溃
        class MinimalDetector:
            def process_image(self, *args, **kwargs):
                return {
                    "fire_detected": False,
                    "confidence": 0.0,
                    "processing_time": 0.0,
                    "highlighted_image": args[0] if args else np.zeros((10, 10, 3), dtype=np.uint8),
                    "error": "火灾检测器初始化失败"
                }
                
            def process_video(self, *args, **kwargs):
                # 返回一个空的结果字典
                return {
                    "status": "error",
                    "message": "火灾检测器初始化失败"
                }
                
        return MinimalDetector()
