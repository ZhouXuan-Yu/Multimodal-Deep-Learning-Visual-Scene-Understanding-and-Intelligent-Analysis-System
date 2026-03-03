from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, FileResponse
import os
import sys
import re
import cv2
import uuid
import json
import math
import shutil
import logging
import datetime

# 导入邮件通知模块
from app.utils.email_notifier import email_notifier

# 设置日志
logger = logging.getLogger(__name__)

# 获取项目基础路径
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# 创建路由器
router = APIRouter(
    # 注意：不要在这里定义prefix，它将在main.py中添加
    # prefix="/api/plate-monitoring",
    tags=["车牌监控"],
    responses={404: {"description": "Not found"}},
)

# 设置文件目录 - 使用ModelService的静态和上传目录结构
STATIC_DIR = os.path.join(parent_dir, "static")
UPLOAD_DIR = os.path.join(parent_dir, "uploads")
MONITORING_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "plate_monitoring")
MONITORING_OUTPUT_DIR = os.path.join(STATIC_DIR, "plate_monitoring")
MONITORING_VIDEO_DIR = os.path.join(MONITORING_OUTPUT_DIR, "videos")
MONITORING_FRAMES_DIR = os.path.join(MONITORING_OUTPUT_DIR, "frames")

# 确保目录存在
os.makedirs(MONITORING_UPLOAD_DIR, exist_ok=True)
os.makedirs(MONITORING_OUTPUT_DIR, exist_ok=True)
os.makedirs(MONITORING_VIDEO_DIR, exist_ok=True)
os.makedirs(MONITORING_FRAMES_DIR, exist_ok=True)

# 目标车牌信息
target_plate_info = {
    'plate_no': None,
    'source': None,
    'timestamp': None,
    'image_path': None
}

# 视频处理状态
video_processing_status = {}

# 从匹配的帧创建视频
def create_video_from_matches(matches, output_path, fps=5):
    """
    从匹配的帧创建视频
    Args:
        matches: 包含frame_path键的字典列表
        output_path: 输出视频路径
        fps: 帧率
    Returns:
        str/bool: 成功返回视频路径，失败返回False
    """
    try:
        if not matches or len(matches) == 0:
            logger.warning("没有匹配的帧可以创建视频")
            return False
            
        # 读取第一帧来获取尺寸信息
        first_frame_path = matches[0].get('frame_path')
        if not first_frame_path or not os.path.exists(first_frame_path):
            logger.warning(f"第一帧不存在: {first_frame_path}")
            return False
            
        first_frame = cv2.imread(first_frame_path)
        if first_frame is None:
            logger.warning(f"无法读取第一帧: {first_frame_path}")
            return False
            
        height, width, _ = first_frame.shape
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 使用比较兼容的视频编码器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not video_writer.isOpened():
            logger.error(f"无法打开视频写入器: {output_path}")
            return False
        
        # 按帧号排序匹配结果
        sorted_matches = sorted(matches, key=lambda x: x.get('frame_number', 0))
        
        # 写入每一帧
        frame_count = 0
        for match in sorted_matches:
            frame_path = match.get('frame_path')
            if not frame_path or not os.path.exists(frame_path):
                logger.warning(f"帧不存在: {frame_path}")
                continue
            
            frame = cv2.imread(frame_path)
            if frame is None:
                logger.warning(f"无法读取帧: {frame_path}")
                continue
            
            # 在帧上绘制识别结果
            if 'plate_number' in match:
                cv2.putText(frame, match['plate_number'], (10, 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            if 'frame_number' in match:
                cv2.putText(frame, f"Frame: {match['frame_number']}", (10, 60), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 写入帧
            video_writer.write(frame)
            frame_count += 1
            
        video_writer.release()
        
        if frame_count == 0:
            logger.warning("没有写入任何帧")
            return False
            
        logger.info(f"成功创建视频，包含 {frame_count} 帧: {output_path}")
        return output_path
            
    except Exception as e:
        logger.error(f"创建视频失败: {str(e)}")
        return False

# API端点：上传车牌图片进行识别
@router.post("/upload-image")
async def upload_image_for_recognition(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """上传图片进行车牌识别，识别所有车牌，供用户选择目标车牌"""
    try:
        # 生成唯一文件名
        original_filename = file.filename
        file_ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(MONITORING_UPLOAD_DIR, unique_filename)
        
        # 保存上传的文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 导入车牌识别相关模块
        from app.services.plate_recognition.recognizer.car_rec import get_color_and_score
        from app.services.plate_recognition.service_manager import PlateRecognitionServiceManager
        import torch
        import cv2
        
        # 读取图像
        img = cv2.imread(file_path)
        if img is None:
            raise HTTPException(status_code=400, detail="无法读取上传的图像")
        
        # 创建服务管理器并初始化
        service_manager = PlateRecognitionServiceManager()
        init_result = service_manager.init_service()
        
        if not init_result.get('success', False):
            logger.error(f"服务初始化失败: {init_result}")
            raise HTTPException(status_code=500, detail=f"车牌识别服务初始化失败: {init_result.get('message', '')}")                
        
        # 调用服务识别车牌
        recognition_result = service_manager.recognize_image(img)
        logger.info(f"原始识别结果: {recognition_result}")
        
        # 分析结果
        if not recognition_result.get('success', False):
            return JSONResponse(content={
                "message": recognition_result.get('message', '未识别到车牌'),
                "plates": [],
                "originalImage": file_path
            })
        
        # 获取识别的车牌信息
        plates_data = recognition_result.get('plates', [])
        
        # 获取车辆颜色识别模型
        service_manager = PlateRecognitionServiceManager()
        # 确保模型已加载
        if not service_manager.model_loaded:
            service_manager.init_service()
        # 从模型字典中获取车辆识别模型
        car_rec_model = service_manager.models.get('car_rec')
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 处理每个识别出的车牌
        plates = []
        for plate_data in plates_data:
            # 裁剪图片车辆部分
            box = plate_data.get('box', [0, 0, 100, 30])
            x1, y1, x2, y2 = max(0, box[0]), max(0, box[1]), min(img.shape[1], box[2]), min(img.shape[0], box[3])
            car_roi = img[y1:y2, x1:x2] if y2 > y1 and x2 > x1 else img
            
            # 装配视频车牌识别服务
            try:
                car_color, color_conf = get_color_and_score(car_rec_model, car_roi, device)
            except Exception as e:
                print(f"车辆颜色识别错误: {str(e)}")
                car_color = ""  # 使用空字符串而不是未知
                color_conf = 0.0
            
            # 确保使用前端期望的字段名称，并且不使用"未知"作为默认值
            plates.append({
                "plate_no": plate_data.get('plate_no', ''),
                "confidence": plate_data.get('confidence', 0.0),
                "box": plate_data.get('box', [0, 0, 0, 0]),
                "color": plate_data.get('plate_color', plate_data.get('color', '')),  # 车牌颜色字段改为"color"
                "car_color": car_color if car_color != "未知" else "",
                "color_confidence": color_conf,
                "plate_type": plate_data.get('plate_type', '')  # 增加车牌类型信息
            })
        
        # 创建结果
        result = {
            "success": True,
            "message": "识别成功",
            "plates": plates,  # 使用包含车辆颜色信息的plates对象
            "visualized_image": recognition_result.get('visualized_image', file_path)
        }
        
        # 输出所有车牌的颜色信息详情用于调试
        for i, plate in enumerate(plates):
            logger.info(f"车牌 #{i+1} 详情: 车牌号={plate['plate_no']}, 车牌颜色={plate['color']}, 车辆颜色={plate.get('car_color', '未知')}")
        logger.info(f"最终响应数据: {result}")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"车牌图片处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"车牌图片处理失败: {str(e)}")

# API端点：设置目标车牌
@router.post("/set-target-plate")
async def set_target_plate(
    plate_number: str = Form(...),
    plate_color: str = Form(None),
    image_path: str = Form(None)
):
    """设置目标车牌信息，后续监控将针对该车牌进行比对"""
    global target_plate_info
    
    # 更新目标车牌信息
    target_plate_info = {
        'plate_no': plate_number,
        'color': plate_color,
        'source': 'user_set',
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'image_path': image_path
    }
    
    logger.info(f"目标车牌已设置为: {plate_number}, 颜色: {plate_color}")
    
    # 记录目标车牌设置信息，但不立即发送报警邮件
    # 报警邮件将在视频处理完成后发送
    logger.info(f"目标车牌已设置，将在视频处理完成后发送报警邮件: {plate_number}")
    
    
    return JSONResponse(content={
        "status": "success", 
        "message": "目标车牌设置成功", 
        "target_plate": target_plate_info
    })

# API端点：上传视频进行分析
@router.post("/upload-video")
async def upload_video_for_monitoring(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """上传视频进行监控分析，检测是否包含目标车牌"""
    try:
        # 检查是否已设置目标车牌
        if not target_plate_info.get('plate_no'):
            raise HTTPException(status_code=400, detail="请先设置目标车牌")
        
        # 生成唯一标识符
        process_id = str(uuid.uuid4())
        original_filename = file.filename
        file_ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{process_id}{file_ext}"
        file_path = os.path.join(MONITORING_UPLOAD_DIR, unique_filename)
        
        # 保存上传的文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 设置初始处理状态
        video_processing_status[process_id] = {
            "status": "processing",
            "progress": 0,
            "message": "正在准备处理视频",
            "file_path": file_path,
            "target_plate": target_plate_info['plate_no'],
            "upload_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "matches": []
        }
        
        # 启动后台处理
        background_tasks.add_task(
            process_video,
            process_id,
            file_path,
            target_plate_info['plate_no']
        )
        
        return JSONResponse(content={
            "status": "success",
            "message": "视频上传成功，开始处理",
            "process_id": process_id,
            "original_filename": original_filename
        })
    except Exception as e:
        logger.error(f"视频上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"视频上传失败: {str(e)}")

# 修复中文显示问题的工具函数
def ensure_utf8_encoding(text):
    """确保文本内容使用UTF-8编码，对中文字符特别重要
    
    Args:
        text: 需要处理的文本
        
    Returns:
        处理后的UTF-8编码文本
    """
    # 如果是空值或非字符串，直接返回
    if text is None or not isinstance(text, str):
        return text
        
    try:
        # 如果含有问号，可能是错误编码导致的中文显示问题
        if '?' in text:
            # 根据常见车牌来检测可能的省份原始字符
            common_provinces = {
                '京': 'A', '津': 'B', '沪': 'C', '渝': 'D', '冀': 'E', '陕': 'F',
                '粤': 'G', '贵': 'H', '琼': 'I', '豫': 'J', '吉': 'K', '苏': 'L',
                '鄂': 'M', '浙': 'N', '闽': 'O', '赣': 'P', '鲁': 'Q', '湘': 'R',
                '皖': 'S', '川': 'T', '蒙': 'U', '桂': 'V', '藏': 'W', '宁': 'X',
                '新': 'Y', '襄': 'Z'
            }
            
            # 如果第一个字符是问号且第二个是字母
            if text.startswith('?') and len(text) > 1 and text[1].isalpha():
                # 根据第二个字符找到可能的省份
                second_char = text[1].upper()
                for province, code in common_provinces.items():
                    if code == second_char:
                        # 替换第一个问号为可能的省份中文
                        logger.info(f"修复可能的车牌编码问题: {text} -> {province}{text[1:]}")
                        return f"{province}{text[1:]}"
                
            # 如果只是包含问号，尝试修复中文显示问题
            for province, code in common_provinces.items():
                # 尝试不同的替换方式
                if f"?{code}" in text:
                    fixed_text = text.replace(f"?{code}", f"{province}{code}")
                    logger.info(f"修复车牌编码: {text} -> {fixed_text}")
                    return fixed_text
        
        # 直接处理字符串
        if isinstance(text, str):
            # 替换常见编码问题字符
            char_map = {
                '\ufffd': '',  # 替换Unicode替代字符
                '?': '',      # 移除单独的问号
            }
            
            # 应用字符映射
            for bad_char, replacement in char_map.items():
                if bad_char in text:
                    text = text.replace(bad_char, replacement)
            
            # 纯数字和字母的车牌有可能是非中国车牌
            if text.isalnum() and len(text) >= 5:
                return text.strip()
                
            # 对于包含字母的车牌号，考虑可能是中国车牌
            if any(c.isalpha() for c in text) and len(text) >= 5:
                # 检查是否符合中国车牌格式
                common_plate_patterns = ["[\u4e00-\u9fa5][A-Z]"]
                for pattern in common_plate_patterns:
                    if re.search(pattern, text):
                        return text.strip()
                
            return text.strip()
            
        # 如果是字节类型，尝试多种解码方式
        if isinstance(text, bytes):
            encodings = ['utf-8', 'gbk', 'gb18030', 'gb2312', 'big5']
            for encoding in encodings:
                try:
                    return text.decode(encoding).strip()
                except UnicodeDecodeError:
                    continue
    except Exception as e:
        logger.error(f"处理文本编码时出错: {str(e)}")
        return f"[编码错误: {str(e)}]"
        
    # 默认情况
    return text

# 处理视频函数
async def process_video(process_id, video_path, target_plate_no):
    """处理视频文件，识别车牌并匹配目标车牌
    
    Args:
        process_id: 处理ID
        video_path: 视频路径
        target_plate_no: 目标车牌号
    """
    # 初始化处理状态
    video_processing_status[process_id] = {
        "status": "processing",
        "progress": 0,
        "message": "开始准备处理...",
        "matches": [],
        "total_matches": 0,
        "completed": False
    }
    
    try:
        # 导入所有必要的模块
        import os
        import sys
        import cv2
        import datetime
        import numpy as np
        from app.services.plate_recognition.service_manager import PlateRecognitionServiceManager
        
        # 初始化车牌识别服务
        logger.info("初始化车牌识别服务...")
        service_manager = PlateRecognitionServiceManager()
        
        # 检查模型是否已加载
        if not service_manager.model_loaded:
            logger.info("模型未加载，尝试加载模型...")
            service_manager.init_service()
            
        # 检查模型是否成功加载
        if not service_manager.model_loaded:
            raise Exception("车牌识别模型加载失败")
        
        # 设定计算设备
        # 使用CPU，遭受torch导入问题
        device = "cpu"
        logger.info(f"使用计算设备: {device}")
        
        # 读取视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            video_processing_status[process_id] = {
                **video_processing_status.get(process_id, {}),
                "status": "error",
                "message": "无法打开视频文件"
            }
            return
            
        # 获取视频信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 为每次处理创建带时间戳的输出目录，确保唯一性
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        process_dir = os.path.join(MONITORING_FRAMES_DIR, f"{process_id}_{timestamp}")
        os.makedirs(process_dir, exist_ok=True)
        
        # 为不同类型的输出创建分类目录
        frames_dir = os.path.join(process_dir, "frames")  # 原始帧
        plates_dir = os.path.join(process_dir, "plates")  # 车牌图片
        debug_dir = os.path.join(process_dir, "debug")    # 调试图片
        all_frames_dir = os.path.join(process_dir, "all_frames")  # 所有被处理的帧
        marked_frames_dir = os.path.join(process_dir, "marked_frames")  # 标记所有车牌的帧
        matches_dir = os.path.join(process_dir, "matches")  # 匹配到目标车牌的帧
        
        # 创建所有必要的目录
        for directory in [frames_dir, plates_dir, debug_dir, all_frames_dir, marked_frames_dir, matches_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # 创建处理过的视频目录
        processed_video_dir = os.path.join(process_dir, "videos")
        os.makedirs(processed_video_dir, exist_ok=True)
        
        # 创建输出视频
        output_video_name = f"{process_id}_{timestamp}_output.mp4"
        output_video_path = os.path.join(processed_video_dir, output_video_name)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        
        # 创建匹配视频路径（用于存储只包含目标车牌的帧组成的视频）
        matches_video_path = os.path.join(processed_video_dir, f"{process_id}_{timestamp}_matches.mp4")
        
        # 创建TXT文件路径，用于记录所有识别到的车牌号
        results_dir = os.path.join(process_dir, "results")
        os.makedirs(results_dir, exist_ok=True)
        all_plates_txt_path = os.path.join(results_dir, f"{process_id}_{timestamp}_all_plates.txt")
        
        # 在日志中记录TXT文件的位置
        logger.info(f"车牌识别结果将存储到文件: {all_plates_txt_path}")
        
        # 初始化车牌号集合用于去重
        unique_plates = set()
        
        # 记录处理信息到日志
        logger.info(f"已创建处理目录: {process_dir}")
        logger.info("所有处理后的图片和视频将保存到该目录")
        
        # 初始化匹配帧列表
        matches = []
        frame_number = 0
        processed_frames = 0
        
        # 更新状态
        video_processing_status[process_id]["message"] = "正在分析视频帧..."
        
        # 使用车牌识别服务的API
        # requests模块实际未使用
        
        # 每秒只处理两帧图像，减少处理负担并保证足够的识别率
        # 计算每秒帧数，然后取一半作为步长（每秒处理两帧）
        if fps > 0 and not math.isnan(fps):
            frame_step = max(int(fps / 2), 1)  # 每秒处理两帧，但步长至少为1
        else:
            frame_step = 15  # 默认值，假设30fps，每秒处理2帧
        
        logger.info(f"将以每秒两帧的频率处理视频，步长为 {frame_step} 帧")
        logger.info(f"视频信息: 总帧数: {total_frames}, FPS: {fps}, 预计处理帧数: {int(total_frames/frame_step)}")
        logger.info(f"视频时长约为 {total_frames/fps:.2f} 秒，将分析约 {int(total_frames/frame_step)} 帧图像")
        
        # 设置保存所有帧的标志
        save_all_frames = True
        logger.info("已设置标志保存所有帧结果")
        
        # 处理视频
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
        
        # 为不同类型的输出创建分类目录
        frames_dir = os.path.join(process_dir, "frames")  # 原始帧
        plates_dir = os.path.join(process_dir, "plates")  # 车牌图片
        debug_dir = os.path.join(process_dir, "debug")    # 调试图片
        all_frames_dir = os.path.join(process_dir, "all_frames")  # 所有被处理的帧
        marked_frames_dir = os.path.join(process_dir, "marked_frames")  # 标记所有车牌的帧
        matches_dir = os.path.join(process_dir, "matches")  # 匹配到目标车牌的帧
        
        # 创建所有必要的目录
        for directory in [frames_dir, plates_dir, debug_dir, all_frames_dir, marked_frames_dir, matches_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # 创建处理过的视频目录
        processed_video_dir = os.path.join(process_dir, "videos")
        os.makedirs(processed_video_dir, exist_ok=True)
        
        # 创建输出视频
        output_video_name = f"{process_id}_{timestamp}_output.mp4"
        output_video_path = os.path.join(processed_video_dir, output_video_name)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        
        # 创建匹配视频路径（用于存储只包含目标车牌的帧组成的视频）
        matches_video_path = os.path.join(processed_video_dir, f"{process_id}_{timestamp}_matches.mp4")
        
        # 创建TXT文件路径，用于记录所有识别到的车牌号
        results_dir = os.path.join(process_dir, "results")
        os.makedirs(results_dir, exist_ok=True)
        all_plates_txt_path = os.path.join(results_dir, f"{process_id}_{timestamp}_all_plates.txt")
        
        # 在日志中记录TXT文件的位置
        logger.info(f"车牌识别结果将存储到文件: {all_plates_txt_path}")
        
        # 初始化车牌号集合用于去重
        unique_plates = set()
        
        # 记录处理信息到日志
        logger.info(f"已创建处理目录: {process_dir}")
        logger.info("所有处理后的图片和视频将保存到该目录")
        
        # 初始化匹配帧列表
        matches = []
        frame_number = 0
        processed_frames = 0
        
        # 更新状态
        video_processing_status[process_id]["message"] = "正在分析视频帧..."
        
        # 使用车牌识别服务的API
        # requests模块实际未使用
        
        # 每秒只处理两帧图像，减少处理负担并保证足够的识别率
        # 计算每秒帧数，然后取一半作为步长（每秒处理两帧）
        if fps > 0 and not math.isnan(fps):
            frame_step = max(int(fps / 2), 1)  # 每秒处理两帧，但步长至少为1
        else:
            frame_step = 15  # 默认值，假设30fps，每秒处理2帧
        
        logger.info(f"将以每秒两帧的频率处理视频，步长为 {frame_step} 帧")
        logger.info(f"视频信息: 总帧数: {total_frames}, FPS: {fps}, 预计处理帧数: {int(total_frames/frame_step)}")
        logger.info(f"视频时长约为 {total_frames/fps:.2f} 秒，将分析约 {int(total_frames/frame_step)} 帧图像")
        
        # 设置保存所有帧的标志
        save_all_frames = True
        logger.info("已设置标志保存所有帧结果")
        
        # 处理视频
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # 根据步长处理
            if frame_number % frame_step == 0:
                logger.info(f"开始处理第 {frame_number} 帧 (总帧数: {total_frames})")
                # 保存当前帧
                frame_path = os.path.join(frames_dir, f"frame_{frame_number}.jpg")
                cv2.imwrite(frame_path, frame)
                
                # 创建调试目录
                debug_dir = os.path.join(frames_dir, "debug")
                os.makedirs(debug_dir, exist_ok=True)
                
                # 检查图像质量
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blurness = cv2.Laplacian(gray, cv2.CV_64F).var()
                logger.info(f"帧 {frame_number}: 图像清晰度指标: {blurness:.2f} (数值越大越清晰)")
                
                # 图像增强 - 使用更多方法的组合提高识别率
                # 创建多个增强版本便于检测
                enhanced_versions = []
                
                # 1. 基本增强 - 亮度和对比度调整
                enhanced1 = cv2.convertScaleAbs(frame, alpha=1.2, beta=10)  # 增加亮度和对比度
                enhanced_versions.append((enhanced1, "基本增强"))
                
                # 2. CLAHE自适应直方图均衡化
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                lab = cv2.cvtColor(enhanced1, cv2.COLOR_BGR2LAB)
                lab[:,:,0] = clahe.apply(lab[:,:,0])
                enhanced2 = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                enhanced_versions.append((enhanced2, "CLAHE增强"))
                
                # 3. 锐化处理 - 增强车牌边缘特征
                kernel_sharpening = np.array([[-1,-1,-1], 
                                            [-1, 9,-1],
                                            [-1,-1,-1]])
                enhanced3 = cv2.filter2D(enhanced2, -1, kernel_sharpening)
                enhanced_versions.append((enhanced3, "锐化增强"))
                
                # 4. 噪声清除 - 对于高噪声图像
                enhanced4 = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
                enhanced_versions.append((enhanced4, "噪声清除"))
                
                # 5. 高斜亮度处理
                high_contrast = cv2.convertScaleAbs(frame, alpha=1.5, beta=20)
                enhanced_versions.append((high_contrast, "高对比度"))
                
                # 选择主要的增强版本作为默认输出
                enhanced = enhanced3  # 锐化增强版本作为主要输出
                
                # 保存增强后的图像
                enhanced_path = os.path.join(debug_dir, f"enhanced_{frame_number}.jpg")
                cv2.imwrite(enhanced_path, enhanced)
                
                # 直接处理帧图像进行车牌识别
                try:
                    # 记录处理帧信息
                    logger.info(f"正在处理帧号: {frame_number}")
                    
                    # 每隔10帧保存一次原始图像和增强图像，用于后续分析
                    if frame_number % 10 == 0:
                        # 创建更详细的分析目录
                        analysis_dir = os.path.join(frames_dir, "analysis")
                        os.makedirs(analysis_dir, exist_ok=True)
                        
                        # 保存原始图像和增强图像
                        cv2.imwrite(os.path.join(analysis_dir, f"original_{frame_number}.jpg"), frame)
                        cv2.imwrite(os.path.join(analysis_dir, f"enhanced_{frame_number}.jpg"), enhanced)
                    
                    # 初始化结果列表
                    combined_results = []
                    
                    # 设置固定的置信度阈值为0.4，不再使用可变置信度
                    conf_threshold = 0.4
                    logger.info(f"使用固定阈值 {conf_threshold} 进行检测")
                    
                    # 首先尝试所有增强版本 - 全部使用相同的阈值
                    for img, strategy_name in enhanced_versions:
                        recognition_result = service_manager.recognize_image(img, conf_thres=conf_threshold)
                        results = recognition_result.get('plates', [])
                        
                        if results:
                            logger.info(f"帧 {frame_number}: {strategy_name}检测到{len(results)}个车牌")
                            for plate in results:
                                plate['strategy'] = strategy_name
                            combined_results.extend(results)
                    
                    # 再尝试原始图像 - 使用相同的阈值
                    recognition_result = service_manager.recognize_image(frame, conf_thres=conf_threshold)
                    results = recognition_result.get('plates', [])
                    
                    if results:
                        logger.info(f"帧 {frame_number}: 原始图像检测到{len(results)}个车牌")
                        for plate in results:
                            plate['strategy'] = "原始图像"
                        combined_results.extend(results)
                    
                    # 去除重复检测结果 - 基于相同位置的车牌
                    deduplicated_results = []
                    seen_boxes = []
                    
                    for plate in combined_results:
                        # 获取车牌框位置
                        box = plate.get('rect', plate.get('box', None))
                        if not box or len(box) < 4:
                            continue
                            
                        # 创建车牌位置的唯一标识
                        box_id = f"{int(box[0])}-{int(box[1])}-{int(box[2])}-{int(box[3])}"
                        
                        # 如果这个位置已经有车牌，跳过
                        if box_id in seen_boxes:
                            continue
                            
                        seen_boxes.append(box_id)
                        deduplicated_results.append(plate)
                    
                    logger.info(f"帧 {frame_number}: 去除重复后有 {len(deduplicated_results)} 个独立车牌")
                    
                    # 使用去重后的组合结果
                    plate_results = deduplicated_results
                    
                    # 不再使用低置信度尝试，保持一致性
                    if len(plate_results) == 0:
                        logger.info(f"帧 {frame_number}: 未发现车牌，使用置信度阈值 {conf_threshold}")
                    # 保存识别到的车牌图像
                    plate_match_info = []
                    for i, plate in enumerate(plate_results):
                        plate_no = plate.get('plate_no', '未知')
                        plate_score = plate.get('score', plate.get('confidence', 0))  # 兼容两种可能的字段名
                        plate_type = plate.get('plate_type', '未知')
                        plate_color = plate.get('color', plate.get('plate_color', '未知'))  # 兼容两种可能的字段名
                        plate_strategy = plate.get('strategy', '标准识别')  # 使用的识别策略
                        
                        # 记录全部车牌原始信息，包括车牌缩放框位置
                        rect_info = plate.get('rect', plate.get('box', []))
                        box_info = rect_info if rect_info else []
                        logger.info(f"  - 车牌{i+1}: {plate_no}, 类型: {plate_type}, 颜色: {plate_color}, 置信度: {plate_score:.4f}, 策略: {plate_strategy}")
                        logger.info(f"  - 车牌{i+1}边框: {box_info}")
                        
                        # 将rect字段复制到box字段，确保一致性
                        if rect_info and 'box' not in plate:
                            plate['box'] = rect_info
                        elif 'box' in plate and 'rect' not in plate:
                            plate['rect'] = plate['box']
                            
                        # 将该车牌号加入唯一车牌集合中
                        if plate_no and plate_no != '未知':
                            # 去除空格和特殊字符
                            clean_plate_no = ensure_utf8_encoding(plate_no.strip().replace(' ', '').replace('?', ''))
                            if clean_plate_no:
                                unique_plates.add(clean_plate_no)
                        
                        # 首先处理中文字符编码问题
                        plate_no = ensure_utf8_encoding(plate_no)
                        
                        # 车牌文本处理 - 清除空格和特殊字符
                        clean_plate_no = plate_no.strip().replace(' ', '').replace('?', '')
                        clean_target = ensure_utf8_encoding(target_plate_no).strip().replace(' ', '').replace('?', '')
                        
                        # 在日志中显示清理后的车牌号码以便于比较
                        logger.info(f"  - 比较车牌: 检测到='{clean_plate_no}', 目标='{clean_target}'")
                        
                        # 使用更先进的相似度计算方法
                        # 1. 精确匹配 - 优先判断
                        if clean_plate_no == clean_target:  
                            match_type = "完全匹配"
                            similarity_score = 1.0
                            is_match = True
                        # 2. 计算字符相似度
                        else:
                            # 计算字符级别的相似性 - 考虑起始位置的匹配
                            similarity_score = 0
                            min_len = min(len(clean_plate_no), len(clean_target))
                            
                            if min_len > 0:
                                # 匹配开头字符给予更高权重
                                matching_chars = 0
                                
                                # 前3个字符匹配权重更高
                                prefix_match_count = 0
                                prefix_len = min(3, min_len)
                                for j in range(prefix_len):
                                    if clean_plate_no[j] == clean_target[j]:
                                        prefix_match_count += 1
                                        matching_chars += 1
                                
                                # 其余字符匹配
                                for j in range(prefix_len, min_len):
                                    if clean_plate_no[j] == clean_target[j]:
                                        matching_chars += 1
                                
                                # 计算加权相似度 - 前缀匹配有更高的权重
                                prefix_weight = 0.6 if prefix_len > 0 else 0
                                other_weight = 0.4
                                
                                prefix_score = (prefix_match_count / prefix_len) * prefix_weight if prefix_len > 0 else 0
                                other_score = ((matching_chars - prefix_match_count) / (min_len - prefix_len)) * other_weight if min_len > prefix_len else 0
                                
                                similarity_score = prefix_score + other_score
                                
                                # 字符位置灵活匹配 - 允许小部分字符错位
                                # 如果得分低，尝试使用更灵活的字符匹配
                                if similarity_score < 0.6:
                                    common_chars = 0
                                    for c in clean_plate_no:
                                        if c in clean_target:
                                            common_chars += 1
                                    flex_score = common_chars / len(clean_target) * 0.8  # 灵活匹配得分稍低
                                    similarity_score = max(similarity_score, flex_score)
                        
                        # 判断是否匹配 - 阈值降低到0.5提高匹配率
                        SIMILARITY_THRESHOLD = 0.5  # 降低阈值提高匹配率
                        is_match = similarity_score >= SIMILARITY_THRESHOLD
                        match_type = f"相似度匹配 ({similarity_score:.2f})"
                        
                        logger.info(f"  - 字符相似度: {similarity_score:.4f} ({similarity_score*100:.1f}%), 判定: {match_type}")
                        
                        # 添加匹配信息
                        plate_match_info.append({
                            'plate_no': plate_no,
                            'clean_plate_no': clean_plate_no,
                            'similarity_score': similarity_score,
                            'is_match': is_match,
                            'match_type': match_type,
                            'plate': plate
                        })
                        
                        # 如果匹配成功
                        if is_match:
                            logger.info(f"  - [匹配成功 - {match_type}] 发现目标车牌: {plate_no}, 相似度: {similarity_score:.4f}")
                            
                            # 保存成功匹配的车牌 ROI 区域
                            if 'box' in plate:
                                box = plate['box']
                                # 确保坐标有效
                                if len(box) >= 4:
                                    x1, y1 = int(box[0]), int(box[1])
                                    x2, y2 = int(box[2]) if len(box) > 2 else x1 + 100, int(box[3]) if len(box) > 3 else y1 + 30
                                    
                                    # 限制在图像范围内
                                    x1, y1 = max(0, x1), max(0, y1)
                                    x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                                    
                                    # 确保面积有效
                                    if x2 > x1 and y2 > y1:
                                        plate_roi = frame[y1:y2, x1:x2]
                                        roi_path = os.path.join(matches_dir, f"plate_roi_{frame_number}.jpg")
                                        cv2.imwrite(roi_path, plate_roi)
                                logger.info(f"  - 已保存车牌 ROI: {roi_path}")
                    
                    # 存储匹配标志
                    matched = False
                    matched_plate = None
                    
                    # 处理车牌识别结果 - 精简为CarRecognition.py中draw_result函数兼容的格式
                    plate_info = []
                    for plate in plate_results:
                        plate_no = plate.get('plate_no', '未知')
                        plate_score = float(plate.get('score', 0))
                        plate_type = plate.get('plate_type', '单层车牌')
                        plate_color = plate.get('plate_color', '蓝色')
                        
                        # 确定车牌类型: 0=单层, 1=双层
                        object_no = 0  # 默认为单层车牌
                        if '双层' in plate_type:
                            object_no = 1
                            
                        # 获取车牌半径
                        box = plate.get('box', [0, 0, 0, 0])
                        rect = [int(box[0]), int(box[1]), int(box[2]), int(box[3])]
                        roi_height = int((box[3] - box[1])/2)  # 用于draw_result函数中绘制文本
                        
                        # 如果有关键点使用关键点, 如果没有则根据边界框生成
                        if 'landmarks' in plate and plate['landmarks']:
                            landmarks = plate['landmarks']
                        else:
                            # 根据box生成四个角点
                            landmarks = [
                                [box[0], box[1]],  # 左上
                                [box[2], box[1]],  # 右上
                                [box[2], box[3]],  # 右下
                                [box[0], box[3]]   # 左下
                            ]
                        
                        # 构建与draw_result函数兼容的结果字典结构
                        curr_plate = {
                            "plate_no": plate_no,           # 车牌号
                            "score": plate_score,          # 识别置信度
                            "class_type": plate_type,       # 车牌类型描述
                            "plate_color": plate_color,     # 车牌颜色
                            "object_no": object_no,         # 车牌类型 (0=单层, 1=双层)
                            "rect": rect,                   # 用于绘制边界框
                            "roi_height": roi_height,        # 用于绘制文字
                            "landmarks": landmarks           # 关键点
                        }
                        
                        # 裁剪车辆区域用于颜色识别
                        x1, y1, x2, y2 = max(0, box[0]), max(0, box[1]), min(frame.shape[1], box[2]), min(frame.shape[0], box[3])
                        car_roi = frame[y1:y2, x1:x2] if y2 > y1 and x2 > x1 else frame
                        
                        # 获取车辆颜色
                        try:
                            car_rec_model = service_manager.models.get('car_rec')
                            if car_rec_model is None:
                                logger.warning("车辆识别模型未加载，跳过车辆颜色识别")
                            else:
                                from app.services.plate_recognition.recognizer.car_rec import get_color_and_score
                                car_color, color_conf = get_color_and_score(car_rec_model, car_roi, device)
                                curr_plate['car_color'] = car_color
                        except Exception as e:
                            logger.error(f"车辆颜色识别失败: {str(e)}")
                            curr_plate['car_color'] = "未知"
                            
                        # 检查车牌完整性
                        if 'plate_no' not in curr_plate or not curr_plate['plate_no'] or curr_plate['plate_no'] == '未知':
                            logger.warning(f"  - 跳过无效车牌信息: {curr_plate}")
                            continue
                            
                        # 过滤字符数不超过5位的车牌（包括汉字、字母、数字）
                        plate_no = curr_plate['plate_no']
                        if len(plate_no) <= 5:
                            logger.warning(f"  - 跳过过短的车牌 [长度{len(plate_no)}]: '{plate_no}'")
                            continue
                        
                        # 添加详细的车牌信息日志
                        logger.info(f"  - 检测到有效车牌: '{plate_no}', 长度: {len(plate_no)}, 置信度: {curr_plate.get('score', 0):.3f}")
                            
                        # 添加到plate_info列表
                        plate_info.append(curr_plate)
                    
                    # 完成所有车牌处理后，处理匹配逻辑
                    # 在所有已处理的车牌中检查匹配
                    matched = False
                    matched_plate = None
                    
                    # 生成当前帧的时间戳
                    current_time = datetime.datetime.now()
                    formatted_timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 打印目标车牌信息以便调试
                    logger.info(f"目标车牌设置: '{target_plate_no}'")
                    
                    # 确保目标车牌始终添加到唯一车牌集合
                    if target_plate_no and target_plate_no.strip() != '':
                        clean_target = target_plate_no.strip().replace(' ', '').replace('?', '')
                        unique_plates.add(clean_target)
                        logger.info(f"已将目标车牌 '{clean_target}' 直接添加到结果集")
                    
                    # 如果没有设置目标车牌或目标车牌为空，自动将所有车牌标记为目标
                    if not target_plate_no or target_plate_no.strip() == '':
                        logger.info("没有设置目标车牌，将显示所有检测到的车牌")
                        # 将所有车牌标记为目标
                        for plate in plate_info:
                            plate['is_target'] = True
                            # 构建匹配信息并添加到matches列表
                            plate_no = plate.get('plate_no', '')
                            match_info = {
                                "frame_number": frame_number,
                                "plate_number": plate_no,
                                "similarity": 1.0,  # 不需要计算相似度
                                "match_type": "全部检测结果",
                                "confidence": float(plate.get('score', 0)),
                                "timestamp": formatted_timestamp,  # 添加时间戳
                                "plate_color": plate.get('color', ''),
                                "box": plate.get('rect', [])
                            }
                            matches.append(match_info)
                        matched = True  # 认为已经匹配成功
                    else:
                        # 有目标车牌时，进行目标匹配
                        clean_target = target_plate_no.strip()
                        logger.info(f"检查是否有匹配车牌: 目标='{clean_target}'")
                        
                        # 对每个车牌进行匹配比较
                        for plate in plate_info:
                            # 去除空格后比较
                            detected_plate_no = plate.get('plate_no', '').strip()
                        
                        # 显示所有检测到的车牌
                        logger.info(f"检测到车牌: '{detected_plate_no}'")
                        
                        # 增强的车牌匹配逻辑，包含多种匹配方式
                        # 在日志中显示当前检测到的车牌和目标车牌，便于调试
                        logger.info(f"\n===== 匹配判断 =====\n检测到: '{detected_plate_no}'\n目标车牌: '{clean_target}'")
                        
                        # 0. 特殊情况 - 检测到的车牌包含目标车牌（子串匹配）
                        is_substring_match = clean_target in detected_plate_no or detected_plate_no in clean_target
                        if is_substring_match:
                            logger.info(f"  - 子串匹配成功: 一个是另一个的子串")
                            
                        # 1. 严格匹配 - 完全相等
                        is_exact_match = (detected_plate_no == clean_target)
                        if is_exact_match:
                            logger.info(f"  - 完全匹配成功: 精确匹配")
                        
                        # 2. 部分匹配 - 字符相似度
                        similarity_score = 0
                        if not is_exact_match and len(detected_plate_no) > 0 and len(clean_target) > 0:
                            # 计算相同字符数
                            min_len = min(len(detected_plate_no), len(clean_target))
                            matching_chars = 0
                            
                            # 第一个字符匹配特别重要（通常是省份简称）
                            first_char_match = False
                            if len(detected_plate_no) > 0 and len(clean_target) > 0:
                                if detected_plate_no[0] == clean_target[0]:
                                    first_char_match = True
                                    matching_chars += 1
                                    logger.info(f"  - 第一个字符匹配成功: '{detected_plate_no[0]}'")
                            
                            # 检查其他字符匹配
                            for i in range(1, min_len):
                                if detected_plate_no[i] == clean_target[i]:
                                    matching_chars += 1
                            
                            # 同位置匹配字符比例
                            position_match_ratio = matching_chars / min_len
                            logger.info(f"  - 同位置匹配字符: {matching_chars}/{min_len} = {position_match_ratio:.2f}")
                                    
                            # 另外的匹配方法 - 在任意位置匹配相同字符
                            common_chars = 0
                            for c in detected_plate_no:
                                if c in clean_target:
                                    common_chars += 1
                            
                            # 共同字符比例
                            common_char_ratio = common_chars / max(len(detected_plate_no), len(clean_target))
                            logger.info(f"  - 共同字符数: {common_chars}/{max(len(detected_plate_no), len(clean_target))} = {common_char_ratio:.2f}")
                                    
                            # 使用更宽松的匹配分数来增加匹配率
                            flexible_score = common_char_ratio
                            
                            # 计算相似度 - 结合严格匹配和灵活匹配
                            position_score = position_match_ratio  # 位置精确匹配分数
                            
                            # 如果第一个字符匹配，给予额外加分
                            if first_char_match:
                                position_score = min(1.0, position_score + 0.2)
                                logger.info(f"  - 位置分加成: {position_score:.2f} (因为第一个字符匹配额外加分20%)")
                            
                            # 取较高的分数作为最终分数 - 这样既能匹配位置相同的车牌，也能匹配字符相似但顺序不同的车牌
                            similarity_score = max(position_score, flexible_score)
                            
                            # 如果是子串匹配，给予额外加分
                            if is_substring_match:
                                similarity_score = min(1.0, similarity_score + 0.3)
                                logger.info(f"  - 由于子串匹配，分数提高到: {similarity_score:.2f}")
                            
                            logger.info(f"  - 最终相似度分数: {similarity_score:.2f} (取位置分和字符分中较高者)")
                        
                        # 如果是精确匹配，设置相似度为1.0
                        if is_exact_match:
                            similarity_score = 1.0
                            
                            # 将相似度阈值调低到0.15，大幅提高匹配率
                            threshold = 0.15  # 非常宽松的阈值确保能捕获到不太精确的匹配
                            
                            logger.info(f"  - 车牌 '{detected_plate_no}' 与目标 '{clean_target}' 的相似度: {similarity_score:.2f} (位置分:{position_score:.2f}, 字符分:{flexible_score:.2f})")
                            logger.info(f"  - 匹配阈值: {threshold} - {'通过' if similarity_score >= threshold else '未通过'}")

                        
                        # 判断是否匹配 - 严格匹配或相似度超过阈值即为匹配
                        is_match = is_exact_match or similarity_score >= threshold
                        
                        if is_match:
                            match_type = "完全匹配" if is_exact_match else f"高相似度匹配({similarity_score:.2f})"
                            logger.info(f"找到匹配的目标车牌: {detected_plate_no} [匹配类型: {match_type}]")
                            matched = True
                            matched_plate = plate
                            
                            # 特别标记该车牌以确保框选
                            plate['is_target'] = True
                            logger.info(f"已标记目标车牌供框选显示: {detected_plate_no}")
                            
                            # 构建匹配信息并添加到matches列表
                            match_info = {
                                "frame_number": frame_number,
                                "plate_number": detected_plate_no,
                                "similarity": 1.0 if is_exact_match else similarity_score,
                                "match_type": match_type,
                                "confidence": float(plate.get('score', 0)),
                                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            matches.append(match_info)
                            logger.info(f"已添加匹配信息: {match_info}")
                        else:
                            # 确保非目标车牌也会被标记和显示
                            plate['is_target'] = False
                    
                    # 如果找到匹配车牌，在帧上高亮显示并保存
                    if matched:
                        try:
                            # 提前导入draw_result函数，确保可以正确从子项目中导入
                            import sys
                            import os
                            import numpy as np
                            
                            # 确保只导入一次draw_result函数
                            if 'draw_result' not in globals():
                                try:
                                    # 自动查找脚本目录路径
                                    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                    parent_dir = os.path.dirname(current_dir)
                                    scripts_dir = os.path.join(parent_dir, 'License_plate_recognition_tracking', 'scripts')
                                    
                                    # 先检查自动路径是否存在
                                    if not os.path.exists(scripts_dir):
                                        logger.warning(f"自动检测的脚本目录不存在: {scripts_dir}")
                                        # 尝试硬编码路径作为备用
                                        scripts_dir = "D:\\Desktop\\ModelService_graduation-main\\License_plate_recognition_tracking\\scripts"
                                        logger.info(f"尝试使用硬编码路径: {scripts_dir}")
                                        
                                        if not os.path.exists(scripts_dir):
                                            raise ImportError(f"无法找到脚本目录: {scripts_dir}")
                                    
                                    # 检查Car_recognition.py文件是否存在
                                    car_rec_file = os.path.join(scripts_dir, 'Car_recognition.py')
                                    if not os.path.exists(car_rec_file):
                                        raise ImportError(f"Car_recognition.py文件不存在: {car_rec_file}")
                                        
                                    # 将目录添加到系统路径，以便导入模块
                                    if scripts_dir not in sys.path:
                                        sys.path.append(scripts_dir)
                                        logger.info(f"已将{scripts_dir}添加到sys.path")
                                    
                                    # 尝试导入draw_result函数
                                    from Car_recognition import draw_result
                                    logger.info("成功导入draw_result函数")
                                except Exception as e:
                                    logger.error(f"导入draw_result函数失败: {str(e)}")
                                    raise
                            
                            # 检查plate_info是否有效
                            if not plate_info:
                                logger.warning("没有检测到车牌，无法绘制结果")
                                raise ValueError("无车牌数据")
                            
                            # 检查有效性
                            valid_plates = [p for p in plate_info if 'rect' in p and 'plate_no' in p]
                            if not valid_plates:
                                logger.warning("没有有效的车牌数据用于绘制")
                                raise ValueError("无效的车牌数据")
                            
                            # 在帧上高亮显示目标车牌
                            logger.info(f"准备用draw_result高亮显示目标车牌: {target_plate_no.strip()}")
                            logger.info(f"用于绘制的plate_info: {plate_info}")
                            
                            # 确保数据结构全部完整
                            for p in plate_info:
                                if 'landmarks' not in p or not p['landmarks']:
                                    # 如果没有关键点，生成它们
                                    rect = p.get('rect', [0, 0, 0, 0])
                                    p['landmarks'] = [
                                        [rect[0], rect[1]],  # 左上
                                        [rect[2], rect[1]],  # 右上
                                        [rect[2], rect[3]],  # 右下
                                        [rect[0], rect[3]]   # 左下
                                    ]
                            
                            # 调用子项目中的draw_result函数高亮目标车牌
                            clean_target = target_plate_no.strip()
                            highlight_frame = draw_result(frame.copy(), plate_info, highlight_plate=clean_target)
                            
                            # 二次确认框选目标车牌（额外保险）
                            for p in plate_info:
                                if p.get('plate_no', '').strip() == clean_target:
                                    # 确保框选目标车牌 - 手动添加框
                                    if 'rect' in p:
                                        rect = p['rect']
                                        cv2.rectangle(highlight_frame, 
                                                    (rect[0], rect[1]), 
                                                    (rect[2], rect[3]), 
                                                    (0, 0, 255), 3)  # 红色粗框
                                        cv2.putText(highlight_frame,
                                                    f"目标车牌: {clean_target}",
                                                    (rect[0], rect[1] - 10),
                                                    cv2.FONT_HERSHEY_SIMPLEX,
                                                    0.8,
                                                    (0, 0, 255),  # 红色文字
                                                    2)
                                        logger.info(f"手动框选目标车牌成功: {clean_target}")
                            
                            # 保存高亮后的帧图像到匹配目录
                            highlight_path = os.path.join(matches_dir, f"highlight_{frame_number}.jpg")
                            cv2.imwrite(highlight_path, highlight_frame)
                            logger.info("高亮更新已保存到: {}".format(highlight_path))
                            
                            # 保存原始帧以便对比
                            orig_path = os.path.join(matches_dir, f"original_{frame_number}.jpg")
                            cv2.imwrite(orig_path, frame)
                            
                            # 构建匹配信息
                            match_info = {
                                "frame_number": frame_number,
                                "frame_path": highlight_path,  # 使用高亮后的图像路径
                                "plate_number": matched_plate.get('plate_no'),
                                "confidence": float(matched_plate.get('score', 0)),
                                "plate_type": matched_plate.get('class_type', '单层车牌'),
                                "plate_color": matched_plate.get('plate_color', '蓝色'),
                                "car_color": matched_plate.get('car_color', '未知'),
                                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            matches.append(match_info)
                            logger.info(f"添加匹配信息: {match_info}")
                            
                            # 使用高亮后的帧替换原始帧 - 这样域效果能被保存到输出视频中
                            frame = highlight_frame
                            
                            # 更新状态
                            video_processing_status[process_id]["matches"] = matches.copy()  # 使用副本避免引用问题
                            
                        except Exception as e:
                            logger.error(f"高亮显示目标车牌失败: {str(e)}")
                            # 如果高亮失败，使用简单的方框标记
                            if matched_plate and 'rect' in matched_plate:
                                box = matched_plate['rect']
                                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 3)
                                cv2.putText(
                                    frame,
                                    f"目标车牌: {target_plate_no}",
                                    (box[0], box[1] - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7,
                                    (0, 0, 255),
                                    2
                                )
                                
                                # 保存高亮后的帧图像
                                highlight_path = os.path.join(frames_dir, f"highlight_{frame_number}.jpg")
                                cv2.imwrite(highlight_path, frame)
                                
                                # 构建匹配信息
                                match_info = {
                                    "frame_number": frame_number,
                                    "frame_path": highlight_path,
                                    "plate_number": matched_plate.get('plate_no'),
                                    "confidence": float(matched_plate.get('score', 0)),
                                    "plate_type": matched_plate.get('plate_type', '未知'),
                                    "plate_color": matched_plate.get('plate_color', '未知'),
                                    "car_color": matched_plate.get('car_color', '未知'),
                                    "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }
                                matches.append(match_info)
                                
                                # 在帧上标记匹配的车牌
                                cv2.putText(
                                    frame,
                                    f"目标车牌: {target_plate_no}",
                                    (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7,
                                    (0, 255, 0),
                                    2
                                )
                                
                                # 更新状态中的匹配信息
                                video_processing_status[process_id]["matches"] = matches
                                break
                except Exception as e:
                    logger.warning(f"处理帧 {frame_number} 失败: {str(e)}")
            
            # 在写入输出视频前，先绘制所有检测到的车牌框
            # 创建一个新的帧副本用于绘制
            marked_frame = frame.copy()
            
            # 如果有检测到车牌，先绘制所有普通车牌，然后再绘制目标车牌
            if len(plate_info) > 0:
                logger.info(f"帧 {frame_number}: 将绘制 {len(plate_info)} 个车牌框")
                
                # 先绘制所有非目标车牌（青绿色框）
                for plate in plate_info:
                    if 'rect' in plate:
                        # 跳过目标车牌，稍后用红色绘制
                        clean_target = target_plate_no.strip()
                        detected_plate_no = plate.get('plate_no', '').strip()
                        
                        # 跳过目标车牌，稍后用红色绘制
                        if detected_plate_no == clean_target:
                            continue
                            
                        box = plate['rect']
                        # 青绿色框标记非目标车牌
                        cv2.rectangle(marked_frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (54, 197, 238), 2)
                        
                        # 使用draw_chinese_text函数显示清晰的车牌号码
                        try:
                            from app.services.plate_recognition.detector.detector import draw_chinese_text
                            plate_no = ensure_utf8_encoding(plate.get('plate_no', ''))
                            marked_frame = draw_chinese_text(
                                marked_frame, 
                                plate_no, 
                                (int(box[0]), int(box[3]) + 30), 
                                font_size=30, 
                                color=(54, 197, 238), 
                                thickness=2
                            )
                        except Exception as e:
                            logger.error(f"使用中文渲染函数失败: {str(e)}")
                            # 如果中文渲染失败，使用普通文本渲染
                            plate_no = plate.get('plate_no', '')
                            cv2.putText(marked_frame, 
                                      f"{plate_no}", 
                                      (int(box[0]), int(box[3]) + 30), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (54, 197, 238), 2)
                
                # 然后绘制目标车牌（红色精细框）
                for plate in plate_info:
                    if 'rect' in plate:
                        clean_target = target_plate_no.strip()
                        detected_plate_no = plate.get('plate_no', '').strip()
                        
                        # 只处理目标车牌
                        if detected_plate_no != clean_target:
                            continue
                            
                        box = plate['rect']
                        # 红色精细框标记目标车牌
                        # 绘制双重边框：外框橙红色，内框红色
                        outer_padding = 2
                        cv2.rectangle(marked_frame, 
                                    (int(box[0])-outer_padding, int(box[1])-outer_padding), 
                                    (int(box[2])+outer_padding, int(box[3])+outer_padding), 
                                    (0, 140, 255), 3)  # 橙红色外框
                        cv2.rectangle(marked_frame, 
                                    (int(box[0]), int(box[1])), 
                                    (int(box[2]), int(box[3])), 
                                    (0, 0, 255), 2)  # 红色内框
                        
                        # 使用draw_chinese_text函数显示清晰的车牌号码
                        try:
                            from app.services.plate_recognition.detector.detector import draw_chinese_text
                            plate_no = ensure_utf8_encoding(plate.get('plate_no', ''))
                            marked_frame = draw_chinese_text(
                                marked_frame, 
                                plate_no, 
                                (int(box[0]), int(box[3]) + 30), 
                                font_size=35, 
                                color=(0, 0, 255), 
                                thickness=2
                            )
                        except Exception as e:
                            logger.error(f"使用中文渲染函数失败: {str(e)}")
                            # 如果中文渲染失败，使用普通文本渲染
                            plate_no = plate.get('plate_no', '')
                            cv2.putText(marked_frame, 
                                      f"目标车牌: {plate_no}", 
                                      (int(box[0]), int(box[3]) + 30), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
                # 更新处理后的帧
                frame = marked_frame
            
            # 写入处理后的帧到输出视频
            out.write(frame)
            
            # 如果设置了保存所有帧，则无论是否检测到车牌都保存
            if save_all_frames:
                # 保存原始帧
                all_frame_path = os.path.join(all_frames_dir, f"frame_{frame_number}.jpg")
                cv2.imwrite(all_frame_path, frame)
                
                # 当检测到车牌时，保存带标记的帧
                if len(plate_info) > 0:
                    marked_frame_path = os.path.join(marked_frames_dir, f"marked_{frame_number}.jpg")
                    cv2.imwrite(marked_frame_path, marked_frame)
                    
                    # 保存标记了所有车牌的帧
                    marked_frame_path = os.path.join(marked_frames_dir, f"marked_{frame_number}.jpg")
                    cv2.imwrite(marked_frame_path, marked_frame)
                
                # 每10帧记录一次保存状态
                if frame_number % 10 == 0:
                    logger.info(f"已保存帧 {frame_number} 到路径: {all_frame_path}")
            
            # 更新进度
            processed_frames += 1
            progress = min(95, int((processed_frames / total_frames) * 100))
            video_processing_status[process_id]["progress"] = progress
            
            # 每10%更新一次消息
            if progress % 10 == 0:
                video_processing_status[process_id]["message"] = f"已处理 {progress}% 的视频..."
            
            # 最后再增加帧计数
            frame_number += 1
            
            # 每25帧输出一下总体处理进度
            if frame_number % 25 == 0:
                logger.info(f"处理进度: {frame_number}/{total_frames} 帧, {progress}%")
        
        # 释放资源
        cap.release()
        out.release()
        
        # 如果有匹配结果，创建匹配帧的视频
        matches_video_path = None
        if len(matches) > 0:
            # 从匹配的帧创建视频
            matches_video_path = os.path.join(
                MONITORING_VIDEO_DIR,
                f"{process_id}_matches.mp4"
            )
            logger.info(f"尝试从 {len(matches)} 个匹配帧创建视频: {matches_video_path}")
            
            # 调用创建视频函数
            matches_video = create_video_from_matches(matches, matches_video_path)
            
            # 如果创建成功，设置视频URL
            if matches_video:
                # 转换为静态URL路径
                matches_video_relative = os.path.relpath(matches_video_path, MONITORING_OUTPUT_DIR)
                matches_video_url = f"/api/plate-monitoring/static/{matches_video_relative}"
                video_processing_status[process_id]["matches_video"] = matches_video_url
                logger.info(f"已设置匹配视频URL: {matches_video_url}")
        else:
            logger.warning("没有匹配结果，不创建结果视频")
        
        # 处理完成，更新状态
        video_processing_status[process_id]['status'] = 'completed'
        video_processing_status[process_id]['completed_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        video_processing_status[process_id]['matches'] = matches
        video_processing_status[process_id]['match_count'] = len(matches)
        
        # 确保视频URL存在于状态对象中
        if 'output_video' not in video_processing_status[process_id]:
            logger.warning("处理状态中没有输出视频URL，前端可能无法显示视频")
        if len(matches) > 0 and 'matches_video' not in video_processing_status[process_id]:
            logger.warning("处理状态中没有匹配视频URL，前端可能无法显示匹配视频")
        
        logger.info(f"视频处理完成 - 过程 ID: {process_id}")
        logger.info(f"视频处理状态对象: {video_processing_status[process_id].keys()}")
        
        # 将所有唯一车牌号写入TXT文件
        with open(all_plates_txt_path, 'w', encoding='utf-8') as f:
            # 将集合转为列表并按字母顺序排序
            sorted_plates = sorted(list(unique_plates))
            
            # 首行写入文件信息
            f.write(f"# 视频车牌识别结果 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 识别出的唯一车牌数量: {len(sorted_plates)}\n")
            f.write(f"# 目标车牌: {target_plate_no}\n")
            f.write("# -----------------------------------\n\n")
            
            # 写入所有号码，每行一个
            for i, plate_no in enumerate(sorted_plates, 1):
                f.write(f"{i}. {plate_no}\n")
                
        logger.info(f"已将 {len(unique_plates)} 个唯一车牌号写入到: {all_plates_txt_path}")
        
        # 保存处理结果到JSON文件
        results_json = {
            "process_id": process_id,
            "video_path": video_path,
            "target_plate_no": target_plate_no,
            "target_plate_detected": target_plate_no in unique_plates,  # 明确标记目标车牌是否被检测到
            "total_frames": total_frames,
            "processed_frames": processed_frames,
            "matches": matches,
            "unique_plates": list(unique_plates),  # 添加唯一车牌列表
            "plates_txt_path": all_plates_txt_path,  # 添加TXT文件路径
            "status": "completed",
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        results_file = os.path.join(process_dir, "results.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_json, f, ensure_ascii=False, indent=2)
        
        # 将原始视频复制到输出目录
        output_video_path = os.path.join(MONITORING_VIDEO_DIR, f"{process_id}_output.mp4")
        shutil.copy(video_path, output_video_path)
        logger.info(f"已复制原始视频到输出目录: {output_video_path}")
        
        # 添加输出视频URL到处理状态
        output_video_relative = os.path.join("videos", f"{process_id}_output.mp4")
        output_video_url = f"/api/plate-monitoring/static/{output_video_relative}"
        video_processing_status[process_id]["output_video"] = output_video_url
        logger.info(f"已设置输出视频URL: {output_video_url}")
        
        # 如果有匹配视频，设置匹配视频URL
        if matches_video_path and os.path.exists(matches_video_path):
            matches_video_relative = os.path.join("videos", f"{process_id}_matches.mp4")
            matches_video_url = f"/api/plate-monitoring/static/{matches_video_relative}"
            video_processing_status[process_id]["matches_video"] = matches_video_url
            logger.info(f"已设置匹配视频URL: {matches_video_url}")
        
        # 创建结果摘要
        summary_path = os.path.join(MONITORING_OUTPUT_DIR, f"{process_id}_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(video_processing_status[process_id], f, ensure_ascii=False, indent=2)
        
        logger.info(f"视频 {process_id} 处理完成，匹配结果数: {len(matches)}")
        
        # 在视频处理成功完成后发送报警邮件
        if target_plate_no and target_plate_no.strip() != '':
            clean_target = target_plate_no.strip()
            logger.info(f"视频处理成功完成，开始发送目标车牌 {clean_target} 的报警邮件")
            
            # 查找目标车牌的匹配信息
            target_match_info = {}
            for match in matches:
                if match.get('plate_number') == clean_target:
                    target_match_info = match
                    break
            
            # 添加报警标记
            video_processing_status[process_id]["has_alarm"] = True
            video_processing_status[process_id]["alarm_plate"] = clean_target
            video_processing_status[process_id]["alarm_reason"] = "目标车牌视频处理完成"
            
            # 发送报警邮件
            try:
                logger.info(f"开始发送报警邮件: 目标车牌 {clean_target}")
                
                # 准备邮件详细信息
                email_details = {
                    "process_id": process_id,
                    "detection_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "video_path": video_path,
                    "target_detected": bool(target_match_info),  # 标记目标车牌是否被检测到
                    "message": "视频处理已完成，该邮件包含处理结果"
                }
                
                # 使用附图，如果有匹配帧
                frame_path = None
                if target_match_info.get("frame_path") and os.path.exists(target_match_info.get("frame_path")):
                    frame_path = target_match_info.get("frame_path")
                
                # 发送报警邮件
                email_sent = email_notifier.send_plate_alarm(
                    plate_number=clean_target,
                    frame_path=frame_path,
                    video_id=process_id,
                    details=email_details
                )
                
                # 更新邮件发送状态
                video_processing_status[process_id]["email_sent"] = email_sent
                if email_sent:
                    logger.info(f"视频处理完成后报警邮件发送成功: {clean_target}")
                else:
                    logger.warning(f"视频处理完成后报警邮件发送失败: {clean_target}")
                    
            except Exception as email_error:
                logger.error(f"视频处理完成后发送报警邮件时出错: {str(email_error)}")
                video_processing_status[process_id]["email_error"] = str(email_error)
        
    except Exception as e:
        logger.error(f"处理视频失败: {str(e)}")
        # 更新错误状态
        if process_id in video_processing_status:
            video_processing_status[process_id] = {
                **video_processing_status.get(process_id, {}),
                "status": "error",
                "message": f"处理失败: {str(e)}",
                "has_alarm": True,
                "alarm_plate": clean_target,
                "alarm_reason": "设置了目标车牌自动触发报警"
            }
            
            # 发送报警邮件
            try:
                logger.info(f"发送报警邮件: 目标车牌 {clean_target}")
                
                # 准备邮件详细信息
                email_details = {
                    "process_id": process_id,
                    "detection_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "video_path": video_path,
                    "is_forced_alarm": True,  # 这是强制报警
                    "reason": "已设置目标车牌，触发自动报警"
                }
                
                # 使用附图，如果有匹配帧
                frame_path = None
                if target_match_info.get("frame_path") and os.path.exists(target_match_info.get("frame_path")):
                    frame_path = target_match_info.get("frame_path")
                
                # 发送报警邮件
                email_sent = email_notifier.send_plate_alarm(
                    plate_number=clean_target,
                    frame_path=frame_path,
                    video_id=process_id,
                    details=email_details
                )
                
                # 更新邮件发送状态
                video_processing_status[process_id]["email_sent"] = email_sent
                if email_sent:
                    logger.info(f"报警邮件发送成功: {clean_target}")
                else:
                    logger.warning(f"报警邮件发送失败: {clean_target}")
                    
            except Exception as email_error:
                logger.error(f"发送报警邮件时出错: {str(email_error)}")
                video_processing_status[process_id]["email_error"] = str(email_error)

# API端点：获取视频处理状态
@router.get("/video-status/{process_id}")
async def get_video_processing_status(process_id: str):
    """获取视频处理状态"""
    if process_id not in video_processing_status:
        raise HTTPException(status_code=404, detail="未找到指定的处理任务")
    
    return JSONResponse(content=video_processing_status[process_id])

# API端点：获取当前目标车牌信息
@router.get("/target-plate")
async def get_target_plate():
    """获取当前设置的目标车牌信息"""
    return JSONResponse(content=target_plate_info)

# API端点：清除目标车牌
@router.post("/clear-target-plate")
async def clear_target_plate():
    """清除当前设置的目标车牌"""
    global target_plate_info
    target_plate_info = {
        'plate_no': None,
        'source': None,
        'timestamp': None,
        'image_path': None
    }
    return JSONResponse(content={"status": "success", "message": "目标车牌已清除"})

# API端点：发送测试邮件
@router.post("/test-email")
async def send_test_email():
    """发送测试邮件以验证邮件功能是否正常"""
    try:
        # 发送测试邮件
        success = email_notifier.send_test_email()
        
        if success:
            return JSONResponse(content={"status": "success", "message": "测试邮件发送成功"})
        else:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "测试邮件发送失败"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"测试邮件发送时出错: {str(e)}"})

# API端点：手动发送报警邮件
@router.post("/send-alarm-email")
async def send_alarm_email(plate_number: str = Form(...), message: str = Form(None)):
    """手动发送车牌报警邮件"""
    try:
        # 准备邮件详细信息
        details = {
            "source": "手动触发报警",
            "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "message": message if message else "用户手动触发的车牌报警"
        }
        
        # 发送报警邮件
        email_sent = email_notifier.send_plate_alarm(
            plate_number=plate_number,
            details=details
        )
        
        if email_sent:
            return JSONResponse(content={"status": "success", "message": "报警邮件发送成功"})
        else:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "报警邮件发送失败"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"报警邮件发送时出错: {str(e)}"})
        

# 获取静态文件
@router.get("/static/{file_path:path}")
async def get_static_file(file_path: str):
    """获取监控静态文件如视频、图片等"""
    full_path = os.path.join(MONITORING_OUTPUT_DIR, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(full_path)
