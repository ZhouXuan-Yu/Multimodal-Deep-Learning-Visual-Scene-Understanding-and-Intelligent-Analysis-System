import os
import cv2
import numpy as np
import json
import time
import glob
import shutil
import logging
import sys
import torch
from pathlib import Path
import matplotlib.pyplot as plt
from tqdm import tqdm

# 导入YOLOv8检测器
from yolo_detector import create_yolov8_detector, detect_with_yolov8

# 导入自定义模块
from hgtmt_manager import HGTMTManager
from visualization_utils import TrackingVisualizer
from create_video_from_frames import create_video_from_frames

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RGBT-Tiny-Integration")

# 添加HGTMT项目到路径
HGTMT_PATH = os.path.join(os.getcwd(), "HGTMT-main", "HGTMT-main")
sys.path.append(HGTMT_PATH)

# 数据集路径
DATASET_PATH = "D:/Desktop/ModelService_graduation-main/RGBT-Tiny/data/RGBT-Tiny"
IMAGES_PATH = os.path.join(DATASET_PATH, "images")
OUTPUT_PATH = os.path.join(os.getcwd(), "output")

# 创建输出目录
os.makedirs(OUTPUT_PATH, exist_ok=True)

# 检查GPU是否可用
def check_cuda():
    print("CUDA是否可用:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("CUDA版本:", torch.version.cuda)
        print("GPU数量:", torch.cuda.device_count())
        print("GPU型号:", torch.cuda.get_device_name(0))
    else:
        print("CUDA不可用，将使用CPU运行")
    print("-----------------------------------")

# 视频处理：自动提取帧
def extract_frames_from_video(video_path, output_folder, prefix="00", start_idx=0):
    """
    从视频中提取帧并保存为图像序列
    video_path: 视频文件路径
    output_folder: 输出文件夹
    prefix: 输出文件夹前缀，00表示可见光，01表示热成像
    start_idx: 起始帧索引
    """
    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)
    subfolder = os.path.join(output_folder, prefix)
    os.makedirs(subfolder, exist_ok=True)
    
    # 打开视频
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        print(f"无法打开视频: {video_path}")
        return False
    
    # 获取视频信息
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    
    print(f"视频信息: {os.path.basename(video_path)}")
    print(f"  - 帧率: {fps} fps")
    print(f"  - 总帧数: {frame_count}")
    print(f"  - 时长: {duration:.2f} 秒")
    
    # 提取帧
    frame_idx = start_idx
    progress_bar = tqdm(total=frame_count, desc=f"提取{prefix}模态帧")
    
    while True:
        ret, frame = video.read()
        if not ret:
            break
            
        # 保存帧
        frame_path = os.path.join(subfolder, f"{frame_idx:05d}.jpg")
        cv2.imwrite(frame_path, frame)
        frame_idx += 1
        progress_bar.update(1)
    
    progress_bar.close()
    video.release()
    
    print(f"已将视频中的 {frame_idx-start_idx} 帧提取到 {subfolder}")
    return True

# 准备双模态视频数据
def prepare_dual_modal_data(visible_video_path, thermal_video_path, sequence_name):
    """
    准备双模态视频数据，将可见光和热成像视频转换为RGBT-Tiny数据集格式
    """
    print(f"\n准备双模态数据: {sequence_name}")
    output_folder = os.path.join(IMAGES_PATH, sequence_name)
    
    # 提取可见光视频帧
    print("\n处理可见光视频...")
    extract_frames_from_video(visible_video_path, output_folder, prefix="00")
    
    # 提取热成像视频帧
    print("\n处理热成像视频...")
    extract_frames_from_video(thermal_video_path, output_folder, prefix="01")
    
    print(f"\n双模态数据准备完成: {sequence_name}")
    return output_folder

# 创建检测器函数
def create_detector():
    """创建目标检测器，优先使用YOLOv8，如果不可用则回退到YOLOv3"""
    # 先尝试创建YOLOv8检测器
    yolov8_detector = create_yolov8_detector()
    if yolov8_detector is not None:
        print("\n成功创建YOLOv8检测器，将使用该检测器进行目标检测")
        return {
            "type": "yolov8",
            "model": yolov8_detector,
            "detect_func": detect_with_yolov8,
            "classes": None  # YOLOv8内部包含类别信息
        }
    
    # 如果YOLOv8初始化失败，回退到YOLOv3
    print("YOLOv8检测器初始化失败，尝试使用YOLOv3...")
    yolov3_detector = create_simple_detector()
    if yolov3_detector is not None:
        print("成功创建YOLOv3检测器，将使用该检测器进行目标检测")
        return {
            "type": "yolov3",
            "model": yolov3_detector,
            "detect_func": detect_with_simple_detector,
            "classes": yolov3_detector.get("classes")
        }
    
    print("错误: 所有检测器初始化均失败")
    return None

# 创建简单的目标检测器作为替代
def create_simple_detector():
    """创建一个简单的检测器。使用YOLOv3"""
    try:
        # 尝试加载模型
        config_path = "data/models/yolov3.cfg"
        weights_path = "data/models/yolov3.weights"
        classes_path = "data/models/coco.names"
        
        if not os.path.exists(config_path) or not os.path.exists(weights_path):
            print(f"错误: 无法找到YOLOv3模型文件")
            print(f"  配置文件: {config_path}")
            print(f"  权重文件: {weights_path}")
            return None
            
        # 加载模型
        net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
        
        # 检查是否有GPU并使用
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            print("YOLOv3将使用CUDA")
        else:
            print("YOLOv3将使用CPU")
        
        # 加载类别
        classes = []
        if os.path.exists(classes_path):
            with open(classes_path, 'r') as f:
                classes = [line.strip() for line in f.readlines()]
        else:
            print(f"警告: 无法找到类别文件 {classes_path}，将使用类别索引")
        
        # 获取输出层名称
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
        
        return {"net": net, "output_layers": output_layers, "classes": classes}
    except Exception as e:
        print(f"创建简单检测器时出错: {str(e)}")
        return None

# 使用简单检测器进行检测
def detect_with_simple_detector(detector, img):
    """
    使用简单的OpenCV检测器检测图像中的目标
    """
    if detector is None:
        return []
        
    try:
        net = detector["net"]
        output_layers = detector["output_layers"]
        classes = detector["classes"]
        
        # 准备图像
        height, width = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/255.0, (416, 416), swapRB=True, crop=False)
        net.setInput(blob)
        
        # 前向传播
        layer_outputs = net.forward(output_layers)
        
        # 初始化结果
        boxes = []
        confidences = []
        class_ids = []
        
        # 解析结果
        for output in layer_outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                # 过滤非常低置信度的检测 - 降低阈值以检测小目标
                if confidence > 0.1:  # 大幅降低阈值以检测小目标和夜间目标
                    # YOLO返回的是中心坐标和宽高
                    # 转换为左上角和右下角坐标
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    # 计算左上角坐标
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, x + w, y + h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # 应用非极大值抑制
        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.3, 0.4)  # 将NMS阈值也调整为0.3
        
        # 打印检测统计信息
        print(f"检测结果统计: 共找到 {len(indices) if len(indices) > 0 else 0} 个目标，置信度阈值 {0.3}")
        if len(indices) > 0:
            for i in indices.flatten():
                print(f"  目标 {i}: 类别 {class_ids[i]}, 置信度 {confidences[i]:.2f}")
        
        # 准备结果
        detections = []
        if len(indices) > 0:
            for i in indices.flatten():
                box = boxes[i]
                confidence = confidences[i]
                class_id = class_ids[i]
                
                # 格式为 [x1, y1, x2, y2, class_id, confidence]
                detections.append(box + [class_id, confidence])
        
        return detections
    except Exception as e:
        logger.error(f"目标检测失败: {str(e)}")
        return []

# 集成HGTMT的跟踪功能
def initialize_hgtmt_tracker():
    """初始化HGTMT跟踪器

    Returns:
        已初始化的跟踪器，如果初始化失败则返回None
    """
    try:
        # 初始化HGTMT管理器
        hgtmt_mgr = HGTMTManager()

        # 检查环境和依赖
        env_ok = hgtmt_mgr.check_environment()
        if not env_ok:
            print("警告: HGTMT环境检查失败，将尝试初始化地程度修复")

            # 尝试增加小目标检测处理补充依赖错误
            print("启用小目标增强检测模式 - 直接返回类型None，使用YOLOv3检测器")
            return None

        # 加载配置
        config = hgtmt_mgr.load_config()
        if not config:
            print("警告: HGTMT配置加载失败，将使用YOLOv3检测器")
            return None

        # 初始化跟踪器
        print("正在初始化HGTMT跟踪器...（这可能需要几分钟时间）")
        tracker = hgtmt_mgr.initialize_tracker()

        if tracker is not None:
            print("成功初始化HGTMT跟踪器！这将显著提高小目标检测效果")
            return tracker
        else:
            print("初始化HGTMT跟踪器失败，将退回到YOLOv3检测器")
            return None
    except Exception as e:
        print(f"HGTMT模块加载失败: {str(e)}")
        print("将退回到YOLOv3检测器")
        return None

# 加载图像对
def load_image_pair(sequence_name, frame_idx):
    # 可见光图像 (00文件夹)
    visible_path = os.path.join(IMAGES_PATH, sequence_name, "00", f"{frame_idx:05d}.jpg")
    # 热成像图像 (01文件夹)
    thermal_path = os.path.join(IMAGES_PATH, sequence_name, "01", f"{frame_idx:05d}.jpg")
    
    if not os.path.exists(visible_path) or not os.path.exists(thermal_path):
        print(f"找不到图像: {visible_path} 或 {thermal_path}")
        return None, None
    
    visible_img = cv2.imread(visible_path)
    thermal_img = cv2.imread(thermal_path)
    
    # 转换BGR到RGB格式用于显示
    if visible_img is not None:
        visible_img = cv2.cvtColor(visible_img, cv2.COLOR_BGR2RGB)
    if thermal_img is not None:
        thermal_img = cv2.cvtColor(thermal_img, cv2.COLOR_BGR2RGB)
    
    return visible_img, thermal_img

# 处理视频序列并应用跟踪
def process_video_sequence(sequence_name, start_frame=0, end_frame=None, use_tracking=True, use_enhancement=True):
    """处理视频序列"""
    sequence_dir = os.path.join(IMAGES_PATH, sequence_name)
    if not os.path.exists(sequence_dir):
        print(f"错误: 序列 {sequence_name} 不存在")
        return
        
    visible_dir = os.path.join(sequence_dir, "00")
    frame_files = sorted([f for f in os.listdir(visible_dir) if f.endswith(".jpg")])
    
    if not frame_files:
        print(f"错误: 序列 {sequence_name} 中没有找到图像文件")
        return
        
    if end_frame is None:
        end_frame = len(frame_files)
    else:
        end_frame = min(end_frame, len(frame_files))
        
    if start_frame >= end_frame:
        print(f"错误: 开始帧 ({start_frame}) 必须小于结束帧 ({end_frame})")
        return
    
    frame_indices = [int(f.split(".")[0]) for f in frame_files]
    
    # 初始化跟踪器或检测器
    tracker = None
    detector_info = None
    visualizer = TrackingVisualizer()
    
    if use_tracking:
        print("尝试初始化HGTMT跟踪器...")
        tracker = initialize_hgtmt_tracker()
    
    if tracker is None:
        print("HGTMT跟踪器不可用，将使用检测器代替")
        detector_info = create_detector()
        if detector_info is None:
            print("警告: 所有检测器都不可用，将只显示原始图像")
    
    # 确保输出目录存在
    output_dir = os.path.join(OUTPUT_PATH, sequence_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # 处理每一帧
    progress_bar = tqdm(range(start_frame, end_frame), desc="处理帧")
    for i in progress_bar:
        frame_idx = frame_indices[i]
        
        # 加载图像对
        visible_img, thermal_img = load_image_pair(sequence_name, frame_idx)
        if visible_img is None or thermal_img is None:
            print(f"警告: 无法加载帧 {frame_idx}")
            continue
            
        # 创建结果副本
        visible_result = visible_img.copy()
        thermal_result = thermal_img.copy()
        
        # 初始化检测/跟踪结果
        visible_tracks = None
        thermal_tracks = None
        visible_detections = None
        thermal_detections = None
        
        # 热成像图像处理
        # 保存原始热成像图像和可能的增强版本
        
        # ***** 原始图像处理 *****
        # 只进行基本的归一化，不做任何额外增强处理
        thermal_img_orig = thermal_img.copy()  # 保存原始副本
        # 基本归一化处理(这是必需的最小处理)
        thermal_img_orig = cv2.normalize(thermal_img_orig, None, 0, 255, cv2.NORM_MINMAX)
        
        # ***** 增强图像处理 *****
        # 总是创建一个增强版本，以便比较效果
        thermal_img_enhanced = thermal_img.copy()  # 为增强创建单独的副本
        thermal_img_enhanced = cv2.normalize(thermal_img_enhanced, None, 0, 255, cv2.NORM_MINMAX)
        
        # CLAHE增强
        gray = cv2.cvtColor(thermal_img_enhanced, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced_gray = clahe.apply(gray)
        thermal_img_enhanced = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
        
        # 对比度和亮度增强
        alpha = 1.5  # 对比度因子
        beta = 10    # 亮度因子
        thermal_img_enhanced = cv2.convertScaleAbs(thermal_img_enhanced, alpha=alpha, beta=beta)
        
        if use_enhancement:
            print("应用热成像增强处理 - 使用增强版本进行检测")
        else:
            print("仅应用基本归一化，不使用增强处理 - 使用原始版本进行检测")
        
        if tracker is not None:
            try:
                # 使用HGTMT跟踪器
                results = tracker.track(visible_img, thermal_img_enhanced, frame_idx)
                if results:
                    visible_tracks = results.get('visible_tracks', [])
                    thermal_tracks = results.get('thermal_tracks', [])
            except Exception as e:
                print(f"跟踪失败: {str(e)}")
        elif detector_info is not None:
            # 使用检测器
            detect_function = detector_info["detect_func"]
            model = detector_info["model"]
            detector_type = detector_info["type"]
            
            print(f"使用{detector_type}检测器进行检测...")
            
            # 对原图进行检测
            visible_detections = detect_function(model, visible_img)
            
            # 分别对原始版本和增强版本进行检测
            if not use_enhancement:
                # 对原始热成像进行检测(只有归一化处理)
                thermal_orig_detections = detect_function(model, thermal_img_orig)
                # 对增强版本进行检测(用于比较)
                thermal_enhanced_detections = detect_function(model, thermal_img_enhanced)
                # 使用原始热成像检测结果
                thermal_detections = thermal_orig_detections
                print(f"可见光检测到 {len(visible_detections)} 个目标")
                print(f"原始热成像检测到 {len(thermal_orig_detections)} 个目标")
                print(f"增强热成像检测到 {len(thermal_enhanced_detections)} 个目标")
            else:
                # 只对增强版本进行检测
                thermal_detections = detect_function(model, thermal_img_enhanced)
                print(f"可见光检测到 {len(visible_detections)} 个目标，热成像检测到 {len(thermal_detections)} 个目标")
        
        # 创建可视化结果
        if visible_tracks or thermal_tracks:
            # 绘制跟踪结果
            visible_img = visualizer.draw_tracks(visible_img, visible_tracks) if visible_tracks else visible_img
            thermal_img_enhanced = visualizer.draw_tracks(thermal_img_enhanced, thermal_tracks) if thermal_tracks else thermal_img_enhanced
        elif visible_detections is not None or thermal_detections is not None:
            # 绘制检测结果
            visible_threshold = 0.25  # 可见光检测的置信度阈值
            thermal_threshold = 0.1   # 热成像使用更低的阈值显示小目标
            
            visible_img = visualizer.draw_detections(
                visible_img, 
                visible_detections, 
                confidence_threshold=visible_threshold,
                classes=detector_info.get("classes"),
                draw_low_confidence=True  # 显示低置信度目标
            )
            thermal_img_enhanced = visualizer.draw_detections(
                thermal_img_enhanced, 
                thermal_detections, 
                confidence_threshold=thermal_threshold,
                classes=detector_info.get("classes"),
                draw_low_confidence=True  # 显示低置信度目标
            )
        
        # 创建组合双模态可视化结果
        combined_img = visualizer.create_side_by_side_view(
            visible_img, 
            thermal_img_enhanced,
            title_left="Visible",  # 使用英文标题避免编码问题
            title_right="Thermal"  # 使用英文标题避免编码问题
        )
        
        # 保存结果 - 包括合并视图和单独的可见光/热成像视图
        output_filename = f"{frame_idx:05d}_result.jpg"
        
        # 保存标准增强版本的检测结果
        # 首先在增强后的热成像上绘制检测框
        thermal_enhanced_with_det = visualizer.draw_detections(
            thermal_img_enhanced.copy(), 
            thermal_detections if use_enhancement else thermal_enhanced_detections, 
            confidence_threshold=0.1,
            classes=detector_info.get("classes"),
            draw_low_confidence=True
        )
        
        # 创建并保存增强版的并排视图
        enhanced_combined = visualizer.create_side_by_side_view(
            visible_img, 
            thermal_enhanced_with_det,
            title_left="Visible",
            title_right="Thermal (Enhanced)"  
        )
        
        # 保存增强版的检测结果
        visualizer.save_visualization(enhanced_combined, output_dir, output_filename, 
                                    save_separate=True, 
                                    visible_img=visible_img, 
                                    thermal_img=thermal_enhanced_with_det)
                                    
        # 如果不使用增强，额外保存原始版本的图像
        if not use_enhancement and visible_detections is not None:
            # 在原始热成像上绘制检测框
            thermal_orig_with_det = visualizer.draw_detections(
                thermal_img_orig.copy(), 
                thermal_orig_detections,  # 使用原始热成像的检测结果 
                confidence_threshold=0.1,  # 降低阈值以显示更多小目标
                classes=detector_info.get("classes"),
                draw_low_confidence=True
            )
            
            # 创建原始图像的并排视图
            orig_combined = visualizer.create_side_by_side_view(
                visible_img, 
                thermal_orig_with_det,
                title_left="Visible",
                title_right="Thermal (Original)"  
            )
            
            # 直接保存原始版在主输出目录中
            # 使用标记清晰的文件名
            cv2.imwrite(os.path.join(output_dir, f"{frame_idx:05d}_original_result.jpg"), orig_combined)
            cv2.imwrite(os.path.join(output_dir, f"{frame_idx:05d}_original_thermal.jpg"), thermal_orig_with_det)
            
            # 为了兼容现有代码，也保存一份到original文件夹
            orig_output_dir = os.path.join(output_dir, "original")
            os.makedirs(orig_output_dir, exist_ok=True)
            cv2.imwrite(os.path.join(orig_output_dir, f"{frame_idx:05d}_orig.jpg"), orig_combined)
            cv2.imwrite(os.path.join(orig_output_dir, f"{frame_idx:05d}_visible.jpg"), visible_img)
            cv2.imwrite(os.path.join(orig_output_dir, f"{frame_idx:05d}_thermal.jpg"), thermal_orig_with_det)
        
    # 将处理后的帧合成为视频
    try:
        # 1. 生成合并结果视频
        video_path = os.path.join(output_dir, f"{sequence_name}_result.mp4")
        print(f"生成合并视频...")
        create_video_from_frames(output_dir, video_path, file_pattern="*_result.jpg")
        print(f"合并视频已生成: {video_path}")
        
        # 2. 生成可见光独立视频
        visible_video_path = os.path.join(output_dir, f"{sequence_name}_visible.mp4")
        print(f"生成可见光视频...")
        create_video_from_frames(output_dir, visible_video_path, file_pattern="*_visible.jpg")
        print(f"可见光视频已生成: {visible_video_path}")
        
        # 3. 生成热成像独立视频
        thermal_video_path = os.path.join(output_dir, f"{sequence_name}_thermal.mp4")
        print(f"生成热成像视频...")
        create_video_from_frames(output_dir, thermal_video_path, file_pattern="*_thermal.jpg")
        print(f"热成像视频已生成: {thermal_video_path}")
        
        # 4. 如果不使用增强，生成原始图像视频
        if not use_enhancement:
            # 直接从主输出目录生成原始视频
            # 原始合并视频
            orig_video_path = os.path.join(output_dir, f"{sequence_name}_original_result.mp4")
            print(f"生成原始合并视频...")
            create_video_from_frames(output_dir, orig_video_path, file_pattern="*_original_result.jpg")
            print(f"原始合并视频已生成: {orig_video_path}")
            
            # 原始热成像视频
            orig_thermal_path = os.path.join(output_dir, f"{sequence_name}_original_thermal.mp4")
            print(f"生成原始热成像视频...")
            create_video_from_frames(output_dir, orig_thermal_path, file_pattern="*_original_thermal.jpg")
            print(f"原始热成像视频已生成: {orig_thermal_path}")
            
            # 作为备用，从原始子目录也生成一份同样的视频
            orig_dir = os.path.join(output_dir, "original")
            if os.path.exists(orig_dir) and os.listdir(orig_dir):
                # 也在子目录生成一份视频
                sub_orig_video_path = os.path.join(output_dir, f"{sequence_name}_subdir_orig_result.mp4")
                create_video_from_frames(orig_dir, sub_orig_video_path, file_pattern="*_orig.jpg")
        
        print(f"所有视频生成完成!")
    except Exception as e:
        print(f"视频合成失败: {str(e)}")
    
    print(f"处理完成! 结果保存在 {output_dir}")
    
    # 尝试显示最后一帧的结果
    try:
        last_output = os.path.join(output_dir, f"{frame_idx:05d}_result.jpg")
        if os.path.exists(last_output):
            result_img = cv2.imread(last_output)
            plt.figure(figsize=(12, 8))
            plt.imshow(cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB))
            plt.axis('off')
            plt.title(f"序列 {sequence_name} 的处理结果")
            plt.show()
    except Exception as e:
        print(f"显示结果图像失败: {str(e)}")

# 测试自定义视频的入口
def process_custom_videos():
    """
    处理用户的自定义视频
    """
    print("\n=== 自定义视频处理 ===\n")
    
    # 获取用户输入
    print("请提供视频路径信息:")
    visible_video = input("可见光视频路径 (必须): ")
    thermal_video = input("热成像视频路径 (必须): ")
    sequence_name = input("序列名称 (默认为 'custom_video'): ") or "custom_video"
    
    # 验证输入
    if not os.path.exists(visible_video):
        print(f"错误: 可见光视频不存在: {visible_video}")
        return
    
    if not os.path.exists(thermal_video):
        print(f"错误: 热成像视频不存在: {thermal_video}")
        return
    
    # 准备数据
    prepare_dual_modal_data(visible_video, thermal_video, sequence_name)
    
    # 询问用户是否应用跟踪
    use_tracking = input("是否应用HGTMT跟踪功能? (y/n, 默认为y): ").lower() != 'n'
    
    # 询问用户是否应用图像增强
    use_enhancement = input("是否应用热成像增强预处理? (y/n, 默认为y): ").lower() != 'n'
    if not use_enhancement:
        print("将直接检测原始热成像图像，不进行增强处理")
    
    # 处理视频
    output_dir = os.path.join(OUTPUT_PATH, sequence_name)
    process_video_sequence(sequence_name, use_tracking=use_tracking, use_enhancement=use_enhancement)
    
    # 确保合成视频 - 对于自定义视频额外检查
    result_files = [f for f in os.listdir(output_dir) if f.endswith('_result.jpg')]
    if result_files:
        try:
            video_path = os.path.join(output_dir, f"{sequence_name}_result.mp4")
            print(f"\n正在生成最终视频...")
            success = create_video_from_frames(output_dir, video_path)
            if success:
                print(f"\n视频生成成功: {video_path}")
            else:
                print(f"\n视频生成失败，请查看上方错误信息")
        except Exception as e:
            print(f"\n视频生成错误: {str(e)}")
    else:
        print(f"\n未找到任何处理结果图像，无法生成视频")
    
    print(f"\n处理完成! 结果保存在 {output_dir}")

# 主函数
def main():
    print("\n=== RGBT-Tiny + HGTMT 集成处理系统 ===\n")
    check_cuda()
    
    # 检查并下载YOLOv3模型文件（如果需要）
    yolo_files = [
        ("yolov3.cfg", "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg"),
        ("coco.names", "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names")
    ]
    
    for file_name, url in yolo_files:
        file_path = os.path.join(os.getcwd(), file_name)
        if not os.path.exists(file_path):
            try:
                print(f"下载 {file_name}...")
                import urllib.request
                urllib.request.urlretrieve(url, file_path)
                print(f"成功下载 {file_name}")
            except Exception as e:
                print(f"下载 {file_name} 失败: {str(e)}")
    
    # 检查权重文件，但不自动下载（太大了）
    weights_file = os.path.join(os.getcwd(), "yolov3.weights")
    if not os.path.exists(weights_file):
        print("注意: YOLOv3权重文件不存在。如需目标检测功能，请从以下链接手动下载:")
        print("https://pjreddie.com/media/files/yolov3.weights")
    
    # 检查HGTMT依赖项
    try:
        hgtmt_mgr = HGTMTManager()
        hgtmt_mgr.check_environment()
    except Exception as e:
        print(f"HGTMT环境检查失败: {str(e)}")
    
    # 主菜单循环
    while True:
        print("\n请选择功能:")
        print("1. 处理自定义视频 (需要可见光和热成像双模态视频)")
        print("2. 显示样例序列 (使用RGBT-Tiny数据集)")
        print("3. 模型管理")
        print("4. 退出")
        
        try:
            choice = input("\n请选择 (1-4): ")
            
            if choice == '1':
                process_custom_videos()
                
            elif choice == '2':
                # 列出所有序列
                sequences = []
                if os.path.exists(IMAGES_PATH):
                    sequences = sorted([d for d in os.listdir(IMAGES_PATH) 
                                    if os.path.isdir(os.path.join(IMAGES_PATH, d))])
                
                if not sequences:
                    print("未找到样例序列，请确保RGBT-Tiny数据集已下载")
                    continue
                    
                print(f"\n可用序列 ({len(sequences)} 个):")
                for i, seq in enumerate(sequences[:10]):
                    print(f"{i+1}. {seq}")
                if len(sequences) > 10:
                    print(f"... 以及 {len(sequences) - 10} 个更多序列")
                
                seq_idx = input("\n请选择序列编号 (或直接输入序列名称): ")
                
                try:
                    if seq_idx.isdigit() and 1 <= int(seq_idx) <= len(sequences):
                        sequence_name = sequences[int(seq_idx) - 1]
                    else:
                        sequence_name = seq_idx
                    
                    if sequence_name not in sequences:
                        print(f"序列 '{sequence_name}' 不存在")
                        continue
                    
                    start_frame = int(input("起始帧 (默认为0): ") or "0")
                    end_frame = input("结束帧 (默认为全部): ")
                    end_frame = int(end_frame) if end_frame else None
                    
                    use_tracking = input("是否应用HGTMT跟踪? (y/n, 默认为y): ").lower() != 'n'
                    
                    process_video_sequence(sequence_name, start_frame, end_frame, use_tracking)
                except ValueError:
                    print("输入无效，请输入有效的数字")
            
            elif choice == '3':
                # 模型管理功能
                manage_models()
                
            elif choice == '4':
                print("退出程序")
                return  # 使用return而不是break以避免键盘中断错误
            else:
                print("无效选择，请重试")
        except Exception as e:
            print(f"发生错误: {str(e)}")
            logger.error(f"程序执行错误: {str(e)}")

# 模型管理功能
def manage_models():
    """模型管理功能，用于检查、下载和管理HGTMT相关模型"""
    print("\n=== 模型管理 ===")
    
    # 初始化HGTMT管理器
    hgtmt_mgr = HGTMTManager()
    
    while True:
        print("\n1. 检查HGTMT环境")
        print("2. 下载YOLOv3权重文件")
        print("3. 返回主菜单")
        
        choice = input("\n请选择操作 (1-3): ")
        
        if choice == '1':
            # 检查HGTMT环境
            print("\n正在检查HGTMT环境...")
            hgtmt_mgr.check_environment()
            
            # 检查HGTMT配置
            config = hgtmt_mgr.load_config()
            if config:
                print("HGTMT配置加载成功")
                print("\n配置信息:")
                print(f"  - 跟踪器名称: {config['tracktor']['name']}")
                print(f"  - 跟踪阈值: {config['tracktor']['tracker']['track_thresh']}")
                print(f"  - 匹配阈值: {config['tracktor']['tracker']['match_thresh']}")
            else:
                print("HGTMT配置加载失败")
            
        elif choice == '2':
            # 下载YOLOv3权重文件
            weights_file = os.path.join(os.getcwd(), "yolov3.weights")
            if os.path.exists(weights_file):
                print(f"YOLOv3权重文件已存在: {weights_file}")
                overwrite = input("是否重新下载? (y/n): ").lower() == 'y'
                if not overwrite:
                    continue
            
            print("\nYOLOv3权重文件大小约为 236MB，请确保网络连接稳定")
            confirm = input("是否继续下载? (y/n): ").lower()
            
            if confirm == 'y':
                try:
                    yolo_url = "https://pjreddie.com/media/files/yolov3.weights"
                    print(f"开始下载YOLOv3权重文件...")
                    
                    import urllib.request
                    from tqdm import tqdm
                    
                    class DownloadProgressBar(tqdm):
                        def update_to(self, b=1, bsize=1, tsize=None):
                            if tsize is not None:
                                self.total = tsize
                            self.update(b * bsize - self.n)
                    
                    with DownloadProgressBar(unit='B', unit_scale=True,
                                          miniters=1, desc="YOLOv3权重") as t:
                        urllib.request.urlretrieve(yolo_url, weights_file, 
                                              reporthook=t.update_to)
                    
                    print(f"YOLOv3权重文件下载完成: {weights_file}")
                except Exception as e:
                    print(f"下载失败: {str(e)}")
                    print("请从以下链接手动下载YOLOv3权重文件:")
                    print("https://pjreddie.com/media/files/yolov3.weights")
            else:
                print("已取消下载")
                
        elif choice == '3':
            # 返回主菜单
            return
        
        else:
            print("无效选择，请重试")

if __name__ == "__main__":
    main()
