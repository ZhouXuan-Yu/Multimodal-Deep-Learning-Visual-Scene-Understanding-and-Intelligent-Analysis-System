"""
优化版人物特征分析器 (image_analyzer.py)

基于2025年主流技术优化：
1. YOLOv8预训练模型 - 可靠的人体/人脸检测
2. YOLO人体分割掩码 - 精确的服装区域提取
3. CLAHE光照校正 - 提升低光照图像质量
4. K-means颜色聚类 - 更准确的服装颜色分析
5. 图像预处理增强 - 提升整体识别效果
6. 多尺度融合 - 提高检测稳定性
"""

import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import cv2
import os
from pathlib import Path
import numpy as np
from torchvision.models.segmentation import deeplabv3_resnet50
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
import warnings
from ultralytics import YOLO
import base64
import json
import requests
import time
from collections import Counter

warnings.filterwarnings("ignore", category=UserWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- torch.load compatibility ---
def _torch_load_compat(path: str, map_location=None) -> Any:
    try:
        return torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:
        return torch.load(path, map_location=map_location)

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent
MODEL_DIR = ROOT_DIR / "model"

class Singleton(type):
    _instances = {}
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

def get_device():
    """获取可用的设备"""
    if torch.cuda.is_available():
        return ['cuda:0']
    return ['cpu']


# ============== 图像预处理模块 ==============

class ImagePreprocessor:
    """图像预处理增强模块 - 提升低质量和低光照图像的识别效果"""
    
    @staticmethod
    def clahe_enhance(img: np.ndarray, clip_limit: float = 2.0, tile_grid_size: int = 8) -> np.ndarray:
        """
        CLAHE (对比度受限自适应直方图均衡化)
        有效提升低光照、阴影、逆光图像的质量
        """
        try:
            # 转换为LAB色彩空间
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 对L通道应用CLAHE
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
            l_enhanced = clahe.apply(l)
            
            # 合并通道
            enhanced_lab = cv2.merge([l_enhanced, a, b])
            enhanced_img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            
            return enhanced_img
        except Exception as e:
            logger.warning(f"CLAHE增强失败: {str(e)}")
            return img
    
    @staticmethod
    def gamma_correction(img: np.ndarray, gamma: float = 1.2) -> np.ndarray:
        """伽马校正 - 提升暗部细节"""
        try:
            inv_gamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
            return cv2.LUT(img, table)
        except Exception:
            return img
    
    @staticmethod
    def denoise(img: np.ndarray, strength: int = 10) -> np.ndarray:
        """降噪处理"""
        try:
            return cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)
        except Exception:
            return img
    
    @staticmethod
    def sharpen(img: np.ndarray) -> np.ndarray:
        """图像锐化 - 增强边缘"""
        try:
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]])
            return cv2.filter2D(img, -1, kernel)
        except Exception:
            return img
    
    @staticmethod
    def enhance_low_light(img: np.ndarray) -> np.ndarray:
        """综合低光照图像增强"""
        try:
            # 检测是否为低光照图像
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            avg_brightness = np.mean(gray)
            
            if avg_brightness < 80:  # 低光照
                # CLAHE增强
                img = ImagePreprocessor.clahe_enhance(img)
                # 伽马校正
                img = ImagePreprocessor.gamma_correction(img, gamma=1.3)
            elif avg_brightness < 120:  # 中等光照
                img = ImagePreprocessor.clahe_enhance(img, clip_limit=1.5)
            
            return img
        except Exception as e:
            logger.warning(f"低光照增强失败: {str(e)}")
            return img
    
    @staticmethod
    def auto_enhance(img: np.ndarray) -> np.ndarray:
        """自动增强 - 根据图像特性选择最佳处理"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            # 根据对比度调整
            if contrast < 40:
                img = ImagePreprocessor.clahe_enhance(img, clip_limit=2.5)
            
            return img
        except Exception:
            return img


# ============== 颜色分析模块 ==============

class ColorAnalyzer:
    """高级颜色分析模块 - 基于K-means聚类和HSV分析"""
    
    # HSV颜色空间定义 (OpenCV格式: H: 0-180, S: 0-255, V: 0-255)
    HSV_RANGES = {
        'black': ([0, 0, 0], [180, 255, 85]),
        'white': ([0, 0, 200], [180, 30, 255]),
        'gray': ([0, 0, 85], [180, 30, 200]),
        'red': ([0, 100, 100], [10, 255, 255]),
        'red2': ([160, 100, 100], [180, 255, 255]),
        'orange': ([10, 100, 100], [25, 255, 255]),
        'yellow': ([25, 100, 100], [40, 255, 255]),
        'green': ([40, 50, 50], [80, 255, 255]),
        'cyan': ([80, 50, 50], [100, 255, 255]),
        'blue': ([100, 80, 50], [130, 255, 255]),
        'purple': ([130, 50, 50], [160, 255, 255]),
        'pink': ([160, 50, 100], [180, 255, 255]),
    }
    
    # 基础RGB颜色
    RGB_COLORS = {
        'black': [0, 0, 0],
        'white': [255, 255, 255],
        'red': [255, 0, 0],
        'green': [0, 255, 0],
        'blue': [0, 0, 255],
        'yellow': [255, 255, 0],
        'orange': [255, 165, 0],
        'purple': [128, 0, 128],
        'pink': [255, 192, 203],
        'gray': [128, 128, 128],
        'brown': [139, 69, 19],
        'navy': [0, 0, 128],
        'beige': [245, 245, 220],
        'khaki': [195, 176, 145],
    }
    
    @staticmethod
    def kmeans_clustering(img_region: np.ndarray, k: int = 5) -> List[Tuple[str, float, int]]:
        """
        K-means聚类分析 - 找出图像中的主要颜色
        返回: [(颜色名, 置信度, 像素数), ...]
        """
        try:
            if img_region.size == 0:
                return []
            
            # 调整图像大小以加速
            h, w = img_region.shape[:2]
            if h * w > 10000:
                img_region = cv2.resize(img_region, (100, int(100 * h / w)))
            
            # 转换为RGB格式
            rgb = cv2.cvtColor(img_region, cv2.COLOR_BGR2RGB)
            pixels = rgb.reshape(-1, 3).astype(np.float32)
            
            # K-means聚类
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            
            # 统计每个簇的像素数
            unique, counts = np.unique(labels, return_counts=True)
            
            results = []
            for center, count in zip(centers, counts):
                color_name = ColorAnalyzer._rgb_to_color_name(center)
                confidence = min(1.0, count / (len(pixels) * 0.3))  # 根据占比计算置信度
                results.append((color_name, confidence, int(count)))
            
            # 按像素数排序
            results.sort(key=lambda x: x[2], reverse=True)
            return results
        except Exception as e:
            logger.warning(f"K-means聚类失败: {str(e)}")
            return []
    
    @staticmethod
    def _rgb_to_color_name(rgb: np.ndarray) -> str:
        """将RGB值转换为颜色名称"""
        rgb = rgb.astype(int)
        r, g, b = rgb[0], rgb[1], rgb[2]
        
        # 计算到各标准颜色的距离
        min_dist = float('inf')
        best_color = 'unknown'
        
        for color_name, std_rgb in ColorAnalyzer.RGB_COLORS.items():
            dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(rgb, std_rgb)))
            if dist < min_dist:
                min_dist = dist
                best_color = color_name
        
        return best_color
    
    @staticmethod
    def analyze_by_hsv(img_region: np.ndarray) -> Tuple[str, float]:
        """基于HSV的颜色分析"""
        try:
            if img_region.size == 0:
                return 'unknown', 0.0
            
            hsv = cv2.cvtColor(img_region, cv2.COLOR_BGR2HSV)
            
            # 统计每种颜色的像素数
            color_counts = {}
            total_pixels = hsv.shape[0] * hsv.shape[1]
            
            for color_name, (lower, upper) in ColorAnalyzer.HSV_RANGES.items():
                if color_name == 'red2':
                    continue  # 与red合并处理
                
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                mask = cv2.inRange(hsv, lower_np, upper_np)
                color_counts[color_name] = np.sum(mask > 0)
            
            # 处理红色（跨越0度的颜色）
            mask1 = cv2.inRange(hsv, np.array([0, 100, 100], dtype=np.uint8),
                               np.array([10, 255, 255], dtype=np.uint8))
            mask2 = cv2.inRange(hsv, np.array([160, 100, 100], dtype=np.uint8),
                               np.array([180, 255, 255], dtype=np.uint8))
            color_counts['red'] = color_counts.get('red', 0) + np.sum(cv2.bitwise_or(mask1, mask2) > 0)
            
            # 找出主要颜色
            if not color_counts or max(color_counts.values()) == 0:
                return ColorAnalyzer._rgb_fallback(img_region)
            
            best_color = max(color_counts.items(), key=lambda x: x[1])[0]
            best_ratio = color_counts[best_color] / total_pixels
            
            # 根据占比计算置信度
            if best_ratio > 0.5:
                confidence = 0.9
            elif best_ratio > 0.3:
                confidence = 0.8
            elif best_ratio > 0.15:
                confidence = 0.7
            else:
                confidence = 0.6
            
            # 低饱和度处理
            avg_s = np.mean(hsv[:, :, 1])
            avg_v = np.mean(hsv[:, :, 2])
            
            if avg_s < 30:
                if avg_v > 180:
                    return 'white', 0.75
                elif avg_v < 80:
                    return 'black', 0.75
                else:
                    return 'gray', 0.65
            
            return best_color, confidence
        except Exception:
            return ColorAnalyzer._rgb_fallback(img_region)
    
    @staticmethod
    def _rgb_fallback(img_region: np.ndarray) -> Tuple[str, float]:
        """RGB回退分析"""
        try:
            avg_rgb = np.array(cv2.mean(img_region)[:3])
            min_dist = float('inf')
            best_color = 'unknown'
            
            for color_name, rgb in ColorAnalyzer.RGB_COLORS.items():
                dist = np.sqrt(np.sum((avg_rgb - np.array(rgb)) ** 2))
                if dist < min_dist:
                    min_dist = dist
                    best_color = color_name
            
            confidence = max(0.5, 1 - (min_dist / 400))
            return best_color, confidence
        except Exception:
            return 'unknown', 0.0
    
    @classmethod
    def analyze(cls, img_region: np.ndarray, use_kmeans: bool = True) -> Tuple[str, float]:
        """
        综合颜色分析
        优先使用K-means聚类，失败时使用HSV分析
        """
        if img_region is None or img_region.size == 0:
            return 'unknown', 0.0
        
        # K-means分析
        if use_kmeans:
            clusters = cls.kmeans_clustering(img_region, k=5)
            if clusters and clusters[0][1] > 0.4:
                return clusters[0][0], clusters[0][1]
        
        # HSV分析
        return cls.analyze_by_hsv(img_region)


# ============== 基础模型类 ==============

class ModelBase:
    def __init__(self, model_path: str, device: str):
        self.model_path = model_path
        self.device = device
        self.model = None
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
    
    def load_model(self):
        raise NotImplementedError


# ============== 颜色分类模型 ==============

class ColorModel(ModelBase):
    def __init__(self, model_path: str, device: str):
        super().__init__(model_path, device)
        self.classes = None
        self.load_model()
    
    def load_model(self):
        try:
            checkpoint = _torch_load_compat(self.model_path, map_location=self.device)
            if isinstance(checkpoint, dict) and 'classes' in checkpoint:
                self.classes = checkpoint['classes']
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                else:
                    state_dict = checkpoint
            else:
                raise ValueError("无效的模型检查点格式")
            
            self.model = models.resnet18(weights=None)
            num_features = self.model.fc.in_features
            self.model.fc = nn.Sequential()
            self.model.fc.add_module('1', nn.Linear(num_features, 512))
            self.model.fc.add_module('2', nn.ReLU())
            self.model.fc.add_module('4', nn.Linear(512, len(self.classes)))
            
            # 处理model.前缀
            fixed_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith('model.'):
                    fixed_state_dict[k[6:]] = v
                else:
                    fixed_state_dict[k] = v
            
            self.model.load_state_dict(fixed_state_dict)
            self.model.to(self.device)
            self.model.eval()
            logger.info("颜色分类模型加载成功")
        except Exception as e:
            logger.error(f"加载颜色分类模型失败: {str(e)}")
            raise
    
    def predict(self, img):
        try:
            img_tensor = self.transform(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                outputs = self.model(img_tensor)
                probs = torch.softmax(outputs, dim=1)
                conf, idx = torch.max(probs, dim=1)
                return self.classes[idx.item()], conf.item()
        except Exception as e:
            logger.error(f"颜色预测失败: {str(e)}")
            return None, 0.0


# ============== 年龄估计模型 ==============

class AgeModel(ModelBase):
    def __init__(self, model_path: str, device: str):
        super().__init__(model_path, device)
        self.age_classes = ['0-10', '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71+']
        self.load_model()
    
    def load_model(self):
        try:
            class AgeEstimationModel(nn.Module):
                def __init__(self, num_classes):
                    super().__init__()
                    self.backbone = models.resnet50(weights=None)
                    in_features = self.backbone.fc.in_features
                    self.backbone.fc = nn.Sequential(
                        nn.Linear(in_features, 1024),
                        nn.BatchNorm1d(1024),
                        nn.ReLU(),
                        nn.Dropout(0.5),
                        nn.Linear(1024, 512),
                        nn.BatchNorm1d(512),
                        nn.ReLU(),
                        nn.Dropout(0.3),
                        nn.Linear(512, num_classes)
                    )
                
                def forward(self, x):
                    return self.backbone(x)
            
            self.model = AgeEstimationModel(num_classes=len(self.age_classes))
            
            checkpoint = _torch_load_compat(self.model_path, map_location=self.device)
            if isinstance(checkpoint, dict):
                state_dict = checkpoint.get('model_state_dict', checkpoint)
            else:
                state_dict = checkpoint
            
            new_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith('module.'):
                    k = k[7:]
                new_state_dict[k] = v
            
            self.model.load_state_dict(new_state_dict)
            self.model.to(self.device)
            self.model.eval()
            logger.info("年龄估计模型加载成功")
        except Exception as e:
            logger.error(f"加载年龄估计模型失败: {str(e)}")
            raise
    
    def predict(self, img):
        try:
            if not isinstance(img, Image.Image):
                if isinstance(img, np.ndarray):
                    img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                else:
                    raise ValueError("输入必须是PIL图像或numpy数组")
            
            img_tensor = self.transform(img).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(img_tensor)
                probs = torch.softmax(outputs, dim=1)
                confidence, pred_idx = torch.max(probs, dim=1)
                pred_age = self.age_classes[pred_idx.item()]
                
                # 解析年龄范围
                age_range = pred_age.split('-')
                if len(age_range) == 2:
                    min_age = int(age_range[0])
                    max_age = int(age_range[1])
                else:
                    min_age = int(pred_age.replace('+', ''))
                    max_age = min_age + 29
                
                predicted_age = min_age + (max_age - min_age) * confidence.item()
                return predicted_age, confidence.item()
        except Exception as e:
            logger.error(f"年龄预测失败: {str(e)}")
            return None, 0.0


# ============== 性别分类模型 ==============

class GenderModel(ModelBase):
    def __init__(self, model_path: str, device: str):
        super().__init__(model_path, device)
        self.confidence_threshold = 0.4
        self.load_model()
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def load_model(self):
        try:
            self.model = YOLO(self.model_path)
            self.model.to(self.device)
            logger.info("性别分类模型加载成功")
        except Exception as e:
            logger.error(f"加载性别分类模型失败: {str(e)}")
            raise

    def predict(self, img):
        try:
            if isinstance(img, Image.Image):
                img = np.array(img)
            
            results = self.model(img)
            
            if not results or len(results) == 0:
                return "unknown", 0.0
            
            result = results[0]
            
            if not hasattr(result, 'probs') or not result.probs:
                return "unknown", 0.0
            
            probs = result.probs
            female_prob = float(probs.data[0])
            male_prob = float(probs.data[1])
            
            if female_prob >= male_prob:
                gender, confidence = 'female', female_prob
            else:
                gender, confidence = 'male', male_prob
            
            if confidence < 0.4:
                return "unknown", confidence
            
            return gender, confidence
        except Exception as e:
            logger.error(f"性别预测失败: {str(e)}")
            return "unknown", 0.0


# ============== 核心图像分析器 ==============

class ImageAnalyzer(metaclass=Singleton):
    def __init__(self):
        self.device = get_device()[0]
        self.models = {}
        self.model_paths = self._get_model_paths()
        
        # 检测参数
        self.face_conf_threshold = 0.20  # 进一步降低阈值
        self.body_conf_threshold = 0.30
        
        # 预处理
        self.preprocessor = ImagePreprocessor()
        self.color_analyzer = ColorAnalyzer()
        
        # DeepLabV3分割模型
        self.deeplabv3 = None
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        # Ollama配置
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_model_name = os.getenv("OLLAMA_QWEN_MODEL", "qwen3.5:4b")
        self.ollama_timeout_s = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))
        
        # YOLOv8预训练模型
        self.yolo_model = None  # YOLOv8n预训练模型
        
        # 人体分割模型
        self.person_seg_model = None
        
        logger.info(
            f"增强分析配置：OLLAMA_BASE_URL={self.ollama_base_url}, "
            f"OLLAMA_QWEN_MODEL={self.ollama_model_name}, timeout={self.ollama_timeout_s}s"
        )
        
        self.load_models()
        self.cache = {}
    
    def _get_model_paths(self) -> Dict[str, str]:
        paths = {
            'face': str(MODEL_DIR / "output/face_detection/train2/weights/best.pt"),
            'color': str(MODEL_DIR / "output/color_classification/best_model.pth"),
            'age': str(MODEL_DIR / "output/age_estimation/weights/best.pt"),
            'gender': str(MODEL_DIR / "output/gender_classification/train/weights/best.pt")
        }
        
        for name, path in paths.items():
            if not os.path.exists(path):
                logger.warning(f"模型文件不存在: {path}")
                paths[name] = None
        
        return paths
    
    def load_models(self):
        """加载所有模型"""
        try:
            # DeepLabV3分割模型
            try:
                self.deeplabv3 = models.segmentation.deeplabv3_resnet50(pretrained=True)
                self.deeplabv3.eval()
                self.deeplabv3.to(self.device)
                logger.info("DeepLabV3模型加载成功")
            except Exception as e:
                logger.error(f"加载DeepLabV3模型失败: {str(e)}")
                self.deeplabv3 = None
            
            # YOLO模型
            from ultralytics import YOLO
            
            # 人脸检测模型
            if self.model_paths['face']:
                try:
                    self.models['face'] = YOLO(self.model_paths['face'])
                    self.models['face'].to(self.device)
                    logger.info("人脸检测模型加载成功")
                except Exception as e:
                    logger.error(f"加载人脸检测模型失败: {str(e)}")
                    self.models['face'] = None
            
            # 颜色分类模型
            if self.model_paths['color']:
                try:
                    self.models['color'] = ColorModel(self.model_paths['color'], self.device)
                except Exception as e:
                    logger.error(f"加载颜色分类模型失败: {str(e)}")
                    self.models['color'] = None
            
            # 年龄估计模型
            if self.model_paths['age']:
                try:
                    self.models['age'] = AgeModel(self.model_paths['age'], self.device)
                except Exception as e:
                    logger.error(f"加载年龄估计模型失败: {str(e)}")
                    self.models['age'] = None
            
            # 性别分类模型
            if self.model_paths['gender']:
                try:
                    self.models['gender'] = GenderModel(self.model_paths['gender'], self.device)
                except Exception as e:
                    logger.error(f"加载性别分类模型失败: {str(e)}")
                    self.models['gender'] = None
            
            # 加载YOLOv8预训练模型（可靠的人体检测）
            try:
                self.yolo_model = YOLO("yolov8n.pt")
                self.yolo_model.to(self.device)
                logger.info("YOLOv8n预训练模型加载成功")
            except Exception as e:
                logger.warning(f"加载YOLOv8预训练模型失败: {str(e)}")
                self.yolo_model = None
            
            # 加载YOLO12L人体分割模型
            try:
                self.person_seg_model = YOLO("yolo12l-person-seg.pt")
                self.person_seg_model.to(self.device)
                logger.info("YOLO12L人体分割模型加载成功")
            except Exception as e:
                logger.warning(f"加载人体分割模型失败（将使用其他方案）: {str(e)}")
                self.person_seg_model = None
            
        except ImportError as e:
            logger.error(f"加载模型失败: {str(e)}")
    
    def _detect_clothing_regions_with_yolo_mask(
        self,
        img: np.ndarray,
        person_mask: np.ndarray,
        face_box: Tuple[int, int, int, int]
    ) -> Dict[str, Dict]:
        """使用YOLO人体分割掩码精确提取服装区域"""
        x1, y1, x2, y2 = face_box
        face_height = y2 - y1
        face_width = x2 - x1
        h, w = img.shape[:2]
        
        if face_height <= 0 or face_width <= 0:
            return {
                "upper": {"region": np.array([]), "bbox": (0, 0, 0, 0)},
                "lower": {"region": np.array([]), "bbox": (0, 0, 0, 0)}
            }
        
        # 人体比例估算
        upper_y1 = y2
        upper_y2 = min(upper_y1 + int(face_height * 2.2), h)
        upper_x1 = max(0, x1 - int(face_width * 0.5))
        upper_x2 = min(x2 + int(face_width * 0.5), w)
        
        lower_y1 = upper_y2
        lower_y2 = min(lower_y1 + int(face_height * 2.5), h)
        lower_x1 = max(0, x1 - int(face_width * 0.6))
        lower_x2 = min(x2 + int(face_width * 0.6), w)
        
        # 使用人体掩码细化区域
        if person_mask is not None:
            try:
                # 确保掩码与图像大小匹配
                if person_mask.shape[:2] != (h, w):
                    person_mask = cv2.resize(person_mask.astype(np.uint8), (w, h))
                
                person_mask = person_mask.astype(bool)
                
                def refine_with_mask(x1_, y1_, x2_, y2_):
                    x1_ = max(0, min(x1_, w - 1))
                    x2_ = max(0, min(x2_, w))
                    y1_ = max(0, min(y1_, h - 1))
                    y2_ = max(0, min(y2_, h))
                    if x2_ <= x1_ or y2_ <= y1_:
                        return x1_, y1_, x2_, y2_
                    
                    sub_mask = person_mask[y1_:y2_, x1_:x2_]
                    if not sub_mask.any():
                        return x1_, y1_, x2_, y2_
                    
                    rows = np.any(sub_mask, axis=1)
                    cols = np.any(sub_mask, axis=0)
                    ys = np.where(rows)[0]
                    xs = np.where(cols)[0]
                    
                    if len(ys) == 0 or len(xs) == 0:
                        return x1_, y1_, x2_, y2_
                    
                    return (x1_ + xs[0], y1_ + ys[0], x1_ + xs[-1], y1_ + ys[-1])
                
                upper_x1, upper_y1, upper_x2, upper_y2 = refine_with_mask(
                    upper_x1, upper_y1, upper_x2, upper_y2)
                lower_x1, lower_y1, lower_x2, lower_y2 = refine_with_mask(
                    lower_x1, lower_y1, lower_x2, lower_y2)
                    
            except Exception as e:
                logger.warning(f"使用掩码细化失败: {str(e)}")
        
        upper_region = img[upper_y1:upper_y2, upper_x1:upper_x2]
        lower_region = img[lower_y1:lower_y2, lower_x1:lower_x2]
        
        return {
            "upper": {"region": upper_region, "bbox": (int(upper_x1), int(upper_y1), int(upper_x2), int(upper_y2))},
            "lower": {"region": lower_region, "bbox": (int(lower_x1), int(lower_y1), int(lower_x2), int(lower_y2))}
        }
    
    def _analyze_clothing_color(self, img_region: np.ndarray, region_type: str = "upper") -> Tuple[str, float]:
        """分析服装颜色"""
        if img_region is None or img_region.size == 0:
            return "unknown", 0.0
        
        # 优先使用K-means聚类
        clusters = self.color_analyzer.kmeans_clustering(img_region, k=5)
        if clusters:
            main_color, confidence, _ = clusters[0]
            if confidence > 0.35:
                return main_color, confidence
        
        # 使用颜色分类模型
        if self.models.get("color"):
            try:
                rgb_img = cv2.cvtColor(img_region, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                
                colors = []
                confidences = []
                scales = [0.7, 0.85, 1.0, 1.15, 1.3]
                
                for scale in scales:
                    scaled_img = pil_img.resize((int(224 * scale), int(224 * scale)))
                    color, conf = self.models["color"].predict(scaled_img)
                    if color:
                        colors.append(color)
                        confidences.append(conf)
                
                if colors:
                    color_counts = Counter(colors)
                    most_common = color_counts.most_common(1)[0][0]
                    avg_conf = np.mean([c for c, conf in zip(colors, confidences) if c == most_common])
                    if avg_conf > 0.22:
                        return most_common, avg_conf
            except Exception as e:
                logger.warning(f"颜色模型预测失败: {str(e)}")
        
        # HSV分析
        return self.color_analyzer.analyze_by_hsv(img_region)
    
    def _get_person_segmentation_mask(self, img: np.ndarray) -> Optional[np.ndarray]:
        """获取人体分割掩码"""
        h, w = img.shape[:2]
        
        # 尝试使用YOLO12L人体分割模型
        if self.person_seg_model is not None:
            try:
                results = self.person_seg_model.predict(img, conf=0.3, verbose=False)
                if results and len(results) > 0 and hasattr(results[0], 'masks') and results[0].masks is not None:
                    masks = results[0].masks.data.cpu().numpy()
                    if len(masks) > 0:
                        combined_mask = np.any(masks, axis=0).astype(np.uint8) * 255
                        return combined_mask
            except Exception as e:
                logger.warning(f"YOLO12L分割失败: {str(e)}")
        
        # 使用DeepLabV3
        if self.deeplabv3 is not None:
            try:
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    output = self.deeplabv3(input_tensor)['out'][0]
                
                mask = torch.argmax(output, dim=0).cpu().numpy()
                # person类别在COCO中为15
                person_mask = (mask == 15).astype(np.uint8) * 255
                person_mask = cv2.resize(person_mask, (w, h), interpolation=cv2.INTER_NEAREST)
                return person_mask
            except Exception as e:
                logger.warning(f"DeepLabV3分割失败: {str(e)}")
        
        return None
    
    def _detect_persons_yolo(self, img: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """使用YOLOv8检测人物"""
        boxes = []
        
        # 方法1: 使用专用人脸检测模型
        if self.models.get('face'):
            try:
                results = self.models['face'].predict(
                    img, conf=self.face_conf_threshold, verbose=False
                )
                
                if results and len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                        conf = float(box.conf[0].item()) if hasattr(box, 'conf') else 0.5
                        boxes.append((x1, y1, x2, y2, conf))
                    logger.info(f"YOLO人脸检测发现 {len(boxes)} 个人脸")
            except Exception as e:
                logger.warning(f"YOLO人脸检测失败: {str(e)}")
        
        # 方法2: 使用YOLOv8n预训练模型检测人体
        if self.yolo_model is not None and len(boxes) == 0:
            try:
                results = self.yolo_model.predict(img, conf=self.body_conf_threshold, verbose=False)
                
                if results and len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        cls = int(box.cls[0].item())
                        if cls == 0:  # person类别
                            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                            conf = float(box.conf[0].item())
                            boxes.append((x1, y1, x2, y2, conf))
                    logger.info(f"YOLOv8n人体检测发现 {len(boxes)} 个人体")
            except Exception as e:
                logger.warning(f"YOLOv8n人体检测失败: {str(e)}")
        
        # IoU去重
        if len(boxes) > 1:
            def iou(a, b):
                ax1, ay1, ax2, ay2 = a[:4]
                bx1, by1, bx2, by2 = b[:4]
                inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
                inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
                inter = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
                area_a = (ax2 - ax1) * (ay2 - ay1)
                area_b = (bx2 - bx1) * (by2 - by1)
                union = area_a + area_b - inter
                return inter / union if union > 0 else 0
            
            selected = []
            for box in sorted(boxes, key=lambda x: x[4], reverse=True):
                if not any(iou(box, s) > 0.5 for s in selected):
                    selected.append(box)
            boxes = selected
        
        return boxes
    
    def _analyze_with_local_models(self, image_path: str) -> Dict:
        """使用本地模型进行分析（优化版）"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"无法读取图像: {image_path}")
            
            img_height, img_width = img.shape[:2]
            
            # 图像预处理
            enhanced_img = self.preprocessor.auto_enhance(img)
            
            # 获取人体分割掩码
            segmentation_mask = self._get_person_segmentation_mask(img)
            
            # 检测人物
            person_boxes = self._detect_persons_yolo(enhanced_img)
            
            result = {
                "detected": len(person_boxes),
                "persons": [],
                "success": True
            }
            
            for idx, (x1, y1, x2, y2, conf) in enumerate(person_boxes):
                # 边界检查
                x1, x2 = max(0, min(x1, img_width - 1)), max(0, min(x2, img_width))
                y1, y2 = max(0, min(y1, img_height - 1)), max(0, min(y2, img_height))
                
                if x2 <= x1 or y2 <= y1:
                    continue
                
                face_height = y2 - y1
                face_width = x2 - x1
                
                # 估算人脸位置（如果是人体框）
                is_body_box = face_height > face_width * 1.5
                if is_body_box:
                    face_y1 = max(0, int(y1))
                    face_y2 = min(y2, int(y1 + face_height * 0.3))
                    face_x1 = max(0, int(x1 + face_width * 0.2))
                    face_x2 = min(img_width, int(x2 - face_width * 0.2))
                else:
                    face_y1, face_y2, face_x1, face_x2 = y1, y2, x1, x2
                
                face_img = img[face_y1:face_y2, face_x1:face_x2]
                face_pil = None
                if face_img.size > 0:
                    face_pil = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
                
                # 性别预测
                gender, gender_conf = "unknown", 0.0
                if self.models.get("gender") and face_img.size > 0:
                    try:
                        gender, gender_conf = self.models["gender"].predict(face_img)
                    except Exception as e:
                        logger.warning(f"性别预测失败: {str(e)}")
                
                # 年龄预测
                age, age_conf = 0.0, 0.0
                if self.models.get("age") and face_pil is not None:
                    try:
                        result = self.models["age"].predict(face_pil)
                        if result[0] is not None:
                            age, age_conf = result
                    except Exception as e:
                        logger.warning(f"年龄预测失败: {str(e)}")
                
                # 服装区域检测
                clothing_regions = self._detect_clothing_regions_with_yolo_mask(
                    img, segmentation_mask, (face_x1, face_y1, face_x2, face_y2)
                )
                
                upper_region = clothing_regions["upper"]["region"]
                lower_region = clothing_regions["lower"]["region"]
                
                # 服装颜色分析
                upper_color, upper_conf = self._analyze_clothing_color(upper_region, "upper")
                lower_color, lower_conf = self._analyze_clothing_color(lower_region, "lower")
                
                person_data = {
                    "gender": gender,
                    "gender_confidence": gender_conf,
                    "age": age,
                    "age_confidence": age_conf,
                    "upper_color": upper_color,
                    "upper_color_confidence": upper_conf,
                    "lower_color": lower_color,
                    "lower_color_confidence": lower_conf,
                    "bbox": [face_x1, face_y1, face_x2, face_y2],
                    "upper_bbox": list(clothing_regions["upper"]["bbox"]),
                    "lower_bbox": list(clothing_regions["lower"]["bbox"]),
                    "detection_mode": "yolo_body" if is_body_box else "yolo_face",
                    "confidence": conf
                }
                
                result["persons"].append(person_data)
                logger.info(f"人物 {idx+1}: gender={gender}, age={age}, upper={upper_color}, lower={lower_color}")
            
            result["detected"] = len(result["persons"])
            return result
        
        except Exception as e:
            logger.error(f"本地模型分析失败: {str(e)}")
            return {"detected": 0, "persons": [], "success": False, "error": str(e)}
    
    def analyze_image(self, image_path: str, mode: str = "normal") -> Dict:
        """分析图像"""
        try:
            start_time = time.time()
            
            # 使用本地模型分析
            local_result = self._analyze_with_local_models(image_path)
            
            # 增强模式：使用大模型辅助
            if mode == "enhanced" and local_result.get("detected", 0) == 0:
                logger.info("本地模型未检测到人物，尝试使用大模型...")
                qwen_result = self.analyze_with_qwen(image_path)
                
                if "error" not in qwen_result:
                    local_result = qwen_result
                    local_result["mode"] = "enhanced_qwen"
            
            # 确保结果完整
            if "persons" not in local_result:
                local_result["persons"] = []
            if "detected" not in local_result:
                local_result["detected"] = len(local_result.get("persons", []))
            
            local_result["processing_time"] = time.time() - start_time
            local_result["mode"] = mode
            
            return local_result
        
        except Exception as e:
            logger.error(f"图像分析失败: {str(e)}")
            return {
                "error": str(e),
                "detected": 0,
                "persons": [],
                "mode": mode
            }
    
    def analyze_with_qwen(self, image_path: str) -> Dict:
        """使用Qwen-VL分析图片"""
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")
            
            prompt = """分析图像中的人物信息，返回JSON格式：
{
    "detected": 人数,
    "persons": [
        {
            "gender": "male/female",
            "gender_confidence": 0.9,
            "age": 25,
            "age_confidence": 0.8,
            "upper_color": "red/blue/...",
            "upper_color_confidence": 0.8,
            "lower_color": "black/white/...",
            "lower_color_confidence": 0.8,
            "bbox": [x1, y1, x2, y2]
        }
    ],
    "success": true
}
只输出JSON。"""

            url = f"{self.ollama_base_url}/api/chat"
            payload = {
                "model": self.ollama_model_name,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "你是图像分析助手，只输出有效JSON。"},
                    {"role": "user", "content": prompt, "images": [base64_image]},
                ],
            }
            
            resp = requests.post(url, json=payload, timeout=self.ollama_timeout_s)
            
            if resp.status_code != 200:
                return {"error": f"Ollama错误: {resp.status_code}"}
            
            resp_json = resp.json()
            content = resp_json.get("message", {}).get("content", "")
            
            # 提取JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
            
            return {"error": "无法解析响应"}
        
        except Exception as e:
            logger.error(f"Qwen分析失败: {str(e)}")
            return {"error": str(e)}


# 创建全局实例
image_analyzer = ImageAnalyzer()
