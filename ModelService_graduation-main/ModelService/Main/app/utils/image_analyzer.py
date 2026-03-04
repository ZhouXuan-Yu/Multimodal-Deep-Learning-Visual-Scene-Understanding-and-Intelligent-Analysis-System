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
import requests  # 替换 OpenAI 客户端，使用 requests 直接调用 API
import time
from functools import lru_cache
import hashlib
try:
    from openai import OpenAI
except ImportError:
    print("Warning: OpenAI import failed, enhanced analysis mode may not be available")
    OpenAI = None

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
        self.face_conf_threshold = 0.4
        self.deeplabv3 = None
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        # 修改 API key 的获取逻辑
        self.api_key = os.getenv('DASHSCOPE_API_KEY', 'sk-8ecbfb7922bc425bafb971616f5a7674')
        if self.api_key == 'sk-8ecbfb7922bc425bafb971616f5a7674':
            logger.info("使用默认 API key")
        else:
            logger.info("使用环境变量中的 API key")
        
        if OpenAI is None:
            logger.warning("OpenAI 导入失败，增强模式可能无法使用")
        
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
            
        except ImportError as e:
            logger.error(f"加载模型失败: {str(e)}")
    
    def _detect_clothing_regions(
        self,
        img: np.ndarray,
        face_box: Tuple[int, int, int, int],
        segmentation_mask: Optional[np.ndarray] = None
    ) -> Dict[str, Dict]:
        """
        参考 test_hunhe.py 中的 ClothingDetector.detect_clothing_regions，
        通过人脸框稳定地推断上衣/下装区域（先做人脸 -> 再衣服）。
        """
        x1, y1, x2, y2 = face_box
        face_height = y2 - y1
        face_width = x2 - x1
        img_height, img_width = img.shape[:2]

        # 基于几何关系估计上衣/下装区域（与 test_hunhe.py 一致）
        # 上衣区域：从脸底向下 1.5 倍人脸高度，略向两侧扩展
        upper_y1 = y2
        upper_y2 = min(upper_y1 + int(face_height * 1.5), img_height)
        upper_x1 = max(0, x1 - int(face_width * 0.3))
        upper_x2 = min(x2 + int(face_width * 0.3), img_width)

        # 下装区域：从上衣底部向下 2 倍人脸高度，略比上衣更宽
        lower_y1 = upper_y2
        lower_y2 = min(lower_y1 + int(face_height * 2.0), img_height)
        lower_x1 = max(0, x1 - int(face_width * 0.5))
        lower_x2 = min(x2 + int(face_width * 0.5), img_width)

        # 如果有语义分割掩码，用 person 类别(=15)在每个候选框内部做一次收缩，
        # 只依赖当前人脸，不和其它人物交互，保证稳定性。
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
        """对单个衣物区域进行颜色分类（从 test_hunhe 的逻辑抽取为公共方法）"""
        if img_region is None or img_region.size == 0:
            return "unknown", 0.0

        try:
            if not self.models.get("color"):
                return "unknown", 0.0

            rgb_img = cv2.cvtColor(img_region, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)

            # 基本颜色映射和阈值
            basic_colors = {
                "black": ([0, 0, 0], 50),
                "white": ([255, 255, 255], 50),
                "red": ([255, 0, 0], 80),
                "green": ([0, 255, 0], 80),
                "blue": ([0, 0, 255], 80),
                "yellow": ([255, 255, 0], 80),
                "gray": ([128, 128, 128], 50),
            }

            # 1. 模型预测（多尺度投票）
            colors: List[str] = []
            confidences: List[float] = []
            scales = [0.8, 1.0, 1.2]

            for scale in scales:
                scaled_img = pil_img.resize((int(224 * scale), int(224 * scale)))
                try:
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
                if avg_conf > 0.3:
                    return most_common_color, avg_conf

            # 2. 模型不可靠时，回退到 HSV + 基本颜色距离
            avg_color = cv2.mean(rgb_img)[:3]
            hsv_img = cv2.cvtColor(img_region, cv2.COLOR_BGR2HSV)
            avg_hsv = cv2.mean(hsv_img)[:3]

            brightness = avg_hsv[2]
            saturation = avg_hsv[1]

            if brightness < 50:
                return "black", 0.7
            if brightness > 200 and saturation < 50:
                return "white", 0.7
            if saturation < 30:
                return "gray", 0.6

            min_dist = float("inf")
            selected_color = "unknown"
            max_confidence = 0.0
            for color_name, (rgb, threshold) in basic_colors.items():
                dist = sum((a - b) ** 2 for a, b in zip(avg_color, rgb)) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    confidence = max(0.4, 1 - (dist / 255))
                    selected_color = color_name
                    max_confidence = confidence
            return selected_color, max_confidence

        except Exception as e:
            logger.error(f"{region_type} - 颜色分析失败: {str(e)}")
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
        """使用Qwen-VL模型分析图片"""
        try:
            if OpenAI is None:
                logger.error("OpenAI 模块未正确加载")
                return {"error": "增强分析模式不可用"}

            # 创建 OpenAI 客户端
            try:
                client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
                )
                logger.info("成功创建 OpenAI 客户端")
            except Exception as e:
                logger.error(f"创建 OpenAI 客户端失败: {str(e)}")
                return {"error": "创建 OpenAI 客户端失败"}

            # 读取并编码图片
            try:
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                logger.info("成功读取并编码图片")
            except Exception as e:
                logger.error(f"图片编码失败: {str(e)}")
                return {"error": "图片编码失败"}

            try:
                # 发送请求
                messages = [
                        {
                            "role": "system",
                            "content": [{"type": "text", "text": "你是一个图像分析助手。"}]
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                                },
                                {
                                    "type": "text",
                                    "text": """请分析图像中的人物信息，并按照以下JSON格式返回结果：
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
}"""
                            }
                        ]
                    }
                ]
                
                logger.info("发送 Qwen-VL 请求...")
                completion = client.chat.completions.create(
                    model="qwen-vl-max-latest",
                    messages=messages
                )
                
                # 打印完整的 API 响应
                logger.info(f"Qwen-VL API 完整响应: {completion}")

                # 解析结果
                result_text = completion.choices[0].message.content
                logger.info(f"Qwen-VL 返回原始结果: {result_text}")

                # 提取 JSON 部分
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    try:
                        json_text = result_text[json_start:json_end]
                        json_text = json_text.replace('\n', ' ').replace('\r', ' ')
                        json_text = ' '.join(json_text.split())
                        parsed_result = json.loads(json_text)
                        logger.info(f"成功解析 Qwen-VL 返回结果: {json.dumps(parsed_result, ensure_ascii=False, indent=2)}")
                        
                        # 确保结果格式统一
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
                logger.error(f"Qwen-VL API调用失败: {str(e)}")
                return {"error": f"API调用失败: {str(e)}"}

        except Exception as e:
            logger.error(f"Qwen-VL分析失败: {str(e)}")
            return {"error": str(e)}

    def merge_results(self, local_result: Dict, qwen_result: Dict, local_weight: float = 0.01, qwen_weight: float = 0.99) -> Dict:
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

                # 用Qwen补齐“unknown/低置信度”的语义字段（不改bbox）
                if qwen_person is not None:
                    # gender
                    if _is_unknown(person_data.get("gender")) or _low_conf(person_data.get("gender_confidence")):
                        if not _is_unknown(qwen_person.get("gender")):
                            person_data["gender"] = qwen_person.get("gender", person_data.get("gender"))
                            person_data["gender_confidence"] = float(qwen_person.get("gender_confidence", person_data.get("gender_confidence", 0.0)))
                    # age
                    if (person_data.get("age") in (None, 0)) or _low_conf(person_data.get("age_confidence")):
                        if qwen_person.get("age") not in (None, 0):
                            person_data["age"] = qwen_person.get("age", person_data.get("age"))
                            person_data["age_confidence"] = float(qwen_person.get("age_confidence", person_data.get("age_confidence", 0.0)))
                    # colors
                    if _is_unknown(person_data.get("upper_color")) or _low_conf(person_data.get("upper_color_confidence")):
                        if not _is_unknown(qwen_person.get("upper_color")):
                            person_data["upper_color"] = qwen_person.get("upper_color", person_data.get("upper_color"))
                            person_data["upper_color_confidence"] = float(qwen_person.get("upper_color_confidence", person_data.get("upper_color_confidence", 0.0)))
                    if _is_unknown(person_data.get("lower_color")) or _low_conf(person_data.get("lower_color_confidence")):
                        if not _is_unknown(qwen_person.get("lower_color")):
                            person_data["lower_color"] = qwen_person.get("lower_color", person_data.get("lower_color"))
                            person_data["lower_color_confidence"] = float(qwen_person.get("lower_color_confidence", person_data.get("lower_color_confidence", 0.0)))

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
                                local_weight=0.01,  # 修改权重为 1%
                                qwen_weight=0.99    # 修改权重为 99%
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