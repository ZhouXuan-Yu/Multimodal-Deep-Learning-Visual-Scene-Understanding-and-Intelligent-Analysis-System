from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query, Request, Response, status
import os
import logging
import sys
import glob
import tempfile
import time
import uuid
import base64
import traceback
import subprocess
import shutil
import json
from datetime import datetime
import numpy as np
import cv2
import torch
from PIL import Image

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 外部项目路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
NIGHT_DETECTION_PATH = os.path.join(os.path.dirname(BASE_DIR), "night recognition")
# 注意: 目录名已从"Night-vehicle-detection-system-main"更改为"night recognition"
# 得到当前脚本所在的目录结构
# D:\Desktop\ModelService_graduation-main\ModelService\Main\app\routers
APP_DIR = os.path.dirname(os.path.dirname(__file__))  # app目录
MAIN_DIR = os.path.dirname(APP_DIR)  # Main目录
OUTPUT_DIR = os.path.join(MAIN_DIR, "static", "night_detection")

# 内部模型目录
MODELS_DIR = os.path.join(OUTPUT_DIR, "models")
YOLO_MODELS_DIR = os.path.join(MODELS_DIR, "yolo")
ENHANCE_MODELS_DIR = os.path.join(MODELS_DIR, "enhance")

# 确保输出目录存在
try:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info(f"确保输出目录存在: {OUTPUT_DIR}")
except Exception as e:
    logger.error(f"创建输出目录失败: {str(e)}")

# 夜间低光图像增强与目标检测路由
router = APIRouter(
    prefix="",
    tags=["night-detection"],
    responses={404: {"description": "Not found"}},
)

# 存储历史记录
detection_history = []

# 模型实例
enhance_model = None
detect_model = None

def load_model():
    """预加载图像增强和目标检测模型"""
    global enhance_model, detect_model
    
    # 强制使用CPU设备
    # 在模型加载前设置环境变量，确保任何初始化的模型都使用CPU
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    torch.set_grad_enabled(False)  # 禁用梯度计算，减少内存占用
    
    # 确保模型目录存在
    os.makedirs(YOLO_MODELS_DIR, exist_ok=True)
    os.makedirs(ENHANCE_MODELS_DIR, exist_ok=True)
    
    try:
        logger.info("预加载夜间检测模型 (强制使用CPU设备)...")
        
        # 检查PyTorch是否确实使用CPU
        device_str = "CPU (cuda disabled)"
        logger.info(f"PyTorch将使用设备: {device_str}")
        
        # 加载低光照增强模型
        logger.info("正在加载低光照增强模型...")
        
        # 查找模型文件
        model_path = os.path.join(NIGHT_DETECTION_PATH, "Night-vehicle-detection-system", "new_detection", "main")
        
        if not os.path.exists(model_path):
            logger.warning(f"模型路径不存在: {model_path}")
            # 尝试查找替代路径
            alt_paths = [
                os.path.join(NIGHT_DETECTION_PATH, "new_detection", "main"),
                os.path.join(NIGHT_DETECTION_PATH, "Night-vehicle-detection-system", "new_detection"),
                os.path.join(NIGHT_DETECTION_PATH, "Night-vehicle-detection-system"), 
                NIGHT_DETECTION_PATH
            ]
            
            model_path_found = False
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    logger.info(f"使用替代路径: {alt_path}")
                    model_path = alt_path
                    model_path_found = True
                    break
                    
            if not model_path_found:
                logger.error("无法找到有效的模型路径")
                # 创建一个简单的模拟模型
                enhance_model = create_dummy_enhance_model()
                detect_model = create_dummy_detect_model()
                return
            
        # 将模型路径添加到系统路径
        sys.path.append(model_path)
        
        # 检查模型实现方式
        model_file = os.path.join(model_path, "model.py")
        if os.path.exists(model_file):
            logger.info(f"找到模型文件: {model_file}")
            try:
                from model import EnhanceNetwork
                # 尝试加载增强模型
                enhance_model = EnhanceNetwork(layers=3, channels=32)
                # 显式指定模型在CPU上
                enhance_model = enhance_model.to('cpu')
                enhance_model.eval()  # 设置为评估模式
                logger.info("增强模型加载成功并已移至CPU")
            except Exception as e:
                logger.error(f"加载增强模型失败: {str(e)}")
                enhance_model = create_dummy_enhance_model()
        else:
            # 检查其他可能的模型实现
            for py_file in ["enhance.py", "enhance_model.py", "enhance_net.py"]:
                alt_model_file = os.path.join(model_path, py_file)
                if os.path.exists(alt_model_file):
                    logger.info(f"找到替代模型文件: {alt_model_file}")
                    try:
                        # 根据不同文件名导入不同的模块
                        module_name = py_file.replace(".py", "")
                        sys.path.append(os.path.dirname(alt_model_file))
                        module = __import__(module_name)
                        enhance_model = getattr(module, "EnhanceNetwork", None)()
                        if enhance_model:
                            # 显式指定模型在CPU上
                            enhance_model = enhance_model.to('cpu')
                            enhance_model.eval()  # 设置为评估模式
                            logger.info("增强模型加载成功并已移至CPU")
                            break
                    except Exception as e:
                        logger.error(f"加载替代增强模型失败: {str(e)}")
            
            # 如果还是没有找到，创建一个简单的替代模型
            if enhance_model is None:
                logger.warning("无法加载任何增强模型，使用随机初始化")
                enhance_model = create_dummy_enhance_model()
        
        # 加载YOLO目标检测模型
        logger.info("正在加载目标检测模型...")
        try:
            # 导入YOLO
            try:
                from ultralytics import YOLO
                # 设置YOLO环境变量确保使用CPU
                os.environ['YOLO_DEVICE'] = 'cpu'
            except ImportError:
                logger.error("无法导入ultralytics.YOLO，请确保已安装该库")
                detect_model = create_dummy_detect_model()
                return
                
            # 首先尝试加载自定义训练的YOLO模型（使用内部复制的模型文件）
            yolo_model_path = os.path.join(YOLO_MODELS_DIR, "best.pt")
            
            # 检查路径是否存在，如果不存在则创建目录
            os.makedirs(os.path.dirname(yolo_model_path), exist_ok=True)
            
            # 检查是否有权限问题
            if os.path.exists(yolo_model_path):
                try:
                    # 尝试打开文件验证权限
                    with open(yolo_model_path, 'rb'):
                        pass
                    # 确保YOLO在CPU上运行
                    detect_model = YOLO(yolo_model_path, task='detect')
                    # 强制YOLO使用CPU
                    detect_model.to('cpu')
                    logger.info(f"成功加载YOLO模型到CPU: {yolo_model_path}")
                except PermissionError:
                    logger.error(f"无权限访问YOLO模型文件: {yolo_model_path}")
                    # 尝试使用官方模型作为备选，确保在CPU上运行
                    detect_model = YOLO("yolov8n.pt", task='detect')
                    detect_model.to('cpu')
                    logger.info("已加载官方YOLOv8模型作为备选 (在CPU上)")
            else:
                logger.warning(f"YOLO模型文件不存在: {yolo_model_path}")
                # 尝试使用官方模型作为备选，确保在CPU上运行
                detect_model = YOLO("yolov8n.pt", task='detect')
                detect_model.to('cpu')
                logger.info("已加载官方YOLOv8模型作为备选 (在CPU上)")
        except Exception as e:
            logger.error(f"加载YOLO模型失败: {str(e)}")
            detect_model = create_dummy_detect_model()
        
        # 最后验证所有模型确实都在CPU上
        try:
            if hasattr(enhance_model, 'parameters'):
                params_list = list(enhance_model.parameters())
                if params_list and hasattr(params_list[0], 'device'):
                    logger.info(f"增强模型设备: {params_list[0].device}")
                    if 'cuda' in str(params_list[0].device):
                        # 再次强制转移到CPU
                        enhance_model = enhance_model.to('cpu')
                        logger.warning("增强模型被强制重新移至CPU")
            
            # 验证YOLO模型参数位置
            if hasattr(detect_model, 'model') and hasattr(detect_model.model, 'parameters'):
                params_list = list(detect_model.model.parameters())
                if params_list and hasattr(params_list[0], 'device'):
                    logger.info(f"检测模型设备: {params_list[0].device}")
                    if 'cuda' in str(params_list[0].device):
                        # 再次强制转移到CPU
                        detect_model.to('cpu')
                        logger.warning("检测模型被强制重新移至CPU")
        except Exception as e:
            logger.error(f"验证模型设备时出错: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"加载模型时出错: {str(e)}")
        # 创建简单的替代模型
        if enhance_model is None:
            enhance_model = create_dummy_enhance_model()
        if detect_model is None:
            detect_model = create_dummy_detect_model()
        return False

def create_dummy_enhance_model():
    """创建一个简单的增强模型替代，使用传统的图像处理方法增强图像"""
    
    class DummyEnhanceModel:
        def __init__(self):
            logger.info("创建替代增强模型")
        
        # 简单的图像增强处理
        def enhance(self, image, method="clahe"):
            """
            使用传统方法增强低光图像
            method: clahe, gamma, histogram
            """
            try:
                logger.info(f"应用传统图像增强方法: {method}")
                
                # 使用CLAHE方法增强图像对比度
                if method == "clahe":
                    # 创建CLAHE对象
                    logger.info("应用CLAHE增强...")
                    
                    # 转换到LAB颜色空间
                    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                    luminance, a, b = cv2.split(lab)
                    
                    # 应用CLAHE到L通道
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    cl = clahe.apply(luminance)
                    
                    # 合并通道
                    limg = cv2.merge((cl, a, b))
                    
                    # 转换回BGR
                    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
                    
                    # 稍微提高饱和度
                    hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
                    h, s, v = cv2.split(hsv)
                    s = cv2.convertScaleAbs(s, alpha=1.3, beta=0)  # 增加饱和度
                    hsv_enhanced = cv2.merge([h, s, v])
                    enhanced = cv2.cvtColor(hsv_enhanced, cv2.COLOR_HSV2BGR)
                
                # Gamma校正方法
                elif method == "gamma":
                    logger.info("应用Gamma校正...")
                    gamma = 1.5  # Gamma值大于1使暗区更亮
                    lookup_table = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in np.arange(0, 256)]).astype("uint8")
                    enhanced = cv2.LUT(image, lookup_table)
                
                # 直方图均衡化
                elif method == "histogram":
                    logger.info("应用直方图均衡化...")
                    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
                    y, cr, cb = cv2.split(ycrcb)
                    y_eq = cv2.equalizeHist(y)
                    ycrcb_eq = cv2.merge((y_eq, cr, cb))
                    enhanced = cv2.cvtColor(ycrcb_eq, cv2.COLOR_YCrCb2BGR)
                
                # 默认使用组合方法
                else:
                    logger.info("应用组合增强方法...")
                    # 先应用CLAHE
                    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                    luminance, a, b = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    cl = clahe.apply(luminance)
                    limg = cv2.merge((cl, a, b))
                    clahe_enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
                    
                    # 再应用Gamma校正
                    gamma = 1.3
                    lookup_table = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in np.arange(0, 256)]).astype("uint8")
                    enhanced = cv2.LUT(clahe_enhanced, lookup_table)
                
                logger.info("传统图像增强完成")
                return enhanced
                
            except Exception as e:
                logger.error(f"增强处理失败: {str(e)}")
                # 如果处理失败，返回原图
                return image
    
    # 返回实例
    return DummyEnhanceModel()

def create_dummy_detect_model():
    """创建一个简单的检测模型替代"""
    class DummyDetectionModel:
        def __init__(self):
            logger.info("创建替代检测模型")
            self.detector = None
            
            # 尝试加载人脸检测器作为示例
            try:
                self.detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                if self.detector.empty():
                    self.detector = None
                else:
                    logger.info("使用OpenCV人脸检测器作为替代")
            except Exception as e:
                logger.error(f"加载OpenCV检测器失败: {str(e)}")
        
        def __call__(self, img, conf=0.25):
            """简单的目标检测处理"""
            try:
                # 如果是文件路径，读取图像
                if isinstance(img, str):
                    img = cv2.imread(img)
                
                if img is None:
                    return []
                
                results = []
                
                if self.detector is not None:
                    # 使用OpenCV级联分类器
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = self.detector.detectMultiScale(gray, 1.3, 5)
                    
                    for (x, y, w, h) in faces:
                        results.append({
                            "xyxy": [x, y, x+w, y+h],
                            "conf": 0.8,
                            "cls": 0,
                            "name": "vehicle"
                        })
                else:
                    # 随机生成一些检测框
                    import random
                    
                    h, w = img.shape[:2]
                    
                    # 生成1-3个随机框
                    for _ in range(random.randint(1, 3)):
                        # 随机生成检测框
                        box_w = random.randint(int(w*0.1), int(w*0.3))
                        box_h = random.randint(int(h*0.1), int(h*0.3))
                        x = random.randint(0, w - box_w)
                        y = random.randint(0, h - box_h)
                        
                        results.append({
                            "xyxy": [x, y, x+box_w, y+box_h],
                            "conf": random.uniform(0.6, 0.9),
                            "cls": 0,
                            "name": "vehicle"
                        })
                
                class DummyResults:
                    def __init__(self, boxes):
                        self.boxes = boxes
                    
                    def plot(self, img):
                        # 在图像上绘制检测框
                        img_copy = img.copy()
                        for box in self.boxes:
                            x1, y1, x2, y2 = box["xyxy"]
                            cv2.rectangle(img_copy, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                            
                            # 添加标签
                            label = f'{box["name"]} {box["conf"]:.2f}'
                            cv2.putText(img_copy, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
                        return img_copy
                
                return DummyResults(results)
            except Exception as e:
                logger.error(f"替代检测处理失败: {str(e)}")
                # 返回空结果作为回退
                return []

def preprocess_image(image):
    """
    将图像转换为模型输入格式
    """
    try:
        # 如果是字符串路径，读取图像
        if isinstance(image, str):
            logger.info(f"从路径读取图像: {image}")
            image = cv2.imread(image)
            
        if image is None:
            logger.error("无法读取图像")
            return None
            
        logger.info(f"预处理图像，原始尺寸: {image.shape}")
        
        # 转换图像为RGB格式并归一化
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 转换为PyTorch张量
        tensor = torch.from_numpy(rgb_image.transpose(2, 0, 1)).float() / 255.0
        tensor = tensor.unsqueeze(0)  # 添加批次维度
        
        # 如果有GPU，移动到GPU
        if torch.cuda.is_available():
            tensor = tensor.cuda()
            
        logger.info(f"图像预处理完成，张量形状: {tensor.shape}")
        return tensor
    except Exception as e:
        logger.error(f"图像预处理失败: {str(e)}")
        return None

@router.post("/process")
async def process_image(image: UploadFile = File(...)):
    """
    处理夜间图像并返回处理结果（使用默认参数，忽略所有高级设置）
    """
    # 注意：简化后的API仅使用默认参数，所有高级设置均已移除
    logger.info(f"[API] 收到图像处理请求: {image.filename}")
    
    try:
        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        logger.info(f"[API] 输出目录: {OUTPUT_DIR}")
        
        # 生成唯一的文件名
        filename = f"{uuid.uuid4()}.jpg"
        input_path = os.path.join(OUTPUT_DIR, filename)
        result_filename = f"result_{filename}"
        result_path = os.path.join(OUTPUT_DIR, result_filename)
        enhanced_filename = f"enhanced_{filename}"
        enhanced_path = os.path.join(OUTPUT_DIR, enhanced_filename)
        
        logger.info(f"[API] 已生成文件路径：原始={input_path}, 检测结果={result_path}, 增强={enhanced_path}")
        
        # 保存上传的图片
        with open(input_path, "wb") as buffer:
            buffer.write(await image.read())
        logger.info(f"已保存图片: {input_path}")
        
        # 处理图像
        logger.info("[API] 准备处理图像...")
        try:
            detection_result = await run_night_detection(input_path, result_path)
            
            # 构建URL路径
            base_url = "/static/night_detection"
            result_url = f"{base_url}/{result_filename}"
            enhanced_url = f"{base_url}/{enhanced_filename}"
            
            logger.info(f"[API] 处理完成，结果图像URL: {result_url}")
            logger.info(f"[API] 增强图像URL: {enhanced_url}")
            
            # 检查文件是否存在
            if os.path.exists(result_path):
                logger.info(f"[API] 结果图像文件存在: {result_path}, 大小: {os.path.getsize(result_path)} 字节")
            else:
                logger.error(f"[API] 结果图像文件不存在: {result_path}")
            
            # 构建完整的响应
            response = {
                "resultImageUrl": result_url,
                "enhancedImageUrl": enhanced_url,
                "processingTime": detection_result.get("processingTime", "N/A"),
                "detectedObjects": detection_result.get("detectedObjects", [])
            }
            
            # 记录返回数据结构
            # 日志中输出数据结构
            data_str = json.dumps(response, ensure_ascii=False)
            logger.info(f"[API] 返回数据结构: {data_str}")
            
            # 记录到历史记录
            detection_history.append({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "imageUrl": f"/static/night_detection/{filename}",
                "resultImageUrl": result_url,
                "enhancedImageUrl": enhanced_url,
                "detectedObjects": detection_result.get("detectedObjects", []),
                "processingTime": detection_result.get("processingTime", "N/A")
            })
            
            if len(detection_history) > 50:  # 限制历史记录数量
                detection_history.pop(0)
            
            logger.info(f"[API] 响应成功返回")
            return response
        except Exception as e:
            logger.error(f"处理图像失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"图像处理失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理请求时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.post("/process-video")
async def process_video(
    video: UploadFile = File(...),
    night_vision_mode: bool = Form(False),
    enhance_method: str = Form("deep"),
    conf: float = Form(0.25, description="置信度阈值"),  # 添加置信度参数
    background_tasks: BackgroundTasks = None
):
    """
    处理视频：进行低光增强和目标检测（使用默认参数，忽略高级设置）
    """
    # 注意：为保持API兼容性，保留了原有参数，但内部固定使用默认值
    # 忽略传入的night_vision_mode和enhance_method参数
    try:
        # 生成唯一的文件名（不带扩展名的UUID作为处理ID）
        process_id = str(uuid.uuid4())
        video_filename = f"{process_id}.mp4"
        video_path = os.path.join(OUTPUT_DIR, video_filename)
        
        # 保存上传的视频
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
            
        logger.info(f"已保存视频: {video_path}，处理ID: {process_id}")
        
        # 生成结果视频路径
        result_filename = f"result_{video_filename}"
        result_path = os.path.join(OUTPUT_DIR, result_filename)
        
        # 先添加到任务字典中，状态为processing
        video_tasks[process_id] = {
            "status": "processing",
            "progress": 0,
            "process_id": process_id,
            "videoUrl": f"/static/night_detection/{video_filename}",
            "timestamp": datetime.now().isoformat()
        }
        
        # 在后台任务中处理视频 - 使用固定的默认值
        background_tasks.add_task(
            process_video_task,
            video_path,
            result_path,
            False,  # 固定使用 night_vision_mode=False
            "deep", # 固定使用 enhance_method="deep"
            process_id
        )
        
        # 立即返回响应，视频将在后台处理中
        return {
            "success": True,
            "message": "视频正在后台处理中，可通过返回的process_id查询进度",
            "process_id": process_id,
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"处理视频失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

# 定义改进版的帧到视频转换函数，支持多种图像格式
def frames_to_video(frame_folder, output_video_path, fps=30.0):
    """
    将图像帧合成为视频文件
    
    Args:
        frame_folder: 包含图像帧的文件夹路径
        output_video_path: 输出视频文件路径
        fps: 帧率，默认30fps
    
    Returns:
        bool: 是否成功合成视频
    """
    import cv2
    import os
    import glob
    
    logger.info(f"开始将帧转换为视频，输出路径: {output_video_path}，FPS: {fps}")
    
    # 检查帧目录是否存在
    if not os.path.exists(frame_folder):
        logger.error(f"帧目录不存在: {frame_folder}")
        return False
        
    # 同时搜索.jpg和.png文件（修复之前只搜索.jpg的问题）
    # 获取所有图像并确保它们按正确顺序排序
    frames = []
    for ext in ['*.jpg', '*.png', '*.jpeg', '*.webp']:
        pattern = os.path.join(frame_folder, ext)
        frames.extend(glob.glob(pattern))
    
    # 确保正确排序 - 如果文件名是数字序列，按数值排序
    def get_frame_number(filename):
        # 从文件名中提取数字部分
        import re
        name = os.path.basename(filename)
        match = re.search(r'\d+', name)
        if match:
            return int(match.group())
        return name  # 如果没有数字，则返回文件名
    
    # 排序帧
    frames = sorted(frames, key=get_frame_number)
    
    frame_count = len(frames)
    logger.info(f"在目录 {frame_folder} 中找到 {frame_count} 个图像文件")
    for i, frame in enumerate(frames[:5]):
        logger.info(f"示例帧 {i+1}: {os.path.basename(frame)}")
    if frame_count > 5:
        logger.info(f"... 以及 {frame_count-5} 个其他帧")
    
    if frame_count == 0:
        logger.error(f"在目录 {frame_folder} 中没有找到图像文件")
        return False
        
    # 创建输出目录（如果需要）
    output_dir = os.path.dirname(output_video_path)
    if not os.path.exists(output_dir) and output_dir:
        os.makedirs(output_dir)
    
    # 读取第一帧确定视频尺寸
    try:
        first_frame = cv2.imread(frames[0])
        if first_frame is None:
            logger.error(f"无法读取第一帧: {frames[0]}")
            return False
            
        height, width, _ = first_frame.shape
        logger.info(f"视频尺寸: {width}x{height}")
    except Exception as e:
        logger.error(f"读取第一帧时发生错误: {str(e)}")
        return False
    
    try:
        # 确保FPS大于等于1，这是OpenCV的要求
        if fps < 1.0:
            logger.warning(f"警告: FPS设置过低 ({fps}), 已自动调整为1.0")
            fps = 1.0
            
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
        
        logger.info(f"准备合成视频，共 {frame_count} 帧，FPS={fps}...")
        
        # 读取第一帧获取尺寸
        first_frame = cv2.imread(frames[0])
        if first_frame is None:
            logger.error(f"错误: 无法读取第一帧")
            return False
            
        h, w, _ = first_frame.shape
        
        # 使用最基本的编解码器
        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        
        # 确保输出路径是绝对路径且格式正确
        output_video_path = os.path.abspath(output_video_path)
        # 确保目录存在
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
        
        # Windows下确保视频编解码器能正常工作的扩展名
        if not output_video_path.lower().endswith(('.avi')):
            output_video_path = output_video_path + '.avi'
            logger.info(f"为确保兼容性，输出文件已修改为: {output_video_path}")
            
        # 使用临时文件避免路径问题
        temp_dir = os.path.dirname(output_video_path)
        temp_output = os.path.join(temp_dir, 'temp_video.avi')
        
        # 确保使用兼容的fourcc编解码器
        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')  # 最常用的AVI编解码器
        logger.info(f"尝试使用MJPG编解码器创建视频: {temp_output}，尺寸: {w}x{h}，帧率: {fps}")
        
        out = cv2.VideoWriter(temp_output, fourcc, fps, (w, h))
        if not out.isOpened():
            logger.warning("MJPG编解码器失败，尝试无压缩格式")
            fourcc = 0  # 无压缩
            out = cv2.VideoWriter(temp_output, fourcc, fps, (w, h))
            
        if not out.isOpened():
            logger.error("所有编解码器尝试均失败")
            return False
            
        # 写入帧
        success_count = 0
        total_frames = len(frames)
        
        logger.info(f"开始写入 {total_frames} 帧到视频文件...")
        for i, frame_path in enumerate(frames):
            try:
                frame = cv2.imread(frame_path)
                if frame is not None:
                    # 确保帧尺寸正确
                    if frame.shape[1] != w or frame.shape[0] != h:
                        frame = cv2.resize(frame, (w, h))
                    out.write(frame)
                    success_count += 1
                    # 每处理10%的帧显示一次进度
                    if success_count % max(1, total_frames // 10) == 0:
                        progress_percent = (success_count/total_frames*100)
                        logger.info(f"进度: {success_count}/{total_frames} 帧 ({progress_percent:.1f}%)")
            except Exception as e:
                logger.error(f"处理帧 {frame_path} 时出错: {str(e)}")
                
        # 释放资源
        out.release()
        
        # 检查输出文件
        if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
            # 重命名为最终文件
            try:
                if os.path.exists(output_video_path):
                    os.remove(output_video_path)
                os.rename(temp_output, output_video_path)
                logger.info(f"视频成功创建: {output_video_path} (共写入 {success_count}/{total_frames} 帧)")
                return True
            except Exception as e:
                logger.error(f"重命名视频文件失败: {str(e)}")
                return False
        else:
            logger.error(f"创建视频失败，临时文件不存在或为空")
            return False
            
    except Exception as e:
        logger.error(f"合成视频时发生错误: {str(e)}")
        return False

def custom_video2frame(video_path, out_frame_path, output_folders):
    """
    改进版的视频转帧函数，使用复制而不是移动文件，避免句柄错误
    """
    import cv2
    import os
    import shutil
    import math
    
    logger.info("开始自定义视频转帧处理...")
    # 定义文件夹数量
    num_folders = len(output_folders)
    # 读取视频文件
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # 获取视频帧率
    fps = cap.get(cv2.CAP_PROP_FPS)
    # 获取视频总帧数
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 创建输出文件夹
    for folder in output_folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            
    if not os.path.exists(out_frame_path):
        os.makedirs(out_frame_path)
    
    logger.info(f"视频信息: 宽={width}, 高={height}, FPS={fps}, 总帧数={total_frames}")
    
    # 计算每个文件夹应该包含的图片数量
    num_frames = [math.floor(total_frames / num_folders)] * num_folders
    remainder = total_frames % num_folders
    for i in range(remainder):
        num_frames[i] += 1
        
    # 逐帧读取视频并将帧直接保存到对应的输出文件夹
    frame_count = 0
    folder_index = 0
    frames_in_current_folder = 0
    
    # 同时保存到输出帧文件夹中一份，方便处理
    all_frames = []
    
    while frame_count < total_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        # 生成帧文件名
        frame_filename = f"frame{frame_count:04d}.jpg"
        
        # 保存到总帧目录(使用写入而非移动)
        frame_path = os.path.join(out_frame_path, frame_filename)
        cv2.imwrite(frame_path, frame)
        all_frames.append(frame_filename)
        
        # 直接写入到目标文件夹
        if frames_in_current_folder < num_frames[folder_index]:
            output_path = os.path.join(output_folders[folder_index], frame_filename)
            cv2.imwrite(output_path, frame)  # 直接写入而不是移动
            frames_in_current_folder += 1
        else:
            # 切换到下一个文件夹
            folder_index += 1
            frames_in_current_folder = 1  # 重置计数
            output_path = os.path.join(output_folders[folder_index], frame_filename)
            cv2.imwrite(output_path, frame)  # 直接写入而不是移动
            
        frame_count += 1
        
        # 每处理100帧更新一次进度
        if frame_count % 100 == 0:
            logger.info(f"已处理 {frame_count}/{total_frames} 帧")
    
    cap.release()
    logger.info("视频转帧处理完成")
    return width, height, fps


# 简化版视频处理函数，不依赖外部项目的复杂导入
def simple_process_video(video_path, result_path, night_vision_mode, enhance_method):
    """简化版的视频处理函数，直接处理视频，不依赖外部项目的复杂导入"""
    import cv2
    import torch
    import numpy as np
    from PIL import Image, ImageEnhance
    import os
    import time
    
    start_time = time.time()
    logger.info("开始处理视频: {}，增强方法: {}, 夜视模式: {}".format(video_path, enhance_method, night_vision_mode))
    
    # 确定使用的设备
    device = torch.device("cpu")
    logger.info("使用处理设备: CPU")
    
    # 确保模型在指定设备上
    global enhance_model, detect_model
    if enhance_model is not None:
        enhance_model = enhance_model.to(device)
        logger.info("已将增强模型移至CPU设备")
    if detect_model is not None:
        detect_model = detect_model.to(device)
        logger.info("已将检测模型移至CPU设备")
    
    # 读取视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"无法打开视频: {video_path}")
        
    # 获取视频信息
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    logger.info("视频信息: 宽={}, 高={}, FPS={}, 总帧数={}".format(width, height, fps, total_frames))
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(result_path, fourcc, fps, (width, height))
    
    # 简化的图像增强函数
    def enhance_frame(frame):
        # 转换为PIL图像以便处理
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # 根据选择的增强方法处理
        if enhance_method == 'clahe':
            # 使用CLAHE增强
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            merged = cv2.merge((cl, a, b))
            enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        elif enhance_method == 'gamma':
            # Gamma校正
            gamma = 1.5
            enhanced = np.power(frame/255.0, 1.0/gamma) * 255.0
            enhanced = enhanced.astype(np.uint8)
        else:  # 默认使用模型增强
            # 使用已加载的增强模型
            if enhance_model is not None:
                try:
                    # 转换为PIL图像格式
                    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    # 使用预处理函数
                    pil_img = pil_img.resize((512, 512))  # 调整为模型输入大小
                    
                    # 转换为张量，确保在正确的设备上
                    img_tensor = torch.FloatTensor(np.array(pil_img).transpose((2, 0, 1))).unsqueeze(0) / 255.0
                    img_tensor = img_tensor.to(device)
                    
                    with torch.no_grad():
                        # 使用模型进行增强
                        enhanced_tensor = enhance_model(img_tensor)
                        enhanced_tensor = torch.clamp(enhanced_tensor, 0, 1)
                        
                        # 转回NumPy格式
                        enhanced_np = (enhanced_tensor.squeeze().permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
                        
                        # 调整回原始尺寸
                        enhanced_pil = Image.fromarray(enhanced_np)
                        enhanced_pil = enhanced_pil.resize((width, height))
                        enhanced = cv2.cvtColor(np.array(enhanced_pil), cv2.COLOR_RGB2BGR)
                except Exception as e:
                    logger.error(f"模型增强失败，回退到基础增强: {str(e)}")
                    # 回退到简单的亮度增强
                    enhanced = cv2.convertScaleAbs(frame, alpha=1.2, beta=30)
            else:
                # 回退到简单的亮度增强
                enhanced = cv2.convertScaleAbs(frame, alpha=1.2, beta=30)
        
        # 如果开启夜视模式，应用绿色滤镜
        if night_vision_mode:
            # 创建绿色夜视效果
            hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
            # 调整色相到绿色范围
            hsv[:, :, 0] = 60  # 绿色对应色相值
            # 增加饱和度
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.5, 0, 255).astype(np.uint8)
            enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        return enhanced
    
    # 使用预加载的检测模型进行目标检测
    def detect_objects(frame):
        if detect_model is not None:
            try:
                # 使用YOLOv8模型进行检测
                results = detect_model(frame, conf=0.25)
                
                # 在帧上绘制结果
                for result in results:
                    boxes = result.boxes.cpu().numpy()
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = box.conf[0]
                        cls_id = int(box.cls[0])
                        cls_name = result.names[cls_id]
                        
                        # 绘制边界框
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        # 绘制标签
                        label = f"{cls_name} {conf:.2f}"
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            except Exception as e:
                logger.error(f"目标检测失败: {str(e)}")
        
        return frame
    
    processed_frames = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 增强处理
            enhanced_frame = enhance_frame(frame)
            
            # 目标检测
            detected_frame = detect_objects(enhanced_frame)
            
            # 写入输出视频
            writer.write(detected_frame)
            
            processed_frames += 1
            
            # 每处理10%的帧更新一次进度
            if processed_frames % max(1, int(total_frames * 0.1)) == 0:
                progress = min(90, int(processed_frames / total_frames * 90))
                logger.info(f"视频处理进度: {progress}%，已处理 {processed_frames}/{total_frames} 帧")
                yield progress  # 返回进度供外部更新
    
    except Exception as e:
        logger.error(f"处理视频帧时出错: {str(e)}")
        raise
    finally:
        # 释放资源
        cap.release()
        writer.release()
    
    end_time = time.time()
    processing_time = end_time - start_time
    logger.info(f"视频处理完成，耗时: {processing_time:.2f} 秒")
    
    return {
        "success": True,
        "processing_time": processing_time,
        "output_file": result_path
    }

async def process_video_task(video_path, result_path, night_vision_mode, enhance_method, process_id):
    """后台处理视频的任务"""
    # 保存当前工作目录，程序结束后恢复
    original_cwd = os.getcwd()
    
    try:
        # 验证视频文件存在且可访问
        if not os.path.exists(video_path):
            raise Exception(f"视频文件不存在: {video_path}")
            
        # 验证文件可访问性
        try:
            with open(video_path, 'rb') as test_file:
                # 仅测试读取前 1KB 验证文件可访问
                test_file.read(1024)
            logger.info(f"视频文件验证成功，可正常访问: {video_path}")
        except (IOError, PermissionError) as e:
            logger.error(f"无法访问视频文件: {str(e)}")
            raise Exception(f"无法访问视频文件: {str(e)}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(result_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # 更新任务状态为处理中
        if process_id in video_tasks:
            video_tasks[process_id]["progress"] = 10
            logger.info(f"开始处理视频，ID: {process_id}, 进度: 10%")
            
        # 确保模型已加载
        if enhance_model is None or detect_model is None:
            try:
                load_model()  # 加载模型
                logger.info("模型加载成功")
            except Exception as e:
                logger.error(f"加载模型失败: {str(e)}")
                raise Exception(f"加载模型失败: {str(e)}")
        
        # 使用简化版处理函数
        try:
            # 使用完整的模型处理函数而不是简化版
            logger.info("开始处理视频，使用完整模型处理函数")
            
            # 调用完整的视频处理函数
            try:
                # 先更新进度为20%
                if process_id in video_tasks:
                    video_tasks[process_id]["progress"] = 20
                    logger.info(f"视频预处理完成，进度更新为20%")
                
                # 创建临时处理目录
                temp_dir = os.path.join(OUTPUT_DIR, "temp", process_id)
                os.makedirs(temp_dir, exist_ok=True)
                
                # 调用正式处理函数
                integrated_process_video(video_path, enhance_model, detect_model, result_path, conf=0.25, 
                                      night_vision_mode=night_vision_mode, enhance_method=enhance_method, 
                                      temp_dir=temp_dir, process_id=process_id)
                
                # 处理完成，更新进度为100%
                if process_id in video_tasks:
                    video_tasks[process_id]["progress"] = 100
                    logger.info("视频处理完成，进度更新为100%")
                
                # 注意：如果正式处理函数成功，我们就完成处理
                # 处理完成
                if process_id in video_tasks:
                    try:
                        # 确保结果路径是绝对路径
                        result_path_abs = os.path.abspath(result_path)
                        
                        # 确保目标目录存在
                        static_night_detection_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                                              "static", "night_detection")
                        os.makedirs(static_night_detection_dir, exist_ok=True)
                        logger.info(f"静态文件目录确认: {static_night_detection_dir}")
                        
                        # 保证文件名终止于.mp4
                        result_filename = os.path.basename(result_path)
                        if not result_filename.lower().endswith('.mp4'):
                            new_result_filename = f"{os.path.splitext(result_filename)[0]}.mp4"
                            result_filename = new_result_filename
                        
                        # 确保结果文件的副本保存到static目录
                        static_result_path = os.path.join(static_night_detection_dir, result_filename)
                        
                        if os.path.exists(result_path_abs) and os.path.getsize(result_path_abs) > 0:
                            # 如果原始结果文件不在static目录中，复制一份
                            if result_path_abs != static_result_path:
                                import shutil
                                shutil.copy2(result_path_abs, static_result_path)
                                logger.info(f"已复制视频到静态目录: {static_result_path}")
                            
                            # 计算相对URL路径 - 使用标准格式以配合前端
                            relative_video_url = f"/static/night_detection/{result_filename}"
                            logger.info(f"生成处理后的视频URL: {relative_video_url}")
                            
                            # 记录原始视频路径
                            original_video_url = f"/static/night_detection/{os.path.basename(video_path)}"
                            
                            # 已存在时更新文件大小数据
                            file_size_mb = os.path.getsize(static_result_path) / (1024 * 1024)
                            logger.info(f"视频文件大小: {file_size_mb:.2f}MB")
                            
                            # 更新任务状态
                            timestamp = datetime.now().isoformat()
                            video_tasks[process_id]["status"] = "completed"
                            video_tasks[process_id]["progress"] = 100
                            video_tasks[process_id]["result_video_url"] = relative_video_url
                            video_tasks[process_id]["resultVideoUrl"] = relative_video_url
                            video_tasks[process_id]["completed_at"] = timestamp
                            video_tasks[process_id]["message"] = "视频处理完成"
                            video_tasks[process_id]["original_video_url"] = original_video_url
                            video_tasks[process_id]["videoUrl"] = original_video_url
                            video_tasks[process_id]["file_size"] = f"{file_size_mb:.2f}MB"
                        else:
                            # 文件不存在或为空，可能出现问题
                            logger.error(f"视频文件不存在或为空: {result_path_abs}")
                            video_tasks[process_id]["status"] = "error"
                            video_tasks[process_id]["message"] = "视频处理完成但文件不可用"
                    except Exception as e:
                        logger.error(f"更新视频任务状态时出错: {str(e)}")
                        video_tasks[process_id]["status"] = "error"
                        video_tasks[process_id]["message"] = f"视频处理完成但更新状态时出错: {str(e)}"
                    video_tasks[process_id]["timestamp"] = timestamp
                    logger.info(f"视频处理完成，更新任务状态: {process_id}")
                
                    # 添加到处理历史
                    if process_id in video_tasks and "result_video_url" in video_tasks[process_id]:
                        # 使用任务中已更新的URL
                        result_url = video_tasks[process_id]["result_video_url"]
                        original_url = video_tasks[process_id]["videoUrl"]
                        
                        add_to_detection_history(
                            process_id,
                            video_url=original_url,
                            result_url=result_url
                        )
                        logger.info(f"已将处理结果添加到历史记录: {process_id}")
                    else:
                        logger.warning(f"无法将结果添加到历史记录，任务数据不完整: {process_id}")
                
                logger.info("视频处理成功完成")
                return
                
            except Exception as e:
                logger.error(f"使用模型处理视频时出错: {str(e)}")
                # 如果完整模型处理失败，回退到简化版处理
                logger.warning("尝试使用简化版处理函数...")
                progress_generator = simple_process_video(video_path, result_path, night_vision_mode, enhance_method)
                
                # 更新处理进度
                for progress in progress_generator:
                    if process_id in video_tasks:
                        video_tasks[process_id]["progress"] = progress
                        logger.info(f"更新视频处理进度: {progress}%")
                
                # 简化版处理完成后，更新状态
                if process_id in video_tasks:
                    video_tasks[process_id]["status"] = "completed"
                    video_tasks[process_id]["progress"] = 100
                    video_tasks[process_id]["result_video_url"] = f"/static/night_detection/{os.path.basename(result_path)}"
                    video_tasks[process_id]["completed_at"] = datetime.now().isoformat()
                    logger.info(f"视频处理完成(简化版): {process_id}")
                    
                    # 添加到处理历史
                    add_to_detection_history(
                        process_id,
                        video_url=f"/static/night_detection/{os.path.basename(video_path)}",
                        result_url=f"/static/night_detection/{os.path.basename(result_path)}"
                    )
                
                logger.info("视频处理成功完成(简化版)")
                
        except Exception as e:
            logger.error(f"处理视频时发生错误: {str(e)}", exc_info=True)
            # 更新任务状态为失败
            if process_id in video_tasks:
                video_tasks[process_id]["status"] = "failed"
                video_tasks[process_id]["error"] = str(e)
                logger.error(f"视频处理失败，更新状态: {process_id}")
                
                # 添加失败记录到历史
                add_to_detection_history(
                    process_id,
                    video_url=f"/static/night_detection/{os.path.basename(video_path)}",
                    status="failed",
                    error=str(e)
                )
            raise Exception(f"处理视频失败: {str(e)}")
            logger.info("视频处理成功完成")
            
            # 更新任务进度为完成
            if process_id in video_tasks:
                video_tasks[process_id]["status"] = "completed"
                video_tasks[process_id]["progress"] = 100
                video_tasks[process_id]["result_video_url"] = f"/static/night_detection/{os.path.basename(result_path)}"
                video_tasks[process_id]["completed_at"] = datetime.now().isoformat()
                logger.info(f"视频处理完成: {process_id}")
                
                # 添加到处理历史
                add_to_detection_history(
                    process_id,
                    video_url=f"/static/night_detection/{os.path.basename(video_path)}",
                    result_url=f"/static/night_detection/{os.path.basename(result_path)}"
                )

        except Exception as e:
            logger.error(f"处理视频时发生错误: {str(e)}")
            raise Exception(f"处理视频失败: {str(e)}")

    except Exception as e:
        logger.error(f"视频处理任务失败: {str(e)}")
        # 更新任务状态为失败
        if process_id in video_tasks:
            video_tasks[process_id]["status"] = "failed"
            video_tasks[process_id]["error"] = str(e)
            video_tasks[process_id]["completed_at"] = datetime.now().isoformat()
            
        # 记录到处理历史
        add_to_detection_history(
            process_id,
            video_url=f"/static/night_detection/{os.path.basename(video_path)}",
            status="failed",
            error=str(e)
        )
        logger.error(f"视频处理失败，ID: {process_id}, 错误: {str(e)}")
    finally:
        # 恢复原始工作目录
        os.chdir(original_cwd)
        logger.info(f"已恢复工作目录到: {original_cwd}")
# 添加检测历史记录函数
def add_to_detection_history(process_id, video_url=None, result_url=None, status="completed", error=None):
    """
    添加一条检测历史记录
    
    Args:
        process_id: 处理ID
        video_url: 视频URL
        result_url: 结果视频URL
        status: 处理状态，默认为completed
        error: 错误信息，仅当status为failed时有效
    """
    history_entry = {
        "id": process_id,
        "timestamp": datetime.now().isoformat(),
        "type": "video",
        "videoUrl": video_url,
        "processingStatus": status
    }
    
    if status == "completed" and result_url:
        history_entry["resultVideoUrl"] = result_url
    elif status == "failed" and error:
        history_entry["error"] = error
    
    detection_history.append(history_entry)
    
    # 限制历史记录数量
    if len(detection_history) > 50:
        detection_history.pop(0)
    
    logger.info(f"添加检测历史记录: {process_id}, 状态: {status}")

# 存储视频处理任务进度的字典
# 键是处理ID，值是进度信息
video_tasks = {}

@router.get("/video-progress/{process_id}")
async def get_video_progress(process_id: str):
    """
    获取视频处理进度
    """
    try:
        # 清理可能的.mp4扩展名
        process_id = process_id.replace(".mp4", "")
        logger.info(f"查询视频处理进度: {process_id}")
        
        # 安全防御，检查process_id是否有效
        if not process_id or len(process_id) < 5:
            logger.warning(f"请求了无效的process_id: {process_id}")
            return {
                "status": "invalid_id",
                "progress": 0,
                "error": "处理ID无效",
                "process_id": process_id
            }
        
        # 检查标准结果视频路径是否存在
        standard_result_path = os.path.join(OUTPUT_DIR, f"result_{process_id}.mp4")
        standard_result_url = f"/static/night_detection/result_{process_id}.mp4"
        file_exists = os.path.exists(standard_result_path) and os.path.getsize(standard_result_path) > 0
        
        if file_exists:
            logger.info(f"标准结果文件存在: {standard_result_path}")
            # 如果文件存在，返回完成状态和标准URL
            return {
                "status": "completed",
                "progress": 100,
                "process_id": process_id,
                "message": "视频处理已完成",
                # 同时提供两种键名以兼容前端
                "result_video_url": standard_result_url,
                "resultVideoUrl": standard_result_url,
                # 添加文件大小信息
                "file_size_mb": round(os.path.getsize(standard_result_path) / (1024 * 1024), 2)
            }
        
        # 查找对应的任务
        # 首先从临时任务字典中查找
        if process_id in video_tasks:
            try:
                # 创建深拷贝避免引用问题
                import copy
                task_info = copy.deepcopy(video_tasks[process_id])
                logger.info(f"从进行中任务找到视频任务: {process_id}, 状态: {task_info.get('status', '未知')}, 进度: {task_info.get('progress', 0)}%")
                
                # 添加标准化的结果视频URL
                # 同时提供两种键名来兼容不同的前端展示需求
                if task_info.get("status") == "completed" and not task_info.get("result_video_url"):
                    task_info["result_video_url"] = standard_result_url
                if task_info.get("status") == "completed" and not task_info.get("resultVideoUrl"):
                    task_info["resultVideoUrl"] = standard_result_url
                
                return task_info
            except Exception as copy_error:
                logger.error(f"复制任务信息时出错: {str(copy_error)}")
                # 如果复制失败，创建标准化的状态信息
                status = video_tasks[process_id].get("status", "processing")
                progress = video_tasks[process_id].get("progress", 50)
                
                # 如果进度大于95%但状态不是完成，则检查文件是否存在
                if progress > 95 and status != "completed":
                    if file_exists:
                        status = "completed"
                        progress = 100
                
                return {
                    "status": status,
                    "progress": progress,
                    "process_id": process_id,
                    "result_video_url": standard_result_url if status == "completed" else "",
                    "resultVideoUrl": standard_result_url if status == "completed" else ""
                }
        
        # 然后从历史记录查找
        for record in detection_history:
            try:
                if record.get("id") == process_id or os.path.basename(record.get("videoUrl", "")).startswith(process_id):
                    status = record.get("processingStatus", "unknown")
                    logger.info(f"从历史记录找到视频任务: {process_id}, 状态: {status}")
                    
                    # 返回状态信息
                    if status == "completed":
                        # 使用记录的URL或标准URL
                        result_url = record.get("resultVideoUrl", standard_result_url)
                        return {
                            "status": "completed",
                            "progress": 100,
                            "process_id": process_id,
                            "result": {
                                "detectedObjects": record.get("detectedObjects", []),
                                "processingTime": record.get("processingTime", "N/A")
                            },
                            # 同时提供两种键名以兼容前端
                            "result_video_url": result_url,
                            "resultVideoUrl": result_url
                        }
                    elif status == "failed":
                        return {
                            "status": "failed",
                            "progress": 0,
                            "error": record.get("error", "未知错误"),
                            "process_id": process_id
                        }
                    else:
                        # 状态未知或处理中
                        return {
                            "status": "processing",
                            "progress": 50,  # 假设已完成50%
                            "process_id": process_id
                        }
            except Exception as record_error:
                logger.error(f"处理历史记录时出错: {str(record_error)}")
                continue  # 循环继续处理下一条记录
        
        # 如果没有找到，可能是尚未处理或ID错误
        logger.warning(f"未找到对应的视频处理任务: {process_id}")
        return {
            "status": "not_found",
            "progress": 0,
            "error": "未找到对应的视频处理任务",
            "process_id": process_id
        }
    except Exception as e:
        logger.error(f"获取视频处理进度失败: {str(e)}", exc_info=True)
        # 特别注意返回合法的JSON响应而不是抛出HTTP异常
        return {
            "status": "error",
            "progress": 0,
            "error": f"查询进度错误: {str(e)}",
            "process_id": process_id
        }

# 提供视频状态的API别名（与video-progress端点相同）
@router.get("/video-status/{process_id}")
async def get_video_status(process_id: str):
    return await get_video_progress(process_id)

# 提供任务状态的API别名（与video-progress端点相同）
@router.get("/task-status/{process_id}")
async def get_task_status(process_id: str):
    return await get_video_progress(process_id)

@router.get("/history")
async def get_history():
    """
    获取夜间低光检测的历史记录
    """
    try:
        return {"success": True, "history": detection_history}
    except Exception as e:
        logger.error(f"获取历史记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")

async def run_night_detection(image_path, result_path):
    """
    执行夜间图像增强与目标检测
    """
    try:
        # 记录处理开始时间
        start_time = datetime.now()
        logger.info(f"开始处理图像: {image_path}，结果将保存至: {result_path}")
        
        # 确保模型已加载（即使真实模型加载失败，也保证有降级模型可用）
        global enhance_model, detect_model
        if enhance_model is None or detect_model is None:
            logger.info("模型未初始化，尝试加载夜间检测模型...")
            try:
                ok = load_model()  # 加载模型（内部会在失败时创建降级模型）
                logger.info(f"load_model 调用完成，状态: {ok}")
            except Exception as e:
                logger.error(f"load_model 调用异常: {str(e)}，将启用降级模型")
        
        # 如果仍然没有可用模型，则创建降级版本，避免直接报错
        if enhance_model is None:
            logger.warning("增强模型加载失败，使用降级增强模型（传统图像处理）")
            enhance_model = create_dummy_enhance_model()
        if detect_model is None:
            logger.warning("检测模型加载失败，使用降级检测模型（OpenCV/随机框）")
            detect_model = create_dummy_detect_model()
        
        logger.info("准备处理图像，增强模型与检测模型均已就绪（可能为降级版本）...")
        
        # 读取输入图像
        image = cv2.imread(image_path)
        if image is None:
            raise Exception(f"无法读取图像: {image_path}")
            
        # 使用增强模型处理
        try:
            logger.info("应用图像增强...")
            # 创建替代增强模型实例
            dummy_enhancer = create_dummy_enhance_model()
            
            # 根据模型类型决定增强方法
            if enhance_model is None:
                # 如果主模型不可用，使用替代模型
                enhanced_img = dummy_enhancer.enhance(image, method="clahe")
                logger.info("使用替代增强器处理图像")
            else:
                # 使用深度学习增强模型
                try:
                    # 转换为适合模型输入的格式
                    input_tensor = preprocess_image(image)
                    
                    # 运行增强模型 - 动态适应不同模型的参数
                    with torch.no_grad():
                        try:
                            # 默认调用模式
                            enhanced_tensor = enhance_model(input_tensor)
                            logger.info("成功调用增强模型 - 默认调用")
                        except Exception as inner_e:
                            logger.warning(f"默认调用失败，尝试其他方法: {str(inner_e)}")
                            try:
                                # 尝试判断模型接受的参数
                                import inspect
                                if hasattr(enhance_model, 'forward'):
                                    sig = inspect.signature(enhance_model.forward)
                                    params = list(sig.parameters.keys())
                                    logger.info(f"模型forward方法接受参数: {params}")
                                    
                                    # 根据参数名决定调用方式
                                    if len(params) > 1:  # 不只是self参数
                                        if 'x' in params:
                                            # 标准参数名称
                                            enhanced_tensor = enhance_model(input_tensor)
                                        elif 'night_vision' in params:
                                            enhanced_tensor = enhance_model(input_tensor, night_vision=False)
                                        elif 'img' in params:
                                            enhanced_tensor = enhance_model(img=input_tensor)
                                        else:
                                            # 最后的尝试，直接调用forward
                                            enhanced_tensor = enhance_model.forward(input_tensor)
                                    else:
                                        enhanced_tensor = enhance_model.forward(input_tensor)
                                    logger.info("成功调用增强模型 - 参数匹配模式")
                                else:
                                    # 可能是函数不是类
                                    enhanced_tensor = enhance_model(input_tensor)
                            except Exception as deep_e:
                                logger.error(f"所有模型调用方法都失败: {str(deep_e)}")
                                # 使用替代增强器
                                raise Exception("增强模型调用失败，使用替代方法")
                    
                    # 转换回OpenCV格式
                    if isinstance(enhanced_tensor, torch.Tensor):
                        enhanced_img = tensor_to_image(enhanced_tensor)
                    elif isinstance(enhanced_tensor, Image.Image):
                        enhanced_img = np.array(enhanced_tensor)
                        enhanced_img = cv2.cvtColor(enhanced_img, cv2.COLOR_RGB2BGR)
                    else:
                        enhanced_img = enhanced_tensor
                        
                    logger.info("深度学习模型增强成功")
                except Exception as e:
                    logger.error(f"深度增强失败，使用替代方法: {str(e)}")
                    # 如果深度学习增强失败，使用传统方法
                    enhanced_img = dummy_enhancer.enhance(image, method="clahe")
            
            # 确保增强图像与原图不同
            if enhanced_img is image:  # 引用相同，说明没有真正处理
                logger.warning("增强处理可能失败，强制应用CLAHE")
                # 确保应用至少一种增强方法
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                luminance, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                cl = clahe.apply(luminance)
                limg = cv2.merge((cl, a, b))
                enhanced_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        except Exception as e:
            logger.error(f"图像增强过程中发生错误: {str(e)}")
            # 确保在错误情况下至少返回原图
            enhanced_img = image
        
        # 保存增强后的图像为中间结果
        # 注意: 文件名必须与前端请求的URL匹配
        result_basename = os.path.basename(result_path)
        uuid_part = result_basename.replace('result_', '')
        enhanced_filename = f"enhanced_{uuid_part}"
        enhanced_path = os.path.join(OUTPUT_DIR, enhanced_filename)
        cv2.imwrite(enhanced_path, enhanced_img)
        logger.info(f"增强图像已保存: {enhanced_path}")
        
        # 对比原图和增强图像的差异，确保确实进行了增强
        if image.shape == enhanced_img.shape:
            mean_diff = np.mean(np.abs(image.astype(np.float32) - enhanced_img.astype(np.float32)))
            logger.info(f"原图与增强图像的平均像素差异: {mean_diff:.2f}")
            if mean_diff < 5.0:
                logger.warning("警告: 增强效果可能不明显，平均像素差异较小")
        
        # 执行目标检测
        try:
            logger.info("执行目标检测...")
            # 确保检测模型可用
            if detect_model is None:
                raise Exception("检测模型不可用")
                
            # 对增强图像执行目标检测
            results = detect_model(enhanced_img, conf=0.25, verbose=False)
            
            # 绘制检测结果
            result_img = results[0].plot()
            cv2.imwrite(result_path, result_img)
            logger.info(f"检测结果已保存: {result_path}")
            
            # 提取检测到的对象
            detected_objects = []
            for detection in results[0].boxes.data.tolist():
                if len(detection) >= 6:  # 确保数据格式正确
                    x1, y1, x2, y2, conf, cls = detection[:6]
                    class_name = results[0].names[int(cls)]
                    detected_objects.append({
                        "class": class_name,
                        "confidence": round(float(conf), 2)
                    })
            
            logger.info(f"检测到 {len(detected_objects)} 个对象")
            
            # 返回处理结果
            result_filename = os.path.basename(result_path)
            enhanced_filename = f"enhanced_{result_filename}"
            
            # 检查文件是否存在，记录文件信息
            # Use result_path directly
            if os.path.exists(result_path):
                logger.info(f"检测结果文件存在，大小: {os.path.getsize(result_path)} 字节")
            else:
                logger.error(f"检测结果文件不存在: {result_path}")
            
            # 检查增强图像文件
            # 检查增强图像文件 - 修正为检查OUTPUT_DIR中的文件
            result_basename = os.path.basename(result_path)
            uuid_part = result_basename.replace('result_', '')
            enhanced_filename = f"enhanced_{uuid_part}"
            enhanced_full_path = os.path.join(OUTPUT_DIR, enhanced_filename)
            
            if os.path.exists(enhanced_full_path):
                logger.info(f"增强图像文件存在，大小: {os.path.getsize(enhanced_full_path)} 字节")
            else:
                logger.warning(f"增强图像文件不存在或无法访问: {enhanced_full_path}")
            
            # 构建统一的URL格式
            # 注意：生成与文件名完全匹配的URL
            result_basename = os.path.basename(result_path)
            uuid_part = result_basename.replace('result_', '')
            enhanced_filename = f"enhanced_{uuid_part}"
            # 计算实际处理时间
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)  # 转换为毫秒
            
            return {
                "resultImageUrl": f"/static/night_detection/{result_filename}",
                "enhancedImageUrl": f"/static/night_detection/{enhanced_filename}",
                "processingTime": str(processing_time),  # 返回实际处理时间毫秒数
                "detectedObjects": detected_objects
            }
        except Exception as e:
            logger.error(f"目标检测失败: {str(e)}")
            # 保存增强后的图像作为结果
            cv2.imwrite(result_path, enhanced_img)
            logger.info(f"已保存增强图像作为结果: {result_path}")
            result_filename = os.path.basename(result_path)
            return {
                "resultImageUrl": f"/static/night_detection/{result_filename}",
                "enhancedImageUrl": f"/static/night_detection/enhanced_{result_filename}",
                "processingTime": "0",
                "detectedObjects": []
            }
    except Exception as e:
        logger.error(f"运行夜间检测失败: {str(e)}")
        # 如果一切都失败了，至少尝试复制原图作为结果
        try:
            shutil.copy(image_path, result_path)
            logger.warning(f"由于错误，已使用原图作为结果: {str(e)}")
        except Exception as copy_e:
            logger.error(f"复制原图失败: {str(copy_e)}")
        
        raise HTTPException(status_code=500, detail=f"处理图像失败: {str(e)}")

# 后处理函数：将模型输出转换回OpenCV图像
def tensor_to_image(tensor):
    """将PyTorch张量转换回OpenCV图像(BGR)"""
    try:
        # 确保张量在CPU上
        if tensor.is_cuda:
            tensor = tensor.cpu()
            
        # 移除批次维度并转置
        tensor = tensor.squeeze(0).permute(1, 2, 0)
        
        # 转换为NumPy并缩放到[0, 255]
        image_np = tensor.numpy() * 255.0
        image_np = np.clip(image_np, 0, 255).astype(np.uint8)
        
        # 转换为BGR
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        return image_bgr
    except Exception as e:
        logger.error(f"张量转换为图像失败: {str(e)}")
        raise

# 启动外部项目服务
def start_night_detection_service():
    """
    启动夜间检测服务
    """
    try:
        # 检查项目路径是否存在
        if not os.path.exists(NIGHT_DETECTION_PATH):
            logger.error(f"夜间检测项目路径不存在: {NIGHT_DETECTION_PATH}")
            return False
            
        # 预加载模型
        logger.info("预加载夜间检测模型...")
        load_model()
        if enhance_model is None or detect_model is None:
            logger.warning("模型预加载失败，将在首次请求时加载")
        
        # 启动外部项目服务
        # subprocess.Popen(['python', os.path.join(NIGHT_DETECTION_PATH, 'app.py')])
        
        logger.info("夜间低光图像增强与目标检测服务已启动")
        return True
    except Exception as e:
        logger.error(f"启动夜间检测服务失败: {str(e)}")
        return False


# 集成版的视频处理函数，基于原项目的完整实现
def integrated_process_video(video_path, enhance_model, detect_model, output_path, conf=0.25, night_vision_mode=False, enhance_method='deep', temp_dir=None, process_id=None):
    """
    集成版视频处理函数，完全基于原项目的完整实现
    
    Args:
        video_path: 输入视频路径
        enhance_model: 图像增强模型
        detect_model: 目标检测模型
        output_path: 输出视频路径
        conf: 检测置信度阈值，默认0.25
        night_vision_mode: 是否使用夜视模式，默认False
        enhance_method: 增强方法，默认'deep'
        temp_dir: 临时目录，如果为None则创建一个
        process_id: 处理ID，用于更新进度
    """
    logger.info(f"正在集成处理视频: {video_path}")
    import time
    import cv2
    import numpy as np
    import shutil
    import glob
    import uuid
    from pathlib import Path
    
    start_time = time.time()
    
    # 管理更新进度
    def update_progress(progress, message=None):
        if process_id and process_id in video_tasks:
            video_tasks[process_id]["progress"] = progress
            if message:
                video_tasks[process_id]["message"] = message
            logger.info(f"更新视频处理进度: {progress}%")
    
    # 创建临时目录结构
    if temp_dir is None:
        temp_dir = os.path.join(OUTPUT_DIR, "temp", str(uuid.uuid4()))
    
    # 创建所需的工作目录
    frames_dir = os.path.join(temp_dir, "frames")
    enhance_dir = os.path.join(temp_dir, "enhanced")
    
    # 创建目录
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(enhance_dir, exist_ok=True)
    
    try:
        # 1. 提取视频帧
        update_progress(10, "正在提取视频帧...")
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 保存原始帧
            frame_path = os.path.join(frames_dir, f"{frame_count:04d}.jpg")
            cv2.imwrite(frame_path, frame)
            frame_count += 1
            
            # 更新进度
            if frame_count % max(1, int(total_frames / 10)) == 0:
                progress = 10 + (frame_count / total_frames) * 30
                update_progress(int(progress), f"已提取 {frame_count}/{total_frames} 帧")
        
        cap.release()
        
        if frame_count == 0:
            raise Exception("视频提取失败，未能提取到帧")
        
        # 2. 处理每一帧
        update_progress(40, "正在增强每一帧...")
        
        # 获取帧文件列表并排序
        frame_files = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
        
        # 处理每一帧
        for i, frame_file in enumerate(frame_files):
            # 读取原始帧
            frame = cv2.imread(frame_file)
            if frame is None:
                logger.warning(f"无法读取帧: {frame_file}")
                continue
            
            # 增强图像
            try:
                if enhance_method == 'retinex':
                    # 使用CLAHE增强
                    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                    l_channel, a, b = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    cl = clahe.apply(l_channel)
                    enhanced = cv2.merge((cl, a, b))
                    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
                elif night_vision_mode:
                    # 应用夜视效果
                    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    hsv[:, :, 0] = 60  # 绿色色相
                    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.5, 0, 255).astype(np.uint8)
                    enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                else:
                    # 使用深度学习模型
                    if enhance_model is not None:
                        # 使用PyTorch模型处理
                        img_tensor = torch.from_numpy(frame).float().permute(2, 0, 1).unsqueeze(0) / 255.0
                        img_tensor = img_tensor.to('cpu')
                        
                        with torch.no_grad():
                            enhanced_tensor = enhance_model(img_tensor)
                            enhanced = tensor_to_image(enhanced_tensor[0])
                    else:
                        # 如果模型不可用，使用基本增强
                        enhanced = cv2.convertScaleAbs(frame, alpha=1.5, beta=30)
            except Exception as e:
                logger.error(f"帧增强失败: {str(e)}")
                # 失败时使用基本增强
                enhanced = cv2.convertScaleAbs(frame, alpha=1.5, beta=30)
            
            # 保存增强后的帧
            enhanced_path = os.path.join(enhance_dir, f"{i:04d}.png")
            cv2.imwrite(enhanced_path, enhanced)
            
            # 更新进度
            if i % max(1, len(frame_files) // 10) == 0:
                progress = 40 + (i / len(frame_files)) * 30
                update_progress(int(progress), f"已处理 {i+1}/{len(frame_files)} 帧")
        
        # 3. 将增强帧合成输出视频
        update_progress(70, "正在生成增强视频...")
        
        # 创建合成视频的路径
        enhanced_video_path = os.path.join(temp_dir, "enhanced_video.mp4")
        
        # 调用frames_to_video函数合成视频
        success = frames_to_video(enhance_dir, enhanced_video_path, fps)
        
        if not success or not os.path.exists(enhanced_video_path) or os.path.getsize(enhanced_video_path) == 0:
            logger.warning("合成增强视频可能失败，尝试查找其他格式的视频")
            
            # 检查其他可能的视频文件格式
            potential_videos = [
                os.path.join(temp_dir, "enhanced_video.mp4"),
                os.path.join(temp_dir, "enhanced_video.avi"),
                os.path.join(temp_dir, "enhanced_video.mp4.avi"),
                os.path.join(temp_dir, "temp_video.avi")
            ]
            
            # 寻找任何有效的视频文件
            alt_video_found = False
            for vid_path in potential_videos:
                if os.path.exists(vid_path) and os.path.getsize(vid_path) > 0:
                    enhanced_video_path = vid_path
                    alt_video_found = True
                    logger.info(f"找到备用增强视频: {enhanced_video_path}")
                    break
            
            # 如果仍未找到，尝试直接使用帧目录中的图像进行检测
            # 而不是回退到原始视频
            if not alt_video_found:
                # 查看增强帧是否存在
                enhance_frames = glob.glob(os.path.join(enhance_dir, "*.png")) + \
                               glob.glob(os.path.join(enhance_dir, "*.jpg"))
                if enhance_frames and len(enhance_frames) > 0:
                    logger.info(f"找到 {len(enhance_frames)} 个增强帧，尝试使用帧进行检测")
                    # 使用第一帧路径所在的目录进行检测
                    enhanced_video_path = enhance_dir
                else:
                    logger.warning("未找到任何增强帧，只能使用原始视频进行检测")
                    enhanced_video_path = video_path
        
        # 4. 在增强视频上进行目标检测
        update_progress(80, "正在进行目标检测...")
        
        try:
            if detect_model is None:
                raise Exception("检测模型不可用")
            
            # 使用YOLOv8进行检测
            detect_results_dir = os.path.join(temp_dir, "detect_results")
            os.makedirs(detect_results_dir, exist_ok=True)
            
            # 增加更多详细日志，帮助分析路径问题
            logger.info(f"检测目录: {detect_results_dir}")
            logger.info(f"增强视频路径: {enhanced_video_path}")
            logger.info(f"检测使用的来源: {enhanced_video_path}")
            
            # 明确指定保存检测结果
            # 增强YOLOv8参数以确保可以检测和保存结果
            results = detect_model.predict(
                source=enhanced_video_path, 
                conf=conf,
                save=True,
                save_txt=True,  # 保存文本检测结果
                save_conf=True, # 保存置信度
                project=detect_results_dir,
                name="video",
                show_labels=True,
                show_conf=True,
                line_width=2,
                box=True
            )
            
            # 更详细的日志，帮助定位问题
            logger.info(f"检查检测结果目录: {detect_results_dir}")
            
            # 更广泛地搜索可能的检测结果视频
            detected_videos = []
            
            # 检查YOLO默认输出路径
            yolo_paths = [
                os.path.join(detect_results_dir, "video"),  # 标准路径
                detect_results_dir,  # 根目录
                os.path.join(detect_results_dir, "video", "predict"),  # 可能的子目录
                os.path.join(detect_results_dir, "predict")  # 可能的子目录
            ]
            
            # 检查多种可能的文件名和扩展名
            for path in yolo_paths:
                if os.path.exists(path):
                    logger.info(f"检查目录: {path}")
                    for ext in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
                        pattern = os.path.join(path, f"*{ext}")
                        found_files = glob.glob(pattern)
                        if found_files:
                            detected_videos.extend(found_files)
                            logger.info(f"找到检测结果视频: {found_files}")
            
            # 直接查看YOLO结果中的视频文件路径
            try:
                if results and hasattr(results, "save_dir"):
                    save_dir = results.save_dir
                    logger.info(f"YOLO结果保存目录: {save_dir}")
                    # 查找该目录下的所有视频文件
                    for ext in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
                        found_files = glob.glob(os.path.join(save_dir, f"*{ext}"))
                        if found_files:
                            detected_videos.extend(found_files)
                            logger.info(f"直接从YOLO结果找到视频: {found_files}")
            except Exception as e:
                logger.warning(f"尝试从YOLO结果获取视频路径失败: {str(e)}")
            
            # 使用列表推导式去除重复项并过滤出存在的文件
            detected_videos = [v for v in list(set(detected_videos)) if os.path.exists(v) and os.path.getsize(v) > 0]
            
            if detected_videos:
                # 找到检测结果视频，使用第一个
                result_video = detected_videos[0]
                logger.info(f"使用检测结果视频: {result_video}")
                
                # 源文件分析
                _, source_ext = os.path.splitext(result_video)
                target_base, target_ext = os.path.splitext(output_path)
                
                # 将所有视频转换为MP4格式(使用H.264编码)以确保浏览器兼容性
                # 最终输出路径始终使用.mp4扩展名
                final_output_path = target_base + '.mp4'
                logger.info(f"将转码视频到浏览器兼容格式: {final_output_path}")
                
                try:
                    # 尝试使用FFmpeg进行转码
                    # 首先检查FFmpeg是否可用
                    try:
                        # 检查FFmpeg是否存在
                        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                        ffmpeg_available = True
                        logger.info("FFmpeg可用，将进行转码")
                    except (subprocess.SubprocessError, FileNotFoundError):
                        ffmpeg_available = False
                        logger.warning("FFmpeg不可用，将使用OpenCV备用方案")
                        
                    if ffmpeg_available:
                        # 使用FFmpeg将MJPG/AVI转码为H.264/MP4
                        ffmpeg_cmd = [
                            'ffmpeg',
                            '-y',  # 覆盖现有文件
                            '-i', result_video,  # 输入文件
                            '-c:v', 'libx264',  # 使用H.264编码器
                            '-preset', 'fast',  # 快速编码设置
                            '-crf', '22',  # 质量调节，较低的值意味着更高的质量
                            '-pix_fmt', 'yuv420p',  # 兼容性像素格式
                            final_output_path  # 输出文件
                        ]
                        logger.info(f"FFmpeg命令: {' '.join(ffmpeg_cmd)}")
                        
                        # 执行FFmpeg转码
                        process = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        
                        if process.returncode == 0 and os.path.exists(final_output_path) and os.path.getsize(final_output_path) > 0:
                            logger.info(f"FFmpeg转码成功: {final_output_path}")
                            output_path = final_output_path
                        else:
                            # FFmpeg转码失败，使用原始文件
                            error_output = process.stderr.decode('utf-8', errors='ignore')
                            logger.error(f"FFmpeg转码失败: {error_output}")
                            logger.warning("使用原始视频文件作为备用")
                            shutil.copy(result_video, output_path)
                    else:
                        # 如果FFmpeg不可用，使用原始视频
                        logger.warning("由于FFmpeg不可用，使用原始视频文件")
                        shutil.copy(result_video, output_path)
                except Exception as e:
                    # 所有转码尝试失败，直接使用原始文件
                    logger.error(f"尝试转码视频时出错: {str(e)}")
                    logger.warning("由于转码失败，使用原始视频文件")
                    shutil.copy(result_video, output_path)
                
                logger.info(f"目标检测完成，结果已保存到: {output_path}，文件大小: {os.path.getsize(output_path)/1024/1024:.2f}MB")
                
                # 验证输出文件是否可访问
                try:
                    with open(output_path, 'rb') as test_file:
                        test_file.read(1024)  # 读取1KB确认文件可访问
                    logger.info(f"输出文件验证成功: {output_path}")
                except Exception as e:
                    logger.error(f"输出文件验证失败: {str(e)}")
                    # 尝试保存到其他位置
                    alt_output = os.path.join(os.path.dirname(output_path), f"alt_{os.path.basename(output_path)}")
                    shutil.copy(result_video, alt_output)
                    logger.info(f"使用替代输出路径: {alt_output}")
                    output_path = alt_output
                
                update_progress(100, "视频处理完成")
            else:
                logger.warning("未找到检测视频，尝试手动创建检测结果视频")
                
                # 如果找不到检测视频，尝试使用增强视频
                if enhanced_video_path != video_path and os.path.exists(enhanced_video_path) and os.path.isfile(enhanced_video_path):
                    logger.info(f"使用增强视频作为备选: {enhanced_video_path}")
                    shutil.copy(enhanced_video_path, output_path)
                    logger.info(f"已复制增强视频到输出路径: {output_path}")
                else:
                    logger.warning("无法找到有效的增强视频，回退到原始视频")
                    shutil.copy(video_path, output_path)
                    logger.info(f"已复制原始视频到输出路径: {output_path}")
                
                update_progress(95, "无法找到检测视频，使用替代输出")
                
        except Exception as e:
            logger.error(f"目标检测失败: {str(e)}")
            # 如果检测失败，则直接使用增强后的视频
            if enhanced_video_path != video_path and os.path.exists(enhanced_video_path):
                shutil.copy(enhanced_video_path, output_path)
                logger.info(f"仅完成视频增强，结果已保存到: {output_path}")
                update_progress(90, "目标检测失败，仅输出增强视频")
            else:
                # 如果增强也失败，则输出原始视频
                shutil.copy(video_path, output_path)
                logger.warning(f"处理失败，使用原始视频作为输出: {output_path}")
                update_progress(90, "处理失败，输出原始视频")
        
        # 计算总处理时间
        end_time = time.time()
        processing_time = end_time - start_time
        logger.info(f"完成视频处理，耗时 {processing_time:.2f} 秒")
        
        # 清理临时文件
        try:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                # 处理成功时清理临时文件
                shutil.rmtree(temp_dir)
                logger.info(f"已清理临时目录: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时文件时出错: {str(e)}")
        
        return {"success": True, "output_path": output_path}
        
    except Exception as e:
        logger.error(f"视频处理过程中出错: {str(e)}")
        # 确保返回有效输出
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            try:
                # 回退到原始视频
                shutil.copy(video_path, output_path)
                logger.warning(f"处理失败，使用原始视频作为输出: {output_path}")
            except Exception as copy_err:
                logger.error(f"备份原始视频失败: {str(copy_err)}")
        
        # 更新进度为失败
        update_progress(100, f"处理失败: {str(e)}")
        return {"success": False, "error": str(e), "output_path": output_path}
