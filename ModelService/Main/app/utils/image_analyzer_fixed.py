"""
完全重写的优化版人物特征分析器
修复了所有已知问题
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def _torch_load_compat(path: str, map_location=None) -> Any:
    try:
        return torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:
        return torch.load(path, map_location=map_location)

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
    if torch.cuda.is_available():
        return ['cuda:0']
    return ['cpu']


# ============== 图像预处理 ==============

class ImagePreprocessor:
    @staticmethod
    def clahe_enhance(img: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        except Exception as e:
            logger.warning(f"CLAHE失败: {str(e)}")
            return img
    
    @staticmethod
    def auto_enhance(img: np.ndarray) -> np.ndarray:
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            if contrast < 40:
                img = ImagePreprocessor.clahe_enhance(img, clip_limit=2.5)
            elif brightness < 100:
                img = ImagePreprocessor.clahe_enhance(img, clip_limit=1.5)
            
            return img
        except Exception:
            return img


# ============== 颜色分析 ==============

class ColorAnalyzer:
    HSV_RANGES = {
        'black': ([0, 0, 0], [180, 255, 85]),
        'white': ([0, 0, 200], [180, 30, 255]),
        'gray': ([0, 0, 85], [180, 30, 200]),
        'red': ([0, 100, 100], [10, 255, 255]),
        'orange': ([10, 100, 100], [25, 255, 255]),
        'yellow': ([25, 100, 100], [40, 255, 255]),
        'green': ([40, 50, 50], [80, 255, 255]),
        'cyan': ([80, 50, 50], [100, 255, 255]),
        'blue': ([100, 80, 50], [130, 255, 255]),
        'purple': ([130, 50, 50], [160, 255, 255]),
        'pink': ([160, 50, 100], [180, 255, 255]),
    }
    
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
    }
    
    @staticmethod
    def kmeans_clustering(img_region: np.ndarray, k: int = 5) -> List[Tuple[str, float, int]]:
        try:
            if img_region.size == 0:
                return []
            
            h, w = img_region.shape[:2]
            if h * w > 10000:
                img_region = cv2.resize(img_region, (100, int(100 * h / w)))
            
            rgb = cv2.cvtColor(img_region, cv2.COLOR_BGR2RGB)
            pixels = rgb.reshape(-1, 3).astype(np.float32)
            
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            
            unique, counts = np.unique(labels, return_counts=True)
            
            results = []
            for center, count in zip(centers, counts):
                color_name = ColorAnalyzer._rgb_to_color_name(center)
                confidence = min(1.0, count / (len(pixels) * 0.3))
                results.append((color_name, confidence, int(count)))
            
            results.sort(key=lambda x: x[2], reverse=True)
            return results
        except Exception as e:
            logger.warning(f"K-means失败: {str(e)}")
            return []
    
    @staticmethod
    def _rgb_to_color_name(rgb: np.ndarray) -> str:
        rgb = rgb.astype(int)
        min_dist = float('inf')
        best = 'unknown'
        for name, std_rgb in ColorAnalyzer.RGB_COLORS.items():
            dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(rgb, std_rgb)))
            if dist < min_dist:
                min_dist = dist
                best = name
        return best
    
    @staticmethod
    def analyze_by_hsv(img_region: np.ndarray) -> Tuple[str, float]:
        try:
            if img_region.size == 0:
                return 'unknown', 0.0
            
            hsv = cv2.cvtColor(img_region, cv2.COLOR_BGR2HSV)
            total_pixels = hsv.shape[0] * hsv.shape[1]
            
            color_counts = {}
            for color_name, (lower, upper) in ColorAnalyzer.HSV_RANGES.items():
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                mask = cv2.inRange(hsv, lower_np, upper_np)
                color_counts[color_name] = np.sum(mask > 0)
            
            # 合并红色
            mask1 = cv2.inRange(hsv, np.array([0, 100, 100], dtype=np.uint8),
                               np.array([10, 255, 255], dtype=np.uint8))
            mask2 = cv2.inRange(hsv, np.array([160, 100, 100], dtype=np.uint8),
                               np.array([180, 255, 255], dtype=np.uint8))
            color_counts['red'] = color_counts.get('red', 0) + np.sum(cv2.bitwise_or(mask1, mask2) > 0)
            
            if not color_counts or max(color_counts.values()) == 0:
                return ColorAnalyzer._rgb_fallback(img_region)
            
            best_color = max(color_counts.items(), key=lambda x: x[1])[0]
            best_ratio = color_counts[best_color] / total_pixels
            
            if best_ratio > 0.5:
                confidence = 0.9
            elif best_ratio > 0.3:
                confidence = 0.8
            elif best_ratio > 0.15:
                confidence = 0.7
            else:
                confidence = 0.6
            
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
        try:
            avg_rgb = np.array(cv2.mean(img_region)[:3])
            min_dist = float('inf')
            best = 'unknown'
            for name, rgb in ColorAnalyzer.RGB_COLORS.items():
                dist = np.sqrt(np.sum((avg_rgb - np.array(rgb)) ** 2))
                if dist < min_dist:
                    min_dist = dist
                    best = name
            confidence = max(0.5, 1 - (min_dist / 400))
            return best, confidence
        except Exception:
            return 'unknown', 0.0
    
    @classmethod
    def analyze(cls, img_region: np.ndarray) -> Tuple[str, float]:
        if img_region is None or img_region.size == 0:
            return 'unknown', 0.0
        
        # K-means
        clusters = cls.kmeans_clustering(img_region, k=5)
        if clusters and clusters[0][1] > 0.35:
            return clusters[0][0], clusters[0][1]
        
        # HSV
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
                state_dict = checkpoint.get('model_state_dict', checkpoint)
            else:
                raise ValueError("无效的模型检查点格式")
            
            self.model = models.resnet18(weights=None)
            num_features = self.model.fc.in_features
            self.model.fc = nn.Sequential()
            self.model.fc.add_module('1', nn.Linear(num_features, 512))
            self.model.fc.add_module('2', nn.ReLU())
            self.model.fc.add_module('4', nn.Linear(512, len(self.classes)))
            
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
            class AgeModel(nn.Module):
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
            
            self.model = AgeModel(num_classes=len(self.age_classes))
            
            checkpoint = _torch_load_compat(self.model_path, map_location=self.device)
            state_dict = checkpoint.get('model_state_dict', checkpoint)
            
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
            
            if confidence < 0.35:
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
        
        # 检测参数 - 非常低的阈值以提高检出率
        self.face_conf_threshold = 0.15
        self.body_conf_threshold = 0.25
        
        self.preprocessor = ImagePreprocessor()
        self.color_analyzer = ColorAnalyzer()
        
        # DeepLabV3
        self.deeplabv3 = None
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        # Ollama
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_model_name = os.getenv("OLLAMA_QWEN_MODEL", "qwen3.5:4b")
        self.ollama_timeout_s = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))
        
        # YOLOv8预训练
        self.yolo_model = None
        
        logger.info(f"分析器初始化完成，设备: {self.device}")
        
        self.load_models()
    
    def _get_model_paths(self) -> Dict[str, str]:
        return {
            'face': str(MODEL_DIR / "output/face_detection/train2/weights/best.pt"),
            'color': str(MODEL_DIR / "output/color_classification/best_model.pth"),
            'age': str(MODEL_DIR / "output/age_estimation/weights/best.pt"),
            'gender': str(MODEL_DIR / "output/gender_classification/train/weights/best.pt")
        }
    
    def load_models(self):
        try:
            # DeepLabV3
            try:
                self.deeplabv3 = models.segmentation.deeplabv3_resnet50(pretrained=True)
                self.deeplabv3.eval()
                self.deeplabv3.to(self.device)
                logger.info("DeepLabV3加载成功")
            except Exception as e:
                logger.warning(f"DeepLabV3加载失败: {str(e)}")
                self.deeplabv3 = None
            
            from ultralytics import YOLO
            
            # 人脸检测模型
            if self.model_paths['face'] and os.path.exists(self.model_paths['face']):
                try:
                    self.models['face'] = YOLO(self.model_paths['face'])
                    self.models['face'].to(self.device)
                    logger.info("人脸检测模型加载成功")
                except Exception as e:
                    logger.warning(f"人脸检测模型加载失败: {str(e)}")
                    self.models['face'] = None
            else:
                logger.warning(f"人脸检测模型文件不存在: {self.model_paths['face']}")
                self.models['face'] = None
            
            # 颜色分类模型
            if self.model_paths['color'] and os.path.exists(self.model_paths['color']):
                try:
                    self.models['color'] = ColorModel(self.model_paths['color'], self.device)
                except Exception as e:
                    logger.warning(f"颜色分类模型加载失败: {str(e)}")
                    self.models['color'] = None
            else:
                logger.warning(f"颜色分类模型文件不存在: {self.model_paths['color']}")
                self.models['color'] = None
            
            # 年龄估计模型
            if self.model_paths['age'] and os.path.exists(self.model_paths['age']):
                try:
                    self.models['age'] = AgeModel(self.model_paths['age'], self.device)
                except Exception as e:
                    logger.warning(f"年龄估计模型加载失败: {str(e)}")
                    self.models['age'] = None
            else:
                logger.warning(f"年龄估计模型文件不存在: {self.model_paths['age']}")
                self.models['age'] = None
            
            # 性别分类模型
            if self.model_paths['gender'] and os.path.exists(self.model_paths['gender']):
                try:
                    self.models['gender'] = GenderModel(self.model_paths['gender'], self.device)
                except Exception as e:
                    logger.warning(f"性别分类模型加载失败: {str(e)}")
                    self.models['gender'] = None
            else:
                logger.warning(f"性别分类模型文件不存在: {self.model_paths['gender']}")
                self.models['gender'] = None
            
            # YOLOv8n预训练模型
            try:
                self.yolo_model = YOLO("yolov8n.pt")
                self.yolo_model.to(self.device)
                logger.info("YOLOv8n预训练模型加载成功")
            except Exception as e:
                logger.warning(f"YOLOv8n加载失败: {str(e)}")
                self.yolo_model = None
            
        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
    
    def _get_person_mask(self, img: np.ndarray) -> Optional[np.ndarray]:
        h, w = img.shape[:2]
        
        if self.deeplabv3 is not None:
            try:
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    output = self.deeplabv3(input_tensor)['out'][0]
                
                mask = torch.argmax(output, dim=0).cpu().numpy()
                person_mask = (mask == 15).astype(np.uint8) * 255
                person_mask = cv2.resize(person_mask, (w, h), interpolation=cv2.INTER_NEAREST)
                return person_mask
            except Exception as e:
                logger.warning(f"分割失败: {str(e)}")
        
        return None
    
    def _detect_persons(self, img: np.ndarray) -> List[Tuple[int, int, int, int, float, str]]:
        """检测人物，返回: [(x1, y1, x2, y2, conf, mode), ...]"""
        all_boxes = []
        
        # 方法1: 专用人脸检测模型
        if self.models.get('face'):
            try:
                results = self.models['face'].predict(img, conf=self.face_conf_threshold, verbose=False)
                if results and len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                        conf = float(box.conf[0].item()) if hasattr(box, 'conf') else 0.5
                        all_boxes.append((x1, y1, x2, y2, conf, 'face'))
                    logger.info(f"人脸检测: {len(all_boxes)}个")
            except Exception as e:
                logger.warning(f"人脸检测失败: {str(e)}")
        
        # 方法2: YOLOv8n预训练模型
        if self.yolo_model is not None and len(all_boxes) == 0:
            try:
                results = self.yolo_model.predict(img, conf=self.body_conf_threshold, verbose=False)
                if results and len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        cls = int(box.cls[0].item())
                        if cls == 0:  # person
                            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                            conf = float(box.conf[0].item())
                            all_boxes.append((x1, y1, x2, y2, conf, 'body'))
                    logger.info(f"YOLOv8n检测: {len(all_boxes)}个")
            except Exception as e:
                logger.warning(f"YOLOv8n检测失败: {str(e)}")
        
        # IoU去重
        if len(all_boxes) > 1:
            def calc_iou(a, b):
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
            for box in sorted(all_boxes, key=lambda x: x[4], reverse=True):
                if not any(calc_iou(box, s) > 0.5 for s in selected):
                    selected.append(box)
            all_boxes = selected
        
        return all_boxes
    
    def _detect_clothing_regions(
        self,
        img: np.ndarray,
        face_box: Tuple[int, int, int, int],
        person_mask: Optional[np.ndarray]
    ) -> Dict[str, Dict]:
        x1, y1, x2, y2 = face_box
        face_h = y2 - y1
        face_w = x2 - x1
        h, w = img.shape[:2]
        
        if face_h <= 0 or face_w <= 0:
            return {
                "upper": {"region": np.array([]), "bbox": (0, 0, 0, 0)},
                "lower": {"region": np.array([]), "bbox": (0, 0, 0, 0)}
            }
        
        # 上衣区域
        upper_y1 = y2
        upper_y2 = min(upper_y1 + int(face_h * 2.5), h)
        upper_x1 = max(0, x1 - int(face_w * 0.5))
        upper_x2 = min(x2 + int(face_w * 0.5), w)
        
        # 下装区域
        lower_y1 = upper_y2
        lower_y2 = min(lower_y1 + int(face_h * 2.5), h)
        lower_x1 = max(0, x1 - int(face_w * 0.6))
        lower_x2 = min(x2 + int(face_w * 0.6), w)
        
        # 使用分割掩码优化
        if person_mask is not None:
            try:
                if person_mask.shape[:2] != (h, w):
                    person_mask = cv2.resize(person_mask, (w, h))
                person_mask_bool = person_mask.astype(bool)
                
                def refine(x1_, y1_, x2_, y2_):
                    x1_ = max(0, min(x1_, w - 1))
                    x2_ = max(0, min(x2_, w))
                    y1_ = max(0, min(y1_, h - 1))
                    y2_ = max(0, min(y2_, h))
                    if x2_ <= x1_ or y2_ <= y1_:
                        return x1_, y1_, x2_, y2_
                    sub = person_mask_bool[y1_:y2_, x1_:x2_]
                    if not sub.any():
                        return x1_, y1_, x2_, y2_
                    rows = np.any(sub, axis=1)
                    cols = np.any(sub, axis=0)
                    ys = np.where(rows)[0]
                    xs = np.where(cols)[0]
                    if len(ys) == 0 or len(xs) == 0:
                        return x1_, y1_, x2_, y2_
                    return (x1_ + xs[0], y1_ + ys[0], x1_ + xs[-1], y1_ + ys[-1])
                
                upper_x1, upper_y1, upper_x2, upper_y2 = refine(upper_x1, upper_y1, upper_x2, upper_y2)
                lower_x1, lower_y1, lower_x2, lower_y2 = refine(lower_x1, lower_y1, lower_x2, lower_y2)
            except Exception as e:
                logger.warning(f"掩码优化失败: {str(e)}")
        
        return {
            "upper": {"region": img[upper_y1:upper_y2, upper_x1:upper_x2],
                     "bbox": (int(upper_x1), int(upper_y1), int(upper_x2), int(upper_y2))},
            "lower": {"region": img[lower_y1:lower_y2, lower_x1:lower_x2],
                     "bbox": (int(lower_x1), int(lower_y1), int(lower_x2), int(lower_y2))}
        }
    
    def _analyze_color(self, img_region: np.ndarray, region_type: str = "upper") -> Tuple[str, float]:
        if img_region is None or img_region.size == 0:
            return "unknown", 0.0
        
        # 优先K-means
        clusters = self.color_analyzer.kmeans_clustering(img_region, k=5)
        if clusters and clusters[0][1] > 0.3:
            return clusters[0][0], clusters[0][1]
        
        # 使用颜色模型
        if self.models.get("color"):
            try:
                rgb_img = cv2.cvtColor(img_region, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                
                colors = []
                confidences = []
                for scale in [0.8, 1.0, 1.2]:
                    scaled = pil_img.resize((int(224 * scale), int(224 * scale)))
                    color, conf = self.models["color"].predict(scaled)
                    if color:
                        colors.append(color)
                        confidences.append(conf)
                
                if colors:
                    counts = Counter(colors)
                    most_common = counts.most_common(1)[0][0]
                    avg_conf = np.mean([c for c, conf in zip(colors, confidences) if c == most_common])
                    if avg_conf > 0.2:
                        return most_common, avg_conf
            except Exception as e:
                logger.warning(f"颜色模型预测失败: {str(e)}")
        
        # HSV分析
        return self.color_analyzer.analyze_by_hsv(img_region)
    
    def analyze_image(self, image_path: str, mode: str = "normal") -> Dict:
        """分析图像"""
        start_time = time.time()
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"无法读取图像: {image_path}")
            
            img_h, img_w = img.shape[:2]
            logger.info(f"开始分析图像: {image_path}, 尺寸: {img_w}x{img_h}")
            
            # 图像预处理
            enhanced_img = self.preprocessor.auto_enhance(img)
            
            # 获取分割掩码
            person_mask = self._get_person_mask(img)
            
            # 检测人物
            person_boxes = self._detect_persons(enhanced_img)
            logger.info(f"共检测到 {len(person_boxes)} 个人")
            
            persons = []
            
            for idx, (x1, y1, x2, y2, conf, detect_mode) in enumerate(person_boxes):
                # 边界检查
                x1, x2 = max(0, min(x1, img_w - 1)), max(0, min(x2, img_w))
                y1, y2 = max(0, min(y1, img_h - 1)), max(0, min(y2, img_h))
                
                if x2 <= x1 or y2 <= y1:
                    continue
                
                face_h = y2 - y1
                face_w = x2 - x1
                
                # 估算人脸位置
                is_body = detect_mode == 'body' or face_h > face_w * 1.5
                if is_body:
                    face_y1 = max(0, int(y1))
                    face_y2 = min(y2, int(y1 + face_h * 0.3))
                    face_x1 = max(0, int(x1 + face_w * 0.2))
                    face_x2 = min(img_w, int(x2 - face_w * 0.2))
                else:
                    face_y1, face_y2, face_x1, face_x2 = y1, y2, x1, x2
                
                face_img = img[face_y1:face_y2, face_x1:face_x2]
                face_pil = None
                if face_img.size > 0:
                    face_pil = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
                
                # 性别预测
                gender = "unknown"
                gender_conf = 0.0
                if self.models.get("gender") and face_img.size > 0:
                    try:
                        gender, gender_conf = self.models["gender"].predict(face_img)
                    except Exception as e:
                        logger.warning(f"性别预测失败: {str(e)}")
                
                # 年龄预测
                age = 0.0
                age_conf = 0.0
                if self.models.get("age") and face_pil is not None:
                    try:
                        age_result = self.models["age"].predict(face_pil)
                        if age_result[0] is not None:
                            age, age_conf = age_result
                    except Exception as e:
                        logger.warning(f"年龄预测失败: {str(e)}")
                
                # 服装区域
                clothing = self._detect_clothing_regions(img, (face_x1, face_y1, face_x2, face_y2), person_mask)
                upper_region = clothing["upper"]["region"]
                lower_region = clothing["lower"]["region"]
                
                # 服装颜色
                upper_color, upper_conf = self._analyze_color(upper_region, "upper")
                lower_color, lower_conf = self._analyze_color(lower_region, "lower")
                
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
                    "upper_bbox": list(clothing["upper"]["bbox"]),
                    "lower_bbox": list(clothing["lower"]["bbox"]),
                    "detection_mode": detect_mode,
                    "confidence": conf
                }
                
                persons.append(person_data)
                logger.info(f"人物{idx+1}: gender={gender}, age={age}, upper={upper_color}, lower={lower_color}")
            
            # 如果没有检测到，尝试大模型
            result = {
                "detected": len(persons),
                "persons": persons,
                "success": True,
                "processing_time": time.time() - start_time,
                "mode": mode
            }
            
            if len(persons) == 0 and mode == "enhanced":
                logger.info("本地模型未检测到，尝试大模型...")
                qwen_result = self._analyze_with_qwen(image_path)
                if "error" not in qwen_result:
                    result = qwen_result
                    result["mode"] = "enhanced_qwen"
            
            return result
            
        except Exception as e:
            logger.error(f"分析失败: {str(e)}")
            return {
                "error": str(e),
                "detected": 0,
                "persons": [],
                "success": False,
                "mode": mode
            }
    
    def _analyze_with_qwen(self, image_path: str) -> Dict:
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")
            
            prompt = """分析图像中的人物信息，返回JSON：
{
    "detected": 人数,
    "persons": [{"gender": "male/female", "gender_confidence": 0.9, "age": 25, "age_confidence": 0.8, "upper_color": "red", "upper_color_confidence": 0.8, "lower_color": "blue", "lower_color_confidence": 0.8, "bbox": [x1,y1,x2,y2]}],
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
            
            content = resp.json().get("message", {}).get("content", "")
            
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
            
            return {"error": "无法解析响应"}
        
        except Exception as e:
            logger.error(f"Qwen分析失败: {str(e)}")
            return {"error": str(e)}


# 全局实例
image_analyzer = ImageAnalyzer()
