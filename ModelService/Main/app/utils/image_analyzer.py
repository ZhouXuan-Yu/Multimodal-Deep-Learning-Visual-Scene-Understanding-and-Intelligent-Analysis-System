import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import cv2
import os
from pathlib import Path
import numpy as np
try:
    import mediapipe as mp  # type: ignore
except ImportError:
    # mediapipe 是可选依赖：缺失时不影响本项目的几何/分割回退逻辑
    mp = None
from torchvision.models.segmentation import deeplabv3_resnet50
import logging
import threading
from queue import Queue
from typing import Any, Dict, List, Optional, Tuple
import warnings
from ultralytics import YOLO
from scipy import ndimage
import base64
import json
import requests  # 调用本地 Ollama（Qwen3-VL）
import time
from functools import lru_cache
import hashlib

warnings.filterwarnings("ignore", category=UserWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- torch.load compatibility (PyTorch 2.6+ weights_only default change) ---
def _torch_load_compat(path: str, map_location=None) -> Any:
    """
    兼容 PyTorch 2.6+ 默认 weights_only=True 的行为。
    对于本项目内训练得到的 checkpoint，我们需要允许反序列化完整对象结构。

    - 新版本：显式使用 weights_only=False
    - 旧版本：自动回退到不带该参数的 torch.load
    """
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
    """获取可用的设备，优先使用GPU"""
    if torch.cuda.is_available():
        return ['cuda:0']
    return ['cpu']

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

class ColorModel(ModelBase):
    def __init__(self, model_path: str, device: str):
        super().__init__(model_path, device)
        self.classes = None
        self.load_model()
    
    def load_model(self):
        """加载颜色分类模型"""
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
            
            # 创建ResNet18模型
            self.model = models.resnet18(weights=None)
            num_features = self.model.fc.in_features
            self.model.fc = nn.Sequential()
            self.model.fc.add_module('1', nn.Linear(num_features, 512))
            self.model.fc.add_module('2', nn.ReLU())
            self.model.fc.add_module('4', nn.Linear(512, len(self.classes)))
            
            # 处理状态字典中可能有"model."前缀的情况
            # 移除'model.'前缀以适应模型结构
            fixed_state_dict = {}
            model_prefix = 'model.'
            for k, v in state_dict.items():
                if k.startswith(model_prefix):
                    fixed_state_dict[k[len(model_prefix):]] = v
                else:
                    fixed_state_dict[k] = v
            
            # 加载清理后的权重
            self.model.load_state_dict(fixed_state_dict)
            self.model.to(self.device)
            self.model.eval()
            logger.info("颜色分类模型加载成功")
        except Exception as e:
            logger.error(f"加载颜色分类模型失败: {str(e)}")
            raise
    
    def predict(self, img):
        """预测颜色类别"""
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

class AgeModel(ModelBase):
    def __init__(self, model_path: str, device: str):
        super().__init__(model_path, device)
        self.age_classes = ['0-10', '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71+']
        self.load_model()
    
    def load_model(self):
        """加载年龄估计模型"""
        try:
            class AgeEstimationModel(nn.Module):
                def __init__(self, num_classes):
                    super().__init__()
                    # 使用ResNet50作为基础模型
                    self.backbone = models.resnet50(weights=None)
                    
                    # 修改最后的全连接层，匹配训练时的结构
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
            
            # 创建模型实例
            self.model = AgeEstimationModel(num_classes=len(self.age_classes))
            
            # 加载权重
            checkpoint = _torch_load_compat(self.model_path, map_location=self.device)
            if isinstance(checkpoint, dict):
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                else:
                    state_dict = checkpoint
            else:
                state_dict = checkpoint
            
            # 处理state_dict中的键
            new_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith('module.'):
                    k = k[7:]  # 移除'module.'前缀
                new_state_dict[k] = v
            
            # 加载处理后的权重
            self.model.load_state_dict(new_state_dict)
            self.model.to(self.device)
            self.model.eval()
            logger.info("年龄估计模型加载成功")
        except Exception as e:
            logger.error(f"加载年龄估计模型失败: {str(e)}")
            raise
    
    def predict(self, img):
        """预测年龄"""
        try:
            # 确保输入是PIL图像
            if not isinstance(img, Image.Image):
                if isinstance(img, np.ndarray):
                    img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                else:
                    raise ValueError("输入必须是PIL图像或numpy数组")
            
            # 应用转换
            img_tensor = self.transform(img).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(img_tensor)
                probs = torch.softmax(outputs, dim=1)
                confidence, pred_idx = torch.max(probs, dim=1)
                pred_age = self.age_classes[pred_idx.item()]
                
                # 解析年龄范围并计算中间值
                age_range = pred_age.split('-')
                if len(age_range) == 2:
                    min_age = int(age_range[0])
                    max_age = int(age_range[1])
                else:  # 处理 "71+" 这种情况
                    min_age = int(pred_age.replace('+', ''))
                    max_age = min_age + 29  # 假设最大年龄为100岁
                
                # 根据置信度在范围内插值
                predicted_age = min_age + (max_age - min_age) * confidence.item()
                
                return predicted_age, confidence.item()
        except Exception as e:
            logger.error(f"年龄预测失败: {str(e)}")
            return None, 0.0

class GenderModel(ModelBase):
    def __init__(self, model_path: str, device: str):
        super().__init__(model_path, device)
        self.confidence_threshold = 0.5  # 降低基础阈值
        self.load_model()
        # 增强的预处理转换
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def load_model(self):
        """加载性别分类模型"""
        try:
            self.model = YOLO(self.model_path)
            self.model.to(self.device)
            logger.info("性别分类模型加载成功")
        except Exception as e:
            logger.error(f"加载性别分类模型失败: {str(e)}")
            raise

    def predict(self, img):
        """预测性别"""
        try:
            # 确保输入是PIL图像
            if isinstance(img, Image.Image):
                img = np.array(img)
            
            # 运行YOLO预测
            results = self.model(img)
            
            if not results or len(results) == 0:
                logger.warning("性别预测没有返回结果")
                return "unknown", 0.0
            
            # 获取预测结果
            result = results[0]  # 获取第一个预测结果
            
            if not hasattr(result, 'probs') or not result.probs:
                logger.warning("性别预测概率为空")
                return "unknown", 0.0
            
            # 获取female和male的概率
            probs = result.probs
            female_prob = float(probs.data[0])
            male_prob = float(probs.data[1])
            
            # 记录原始预测概率
            logger.info(f"性别预测原始概率 - 女性: {female_prob:.4f}, 男性: {male_prob:.4f}")
            
            # 修改判断逻辑：直接选择概率最高的性别
            if female_prob >= male_prob:
                gender = 'female'
                confidence = female_prob
            else:
                gender = 'male'
                confidence = male_prob
            
            # 记录最终预测结果
            logger.info(f"性别预测结果: {gender}, 置信度: {confidence:.4f}")
            
            # 如果置信度太低，标记为unknown
            if confidence < 0.4:  # 降低阈值到0.4
                logger.warning(f"性别预测置信度过低: {confidence:.4f}")
                return "unknown", confidence
            
            return gender, confidence
            
        except Exception as e:
            logger.error(f"性别预测失败: {str(e)}")
            return "unknown", 0.0

class ImageAnalyzer(metaclass=Singleton):
    def __init__(self):
        self.device = get_device()[0]
        self.models = {}
        self.model_paths = self._get_model_paths()
        # 人脸检测置信度阈值（适当调低以尽量多检出）
        # 过低会导致同一张脸产生多个重叠框（前端看起来像“一个人被识别成好几个”）
        self.face_conf_threshold = 0.25  # 降低阈值以提高检出率
        # 人体检测置信度阈值（用于备选方案）
        self.body_conf_threshold = 0.35  # 人体检测阈值
        self.deeplabv3 = None
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        # 本地 Ollama（Qwen3.5-4B）配置
        # - OLLAMA_BASE_URL: 默认 http://localhost:11434
        # - OLLAMA_QWEN_MODEL: 默认 qwen3.5:4b
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_model_name = os.getenv("OLLAMA_QWEN_MODEL", "qwen3.5:4b")
        try:
            self.ollama_timeout_s = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))
        except Exception:
            self.ollama_timeout_s = 120
        logger.info(
            f"本地增强分析配置：OLLAMA_BASE_URL={self.ollama_base_url}, "
            f"OLLAMA_QWEN_MODEL={self.ollama_model_name}, timeout={self.ollama_timeout_s}s"
        )
        
        # 人体检测模型（备选方案，用于人脸检测失败时）
        self.body_model = None
        self.body_model_path = str(MODEL_DIR / "output/body_detection/yolov8n.pt")  # 轻量级人体检测模型

        self.load_models()
        self.cache = {}
    
    def _get_model_paths(self) -> Dict[str, str]:
        """获取模型文件路径"""
        paths = {
            'face': str(MODEL_DIR / "output/face_detection/train2/weights/best.pt"),
            'color': str(MODEL_DIR / "output/color_classification/best_model.pth"),
            'age': str(MODEL_DIR / "output/age_estimation/weights/best.pt"),
            'gender': str(MODEL_DIR / "output/gender_classification/train/weights/best.pt")
        }
        
        # 验证模型文件是否存在
        for name, path in paths.items():
            if not os.path.exists(path):
                logger.warning(f"模型文件不存在: {path}")
                paths[name] = None
        
        return paths
    
    def load_models(self):
        """加载所有模型"""
        try:
            # 加载DeepLabV3模型
            try:
                self.deeplabv3 = models.segmentation.deeplabv3_resnet50(pretrained=True)
                self.deeplabv3.eval()
                self.deeplabv3.to(self.device)
                logger.info("DeepLabV3模型加载成功")
            except Exception as e:
                logger.error(f"加载DeepLabV3模型失败: {str(e)}")
                self.deeplabv3 = None
            
            # 加载YOLO模型
            from ultralytics import YOLO
            
            # 加载人脸检测模型
            if self.model_paths['face']:
                try:
                    self.models['face'] = YOLO(self.model_paths['face'])
                    # 将模型移动到指定设备并设置默认置信度阈值
                    try:
                        self.models['face'].to(self.device)
                    except Exception as e:
                        logger.warning(f"人脸检测模型移动到设备失败，将使用默认设备: {str(e)}")
                    # Ultralytics YOLO 支持通过 overrides 设置默认 conf
                    try:
                        if hasattr(self.models['face'], "overrides"):
                            self.models['face'].overrides['conf'] = self.face_conf_threshold
                    except Exception as e:
                        logger.warning(f"设置人脸检测模型默认置信度阈值失败: {str(e)}")
                    logger.info(f"人脸检测模型加载成功，默认置信度阈值: {self.face_conf_threshold}")
                except Exception as e:
                    logger.error(f"加载人脸检测模型失败: {str(e)}")
                    self.models['face'] = None
            
            # 加载颜色分类模型
            if self.model_paths['color']:
                try:
                    self.models['color'] = ColorModel(self.model_paths['color'], self.device)
                    logger.info("颜色分类模型加载成功")
                except Exception as e:
                    logger.error(f"加载颜色分类模型失败: {str(e)}")
                    self.models['color'] = None
            
            # 加载年龄估计模型
            if self.model_paths['age']:
                try:
                    self.models['age'] = AgeModel(self.model_paths['age'], self.device)
                    logger.info("年龄估计模型加载成功")
                except Exception as e:
                    logger.error(f"加载年龄估计模型失败: {str(e)}")
                    self.models['age'] = None
            
            # 加载性别分类模型
            if self.model_paths['gender']:
                try:
                    self.models['gender'] = GenderModel(self.model_paths['gender'], self.device)
                    logger.info("性别分类模型加载成功")
                except Exception as e:
                    logger.error(f"加载性别分类模型失败: {str(e)}")
                    self.models['gender'] = None
            
            # 加载人体检测模型（备选方案）
            if os.path.exists(self.body_model_path):
                try:
                    self.body_model = YOLO(self.body_model_path)
                    self.body_model.to(self.device)
                    logger.info(f"人体检测模型加载成功: {self.body_model_path}")
                except Exception as e:
                    logger.error(f"加载人体检测模型失败: {str(e)}")
                    self.body_model = None
            else:
                logger.warning(f"人体检测模型文件不存在: {self.body_model_path}，将使用内置YOLOv8n")
                try:
                    # 使用内置的YOLOv8n人体检测（person类别为0）
                    self.body_model = YOLO("yolov8n.pt")
                    self.body_model.to(self.device)
                    logger.info("内置YOLOv8n人体检测模型加载成功")
                except Exception as e:
                    logger.error(f"加载内置人体检测模型失败: {str(e)}")
                    self.body_model = None
            
        except ImportError as e:
            logger.error(f"加载模型失败: {str(e)}")
    
    def _detect_clothing_regions(
        self,
        img: np.ndarray,
        face_box: Tuple[int, int, int, int],
        segmentation_mask: Optional[np.ndarray] = None
    ) -> Dict[str, Dict]:
        """
        通过人脸框稳定地推断上衣/下装区域（优化版）
        使用更准确的身体比例估算，并添加更多验证
        """
        x1, y1, x2, y2 = face_box
        face_height = y2 - y1
        face_width = x2 - x1
        img_height, img_width = img.shape[:2]
        
        # 确保人脸框有效
        if face_height <= 0 or face_width <= 0:
            return {
                "upper": {"region": np.array([]), "bbox": (0, 0, 0, 0)},
                "lower": {"region": np.array([]), "bbox": (0, 0, 0, 0)}
            }

        # 使用更准确的身体比例估算
        # 人体比例参考：头身比约为1:6到1:8，上衣约占身高的1/3，下装约占身高的1/4
        # 假设人脸大小约等于身高的1/10到1/12
        
        # 上衣区域：从脸底向下 2-2.5 倍人脸高度（覆盖上半身）
        upper_height = int(face_height * 2.2)
        upper_y1 = y2
        upper_y2 = min(upper_y1 + upper_height, img_height)
        upper_x1 = max(0, x1 - int(face_width * 0.5))
        upper_x2 = min(x2 + int(face_width * 0.5), img_width)

        # 下装区域：从上衣底部开始，向下延伸
        lower_height = int(face_height * 2.5)
        lower_y1 = upper_y2
        lower_y2 = min(lower_y1 + lower_height, img_height)
        lower_x1 = max(0, x1 - int(face_width * 0.6))
        lower_x2 = min(x2 + int(face_width * 0.6), img_width)
        
        # 验证区域大小，确保有足够的像素用于颜色分析
        min_region_size = 10  # 最小区域尺寸
        
        if (upper_x2 - upper_x1) < min_region_size or (upper_y2 - upper_y1) < min_region_size:
            upper_x1, upper_y1, upper_x2, upper_y2 = x1, y2, x2, min(y2 + face_height, img_height)
        
        if (lower_x2 - lower_x1) < min_region_size or (lower_y2 - lower_y1) < min_region_size:
            lower_x1, lower_y1, lower_x2, lower_y2 = x1, upper_y2, x2, min(upper_y2 + face_height * 2, img_height)

        # 如果有语义分割掩码，用 person 类别(=15)在每个候选框内部做一次收缩
        if segmentation_mask is not None:
            try:
                person_mask = (segmentation_mask == 15)

                def refine_with_mask(x1_, y1_, x2_, y2_):
                    x1_ = max(0, min(x1_, img_width - 1))
                    x2_ = max(0, min(x2_, img_width))
                    y1_ = max(0, min(y1_, img_height - 1))
                    y2_ = max(0, min(y2_, img_height))
                    if x2_ <= x1_ or y2_ <= y1_:
                        return x1_, y1_, x2_, y2_
                    sub = person_mask[y1_:y2_, x1_:x2_]
                    if not sub.any():
                        return x1_, y1_, x2_, y2_
                    rows = np.any(sub, axis=1)
                    cols = np.any(sub, axis=0)
                    ys = np.where(rows)[0]
                    xs = np.where(cols)[0]
                    if len(ys) == 0 or len(xs) == 0:
                        return x1_, y1_, x2_, y2_
                    return (
                        x1_ + int(xs[0]),
                        y1_ + int(ys[0]),
                        x1_ + int(xs[-1]),
                        y1_ + int(ys[-1]),
                    )

                upper_x1, upper_y1, upper_x2, upper_y2 = refine_with_mask(
                    upper_x1, upper_y1, upper_x2, upper_y2
                )
                lower_x1, lower_y1, lower_x2, lower_y2 = refine_with_mask(
                    lower_x1, lower_y1, lower_x2, lower_y2
                )
            except Exception as e:
                logger.warning(f"使用分割掩码细化衣服区域失败: {str(e)}")

        upper_region = img[upper_y1:upper_y2, upper_x1:upper_x2]
        lower_region = img[lower_y1:lower_y2, lower_x1:lower_x2]

        return {
            "upper": {
                "region": upper_region,
                "bbox": (int(upper_x1), int(upper_y1), int(upper_x2), int(upper_y2)),
            },
            "lower": {
                "region": lower_region,
                "bbox": (int(lower_x1), int(lower_y1), int(lower_x2), int(lower_y2)),
            },
        }

    def _analyze_color_region(self, img_region, region_type: str = "upper") -> Tuple[str, float]:
        """对单个衣物区域进行颜色分类（优化版）"""
        if img_region is None or img_region.size == 0:
            return "unknown", 0.0

        try:
            if not self.models.get("color"):
                return self._analyze_color_by_hsv(img_region)

            rgb_img = cv2.cvtColor(img_region, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)

            # 1. 模型预测（多尺度投票）
            colors: List[str] = []
            confidences: List[float] = []
            scales = [0.7, 0.85, 1.0, 1.15, 1.3]  # 增加更多尺度

            for scale in scales:
                try:
                    scaled_img = pil_img.resize((int(224 * scale), int(224 * scale)))
                    color, conf = self.models["color"].predict(scaled_img)
                    if color:
                        colors.append(color)
                        confidences.append(conf)
                except Exception:
                    continue

            if colors:
                from collections import Counter
                color_counts = Counter(colors)
                most_common_color = color_counts.most_common(1)[0][0]
                color_confidences = [
                    conf for c, conf in zip(colors, confidences) if c == most_common_color
                ]
                avg_conf = sum(color_confidences) / len(color_confidences)
                # 降低阈值以提高检出率
                if avg_conf > 0.25:
                    return most_common_color, avg_conf

            # 2. 模型不可靠时，回退到 HSV 颜色分析
            return self._analyze_color_by_hsv(img_region)

        except Exception as e:
            logger.error(f"{region_type} - 颜色分析失败: {str(e)}")
            return self._analyze_color_by_hsv(img_region)
    
    def _analyze_color_by_hsv(self, img_region) -> Tuple[str, float]:
        """基于HSV颜色空间的颜色分析（优化版）"""
        try:
            hsv_img = cv2.cvtColor(img_region, cv2.COLOR_BGR2HSV)
            
            # 计算平均HSV值
            avg_h = np.mean(hsv_img[:, :, 0])
            avg_s = np.mean(hsv_img[:, :, 1])
            avg_v = np.mean(hsv_img[:, :, 2])
            
            # 定义更全面的HSV颜色范围
            color_ranges = {
                # OpenCV中H范围是0-180，S和V是0-255
                'black': ([0, 0, 0], [180, 255, 85]),
                'white': ([0, 0, 200], [180, 40, 255]),
                'gray': ([0, 0, 85], [180, 40, 200]),
                'red': ([0, 100, 100], [10, 255, 255]),
                'red2': ([160, 100, 100], [180, 255, 255]),  # 红色的另一端
                'orange': ([10, 100, 100], [25, 255, 255]),
                'yellow': ([25, 100, 100], [40, 255, 255]),
                'green': ([40, 50, 50], [80, 255, 255]),
                'cyan': ([80, 50, 50], [100, 255, 255]),
                'blue': ([100, 80, 50], [130, 255, 255]),
                'purple': ([130, 50, 50], [160, 255, 255]),
                'pink': ([160, 50, 100], [180, 255, 255]),
            }
            
            # 统计每种颜色的像素占比
            color_counts = {}
            for color_name, (lower, upper) in color_ranges.items():
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                
                if color_name == 'red2':
                    # 红色分两段，需要分别统计
                    mask1 = cv2.inRange(hsv_img, np.array([0, 100, 100], dtype=np.uint8), 
                                        np.array([10, 255, 255], dtype=np.uint8))
                    mask2 = cv2.inRange(hsv_img, np.array([160, 100, 100], dtype=np.uint8), 
                                        np.array([180, 255, 255], dtype=np.uint8))
                    mask = cv2.bitwise_or(mask1, mask2)
                else:
                    mask = cv2.inRange(hsv_img, lower_np, upper_np)
                
                color_counts[color_name] = np.sum(mask > 0)
            
            # 处理红色（合并两段）
            if 'red' in color_counts and 'red2' in color_counts:
                color_counts['red'] = color_counts.get('red', 0) + color_counts.get('red2', 0)
            
            total_pixels = img_region.shape[0] * img_region.shape[1]
            
            # 找出占比最高的颜色
            best_color = 'unknown'
            best_ratio = 0.0
            confidence_threshold = 0.08  # 降低阈值
            
            for color_name, count in color_counts.items():
                ratio = count / total_pixels
                if color_name in ['red', 'black', 'white', 'gray']:
                    # 这些颜色更可靠，稍微降低阈值
                    effective_ratio = ratio * 1.2
                else:
                    effective_ratio = ratio
                    
                if effective_ratio > best_ratio and ratio > confidence_threshold:
                    best_ratio = ratio
                    best_color = color_name
            
            # 计算置信度
            if best_ratio > 0.5:
                confidence = 0.85
            elif best_ratio > 0.3:
                confidence = 0.75
            elif best_ratio > 0.15:
                confidence = 0.65
            else:
                confidence = 0.55
            
            # 根据饱和度和亮度调整
            if avg_s < 30:
                # 低饱和度，颜色偏灰白
                if avg_v > 180:
                    return 'white', 0.7
                elif avg_v < 80:
                    return 'black', 0.7
                else:
                    return 'gray', 0.6
            
            if best_color == 'unknown':
                # 最后尝试RGB距离
                avg_rgb = np.array(cv2.mean(img_region)[:3])
                return self._analyze_color_by_rgb_distance(avg_rgb)
            
            return best_color, confidence
            
        except Exception as e:
            logger.error(f"HSV颜色分析失败: {str(e)}")
            try:
                avg_rgb = np.array(cv2.mean(img_region)[:3])
                return self._analyze_color_by_rgb_distance(avg_rgb)
            except Exception:
                return 'unknown', 0.0
    
    def _analyze_color_by_rgb_distance(self, avg_rgb) -> Tuple[str, float]:
        """基于RGB距离的颜色分析"""
        basic_colors = {
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
        
        min_dist = float('inf')
        best_color = 'unknown'
        for color_name, rgb in basic_colors.items():
            dist = np.sqrt(np.sum((avg_rgb - np.array(rgb)) ** 2))
            if dist < min_dist:
                min_dist = dist
                best_color = color_name
        
        confidence = max(0.4, 1 - (min_dist / 400))
        return best_color, confidence
            try:
                avg_color = cv2.mean(img_region)[:3]
                if sum(avg_color) < 380:
                    return "black", 0.4
                if sum(avg_color) > 650:
                    return "white", 0.4
                return "gray", 0.4
            except Exception:
                return "unknown", 0.0
    
    def _prepare_face_image(self, face_img):
        """准备人脸图像用于模型输入"""
        try:
            # 转换为RGB
            if len(face_img.shape) == 3 and face_img.shape[2] == 3:
                face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            else:
                return None
            
            # 调整大小
            face_rgb = cv2.resize(face_rgb, (224, 224))
            
            # 转换为PIL图像
            face_pil = Image.fromarray(face_rgb)
            return face_pil
        except Exception as e:
            logger.error(f"人脸图像预处理失败: {str(e)}")
            return None
    def analyze_with_qwen(self, image_path: str) -> Dict:
        """使用本地 Ollama 中的 Qwen3.5-4B 模型分析图片（增强分析模式）"""
        try:
            # 读取并编码图片
            try:
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                logger.info("成功读取并编码图片（用于本地 Qwen3-VL）")
            except Exception as e:
                logger.error(f"图片编码失败: {str(e)}")
                return {"error": "图片编码失败"}

            prompt = """请分析图像中的人物信息，并按照以下JSON格式返回结果：
{
    "detected": 人物数量,
    "persons": [
        {
            "gender": "male/female",
            "gender_confidence": 0.95,
            "age": 25,
            "age_confidence": 0.85,
            "upper_color": "red/blue/green/...",
            "upper_color_confidence": 0.8,
            "lower_color": "red/blue/green/...",
            "lower_color_confidence": 0.8,
            "bbox": [x1, y1, x2, y2]
        }
    ],
    "success": true
}
请严格只输出一个 JSON，不要输出任何额外说明文本。"""

            url = f"{self.ollama_base_url}/api/chat"
            payload = {
                "model": self.ollama_model_name,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "你是一个严谨的图像分析助手，只能输出有效 JSON。"},
                    {"role": "user", "content": prompt, "images": [base64_image]},
                ],
            }

            logger.info(f"发送本地 Qwen3-VL 请求: url={url}, model={self.ollama_model_name}")
            try:
                resp = requests.post(url, json=payload, timeout=self.ollama_timeout_s)
            except Exception as e:
                logger.error(f"请求本地 Ollama 失败: {str(e)}")
                return {"error": f"Ollama调用失败: {str(e)}"}

            if resp.status_code != 200:
                logger.error(f"Ollama 返回非200: {resp.status_code}, body={resp.text[:500]}")
                return {"error": f"Ollama状态码: {resp.status_code}", "raw_text": resp.text}

            try:
                resp_json = resp.json()
            except Exception as e:
                logger.error(f"解析 Ollama 响应失败: {str(e)}, body={resp.text[:500]}")
                return {"error": "解析Ollama响应失败", "raw_text": resp.text}

            result_text = ""
            if isinstance(resp_json, dict) and "message" in resp_json:
                msg = resp_json.get("message") or {}
                result_text = msg.get("content", "") or ""
            if not result_text:
                result_text = json.dumps(resp_json, ensure_ascii=False)

            logger.info(f"本地 Qwen3-VL 返回原始结果: {result_text[:800]}")

            # 提取 JSON 部分
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                try:
                    json_text = result_text[json_start:json_end]
                    json_text = json_text.replace('\n', ' ').replace('\r', ' ')
                    json_text = ' '.join(json_text.split())
                    parsed_result = json.loads(json_text)
                    logger.info(f"成功解析 Qwen3-VL 返回结果: {json.dumps(parsed_result, ensure_ascii=False, indent=2)}")

                    standardized_result = {
                        "detected": parsed_result.get("detected", 0),
                        "persons": [],
                        "success": True
                    }

                    for person in parsed_result.get("persons", []):
                        standardized_person = {
                            "gender": person.get("gender", "unknown"),
                            "gender_confidence": person.get("gender_confidence", 0.0),
                            "age": person.get("age", 0),
                            "age_confidence": person.get("age_confidence", 0.0),
                            "upper_color": person.get("upper_color", "unknown"),
                            "upper_color_confidence": person.get("upper_color_confidence", 0.0),
                            "lower_color": person.get("lower_color", "unknown"),
                            "lower_color_confidence": person.get("lower_color_confidence", 0.0),
                            "bbox": person.get("bbox", [0, 0, 0, 0])
                        }
                        standardized_result["persons"].append(standardized_person)

                    logger.info(f"标准化后的结果: {json.dumps(standardized_result, ensure_ascii=False, indent=2)}")
                    return standardized_result

                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {str(e)}")
                    return {"error": "JSON解析失败", "raw_text": result_text}
            else:
                logger.error(f"无法从响应中提取JSON结果: {result_text}")
                return {"error": "无法解析返回结果", "raw_text": result_text}

        except Exception as e:
            logger.error(f"本地 Qwen3-VL 分析失败: {str(e)}")
            return {"error": str(e)}

    def merge_results(self, local_result: Dict, qwen_result: Dict, local_weight: float = 0.3, qwen_weight: float = 0.7) -> Dict:
        """合并本地模型和Qwen-VL的分析结果"""
        try:
            logger.info("开始合并分析结果")
            logger.info(f"权重设置 - 本地模型: {local_weight}, Qwen-VL: {qwen_weight}")
            
            # 验证权重和
            total_weight = local_weight + qwen_weight
            if abs(total_weight - 1.0) > 0.0001:
                logger.warning(f"权重和不为1，进行归一化处理: {total_weight}")
                local_weight = local_weight / total_weight
                qwen_weight = qwen_weight / total_weight
            
            merged_result = {
                "detected": 0,
                "persons": [],
                "success": True
            }
            
            # 验证输入数据
            if not isinstance(local_result, dict) or not isinstance(qwen_result, dict):
                logger.error("输入结果格式无效")
                return {
                    "detected": 0,
                    "persons": [],
                    "success": False,
                    "error": "Invalid input format"
                }
            
            # 获取检测到的人数
            local_persons = local_result.get("persons", [])
            qwen_persons = qwen_result.get("persons", [])
            
            logger.info(f"本地模型检测到 {len(local_persons)} 人")
            logger.info(f"Qwen-VL检测到 {len(qwen_persons)} 人")

            # ✅ 关键：增强模式合并以“本地检测结果”为准（人数/框），避免大模型幻觉导致人数飙升、框乱飞
            # Qwen-VL 仅用于在本地模型不确定/unknown 时补充语义（gender/age/color），而不是用来决定检测到几个人。
            merged_result["detected"] = len(local_persons) if local_persons else len(qwen_persons)

            def _is_unknown(v):
                if v is None:
                    return True
                if isinstance(v, str):
                    return v.strip().lower() in {"", "unknown", "未知", "unk"}
                return False

            def _low_conf(v, threshold: float = 0.4) -> bool:
                try:
                    return float(v) < threshold
                except Exception:
                    return True

            def _pick_by_weighted_conf(local_val, local_conf, qwen_val, qwen_conf):
                """两侧都非 unknown 时，按 (weight * confidence) 选更可信的值。"""
                if _is_unknown(local_val) and _is_unknown(qwen_val):
                    return "unknown", 0.0
                if _is_unknown(local_val):
                    return qwen_val, float(qwen_conf or 0.0)
                if _is_unknown(qwen_val):
                    return local_val, float(local_conf or 0.0)

                try:
                    lc = float(local_conf or 0.0)
                except Exception:
                    lc = 0.0
                try:
                    qc = float(qwen_conf or 0.0)
                except Exception:
                    qc = 0.0

                if (qwen_weight * qc) > (local_weight * lc):
                    return qwen_val, qc
                return local_val, lc

            def _blend_number(local_num, local_conf, qwen_num, qwen_conf):
                """数值字段加权融合：两个都有效则按权重算均值，否则取有效的一侧。"""
                def _valid(v):
                    return v not in (None, 0, 0.0, "0")

                l_ok = _valid(local_num)
                q_ok = _valid(qwen_num)

                try:
                    l_num = float(local_num) if l_ok else 0.0
                except Exception:
                    l_ok = False
                    l_num = 0.0
                try:
                    q_num = float(qwen_num) if q_ok else 0.0
                except Exception:
                    q_ok = False
                    q_num = 0.0

                try:
                    l_c = float(local_conf or 0.0)
                except Exception:
                    l_c = 0.0
                try:
                    q_c = float(qwen_conf or 0.0)
                except Exception:
                    q_c = 0.0

                if l_ok and q_ok:
                    return (local_weight * l_num + qwen_weight * q_num), (local_weight * l_c + qwen_weight * q_c)
                if q_ok:
                    return q_num, q_c
                if l_ok:
                    return l_num, l_c
                return 0.0, 0.0

            # 对每个“本地检测到的人物”按索引合并（不尝试用Qwen的bbox匹配，避免坐标体系不一致）
            for i in range(merged_result["detected"]):
                local_person = local_persons[i] if i < len(local_persons) else None
                qwen_person = qwen_persons[i] if i < len(qwen_persons) else None

                if local_person is None and qwen_person is None:
                    continue

                # 先以本地为基准构建 person_data（包含 bbox / upper_bbox / lower_bbox）
                person_data = {}
                if local_person is not None:
                    person_data.update({
                        "gender": local_person.get("gender", "unknown"),
                        "gender_confidence": float(local_person.get("gender_confidence", 0.0)),
                        "age": local_person.get("age", 0),
                        "age_confidence": float(local_person.get("age_confidence", 0.0)),
                        "upper_color": local_person.get("upper_color", "unknown"),
                        "upper_color_confidence": float(local_person.get("upper_color_confidence", 0.0)),
                        "lower_color": local_person.get("lower_color", "unknown"),
                        "lower_color_confidence": float(local_person.get("lower_color_confidence", 0.0)),
                        "bbox": local_person.get("bbox", [0, 0, 0, 0]),
                    })
                    if "upper_bbox" in local_person:
                        person_data["upper_bbox"] = local_person.get("upper_bbox")
                    if "lower_bbox" in local_person:
                        person_data["lower_bbox"] = local_person.get("lower_bbox")
                else:
                    # 没有本地结果时，退化为Qwen（bbox也只能信Qwen）
                    person_data.update({
                        "gender": qwen_person.get("gender", "unknown"),
                        "gender_confidence": float(qwen_person.get("gender_confidence", 0.0)),
                        "age": qwen_person.get("age", 0),
                        "age_confidence": float(qwen_person.get("age_confidence", 0.0)),
                        "upper_color": qwen_person.get("upper_color", "unknown"),
                        "upper_color_confidence": float(qwen_person.get("upper_color_confidence", 0.0)),
                        "lower_color": qwen_person.get("lower_color", "unknown"),
                        "lower_color_confidence": float(qwen_person.get("lower_color_confidence", 0.0)),
                        "bbox": qwen_person.get("bbox", [0, 0, 0, 0]),
                    })
                # 用权重做字段融合（不改 bbox；检测框仍以本地为准）
                if qwen_person is not None:
                    g, g_conf = _pick_by_weighted_conf(
                        person_data.get("gender", "unknown"),
                        person_data.get("gender_confidence", 0.0),
                        qwen_person.get("gender", "unknown"),
                        qwen_person.get("gender_confidence", 0.0),
                    )
                    person_data["gender"] = g
                    person_data["gender_confidence"] = float(g_conf or 0.0)

                    age, age_conf = _blend_number(
                        person_data.get("age", 0),
                        person_data.get("age_confidence", 0.0),
                        qwen_person.get("age", 0),
                        qwen_person.get("age_confidence", 0.0),
                    )
                    try:
                        person_data["age"] = int(round(float(age)))
                    except Exception:
                        person_data["age"] = 0
                    person_data["age_confidence"] = float(age_conf or 0.0)

                    uc, uc_conf = _pick_by_weighted_conf(
                        person_data.get("upper_color", "unknown"),
                        person_data.get("upper_color_confidence", 0.0),
                        qwen_person.get("upper_color", "unknown"),
                        qwen_person.get("upper_color_confidence", 0.0),
                    )
                    person_data["upper_color"] = uc
                    person_data["upper_color_confidence"] = float(uc_conf or 0.0)

                    lc, lc_conf = _pick_by_weighted_conf(
                        person_data.get("lower_color", "unknown"),
                        person_data.get("lower_color_confidence", 0.0),
                        qwen_person.get("lower_color", "unknown"),
                        qwen_person.get("lower_color_confidence", 0.0),
                    )
                    person_data["lower_color"] = lc
                    person_data["lower_color_confidence"] = float(lc_conf or 0.0)

                merged_result["persons"].append(person_data)
                logger.info(f"人物 {i+1} 合并结果: {json.dumps(person_data, ensure_ascii=False, indent=2)}")

            return merged_result

        except Exception as e:
            logger.error(f"合并结果时出错: {str(e)}")
            return {
                "detected": 0,
                "persons": [],
                "success": False,
                "error": str(e)
            }

    def _get_image_hash(self, image_path: str) -> str:
        """计算图片哈希值"""
        with open(image_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def analyze_image(self, image_path: str, mode: str = "normal") -> Dict:
        """分析图像"""
        try:
            logger.info(f"开始图像分析，模式: {mode}")
            start_time = time.time()
            
            # 使用本地模型进行分析
            local_result = self._analyze_with_local_models(image_path)
            logger.info(f"本地模型分析结果: {json.dumps(local_result, ensure_ascii=False, indent=2)}")
            
            # 在增强模式下，同时使用本地模型和 Qwen-VL
            if mode == "enhanced":
                logger.info("使用增强模式，调用 Qwen-VL API")
                try:
                    # 使用 Qwen-VL 进行分析
                    qwen_result = self.analyze_with_qwen(image_path)
                    logger.info(f"Qwen-VL 分析结果: {json.dumps(qwen_result, ensure_ascii=False, indent=2)}")
                    
                    # 检查 Qwen-VL 结果
                    if "error" not in qwen_result:
                        logger.info("成功获取 Qwen-VL 分析结果，开始合并结果")
                        
                        # 确保 local_result 中有必要的字段
                        if "persons" not in local_result:
                            local_result["persons"] = []
                        if "detected" not in local_result:
                            local_result["detected"] = 0
                        
                        # 合并两个模型的结果
                        try:
                            final_result = self.merge_results(
                                local_result,
                                qwen_result,
                                local_weight=0.3,  # 本地模型 30%
                                qwen_weight=0.7    # 大模型 70%
                            )
                            logger.info(f"合并后的最终结果: {json.dumps(final_result, ensure_ascii=False, indent=2)}")
                        except Exception as e:
                            logger.error(f"合并结果失败: {str(e)}")
                            final_result = local_result
                    else:
                        logger.warning(f"Qwen-VL分析失败，使用本地模型结果: {qwen_result.get('error')}")
                        final_result = local_result
                except Exception as e:
                    logger.error(f"Qwen-VL分析失败: {str(e)}")
                    final_result = local_result
            else:
                logger.info("使用普通模式，仅使用本地模型")
                final_result = local_result
            
            # 确保结果包含所有必要字段
            if "persons" not in final_result:
                final_result["persons"] = []
            if "detected" not in final_result:
                final_result["detected"] = len(final_result.get("persons", []))
            
            # 添加处理时间和模式信息
            final_result["processing_time"] = time.time() - start_time
            final_result["mode"] = mode
            
            logger.info(f"图像分析完成，耗时: {final_result['processing_time']:.2f}秒")
            return final_result
            
        except Exception as e:
            logger.error(f"图像分析失败: {str(e)}")
            return {
                "error": str(e),
                "detected": 0,
                "persons": [],
                "mode": mode,
                "processing_time": time.time() - start_time
            }

    def _analyze_with_local_models(self, image_path: str) -> Dict:
        """使用本地模型进行分析"""
        try:
            # 读取图像
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"无法读取图像: {image_path}")
            
            # 获取图像尺寸
            img_height, img_width = img.shape[:2]

            # 如果有语义分割模型，先生成整图的分割掩码，用于后续衣服区域细化
            segmentation_mask = None
            if self.deeplabv3 is not None:
                try:
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_img)
                    input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
                    with torch.no_grad():
                        output = self.deeplabv3(input_tensor)['out'][0]
                    segmentation_mask = torch.argmax(output, dim=0).cpu().numpy()
                    # 调整到原图大小
                    segmentation_mask = cv2.resize(
                        segmentation_mask.astype(np.uint8),
                        (img_width, img_height),
                        interpolation=cv2.INTER_NEAREST
                    )
                    logger.info("语义分割掩码生成成功")
                except Exception as e:
                    logger.error(f"生成语义分割掩码失败: {str(e)}")
                    segmentation_mask = None
            
            # 初始化结果
            result = {
                "detected": 0,
                "persons": [],
                "success": True
            }
            
            # 人脸检测
            if self.models.get('face'):
                try:
                    # 使用YOLO进行人脸检测，并显式指定较低的置信度阈值
                    face_results = self.models['face'].predict(
                        img,
                        conf=self.face_conf_threshold,
                        verbose=False
                    )
                    
                    if len(face_results) > 0 and len(face_results[0].boxes) > 0:
                        boxes = face_results[0].boxes
                        boxes_list = list(boxes)

                        # 额外做一层 IoU 去重：YOLO 在极端情况下仍可能产生多个高度重叠的人脸框
                        def _iou_xyxy(a, b) -> float:
                            ax1, ay1, ax2, ay2 = [float(x) for x in a]
                            bx1, by1, bx2, by2 = [float(x) for x in b]
                            inter_x1 = max(ax1, bx1)
                            inter_y1 = max(ay1, by1)
                            inter_x2 = min(ax2, bx2)
                            inter_y2 = min(ay2, by2)
                            inter_w = max(0.0, inter_x2 - inter_x1)
                            inter_h = max(0.0, inter_y2 - inter_y1)
                            inter = inter_w * inter_h
                            area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
                            area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
                            denom = area_a + area_b - inter
                            return inter / denom if denom > 0 else 0.0

                        def _get_conf(b) -> float:
                            try:
                                return float(b.conf[0]) if hasattr(b, "conf") else 0.0
                            except Exception:
                                return 0.0

                        # 先按置信度降序选框，再按 x1 排序保证展示稳定
                        boxes_list.sort(key=_get_conf, reverse=True)
                        selected = []
                        for b in boxes_list:
                            bb = b.xyxy[0].tolist()
                            if any(_iou_xyxy(bb, s.xyxy[0].tolist()) > 0.7 for s in selected):
                                continue
                            selected.append(b)
                        selected.sort(key=lambda b: float(b.xyxy[0][0]))
                        boxes = selected
                        logger.info(
                            f"人脸检测完成，共检测到 {len(boxes)} 个候选框（conf阈值={self.face_conf_threshold}）"
                        )
                        self.current_boxes = [box.xyxy[0].tolist() for box in boxes]
                        for idx, box in enumerate(boxes):
                            try:
                                # 获取边界框坐标
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                # 将坐标裁剪到图像范围，避免越界导致框全部堆到一起
                                x1 = max(0, min(x1, img_width - 1))
                                x2 = max(0, min(x2, img_width))
                                y1 = max(0, min(y1, img_height - 1))
                                y2 = max(0, min(y2, img_height))

                                if x2 <= x1 or y2 <= y1:
                                    logger.warning(f"跳过无效人脸框 {idx}: ({x1},{y1},{x2},{y2})")
                                    continue

                                confidence = float(box.conf[0]) if hasattr(box, "conf") else 0.0
                                logger.info(
                                    f"人脸 {idx}: bbox=({x1},{y1},{x2},{y2}), conf={confidence:.4f}"
                                )
                                
                                # 提取人脸区域
                                face_img = img[y1:y2, x1:x2]
                                if face_img.size == 0:
                                    continue
                                
                                # 转换为PIL图像
                                face_pil = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
                                
                                # 性别预测（缺模型时降级，不影响输出 persons）
                                gender, gender_conf = "unknown", 0.0
                                if self.models.get("gender") is not None:
                                    try:
                                        gender, gender_conf = self.models["gender"].predict(face_img)
                                    except Exception as e:
                                        logger.warning(f"性别预测失败（将降级为unknown）: {str(e)}")

                                # 年龄预测（缺模型时降级，不影响输出 persons）
                                age, age_conf = 0.0, 0.0
                                if self.models.get("age") is not None:
                                    try:
                                        age, age_conf = self.models["age"].predict(face_pil)
                                        if age is None:
                                            age, age_conf = 0.0, 0.0
                                    except Exception as e:
                                        logger.warning(f"年龄预测失败（将降级为0）: {str(e)}")
                                
                                # 衣服区域检测（参考 test_hunhe 中 ClothingDetector）
                                clothing_regions = self._detect_clothing_regions(
                                    img,
                                    (x1, y1, x2, y2),
                                    segmentation_mask,
                                )

                                upper_region = clothing_regions["upper"]["region"]
                                lower_region = clothing_regions["lower"]["region"]

                                # 上衣/下装颜色分析
                                upper_color, upper_conf = self._analyze_color_region(
                                    upper_region, "upper"
                                )
                                lower_color, lower_conf = self._analyze_color_region(
                                    lower_region, "lower"
                                )

                                # 收集人物信息
                                person_data = {
                                    "gender": gender,
                                    "gender_confidence": gender_conf,
                                    "age": age,
                                    "age_confidence": age_conf,
                                    "upper_color": upper_color,
                                    "upper_color_confidence": upper_conf,
                                    "lower_color": lower_color,
                                    "lower_color_confidence": lower_conf,
                                    "bbox": [x1, y1, x2, y2],
                                    # 额外返回衣服框，方便前端单独绘制
                                    "upper_bbox": list(
                                        clothing_regions["upper"]["bbox"]
                                    ),
                                    "lower_bbox": list(
                                        clothing_regions["lower"]["bbox"]
                                    ),
                                }
                                
                                result["persons"].append(person_data)
                            
                            except Exception as e:
                                logger.error(f"处理人物 {idx} 时出错: {str(e)}")
                                continue
                    
                    result["detected"] = len(result["persons"])
                
                except Exception as e:
                    logger.error(f"人脸检测失败: {str(e)}")
            
            # 如果人脸检测没有结果，尝试使用人体检测作为备选方案
            if result["detected"] == 0 and self.body_model is not None:
                logger.info("人脸检测未发现目标，尝试人体检测作为备选...")
                try:
                    # 使用YOLOv8进行人体检测（person类别）
                    body_results = self.body_model.predict(
                        img,
                        conf=self.body_conf_threshold,
                        verbose=False
                    )
                    
                    if len(body_results) > 0 and len(body_results[0].boxes) > 0:
                        body_boxes = []
                        for box in body_results[0].boxes:
                            # 检查是否为人体（person类别，YOLOv8中为类别0）
                            cls = int(box.cls[0].item()) if hasattr(box, 'cls') else -1
                            if cls == 0:  # person类别
                                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                                conf = float(box.conf[0].item()) if hasattr(box, 'conf') else 0.0
                                body_boxes.append((x1, y1, x2, y2, conf))
                        
                        logger.info(f"人体检测发现 {len(body_boxes)} 个人体")
                        
                        for idx, (x1, y1, x2, y2, conf) in enumerate(body_boxes):
                            # 裁剪到图像范围
                            x1 = max(0, min(x1, img_width - 1))
                            x2 = max(0, min(x2, img_width))
                            y1 = max(0, min(y1, img_height - 1))
                            y2 = max(0, min(y2, img_height))
                            
                            if x2 <= x1 or y2 <= y1:
                                continue
                            
                            body_height = y2 - y1
                            body_width = x2 - x1
                            
                            # 根据人体框估算人脸位置（人脸通常在上半部分）
                            face_x1 = max(0, int(x1 + body_width * 0.15))
                            face_x2 = min(img_width, int(x2 - body_width * 0.15))
                            face_y1 = max(0, int(y1))
                            face_y2 = min(y2, int(y1 + body_height * 0.35))
                            
                            face_width = face_x2 - face_x1
                            face_height = face_y2 - face_y1
                            
                            # 提取人脸区域用于性别/年龄预测
                            face_img = img[face_y1:face_y2, face_x1:face_x2]
                            face_pil = None
                            if face_img.size > 0:
                                face_pil = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
                            
                            # 性别预测
                            gender, gender_conf = "unknown", 0.0
                            if self.models.get("gender") is not None and face_img.size > 0:
                                try:
                                    gender, gender_conf = self.models["gender"].predict(face_img)
                                except Exception as e:
                                    logger.warning(f"人体模式-性别预测失败: {str(e)}")
                            
                            # 年龄预测
                            age, age_conf = 0.0, 0.0
                            if self.models.get("age") is not None and face_pil is not None:
                                try:
                                    age, age_conf = self.models["age"].predict(face_pil)
                                    if age is None:
                                        age, age_conf = 0.0, 0.0
                                except Exception as e:
                                    logger.warning(f"人体模式-年龄预测失败: {str(e)}")
                            
                            # 衣服区域检测（基于人体框）
                            clothing_regions = self._detect_clothing_regions(
                                img,
                                (face_x1, face_y1, face_x2, face_y2),
                                segmentation_mask,
                            )
                            
                            upper_region = clothing_regions["upper"]["region"]
                            lower_region = clothing_regions["lower"]["region"]
                            
                            # 颜色分析
                            upper_color, upper_conf = self._analyze_color_region(upper_region, "upper")
                            lower_color, lower_conf = self._analyze_color_region(lower_region, "lower")
                            
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
                                "detection_mode": "body"  # 标记为人体检测模式
                            }
                            
                            result["persons"].append(person_data)
                            logger.info(f"人体检测-人物 {idx+1}: 人脸框=({face_x1},{face_y1},{face_x2},{face_y2})")
                        
                        result["detected"] = len(result["persons"])
                        logger.info(f"人体检测模式完成，共检测到 {result['detected']} 个人")
                        
                except Exception as e:
                    logger.error(f"人体检测备选失败: {str(e)}")
            
            logger.info(f"本地模型分析结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result
        
        except Exception as e:
            logger.error(f"本地模型分析失败: {str(e)}")
            return {
                "detected": 0,
                "persons": [],
                "success": False,
                "error": str(e)
            }

# 创建全局分析器实例
image_analyzer = ImageAnalyzer() 