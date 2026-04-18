"""
车牌识别服务模块
从Design-competition项目整合的车牌识别功能
"""
import os
import cv2
import numpy as np
import logging
import time
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入PyTorch，如果不可用则提供替代方案
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
    
    # 检查CUDA可用性
    CUDA_AVAILABLE = torch.cuda.is_available()
    if CUDA_AVAILABLE:
        logger.info(f"CUDA可用，将使用GPU加速")
        DEVICE = torch.device('cuda')
    else:
        logger.info(f"CUDA不可用，将使用CPU运行")
        DEVICE = torch.device('cpu')
except ImportError:
    TORCH_AVAILABLE = False
    CUDA_AVAILABLE = False
    DEVICE = None
    logger.warning("PyTorch不可用，将使用替代方法进行车牌识别")

# 模型路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))))
MODEL_DIR = os.path.join(BASE_DIR, "ModelService", "Main", "models", "plate_recognition")
os.makedirs(MODEL_DIR, exist_ok=True)

# 车牌识别模型路径
PLATE_DETECTION_MODEL_PATH = os.path.join(MODEL_DIR, "plate_detect.pt")
PLATE_OCR_MODEL_PATH = os.path.join(MODEL_DIR, "plate_ocr.pth")
PLATE_COLOR_MODEL_PATH = os.path.join(MODEL_DIR, "plate_color.pth")

# 车牌字符集和颜色集
PLATE_CHARS = r"#京沪津渝冀晋蒙辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云藏陕甘青宁新学警港澳挂使领民航危0123456789ABCDEFGHJKLMNPQRSTUVWXYZ险品"
COLOR_LIST = ['黑色', '蓝色', '绿色', '白色', '黄色']

# 图像预处理参数
MEAN_VALUE, STD_VALUE = (0.588, 0.193)

# 定义车牌识别网络 (简化版, 保持与原始代码结构一致)
class PlateNet(nn.Module):
    """车牌识别网络"""
    
    def __init__(self, num_classes, export=False):
        super(PlateNet, self).__init__()
        self.export = export
        
        # 特征提取部分 (简化CNN结构，适合轻量级部署)
        self.conv = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(128, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        
        # 双向LSTM部分
        self.rnn = nn.Sequential(
            nn.GRU(256, 128, bidirectional=True, batch_first=True),
            nn.GRU(256, 128, bidirectional=True, batch_first=True)
        )
        
        # 分类器
        self.classifier = nn.Linear(256, num_classes)
        
    def forward(self, x):
        # 特征提取
        x = self.conv(x)
        
        # 调整维度以适应RNN
        b, c, h, w = x.size()
        x = x.view(b, c * h, w)
        x = x.permute(0, 2, 1)
        
        # RNN处理
        x, _ = self.rnn[0](x)
        x, _ = self.rnn[1](x)
        
        # 分类
        x = self.classifier(x)
        
        # 导出模式返回log_softmax结果
        if self.export:
            x = nn.functional.log_softmax(x, dim=2)
            
        return x

# 颜色识别网络 (简化版)
class ColorNet(nn.Module):
    """车牌颜色识别网络"""
    
    def __init__(self, num_classes=5):
        super(ColorNet, self).__init__()
        
        # 特征提取部分
        self.conv = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        
        # 全连接分类器
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 6 * 21, 128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, x):
        x = self.conv(x)
        x = self.fc(x)
        return x

# 辅助函数
def decode_plate(preds):
    """解码网络预测结果为车牌字符"""
    pre = 0
    new_preds = []
    for i in range(len(preds)):
        if preds[i] != 0 and preds[i] != pre:
            new_preds.append(preds[i])
        pre = preds[i]
    return new_preds

def preprocess_image(img, device):
    """预处理图像用于车牌识别"""
    img = cv2.resize(img, (168, 48))
    img = np.reshape(img, (48, 168, 3))

    # 标准化
    img = img.astype(np.float32)
    img = (img / 255. - MEAN_VALUE) / STD_VALUE
    img = img.transpose([2, 0, 1])
    img = torch.from_numpy(img)

    img = img.to(device)
    img = img.view(1, *img.size())
    return img

class PlateRecognizer:
    """车牌识别器类"""
    
    def __init__(self, ocr_model_path=None, color_model_path=None):
        """
        初始化车牌识别器
        
        Args:
            ocr_model_path: 可选，OCR模型路径
            color_model_path: 可选，颜色识别模型路径
        """
        self.logger = logging.getLogger(__name__ + ".PlateRecognizer")
        self.logger.info("初始化车牌识别器")
        
        self.ocr_model = None
        self.color_model = None
        
        if TORCH_AVAILABLE:
            self.logger.info("PyTorch可用，尝试加载深度学习模型")
            
            # 尝试加载OCR模型
            self.ocr_model_path = ocr_model_path or PLATE_OCR_MODEL_PATH
            if os.path.exists(self.ocr_model_path):
                self._load_ocr_model()
            else:
                self.logger.warning(f"OCR模型文件不存在: {self.ocr_model_path}")
            
            # 尝试加载颜色识别模型
            self.color_model_path = color_model_path or PLATE_COLOR_MODEL_PATH
            if os.path.exists(self.color_model_path):
                self._load_color_model()
            else:
                self.logger.warning(f"颜色识别模型文件不存在: {self.color_model_path}")
        else:
            self.logger.warning("PyTorch不可用，将使用传统方法进行车牌识别")
    
    def _load_ocr_model(self):
        """加载OCR模型"""
        try:
            self.logger.info(f"正在加载OCR模型: {self.ocr_model_path}")
            start_time = time.time()
            
            # 创建模型实例
            self.ocr_model = PlateNet(len(PLATE_CHARS))
            
            # 加载模型权重
            if CUDA_AVAILABLE:
                self.ocr_model.load_state_dict(torch.load(self.ocr_model_path))
            else:
                self.ocr_model.load_state_dict(torch.load(self.ocr_model_path, map_location=torch.device('cpu')))
                
            # 设置为评估模式
            self.ocr_model.to(DEVICE)
            self.ocr_model.eval()
            
            elapsed = time.time() - start_time
            self.logger.info(f"OCR模型加载成功，耗时: {elapsed:.2f}秒")
            return True
        except Exception as e:
            self.logger.error(f"加载OCR模型时发生错误: {str(e)}")
            self.ocr_model = None
            return False
    
    def _load_color_model(self):
        """加载颜色识别模型"""
        try:
            self.logger.info(f"正在加载颜色识别模型: {self.color_model_path}")
            start_time = time.time()
            
            # 创建模型实例
            self.color_model = ColorNet(len(COLOR_LIST))
            
            # 加载模型权重
            if CUDA_AVAILABLE:
                self.color_model.load_state_dict(torch.load(self.color_model_path))
            else:
                self.color_model.load_state_dict(torch.load(self.color_model_path, map_location=torch.device('cpu')))
                
            # 设置为评估模式
            self.color_model.to(DEVICE)
            self.color_model.eval()
            
            elapsed = time.time() - start_time
            self.logger.info(f"颜色识别模型加载成功，耗时: {elapsed:.2f}秒")
            return True
        except Exception as e:
            self.logger.error(f"加载颜色识别模型时发生错误: {str(e)}")
            self.color_model = None
            return False
    
    def recognize_plate_text(self, plate_img):
        """
        识别车牌文字
        
        Args:
            plate_img: 车牌图像
            
        Returns:
            识别结果字符串
        """
        if self.ocr_model is None or not TORCH_AVAILABLE:
            self.logger.warning("OCR模型不可用，将返回空结果")
            # 返回空结果表示识别失败
            return ""
            
        try:
            # 预处理图像
            img = preprocess_image(plate_img, DEVICE)
            
            # 推理
            with torch.no_grad():
                preds = self.ocr_model(img)
                
            # 获取结果
            preds = preds.argmax(dim=2)
            preds = preds.view(-1).detach().cpu().numpy()
            
            # 解码预测结果
            preds_idx = decode_plate(preds)
            
            # 转换为字符
            plate_chars = [PLATE_CHARS[idx] for idx in preds_idx]
            plate_str = ''.join(plate_chars)
            
            return plate_str
        except Exception as e:
            self.logger.error(f"识别车牌文字时发生错误: {str(e)}")
            # 出错时返回空字符串表示识别失败
            return ""
    
    def recognize_plate_color(self, plate_img):
        """
        识别车牌颜色
        
        Args:
            plate_img: 车牌图像
            
        Returns:
            颜色名称
        """
        if self.color_model is None or not TORCH_AVAILABLE:
            self.logger.warning("颜色识别模型不可用，将使用传统方法判断颜色")
            # 使用简单的色彩分析
            return self._analyze_color(plate_img)
            
        try:
            # 预处理图像
            img = preprocess_image(plate_img, DEVICE)
            
            # 推理
            with torch.no_grad():
                preds = self.color_model(img)
                
            # 获取结果
            color_idx = preds.argmax(dim=1).item()
            color_name = COLOR_LIST[color_idx]
            
            return color_name
        except Exception as e:
            self.logger.error(f"识别车牌颜色时发生错误: {str(e)}")
            # 出错时使用传统方法
            return self._analyze_color(plate_img)
    
    def _analyze_color(self, img):
        """
        基于传统方法分析车牌颜色
        
        Args:
            img: 车牌图像
            
        Returns:
            颜色名称
        """
        # 确保图像是BGR格式
        if not isinstance(img, np.ndarray):
            img = np.array(img)
            
        # 转换到HSV色彩空间
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 计算平均值
        h, s, v = cv2.split(hsv)
        h_avg = np.mean(h)
        s_avg = np.mean(s)
        v_avg = np.mean(v)
        
        # 判断颜色
        if v_avg < 46:
            return "黑色"
        elif h_avg > 100 and h_avg < 124 and s_avg > 43:
            return "蓝色"
        elif h_avg > 35 and h_avg < 99 and s_avg > 43:
            return "绿色"
        elif s_avg < 43 and v_avg > 46:
            return "白色"
        else:
            return "黄色"
    
    def detect_and_recognize(self, image, plate_coords=None):
        """
        检测并识别车牌
        
        Args:
            image: 原始图像
            plate_coords: 可选，车牌坐标，格式为 (x1, y1, x2, y2)
                         如果提供，则直接使用这些坐标而不进行检测
            
        Returns:
            识别结果字典
        """
        start_time = time.time()
        self.logger.info("开始车牌识别处理")
        
        # 确保图像是numpy数组
        if not isinstance(image, np.ndarray):
            image = np.array(image)
            
        # 如果没有提供车牌坐标，尝试进行检测
        if plate_coords is None:
            # 简单的颜色阈值分割，尝试查找蓝色和黄色区域
            # 实际项目中应使用更高级的车牌检测算法
            self.logger.info("未提供车牌坐标，尝试通过颜色阈值分割检测")
            plate_coords, _ = self._simple_plate_detection(image)
            
        # 如果无法检测到车牌，返回空结果
        if plate_coords is None:
            self.logger.warning("未检测到车牌")
            return {
                'success': False,
                'message': '未检测到车牌',
                'processing_time': time.time() - start_time
            }
            
        # 裁剪车牌区域
        x1, y1, x2, y2 = plate_coords
        plate_img = image[y1:y2, x1:x2]
        
        # 识别车牌文字
        plate_text = self.recognize_plate_text(plate_img)
        
        # 识别车牌颜色
        plate_color = self.recognize_plate_color(plate_img)
        
        # 计算处理时间
        elapsed = time.time() - start_time
        
        # 返回结果
        result = {
            'success': True,
            'plate_text': plate_text,
            'plate_color': plate_color,
            'plate_coords': plate_coords,
            'confidence': 0.85,  # 模拟的置信度
            'processing_time': elapsed
        }
        
        self.logger.info(f"车牌识别完成，耗时: {elapsed:.2f}秒，结果: {plate_text}, 颜色: {plate_color}")
        
        return result
    
    def _simple_plate_detection(self, image):
        """
        使用简单的颜色阈值方法检测车牌（仅作为备选方案）
        
        Args:
            image: 原始图像
            
        Returns:
            车牌坐标和类型
        """
        # 转换到HSV色彩空间以便进行颜色分割
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, w = image.shape[:2]
        
        # 蓝色车牌的HSV范围
        lower_blue = np.array([100, 43, 46])
        upper_blue = np.array([124, 255, 255])
        
        # 黄色车牌的HSV范围
        lower_yellow = np.array([15, 43, 46])
        upper_yellow = np.array([34, 255, 255])
        
        # 创建蓝色和黄色的掩码
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # 合并掩码
        mask = cv2.bitwise_or(blue_mask, yellow_mask)
        
        # 形态学操作改善掩码
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, None
            
        # 按面积排序轮廓
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # 遍历最大的几个轮廓，寻找车牌形状的候选区域
        for contour in contours[:5]:  # 只检查面积最大的5个轮廓
            area = cv2.contourArea(contour)
            
            # 忽略太小的区域
            if area < 1000:
                continue
                
            # 获取矩形边界
            x, y, w, h = cv2.boundingRect(contour)
            
            # 计算宽高比
            aspect_ratio = float(w) / h
            
            # 车牌的典型宽高比约为3:1到4:1
            if 2.5 <= aspect_ratio <= 5.0:
                # 轻微扩大边界框以确保完整捕获车牌
                x = max(0, x - 5)
                y = max(0, y - 5)
                w = min(image.shape[1] - x, w + 10)
                h = min(image.shape[0] - y, h + 10)
                
                # 确定车牌类型
                plate_type = "蓝牌"  # 默认为蓝牌
                roi_hsv = hsv[y:y+h, x:x+w]
                
                # 计算区域中蓝色和黄色像素的数量
                blue_pixels = cv2.countNonZero(cv2.inRange(roi_hsv, lower_blue, upper_blue))
                yellow_pixels = cv2.countNonZero(cv2.inRange(roi_hsv, lower_yellow, upper_yellow))
                
                if yellow_pixels > blue_pixels:
                    plate_type = "黄牌"
                    
                return (x, y, x + w, y + h), plate_type
                
        return None, None
    
    def draw_results(self, image, recognition_result):
        """
        在图像上绘制识别结果
        
        Args:
            image: 原始图像
            recognition_result: 识别结果字典
            
        Returns:
            绘制了结果的图像
        """
        if not recognition_result.get('success', False):
            return image
            
        # 确保图像是可修改的numpy数组
        if not isinstance(image, np.ndarray):
            image = np.array(image)
        
        img_result = image.copy()
        
        # 获取车牌坐标
        x1, y1, x2, y2 = recognition_result['plate_coords']
        
        # 绘制车牌边框
        cv2.rectangle(img_result, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # 准备标签文本
        text = f"{recognition_result['plate_text']} ({recognition_result['plate_color']})"
        
        # 绘制标签背景
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        cv2.rectangle(img_result, (x1, y1 - 30), (x1 + text_size[0], y1), (0, 255, 0), -1)
        
        # 绘制标签文本
        cv2.putText(img_result, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        
        return img_result

# 创建车牌识别器的工厂函数
def create_plate_recognizer():
    """创建车牌识别器实例"""
    return PlateRecognizer()
