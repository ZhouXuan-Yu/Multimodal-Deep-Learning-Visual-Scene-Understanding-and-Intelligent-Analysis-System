"""
人物特征分析器 v2
完全重写版本，修复所有语法错误，使用Singleton模式
"""

import os
import sys
import base64
import json
import time
import logging
import threading
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import requests
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from ultralytics import YOLO
from collections import Counter

warnings.filterwarnings("ignore", category=UserWarning)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent.parent / "model"


def _torch_load_compat(path: str, map_location: Optional[str] = None) -> Any:
    try:
        return torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:
        return torch.load(path, map_location=map_location)


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


class Singleton(type):
    _instances: Dict[type, object] = {}
    _lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> object:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ImagePreprocessor:
    """图像预处理工具类"""

    @staticmethod
    def clahe_enhance(img: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l_channel)
            merged = cv2.merge([l_enhanced, a_channel, b_channel])
            return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        except Exception as e:
            logger.warning(f"CLAHE enhance failed: {e}")
            return img

    @staticmethod
    def auto_enhance(img: np.ndarray) -> np.ndarray:
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))
            contrast = float(np.std(gray))
            if contrast < 40:
                return ImagePreprocessor.clahe_enhance(img, clip_limit=2.5)
            elif brightness < 100:
                return ImagePreprocessor.clahe_enhance(img, clip_limit=1.5)
            return img
        except Exception:
            return img


class ColorAnalyzer:
    """颜色分析工具类"""

    HSV_RANGES: Dict[str, Tuple[List[int], List[int]]] = {
        "black": ([0, 0, 0], [180, 255, 85]),
        "white": ([0, 0, 200], [180, 30, 255]),
        "gray": ([0, 0, 85], [180, 30, 200]),
        "red": ([0, 100, 100], [10, 255, 255]),
        "orange": ([10, 100, 100], [25, 255, 255]),
        "yellow": ([25, 100, 100], [40, 255, 255]),
        "green": ([40, 50, 50], [80, 255, 255]),
        "cyan": ([80, 50, 50], [100, 255, 255]),
        "blue": ([100, 80, 50], [130, 255, 255]),
        "purple": ([130, 50, 50], [160, 255, 255]),
        "pink": ([160, 50, 100], [180, 255, 255]),
    }

    RGB_COLORS: Dict[str, List[int]] = {
        "black": [0, 0, 0],
        "white": [255, 255, 255],
        "red": [255, 0, 0],
        "green": [0, 255, 0],
        "blue": [0, 0, 255],
        "yellow": [255, 255, 0],
        "orange": [255, 165, 0],
        "purple": [128, 0, 128],
        "pink": [255, 192, 203],
        "gray": [128, 128, 128],
        "brown": [139, 69, 19],
        "cyan": [0, 255, 255],
    }

    @staticmethod
    def kmeans_clustering(
        img_region: np.ndarray, k: int = 5
    ) -> List[Tuple[str, float, int]]:
        try:
            if img_region is None or img_region.size == 0:
                return []
            h, w = img_region.shape[:2]
            if h * w > 10000:
                img_region = cv2.resize(
                    img_region, (100, int(100 * h / w))
                )
            rgb = cv2.cvtColor(img_region, cv2.COLOR_BGR2RGB)
            pixels = rgb.reshape(-1, 3).astype(np.float32)
            criteria = (
                cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                10,
                1.0,
            )
            _, labels, centers = cv2.kmeans(
                pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
            )
            unique, counts = np.unique(labels, return_counts=True)
            results: List[Tuple[str, float, int]] = []
            total = len(pixels)
            for center, count in zip(centers, counts):
                color_name = ColorAnalyzer._rgb_to_color_name(center)
                confidence = float(min(1.0, count / (total * 0.3)))
                results.append((color_name, confidence, int(count)))
            results.sort(key=lambda x: x[2], reverse=True)
            return results
        except Exception as e:
            logger.warning(f"K-means clustering failed: {e}")
            return []

    @staticmethod
    def _rgb_to_color_name(rgb: np.ndarray) -> str:
        rgb_int = rgb.astype(int)
        min_dist = float("inf")
        best = "unknown"
        for name, std_rgb in ColorAnalyzer.RGB_COLORS.items():
            dist = float(
                np.sqrt(
                    sum(
                        (float(a) - float(b)) ** 2
                        for a, b in zip(rgb_int, std_rgb)
                    )
                )
            )
            if dist < min_dist:
                min_dist = dist
                best = name
        return best

    @staticmethod
    def analyze_by_hsv(img_region: np.ndarray) -> Tuple[str, float]:
        try:
            if img_region is None or img_region.size == 0:
                return "unknown", 0.0
            hsv = cv2.cvtColor(img_region, cv2.COLOR_BGR2HSV)
            total_pixels = hsv.shape[0] * hsv.shape[1]
            color_counts: Dict[str, int] = {}
            for color_name, (lower, upper) in ColorAnalyzer.HSV_RANGES.items():
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                mask = cv2.inRange(hsv, lower_np, upper_np)
                color_counts[color_name] = int(np.sum(mask > 0))
            mask1 = cv2.inRange(
                hsv,
                np.array([0, 100, 100], dtype=np.uint8),
                np.array([10, 255, 255], dtype=np.uint8),
            )
            mask2 = cv2.inRange(
                hsv,
                np.array([160, 100, 100], dtype=np.uint8),
                np.array([180, 255, 255], dtype=np.uint8),
            )
            color_counts["red"] = color_counts.get("red", 0) + int(
                np.sum(cv2.bitwise_or(mask1, mask2) > 0)
            )
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
            avg_s = float(np.mean(hsv[:, :, 1]))
            avg_v = float(np.mean(hsv[:, :, 2]))
            if avg_s < 30:
                if avg_v > 180:
                    return "white", 0.75
                elif avg_v < 80:
                    return "black", 0.75
                else:
                    return "gray", 0.65
            return best_color, confidence
        except Exception:
            return ColorAnalyzer._rgb_fallback(img_region)

    @staticmethod
    def _rgb_fallback(img_region: np.ndarray) -> Tuple[str, float]:
        try:
            avg_rgb = np.array(cv2.mean(img_region)[:3])
            min_dist = float("inf")
            best = "unknown"
            for name, rgb in ColorAnalyzer.RGB_COLORS.items():
                dist = float(
                    np.sqrt(np.sum((avg_rgb - np.array(rgb)) ** 2))
                )
                if dist < min_dist:
                    min_dist = dist
                    best = name
            confidence = float(max(0.5, 1 - (min_dist / 400)))
            return best, confidence
        except Exception:
            return "unknown", 0.0

    @classmethod
    def analyze(cls, img_region: np.ndarray) -> Tuple[str, float]:
        if img_region is None or img_region.size == 0:
            return "unknown", 0.0
        clusters = cls.kmeans_clustering(img_region, k=5)
        if clusters and clusters[0][1] > 0.35:
            return clusters[0][0], clusters[0][1]
        return cls.analyze_by_hsv(img_region)


class ModelBase:
    """基础模型类"""

    def __init__(self, model_path: str, device: str):
        self.model_path = model_path
        self.device = device
        self.model: Optional[nn.Module] = None
        self.transform = transforms.Compose(
            [
                transforms.Resize((256, 256)),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
                ),
            ]
        )

    def load_model(self) -> None:
        raise NotImplementedError


class ColorModel(ModelBase):
    """颜色分类模型"""

    def __init__(self, model_path: str, device: str):
        self.classes: Optional[List[str]] = None
        super().__init__(model_path, device)
        self.load_model()

    def load_model(self) -> None:
        try:
            checkpoint = _torch_load_compat(self.model_path, self.device)
            if isinstance(checkpoint, dict) and "classes" in checkpoint:
                self.classes = checkpoint["classes"]
                state_dict = checkpoint.get("model_state_dict", checkpoint)
            else:
                raise ValueError("Invalid model checkpoint format")
            self.model = models.resnet18(weights=None)
            num_features = self.model.fc.in_features
            self.model.fc = nn.Sequential()
            self.model.fc.add_module("1", nn.Linear(num_features, 512))
            self.model.fc.add_module("2", nn.ReLU())
            self.model.fc.add_module("4", nn.Linear(512, len(self.classes)))
            fixed_state_dict: Dict[str, torch.Tensor] = {}
            for k, v in state_dict.items():
                if k.startswith("model."):
                    fixed_state_dict[k[6:]] = v
                else:
                    fixed_state_dict[k] = v
            self.model.load_state_dict(fixed_state_dict)
            self.model.to(self.device)
            self.model.eval()
            logger.info("Color classification model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load color model: {e}")
            raise

    def predict(
        self, img: Image.Image
    ) -> Tuple[Optional[str], float]:
        try:
            img_tensor = self.transform(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                outputs = self.model(img_tensor)
                probs = torch.softmax(outputs, dim=1)
                conf, idx = torch.max(probs, dim=1)
                return self.classes[idx.item()], conf.item()
        except Exception as e:
            logger.error(f"Color prediction failed: {e}")
            return None, 0.0


class AgeModel(ModelBase):
    """年龄估计模型"""

    def __init__(self, model_path: str, device: str):
        self.age_classes = [
            "0-10",
            "11-20",
            "21-30",
            "31-40",
            "41-50",
            "51-60",
            "61-70",
            "71+",
        ]
        super().__init__(model_path, device)
        self.load_model()

    def load_model(self) -> None:
        try:
            class _AgeNet(nn.Module):
                def __init__(self, num_classes: int):
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
                        nn.Linear(512, num_classes),
                    )

                def forward(self, x: torch.Tensor) -> torch.Tensor:
                    return self.backbone(x)

            self.model = _AgeNet(num_classes=len(self.age_classes))
            checkpoint = _torch_load_compat(self.model_path, self.device)
            state_dict = checkpoint.get("model_state_dict", checkpoint)
            new_state_dict: Dict[str, torch.Tensor] = {}
            for k, v in state_dict.items():
                if k.startswith("module."):
                    k = k[7:]
                new_state_dict[k] = v
            self.model.load_state_dict(new_state_dict)
            self.model.to(self.device)
            self.model.eval()
            logger.info("Age estimation model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load age model: {e}")
            raise

    def predict(
        self, img: Any
    ) -> Tuple[Optional[float], float]:
        try:
            if not isinstance(img, Image.Image):
                if isinstance(img, np.ndarray):
                    img = Image.fromarray(
                        cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    )
                else:
                    raise ValueError("Input must be PIL Image or numpy array")
            img_tensor = self.transform(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                outputs = self.model(img_tensor)
                probs = torch.softmax(outputs, dim=1)
                confidence, pred_idx = torch.max(probs, dim=1)
                pred_age = self.age_classes[pred_idx.item()]
                age_range = pred_age.split("-")
                if len(age_range) == 2:
                    min_age = int(age_range[0])
                    max_age = int(age_range[1])
                else:
                    min_age = int(pred_age.replace("+", ""))
                    max_age = min_age + 29
                predicted_age = min_age + (max_age - min_age) * confidence.item()
                return predicted_age, confidence.item()
        except Exception as e:
            logger.error(f"Age prediction failed: {e}")
            return None, 0.0


class GenderModel(ModelBase):
    """性别分类模型 - 使用YOLO模型"""

    def __init__(self, model_path: str, device: str):
        super().__init__(model_path, device)
        self.load_model()

    def load_model(self) -> None:
        try:
            self.model = YOLO(self.model_path)
            self.model.to(self.device)
            logger.info("Gender classification model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load gender model: {e}")
            raise

    def predict(
        self, img: Any
    ) -> Tuple[str, float]:
        try:
            if isinstance(img, Image.Image):
                img = np.array(img)
            results = self.model(img)
            if not results or len(results) == 0:
                return "unknown", 0.0
            result = results[0]
            if not hasattr(result, "probs") or not result.probs:
                return "unknown", 0.0
            probs = result.probs
            female_prob = float(probs.data[0])
            male_prob = float(probs.data[1])
            if female_prob >= male_prob:
                gender = "female"
                confidence = female_prob
            else:
                gender = "male"
                confidence = male_prob
            if confidence < 0.35:
                return "unknown", confidence
            return gender, confidence
        except Exception as e:
            logger.error(f"Gender prediction failed: {e}")
            return "unknown", 0.0


class ImageAnalyzer(metaclass=Singleton):
    """
    核心图像分析器
    检测人脸、人体，分析服装颜色、年龄、性别
    """

    face_conf_threshold = 0.15
    body_conf_threshold = 0.25

    def __init__(self) -> None:
        self.device = get_device()
        self.models: Dict[str, Any] = {}
        self.model_paths = self._get_model_paths()
        self.preprocessor = ImagePreprocessor()
        self.color_analyzer = ColorAnalyzer()
        self.deeplabv3: Optional[Any] = None
        self.yolo_model: Optional[YOLO] = None
        self.transform = transforms.Compose(
            [
                transforms.Resize((256, 256)),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
                ),
            ]
        )
        self.ollama_base_url = os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        ).rstrip("/")
        self.ollama_model_name = os.getenv("OLLAMA_QWEN_MODEL", "qwen3.5:4b")
        self.ollama_timeout_s = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))
        logger.info(f"ImageAnalyzer initialized on device: {self.device}")
        self.load_models()

    def _get_model_paths(self) -> Dict[str, str]:
        return {
            "face": str(
                MODEL_DIR / "output/face_detection/train2/weights/best.pt"
            ),
            "color": str(MODEL_DIR / "output/color_classification/best_model.pth"),
            "age": str(MODEL_DIR / "output/age_estimation/weights/best.pt"),
            "gender": str(
                MODEL_DIR / "output/gender_classification/train/weights/best.pt"
            ),
        }

    def load_models(self) -> None:
        try:
            # DeepLabV3 for semantic segmentation
            try:
                self.deeplabv3 = models.segmentation.deeplabv3_resnet50(
                    pretrained=True
                )
                self.deeplabv3.eval()
                self.deeplabv3.to(self.device)
                logger.info("DeepLabV3 loaded successfully")
            except Exception as e:
                logger.warning(f"DeepLabV3 load failed: {e}")
                self.deeplabv3 = None

            # YOLOv8n pretrained model for person detection
            try:
                self.yolo_model = YOLO("yolov8n.pt")
                self.yolo_model.to(self.device)
                logger.info("YOLOv8n pretrained model loaded successfully")
            except Exception as e:
                logger.warning(f"YOLOv8n load failed: {e}")
                self.yolo_model = None

            # Face detection model
            face_path = self.model_paths.get("face")
            if face_path and os.path.exists(face_path):
                try:
                    self.models["face"] = YOLO(face_path)
                    self.models["face"].to(self.device)
                    logger.info("Face detection model loaded")
                except Exception as e:
                    logger.warning(f"Face model load failed: {e}")
                    self.models["face"] = None
            else:
                logger.warning(
                    f"Face model not found: {face_path}"
                )
                self.models["face"] = None

            # Color classification model
            color_path = self.model_paths.get("color")
            if color_path and os.path.exists(color_path):
                try:
                    self.models["color"] = ColorModel(color_path, self.device)
                except Exception as e:
                    logger.warning(f"Color model load failed: {e}")
                    self.models["color"] = None
            else:
                logger.warning(f"Color model not found: {color_path}")
                self.models["color"] = None

            # Age estimation model
            age_path = self.model_paths.get("age")
            if age_path and os.path.exists(age_path):
                try:
                    self.models["age"] = AgeModel(age_path, self.device)
                except Exception as e:
                    logger.warning(f"Age model load failed: {e}")
                    self.models["age"] = None
            else:
                logger.warning(f"Age model not found: {age_path}")
                self.models["age"] = None

            # Gender classification model
            gender_path = self.model_paths.get("gender")
            if gender_path and os.path.exists(gender_path):
                try:
                    self.models["gender"] = GenderModel(gender_path, self.device)
                except Exception as e:
                    logger.warning(f"Gender model load failed: {e}")
                    self.models["gender"] = None
            else:
                logger.warning(f"Gender model not found: {gender_path}")
                self.models["gender"] = None

        except Exception as e:
            logger.error(f"Model loading failed: {e}")

    def _get_person_mask(
        self, img: np.ndarray
    ) -> Optional[np.ndarray]:
        h, w = img.shape[:2]
        if self.deeplabv3 is not None:
            try:
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                input_tensor = (
                    self.transform(pil_img).unsqueeze(0).to(self.device)
                )
                with torch.no_grad():
                    output = self.deeplabv3(input_tensor)["out"][0]
                mask = torch.argmax(output, dim=0).cpu().numpy()
                person_mask = (mask == 15).astype(np.uint8) * 255
                person_mask = cv2.resize(
                    person_mask,
                    (w, h),
                    interpolation=cv2.INTER_NEAREST,
                )
                return person_mask
            except Exception as e:
                logger.warning(f"Segmentation failed: {e}")
        return None

    def _detect_persons(
        self, img: np.ndarray
    ) -> List[Tuple[int, int, int, int, float, str]]:
        """
        检测人脸和人体
        Returns: [(x1, y1, x2, y2, conf, mode), ...]
        mode: 'face' or 'body'
        """
        all_boxes: List[Tuple[int, int, int, int, float, str]] = []

        # Method 1: Dedicated face detection model
        if self.models.get("face"):
            try:
                results = self.models["face"].predict(
                    img,
                    conf=self.face_conf_threshold,
                    verbose=False,
                )
                if results and len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = map(
                            int, box.xyxy[0].cpu().numpy()
                        )
                        conf = (
                            float(box.conf[0].item())
                            if hasattr(box, "conf")
                            else 0.5
                        )
                        all_boxes.append((x1, y1, x2, y2, conf, "face"))
                    logger.info(f"Face detection: {len(all_boxes)} found")
            except Exception as e:
                logger.warning(f"Face detection failed: {e}")

        # Method 2: YOLOv8n pretrained model for body/person
        if self.yolo_model is not None and len(all_boxes) == 0:
            try:
                results = self.yolo_model.predict(
                    img,
                    conf=self.body_conf_threshold,
                    verbose=False,
                )
                if results and len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        cls = int(box.cls[0].item())
                        if cls == 0:  # person class in COCO
                            x1, y1, x2, y2 = map(
                                int, box.xyxy[0].cpu().numpy()
                            )
                            conf = float(box.conf[0].item())
                            all_boxes.append((x1, y1, x2, y2, conf, "body"))
                    logger.info(f"YOLOv8n detection: {len(all_boxes)} found")
            except Exception as e:
                logger.warning(f"YOLOv8n detection failed: {e}")

        # IoU deduplication
        if len(all_boxes) > 1:
            def calc_iou(a: Tuple, b: Tuple) -> float:
                ax1, ay1, ax2, ay2 = a[:4]
                bx1, by1, bx2, by2 = b[:4]
                inter_x1 = max(ax1, bx1)
                inter_y1 = max(ay1, by1)
                inter_x2 = min(ax2, bx2)
                inter_y2 = min(ay2, by2)
                inter_w = max(0, inter_x2 - inter_x1)
                inter_h = max(0, inter_y2 - inter_y1)
                inter = inter_w * inter_h
                area_a = (ax2 - ax1) * (ay2 - ay1)
                area_b = (bx2 - bx1) * (by2 - by1)
                union = area_a + area_b - inter
                return float(inter / union) if union > 0 else 0.0

            selected: List[Tuple] = []
            for box in sorted(all_boxes, key=lambda x: x[4], reverse=True):
                if not any(calc_iou(box, s) > 0.5 for s in selected):
                    selected.append(box)
            all_boxes = selected

        return all_boxes

    def _detect_clothing_regions(
        self,
        img: np.ndarray,
        face_box: Tuple[int, int, int, int],
        person_mask: Optional[np.ndarray],
    ) -> Dict[str, Dict[str, Any]]:
        x1, y1, x2, y2 = face_box
        face_h = y2 - y1
        face_w = x2 - x1
        h, w = img.shape[:2]
        if face_h <= 0 or face_w <= 0:
            return {
                "upper": {"region": np.array([]), "bbox": (0, 0, 0, 0)},
                "lower": {"region": np.array([]), "bbox": (0, 0, 0, 0)},
            }

        # Upper clothing region
        upper_y1 = y2
        upper_y2 = min(upper_y1 + int(face_h * 2.5), h)
        upper_x1 = max(0, x1 - int(face_w * 0.5))
        upper_x2 = min(x2 + int(face_w * 0.5), w)

        # Lower clothing region
        lower_y1 = upper_y2
        lower_y2 = min(lower_y1 + int(face_h * 2.5), h)
        lower_x1 = max(0, x1 - int(face_w * 0.6))
        lower_x2 = min(x2 + int(face_w * 0.6), w)

        # Refine using person segmentation mask
        if person_mask is not None:
            try:
                if person_mask.shape[:2] != (h, w):
                    person_mask = cv2.resize(person_mask, (w, h))
                person_mask_bool = person_mask.astype(bool)

                def refine(
                    rx1: int, ry1: int, rx2: int, ry2: int
                ) -> Tuple[int, int, int, int]:
                    rx1 = max(0, min(rx1, w - 1))
                    rx2 = max(0, min(rx2, w))
                    ry1 = max(0, min(ry1, h - 1))
                    ry2 = max(0, min(ry2, h))
                    if rx2 <= rx1 or ry2 <= ry1:
                        return rx1, ry1, rx2, ry2
                    sub = person_mask_bool[ry1:ry2, rx1:rx2]
                    if not sub.any():
                        return rx1, ry1, rx2, ry2
                    rows = np.any(sub, axis=1)
                    cols = np.any(sub, axis=0)
                    ys = np.where(rows)[0]
                    xs = np.where(cols)[0]
                    if len(ys) == 0 or len(xs) == 0:
                        return rx1, ry1, rx2, ry2
                    return (rx1 + xs[0], ry1 + ys[0], rx1 + xs[-1], ry1 + ys[-1])

                upper_x1, upper_y1, upper_x2, upper_y2 = refine(
                    upper_x1, upper_y1, upper_x2, upper_y2
                )
                lower_x1, lower_y1, lower_x2, lower_y2 = refine(
                    lower_x1, lower_y1, lower_x2, lower_y2
                )
            except Exception as e:
                logger.warning(f"Mask refinement failed: {e}")

        return {
            "upper": {
                "region": img[upper_y1:upper_y2, upper_x1:upper_x2],
                "bbox": (
                    int(upper_x1),
                    int(upper_y1),
                    int(upper_x2),
                    int(upper_y2),
                ),
            },
            "lower": {
                "region": img[lower_y1:lower_y2, lower_x1:lower_x2],
                "bbox": (
                    int(lower_x1),
                    int(lower_y1),
                    int(lower_x2),
                    int(lower_y2),
                ),
            },
        }

    def _analyze_color(
        self, img_region: np.ndarray, region_type: str = "upper"
    ) -> Tuple[str, float]:
        if img_region is None or img_region.size == 0:
            return "unknown", 0.0

        # Prefer K-means result
        clusters = self.color_analyzer.kmeans_clustering(img_region, k=5)
        if clusters and clusters[0][1] > 0.3:
            return clusters[0][0], clusters[0][1]

        # Use color classification model
        if self.models.get("color"):
            try:
                rgb_img = cv2.cvtColor(img_region, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                colors: List[str] = []
                confidences: List[float] = []
                for scale in [0.8, 1.0, 1.2]:
                    scaled = pil_img.resize(
                        (int(224 * scale), int(224 * scale))
                    )
                    color, conf = self.models["color"].predict(scaled)
                    if color is not None:
                        colors.append(color)
                        confidences.append(conf)
                if colors:
                    counts = Counter(colors)
                    most_common = counts.most_common(1)[0][0]
                    avg_conf = float(
                        np.mean(
                            [
                                c_val
                                for c_val, c_name in zip(
                                    colors, confidences
                                )
                                if c_name == most_common
                            ]
                        )
                    )
                    if avg_conf > 0.2:
                        return most_common, avg_conf
            except Exception as e:
                logger.warning(f"Color model prediction failed: {e}")

        # Fallback to HSV analysis
        return self.color_analyzer.analyze_by_hsv(img_region)

    def analyze_image(
        self, image_path: str, mode: str = "normal"
    ) -> Dict[str, Any]:
        """
        Main image analysis method
        Detects persons, analyzes clothing color, age, and gender
        """
        start_time = time.time()
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Cannot read image: {image_path}")
            img_h, img_w = img.shape[:2]
            logger.info(
                f"Analyzing image: {image_path}, size: {img_w}x{img_h}"
            )

            # Preprocess image
            enhanced_img = self.preprocessor.auto_enhance(img)

            # Get person segmentation mask
            person_mask = self._get_person_mask(img)

            # Detect persons (face/body)
            person_boxes = self._detect_persons(enhanced_img)
            logger.info(f"Detected {len(person_boxes)} person(s)")

            persons: List[Dict[str, Any]] = []

            for idx, (x1, y1, x2, y2, conf, detect_mode) in enumerate(
                person_boxes
            ):
                # Boundary check
                x1 = max(0, min(x1, img_w - 1))
                x2 = max(0, min(x2, img_w))
                y1 = max(0, min(y1, img_h - 1))
                y2 = max(0, min(y2, img_h))

                if x2 <= x1 or y2 <= y1:
                    continue

                face_h = y2 - y1
                face_w = x2 - x1

                # Estimate face region for body detection
                is_body = detect_mode == "body" or face_h > face_w * 1.5
                if is_body:
                    face_y1 = max(0, int(y1))
                    face_y2 = min(y2, int(y1 + face_h * 0.3))
                    face_x1 = max(0, int(x1 + face_w * 0.2))
                    face_x2 = min(img_w, int(x2 - face_w * 0.2))
                else:
                    face_y1, face_y2, face_x1, face_x2 = y1, y2, x1, x2

                face_img = img[face_y1:face_y2, face_x1:face_x2]
                face_pil: Optional[Image.Image] = None
                if face_img.size > 0:
                    face_pil = Image.fromarray(
                        cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                    )

                # Gender prediction
                gender = "unknown"
                gender_conf = 0.0
                if self.models.get("gender") and face_img.size > 0:
                    try:
                        gender, gender_conf = self.models["gender"].predict(
                            face_img
                        )
                    except Exception as e:
                        logger.warning(f"Gender prediction failed: {e}")

                # Age prediction
                age = 0.0
                age_conf = 0.0
                if self.models.get("age") and face_pil is not None:
                    try:
                        age_result = self.models["age"].predict(face_pil)
                        if age_result[0] is not None:
                            age, age_conf = age_result
                    except Exception as e:
                        logger.warning(f"Age prediction failed: {e}")

                # Detect clothing regions
                clothing = self._detect_clothing_regions(
                    img,
                    (face_x1, face_y1, face_x2, face_y2),
                    person_mask,
                )
                upper_region = clothing["upper"]["region"]
                lower_region = clothing["lower"]["region"]

                # Analyze clothing colors
                upper_color, upper_conf = self._analyze_color(
                    upper_region, "upper"
                )
                lower_color, lower_conf = self._analyze_color(
                    lower_region, "lower"
                )

                person_data: Dict[str, Any] = {
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
                    "confidence": conf,
                }
                persons.append(person_data)
                logger.info(
                    f"Person {idx+1}: gender={gender}, age={age}, "
                    f"upper={upper_color}, lower={lower_color}"
                )

            result: Dict[str, Any] = {
                "detected": len(persons),
                "persons": persons,
                "success": True,
                "processing_time": time.time() - start_time,
                "mode": mode,
            }

            # Fallback to LLM if no persons detected in enhanced mode
            if len(persons) == 0 and mode == "enhanced":
                logger.info(
                    "Local models detected nothing, trying LLM..."
                )
                qwen_result = self._analyze_with_qwen(image_path)
                if "error" not in qwen_result:
                    result = qwen_result
                    result["mode"] = "enhanced_qwen"

            return result

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "error": str(e),
                "detected": 0,
                "persons": [],
                "success": False,
                "mode": mode,
            }

    def _analyze_with_qwen(self, image_path: str) -> Dict[str, Any]:
        """Use Qwen LLM via Ollama to analyze image"""
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")

            prompt = (
                'Analyze the person(s) in the image and return JSON:\n'
                '{\n'
                '    "detected": number_of_people,\n'
                '    "persons": [\n'
                '        {\n'
                '            "gender": "male/female",\n'
                '            "gender_confidence": 0.9,\n'
                '            "age": 25,\n'
                '            "age_confidence": 0.8,\n'
                '            "upper_color": "red",\n'
                '            "upper_color_confidence": 0.8,\n'
                '            "lower_color": "blue",\n'
                '            "lower_color_confidence": 0.8,\n'
                '            "bbox": [x1, y1, x2, y2]\n'
                '        }\n'
                '    ],\n'
                '    "success": true\n'
                '}\n'
                'Only output valid JSON.'
            )

            url = f"{self.ollama_base_url}/api/chat"
            payload = {
                "model": self.ollama_model_name,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an image analysis assistant. Only output valid JSON.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [base64_image],
                    },
                ],
            }

            resp = requests.post(url, json=payload, timeout=self.ollama_timeout_s)

            if resp.status_code != 200:
                return {"error": f"Ollama error: {resp.status_code}"}

            content = resp.json().get("message", {}).get("content", "")
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])

            return {"error": "Cannot parse response"}

        except Exception as e:
            logger.error(f"Qwen analysis failed: {e}")
            return {"error": str(e)}


# Global singleton instance
image_analyzer = ImageAnalyzer()
