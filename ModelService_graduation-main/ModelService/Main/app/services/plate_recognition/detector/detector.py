"""
车牌检测模块
提供车牌检测、识别和结果处理相关功能
"""
import os
import sys
import time
import torch
import numpy as np
import logging
import cv2
import copy
import importlib.util
from PIL import Image, ImageDraw, ImageFont
import platform

# 设置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 创建日志对象
logger = logging.getLogger(__name__)

# 用于绘制支持中文的文本函数
def draw_chinese_text(img, text, position, font_size=30, color=(255, 255, 255), thickness=2):
    """在图像上绘制支持中文的文本
    
    Args:
        img: OpenCV格式的图像
        text: 要绘制的文本
        position: 文本位置 (x, y)
        font_size: 字体大小
        color: 文本颜色 RGB格式
        thickness: 字体粗细
        
    Returns:
        处理后的图像
    """
    if not text:
        return img
        
    # 图像转换为PIL格式
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    
    # 加载字体
    try:
        # 根据操作系统选择适合的常见中文字体
        if platform.system() == 'Windows':
            font_path = "C:/Windows/Fonts/simhei.ttf"  # Windows默认黑体
        elif platform.system() == 'Darwin':
            font_path = "/System/Library/Fonts/PingFang.ttc"  # macOS默认
        else:  # Linux和其他系统
            font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
            
        # 检查字体文件是否存在
        if not os.path.exists(font_path):
            # 如果默认路径不存在，尝试其他可能的位置
            common_font_paths = [
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                "/System/Library/Fonts/STHeiti Light.ttc",
                # 在这里添加更多常见字体路径
            ]
            
            for path in common_font_paths:
                if os.path.exists(path):
                    font_path = path
                    break
        
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        logger.error(f"加载中文字体失败: {str(e)}")
        # 如果无法加载中文字体，使用默认字体
        font = ImageFont.load_default()
    
    # 绘制文字通道
    # 绘制文本阴影增强可读性
    for offset in [(2, 2), (-2, -2), (2, -2), (-2, 2)]:
        draw.text((position[0]+offset[0], position[1]+offset[1]), text, font=font, fill=(0, 0, 0))
    
    # 绘制文本
    draw.text(position, text, font=font, fill=color[::-1])  # 将BGR转为RGB
    
    # 转回OpenCV格式
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    return img_cv

# 设置全局路径
MAIN_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DESIGN_COMPETITION_DIR = os.path.join(BASE_DIR, "design_competition")

# 添加必要的模块搜索路径
if MAIN_DIR not in sys.path:
    sys.path.append(MAIN_DIR)
    logger.info(f"添加根目录到Python路径: {MAIN_DIR}")
if DESIGN_COMPETITION_DIR not in sys.path:
    sys.path.append(DESIGN_COMPETITION_DIR)
    logger.info(f"添加design_competition到Python路径: {DESIGN_COMPETITION_DIR}")

# 从必要的模块导入
# 车牌检测相关导入
# 使用正确的模块路径
from ..models.experimental import attempt_load
from ..utilss.datasets import letterbox
from ..utilss.general import check_img_size, non_max_suppression_face, scale_coords
from ..utilss.torch_utils import time_synchronized

# 车牌识别相关导入
from ..recognizer.plate_rec import get_plate_result
from ..recognizer.double_plate_split_merge import get_split_merge
from ..recognizer.car_rec import get_color_and_score

# 检查核心模块是否可用
required_modules = ['models.yolo', 'models.common', 'models.experimental', 
                   'utilss.datasets', 'utilss.general', 'utilss.torch_utils']
modules_status = {}

for module_name in required_modules:
    spec = importlib.util.find_spec(module_name)
    if spec is not None:
        logger.info(f"已找到模块: {module_name}")
        modules_status[module_name] = True
    else:
        logger.error(f"缺失必要模块: {module_name}")
        models_dir = os.path.join(MAIN_DIR, 'models')
        utils_dir = os.path.join(MAIN_DIR, 'utilss')
        logger.info(f"Python路径前三项: {sys.path[:3]}")
        if os.path.exists(models_dir):
            logger.info(f"models目录内容: {os.listdir(models_dir)}")
        if os.path.exists(utils_dir):
            logger.info(f"utilss目录内容: {os.listdir(utils_dir)}")
        modules_status[module_name] = False

# 如果有模块缺失，添加详细警告
if not all(modules_status.values()):
    missing = [m for m, status in modules_status.items() if not status]
    logger.warning(f"缺失必要的模块，这可能导致车牌检测模型加载失败: {missing}")

# 常量定义
COLORS = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (0,255,255)]
DANGER = ['危', '险']
OBJECT_COLOR = [(0,255,255), (0,255,0), (255,255,0)]
CLASS_TYPE = ['单层车牌', '双层车牌', '汽车']

# 最小置信度和IOU阈值
CONF_THRES = 0.3  # 降低阈值以提高检测率
IOU_THRES = 0.4

# 类别ID映射函数
def map_class_num(class_num):
    """
    将模型输出的类别ID映射到标准类别ID: 0(单层车牌), 1(双层车牌), 2(车辆)
    
    参数:
        class_num: 原始类别ID
        
    返回:
        标准类别ID
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 确保class_num是float类型时正确处理
    if isinstance(class_num, float):
        class_num = int(class_num)
    
    logger.info(f"开始类别映射: 原始类别 = {class_num}, 类型 = {type(class_num)}")
    print(f"开始类别映射: 原始类别 = {class_num}, 类型 = {type(class_num)}")
    
    # 获取服务管理器实例，访问类别映射
    from ..service_manager import PlateRecognitionServiceManager
    service_manager = PlateRecognitionServiceManager()
    
    if not hasattr(service_manager, 'class_mapping') or not service_manager.class_mapping:
        # 直接使用原始类别号映射
        if class_num == 0:  # 对应输出中的第一个类别
            mapped = 0  # 单层车牌
        elif class_num == 1:  # 对应输出中的第二个类别
            mapped = 1  # 双层车牌
        elif class_num == 2:  # 对应输出中的第三个类别
            mapped = 2  # 车辆
        else:
            mapped = min(2, max(0, int(class_num)))
            
        logger.info(f"使用直接映射: {class_num} -> {mapped} ({CLASS_TYPE[mapped]})")
        print(f"使用直接映射: {class_num} -> {mapped} ({CLASS_TYPE[mapped]})")
        return mapped
        
    # 反向查找类别
    for key, value in service_manager.class_mapping.items():
        if value == class_num:
            if key == 'single_plate':
                mapped = 0
                logger.info(f"使用服务管理器映射: {key}({class_num}) -> {mapped}")
                print(f"使用服务管理器映射: {key}({class_num}) -> {mapped}")
                return mapped
            elif key == 'double_plate':
                mapped = 1
                logger.info(f"使用服务管理器映射: {key}({class_num}) -> {mapped}")
                print(f"使用服务管理器映射: {key}({class_num}) -> {mapped}")
                return mapped
            elif key == 'vehicle':
                mapped = 2
                logger.info(f"使用服务管理器映射: {key}({class_num}) -> {mapped}")
                print(f"使用服务管理器映射: {key}({class_num}) -> {mapped}")
                return mapped
    
    # 如果找不到匹配项，默认为单层车牌
    logger.warning(f"未找到匹配类别 {class_num}，默认映射为单层车牌(0)")
    print(f"未找到匹配类别 {class_num}，默认映射为单层车牌(0)")
    return 0

# 获取当前文件所在路径作为基础路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def order_points(pts):
    """四个点按照左上、右上、右下、左下排列"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    """透视变换得到车牌小图"""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped

def load_model(weights, device):
    """加载模型"""
    try:
        # 确保能够正确导入models.yolo模块
        sys.path.insert(0, MAIN_DIR)  # 将主目录放在最前面
        
        # 记录加载情况
        logger.info(f"开始加载模型: {weights}")
        logger.info(f"当前Python路径: {sys.path[:3]}...")
        
        # 检查模型文件是否存在
        if not os.path.exists(weights):
            logger.error(f"模型文件不存在: {weights}")
            return None
            
        # 加载模型
        model = attempt_load(weights, map_location=device)
        logger.info(f"模型加载成功: {type(model).__name__}")
        
        return model
    except Exception as e:
        logger.error(f"模型加载失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def scale_coords_landmarks(img1_shape, coords, img0_shape, ratio_pad=None):
    """缩放关键点坐标"""
    # Rescale coords (xyxy) from img1_shape to img0_shape
    if ratio_pad is None:  # calculate from img0_shape
        gain = min(img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1])  # gain  = old / new
        pad = (img1_shape[1] - img0_shape[1] * gain) / 2, (img1_shape[0] - img0_shape[0] * gain) / 2  # wh padding
    else:
        gain = ratio_pad[0][0]
        pad = ratio_pad[1]

    coords[:, [0, 2, 4, 6]] -= pad[0]  # x padding
    coords[:, [1, 3, 5, 7]] -= pad[1]  # y padding
    coords[:, :8] /= gain
    #clip_coords(coords, img0_shape)
    coords[:, 0].clamp_(0, img0_shape[1])  # x1
    coords[:, 1].clamp_(0, img0_shape[0])  # y1
    coords[:, 2].clamp_(0, img0_shape[1])  # x2
    coords[:, 3].clamp_(0, img0_shape[0])  # y2
    coords[:, 4].clamp_(0, img0_shape[1])  # x3
    coords[:, 5].clamp_(0, img0_shape[0])  # y3
    coords[:, 6].clamp_(0, img0_shape[1])  # x4
    coords[:, 7].clamp_(0, img0_shape[0])  # y4
    return coords

def enhance_plate_image(roi_img):
    """增强车牌图像质量
    
    参数:
        roi_img: 车牌区域图像
    返回:
        enhanced_img: 增强后的车牌图像
    """
    try:
        # 转换为灰度图
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        
        # 评估图像清晰度
        blurness = cv2.Laplacian(gray, cv2.CV_64F).var()
        logger.info(f"车牌图像清晰度: {blurness:.2f}")
        
        # 如果图像较模糊，应用增强
        if blurness < 100:
            logger.info("车牌图像较模糊，应用图像增强")
            
            # 自适应直方图均衡化
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced_gray = clahe.apply(gray)
            
            # 降噪处理
            denoised = cv2.fastNlMeansDenoising(enhanced_gray, None, 10, 7, 21)
            
            # 锐化处理
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            # 二值化处理，以进一步增强车牌文字
            _, binary = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 重新转换为彩色图像保持与原接口兼容
            enhanced_img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
            
            # 保存增强后的车牌小图
            debug_dir = os.path.join(BASE_DIR, "static", "debug")
            os.makedirs(debug_dir, exist_ok=True)
            enhanced_filename = os.path.join(debug_dir, f"enhanced_plate_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
            cv2.imwrite(enhanced_filename, enhanced_img)
            logger.info(f"保存增强后的车牌小图: {enhanced_filename}")
            
            return enhanced_img
        else:
            # 图像清晰度足够，仅做基本增强
            # 自适应直方图均衡化提高对比度
            clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8,8))
            lab = cv2.cvtColor(roi_img, cv2.COLOR_BGR2LAB)
            lab[:,:,0] = clahe.apply(lab[:,:,0])
            enhanced_img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # 对比度略微增强
            enhanced_img = cv2.convertScaleAbs(enhanced_img, alpha=1.2, beta=5)
            
            return enhanced_img
    except Exception as e:
        logger.error(f"车牌图像增强处理出错: {str(e)}")
        return roi_img  # 出错时返回原图

def detect_plate_type(roi_img):
    """智能检测车牌类型，区分普通蓝牌、黄牌、新能源绿牌等
    
    参数:
        roi_img: 车牌区域图像
    返回:
        plate_type: 检测到的车牌类型
    """
    try:
        # 转换为HSV空间进行颜色分析
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        
        # 蓝牌特征
        blue_lower = np.array([100, 50, 50])
        blue_upper = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
        blue_ratio = np.count_nonzero(blue_mask) / (roi_img.shape[0] * roi_img.shape[1])
        
        # 绿牌特征（新能源）
        green_lower = np.array([35, 50, 50])
        green_upper = np.array([90, 255, 255])
        green_mask = cv2.inRange(hsv, green_lower, green_upper)
        green_ratio = np.count_nonzero(green_mask) / (roi_img.shape[0] * roi_img.shape[1])
        
        # 黄牌特征
        yellow_lower = np.array([15, 50, 50])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        yellow_ratio = np.count_nonzero(yellow_mask) / (roi_img.shape[0] * roi_img.shape[1])
        
        # 根据占比确定车牌类型
        ratios = {
            '蓝牌': blue_ratio,
            '绿牌': green_ratio,
            '黄牌': yellow_ratio
        }
        
        detected_type = max(ratios, key=ratios.get)
        logger.info(f"车牌颜色分析: 蓝={blue_ratio:.2f}, 绿={green_ratio:.2f}, 黄={yellow_ratio:.2f}, 检测类型={detected_type}")
        
        return detected_type
    except Exception as e:
        logger.error(f"车牌类型检测出错: {str(e)}")
        return "未知"  # 出错时返回未知类型

def get_plate_rec_landmark(img, xyxy, conf, landmarks, class_num, device, plate_rec_model, car_rec_model=None):
    """
    识别车牌文字和汽车颜色
    
    Args:
        img: 输入图像
        xyxy: 检测框坐标 [x1,y1,x2,y2]
        conf: 检测置信度
        landmarks: 关键点坐标
        class_num: 类别编号 (0=单层车牌, 1=双层车牌, 2=汽车)
        device: 设备
        plate_rec_model: 车牌识别模型
        car_rec_model: 车辆颜色识别模型（可选） 
        
    Returns:
        result_dict: 包含车牌号码、颜色等信息的字典
    """
    # 为避免后续未定义错误，先定义类别映射
    CLASS_TYPE = ['single_plate', 'double_plate', 'vehicle']
    
    try:
        h, w, c = img.shape
        result_dict = {}
        x1 = max(0, int(xyxy[0]))
        y1 = max(0, int(xyxy[1]))
        x2 = min(w-1, int(xyxy[2]))
        y2 = min(h-1, int(xyxy[3]))
        
        # 检查是否是有效的检测框
        if x2 <= x1 or y2 <= y1 or (x2-x1) < 10 or (y2-y1) < 5:
            logger.warning(f"无效的检测框: [{x1}, {y1}, {x2}, {y2}], 使用默认值")
            # 使用原始图像的中心区域作为默认检测区域
            center_x, center_y = w//2, h//2
            box_w, box_h = min(w//3, 120), min(h//8, 40) # 适合车牌的比例
            x1, y1 = center_x - box_w//2, center_y - box_h//2
            x2, y2 = center_x + box_w//2, center_y + box_h//2
            
        landmarks_np = np.zeros((4, 2))
        rect = [x1, y1, x2, y2]
        
        # 如果是车辆类别而非车牌
        if int(class_num) == 2:
            if car_rec_model is not None:
                # 提取车辆ROI并识别颜色
                car_roi_img = img[y1:y2, x1:x2]
                try:
                    # 添加异常处理，确保即使车辆颜色识别失败也能继续执行
                    color_result = get_color_and_score(car_rec_model, car_roi_img, device)
                    # 结果不为None且是元组/列表/字典
                    if color_result and isinstance(color_result, (tuple, list)) and len(color_result) == 2:
                        car_color, color_conf = color_result
                    else:
                        # 返回值不符合预期，使用默认値
                        car_color, color_conf = '未知', 0.0
                        logger.warning("车辆颜色识别返回值格式不正确")
                except Exception as e:
                    # 异常处理，确保程序继续运行
                    car_color, color_conf = '未知', 0.0
                    logger.error(f"车辆颜色识别出错: {str(e)}")
                
                # 填充结果
                result_dict['class_type'] = CLASS_TYPE[int(class_num)]
                result_dict['rect'] = rect  # 车辆roi坐标
                result_dict['score'] = conf  # 车辆检测得分
                result_dict['object_no'] = int(class_num)
                result_dict['car_color'] = car_color
                result_dict['color_conf'] = color_conf
            else:
                logger.warning("车辆识别模型未加载，无法识别车辆颜色")
                result_dict['class_type'] = CLASS_TYPE[int(class_num)]
                result_dict['rect'] = rect
                result_dict['score'] = conf
                result_dict['object_no'] = int(class_num)
            return result_dict
        
        # 提取车牌四个角点坐标
        for i in range(4):
            point_x = int(landmarks[2 * i])
            point_y = int(landmarks[2 * i + 1])
            landmarks_np[i] = np.array([point_x, point_y])
        
        # 汇总信息
        class_label = int(class_num)
        CLASS_TYPE = ['single_plate', 'double_plate', 'vehicle']
        DANGER = ["危", "dan"]
        
        # 输出详细调试信息
        logger.info(f"检测到类别: {class_label}, 类别名称: {CLASS_TYPE[class_label]} 置信度: {conf:.4f}")
        logger.info(f"检测到的坐标: {xyxy}, 关键点: {landmarks}")
        
        # 透视变换得到车牌小图
        roi_img = four_point_transform(img, landmarks_np)
        
        # 保存原始ROI用于备份识别
        original_roi_img = roi_img.copy()
        
        # 应用图像增强处理(提高清晰度、对比度)
        enhanced_roi_img = enhance_plate_image(roi_img)
        
        # 对双层车牌进行分割后拼接处理
        if class_label == 1:
            roi_img = get_split_merge(roi_img)  # 原始图像处理
            enhanced_roi_img = get_split_merge(enhanced_roi_img)  # 增强图像处理
            
        # 识别车牌号码和颜色 - 先用增强版尝试
        try:
            # get_plate_result现在只返回2个值：车牌号码和颜色名称
            plate_no, plate_color_str = get_plate_result(enhanced_roi_img, device, plate_rec_model)
            # 根据颜色名称确定车牌类型
            plate_type_str = '单行蓝牌'  # 默认类型
            if len(plate_no) >= 8:  # 双层车牌字符数量通常更8个或以上
                plate_type_str = f'双行{plate_color_str}'
            elif plate_color_str == '黄色':
                plate_type_str = '单行黄牌'
            elif plate_color_str == '绿色':
                plate_type_str = '单行绿牌'
            logger.info(f"增强图像识别结果：车牌={plate_no}, 颜色={plate_color_str}, 类型={plate_type_str}")
            logger.info(f"识别结果有效性评估: 长度={len(plate_no) if plate_no else 0}, 第一个字符={plate_no[0] if plate_no and len(plate_no) > 0 else '无'}")
            
            # 注意：这里我们不需要颜色模型的颜色识别功能，因为plate_rec_model已经返回了颜色结果
            # 后续如果需要专用的颜色识别模型，则需要在函数参数中添加对应的颜色识别模型
            
            # 如果没有有效的车牌号，使用原始图像识别结果
            if not plate_no or len(plate_no) < 7 or not plate_no[0].isalnum():
                try:
                    orig_plate_no, orig_color_str = get_plate_result(roi_img, device, plate_rec_model)
                    # 根据颜色名称确定车牌类型
                    orig_type_str = '单行蓝牌'  # 默认类型
                    if len(orig_plate_no) >= 8:
                        orig_type_str = f'双行{orig_color_str}'
                    elif orig_color_str == '黄色':
                        orig_type_str = '单行黄牌'
                    elif orig_color_str == '绿色':
                        orig_type_str = '单行绿牌'
                    logger.info(f"原始图像识别结果：车牌={orig_plate_no}, 类型={orig_type_str}, 颜色={orig_color_str}")
                    
                    # 使用原始图像结果，即使不完整也使用
                    if orig_plate_no:
                        logger.info("使用原始图像识别结果")
                        plate_no = orig_plate_no
                        # 使用原始识别的颜色和类型
                        plate_type_str = orig_type_str
                        plate_color_str = orig_color_str
                except Exception as e:
                    logger.error(f"原始图像车牌识别处理时出错: {str(e)}")
            
            # 校验车牌号合法性
            if plate_no and len(plate_no) >= 7:
                # 确保第一个字符是省份缩写或者特殊车牌标识
                valid_first_chars = "京津沪渝冀晋蒙辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云藏陕甘青宁新学警港澳"
                if plate_no[0] not in valid_first_chars:
                    logger.warning(f"车牌首字符不合法: {plate_no[0]}，尝试修正")
                    # 尝试修正为最可能的省份
                    plate_no = "京" + plate_no[1:]
            else:
                logger.warning("车牌号识别失败或不完整")
                plate_no = ""
                plate_color_str = ""
                plate_type_str = ""
                
        except Exception as e:
            logger.error(f"车牌识别处理时出错: {str(e)}")
            plate_no = ""
            color_idx = 0  # 这个变量没有使用，但保留以避免修改结构
            plate_type_str = ""  # 使用空字符串代替"未知"
            plate_color_str = ""  # 使用空字符串代替颜色信息
            
        # 最后一次尝试 - 使用不同尺度的ROI
        if not plate_no or len(plate_no) < 7:
            logger.warning("尝试使用不同尺度的ROI进行最后识别")
            try:
                # 调整ROI大小进行最后尝试
                scales = [0.8, 1.2, 0.9, 1.1]  # 尝试的缩放比例
                for scale in scales:
                    scaled_roi = cv2.resize(original_roi_img, None, fx=scale, fy=scale, 
                                           interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
                    # 针对双层车牌进行特殊处理
                    # 注意：这里是双层车牌识别的关键点
                    # class_label == 1 表示这是双层车牌
                    if class_label == 1:
                        logger.info("检测到双层车牌，应用特殊处理")
                        # 保存原始图片便于调试
                        debug_dir = os.path.join(MAIN_DIR, "debug_images")
                        os.makedirs(debug_dir, exist_ok=True)
                        cv2.imwrite(os.path.join(debug_dir, f"double_plate_original_{time.time()}.jpg"), scaled_roi)
                        
                        # 使用双层车牌特殊处理函数
                        scaled_roi = get_split_merge(scaled_roi)
                        
                        # 保存处理后的图片便于调试
                        cv2.imwrite(os.path.join(debug_dir, f"double_plate_processed_{time.time()}.jpg"), scaled_roi)
                    
                    try:
                        rescaled_plate_no, rescaled_color_str = get_plate_result(scaled_roi, device, plate_rec_model)
                        # 根据颜色名称确定车牌类型
                        rescaled_type_str = '单行蓝牌'  # 默认类型
                        if len(rescaled_plate_no) >= 8:
                            rescaled_type_str = f'双行{rescaled_color_str}'
                        elif rescaled_color_str == '黄色':
                            rescaled_type_str = '单行黄牌'
                        elif rescaled_color_str == '绿色':
                            rescaled_type_str = '单行绿牌'
                        logger.info(f"缩放尺度{scale}识别结果：车牌={rescaled_plate_no}, 类型={rescaled_type_str}, 颜色={rescaled_color_str}")
                        
                        # 降低判断标准，只要有车牌号就使用
                        if rescaled_plate_no:
                            logger.info(f"使用缩放尺度{scale}识别结果")
                            plate_no = rescaled_plate_no
                            plate_type_str = rescaled_type_str
                            plate_color_str = rescaled_color_str
                            break
                    except Exception as e:
                        logger.error(f"缩放尺度{scale}识别出错: {str(e)}")
            except Exception as e:
                logger.error(f"多尺度识别尝试失败: {str(e)}")
        
        # 不再将检测到的车牌替换为「危险品」标签
        # 如果实际识别到了危险品车牌，直接显示原始车牌号
        # 只记录但不修改车牌号
        for dan in DANGER:
            if plate_no and dan in plate_no:
                logger.info(f"  检测到可能的危险品车牌: {plate_no}, 包含关键词: {dan}")
                break
        
        # 在源头就过滤掉短车牌
        if plate_no and len(plate_no) <= 5:
            logger.warning(f"检测到短车牌，已过滤: '{plate_no}' [长度: {len(plate_no)}]")
            plate_no = ""
        
        # 如果没有检测到有效车牌，直接设置为未知而不使用描述性文本
        if not plate_no:
            plate_no = '未知'
            # 记录原因
            logger.info(f"  车牌识别失败，设置为未知，车牌颜色: {plate_color_str}")
        
        # 输出车牌识别信息 - 完全使用模型预测结果
        logger.info(f"车牌识别信息: {plate_no}, 颜色: {plate_color_str}, 类型: {plate_type_str}")
        
        # 记录双层车牌信息
        if class_label == 1:
            logger.info(f"检测到双层车牌，颜色: {plate_color_str}")


        
        # 处理双层车牌，只基于实际检测结果
        is_double_plate = False
        
        # 仅当模型真正检测到它是双层车牌时才设置
        if class_label == 1:
            logger.info(f"检测到双层车牌: 类别={class_label}, 车牌号={plate_no}")
            is_double_plate = True
            
            # 如果是双层车牌，则记录其结构信息
            if plate_no and len(plate_no) >= 7:
                # 分析车牌结构
                first_char = plate_no[0]  # 省份简称
                second_char = plate_no[1]  # 字母
                rest_chars = plate_no[2:]  # 剩余字符
                
                logger.info(f"双层车牌结构: 省份={first_char}, 区域字母={second_char}, 唯一标识符={rest_chars}")
                
                # 记录车牌结构信息供前端处理
                result_dict['original_plate_no'] = plate_no
                result_dict['is_double_plate'] = True
                result_dict['plate_parts'] = {
                    'upper': f"{first_char}{second_char}",  # 上部分
                    'lower': rest_chars  # 下部分
                }
                
                logger.info(f"双层车牌信息已记录: {plate_no}")
            else:
                logger.warning(f"检测到双层车牌，但格式不符合预期: {plate_no}")
        
        # 注意：这里不强制转换车牌类型和颜色，而是保留模型的原始识别结果
        
        # 填充结果字典
        result_dict['class_type'] = CLASS_TYPE[class_label] 
        result_dict['rect'] = rect  # 车牌边框坐标
        result_dict['landmarks'] = landmarks_np.tolist()  # 车牌角点坐标
        result_dict['plate_no'] = plate_no  # 车牌号
        result_dict['roi_height'] = roi_img.shape[0]  # 车牌高度
        result_dict['plate_color'] = plate_color_str  # 车牌颜色
        result_dict['plate_type'] = plate_type_str  # 完全使用模型预测的车牌类型
        result_dict['object_no'] = 1 if is_double_plate else class_label  # 单双层 0单层 1双层
        result_dict['score'] = conf  # 车牌区域检测得分
    except Exception as e:
        logger.error(f"车牌识别处理时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {}
    
    return result_dict

def get_adaptive_threshold(image):
    """基于图像质量自适应调整置信度阈值
    
    参数:
        image: 输入图像
        
    返回:
        conf_thres: 调整后的置信度阈值
        iou_thres: 调整后的IOU阈值
    """
    # 基础阈值
    base_conf = CONF_THRES
    base_iou = IOU_THRES
    
    try:
        # 评估清晰度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurness = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # 计算亮度和对比度
        brightness = np.mean(gray)
        contrast = np.std(gray)
        
        # 基于清晰度调整置信度
        if blurness < 50:  # 非常模糊
            conf_thres = base_conf - 0.15  # 大幅降低阈值以提高召回率
            iou_thres = base_iou - 0.1
            logger.info(f"图像非常模糊({blurness:.2f})，调整置信度阈值至 {conf_thres:.2f}")
        elif blurness < 100:  # 较模糊
            conf_thres = base_conf - 0.1
            iou_thres = base_iou - 0.05
            logger.info(f"图像较模糊({blurness:.2f})，调整置信度阈值至 {conf_thres:.2f}")
        elif blurness > 300:  # 非常清晰
            conf_thres = base_conf + 0.05
            iou_thres = base_iou + 0.05
            logger.info(f"图像非常清晰({blurness:.2f})，调整置信度阈值至 {conf_thres:.2f}")
        else:  # 正常清晰度
            conf_thres = base_conf
            iou_thres = base_iou
            logger.info(f"图像清晰度正常({blurness:.2f})，使用标准置信度阈值 {conf_thres:.2f}")
        
        # 基于亮度进一步调整
        if brightness < 50:  # 过暗
            conf_thres -= 0.05
            logger.info(f"图像过暗({brightness:.2f})，进一步降低阈值至 {conf_thres:.2f}")
        elif brightness > 200:  # 过亮
            conf_thres -= 0.05
            logger.info(f"图像过亮({brightness:.2f})，进一步降低阈值至 {conf_thres:.2f}")
            
        # 基于对比度进一步调整
        if contrast < 30:  # 低对比度
            conf_thres -= 0.05
            logger.info(f"图像对比度低({contrast:.2f})，进一步降低阈值至 {conf_thres:.2f}")
            
        # 设置参数地板和上限
        conf_thres = max(0.2, min(conf_thres, 0.7))  # 限制在 0.2-0.7 范围内
        iou_thres = max(0.3, min(iou_thres, 0.6))   # 限制在 0.3-0.6 范围内
        
        return conf_thres, iou_thres
    except Exception as e:
        logger.error(f"自适应阈值计算出错: {str(e)}")
        return base_conf, base_iou

def detect_Recognition_plate(model, orgimg, device, plate_rec_model, img_size, car_rec_model=None, conf_thres=None):
    """
    车牌检测与识别主函数 (增强版)
    
    参数:
        model: 检测模型
        orgimg: 原始图像
        device: 设备类型(CPU/GPU)
        plate_rec_model: 车牌识别模型
        img_size: 图像尺寸
        car_rec_model: 车辆识别模型(可选)
        conf_thres: 置信度阈值，如果为None则使用自适应阈值
        
    返回:
        dict_list: 识别结果列表
    """
    dict_list = []
    
    logger.info("\n---------- 车牌识别开始 (增强版) ----------")
    logger.info(f"输入图像形状: {orgimg.shape}")
    
    # 确定阈值：如果外部传入了conf_thres，则使用外部值；否则根据图像质量自适应确定阈值
    if conf_thres is None:
        # 使用自适应阈值
        conf_thres, iou_thres = get_adaptive_threshold(orgimg)
        logger.info(f"使用自适应置信度阈值: conf_thres={conf_thres}, iou_thres={iou_thres}")
    else:
        # 使用外部传入的置信度阈值，但仍使用自适应计算的IOU阈值
        _, iou_thres = get_adaptive_threshold(orgimg)
        logger.info(f"使用外部传入置信度阈值: conf_thres={conf_thres}, iou_thres={iou_thres}")
    
    # 保存检测用的输入图像以便分析
    debug_dir = os.path.join(BASE_DIR, "static", "debug")
    os.makedirs(debug_dir, exist_ok=True)
    debug_filename = os.path.join(debug_dir, f"input_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
    cv2.imwrite(debug_filename, orgimg)
    logger.info(f"保存输入图像至: {debug_filename}")
    
    # 查看原始图像尺寸
    img0 = copy.deepcopy(orgimg)
    assert orgimg is not None, 'Image Not Found'
    h0, w0 = orgimg.shape[:2]  # 原始图像高宽
    
    # 图像预处理 - 调整大小
    r = img_size / max(h0, w0)  # resize image to img_size
    if r != 1:  # always resize down, only resize up if training with augmentation
        interp = cv2.INTER_AREA if r < 1 else cv2.INTER_LINEAR
        img0 = cv2.resize(img0, (int(w0 * r), int(h0 * r)), interpolation=interp)
        logger.info(f"调整图像大小: 原始尺寸={h0}x{w0}, 调整后尺寸={img0.shape[0]}x{img0.shape[1]}")
    
    # 图像预处理 - 检查并调整输入尺寸
    # 先检查模型是否加载成功
    if model is None:
        logger.error("车牌检测模型未成功加载")
        return []
        
    imgsz = check_img_size(img_size, s=model.stride.max())  # 检查图像尺寸
    logger.info(f"模型输入尺寸: {imgsz}")

    # 图像预处理 - letterbox填充
    img = letterbox(img0, new_shape=imgsz)[0]
    logger.info(f"填充后图像形状: {img.shape}")
    
    # 转换为模型输入格式
    img = img[:, :, ::-1].transpose(2, 0, 1).copy()  # BGR to RGB, to 3x416x416

    # 开始推理计时
    t0 = time.time()

    # 转为Tensor
    img = torch.from_numpy(img).to(device)
    img = img.float()  # uint8 to fp16/32
    img /= 255.0  # 0 - 255 to 0.0 - 1.0
    if img.ndimension() == 3:
        img = img.unsqueeze(0)
    logger.info(f"输入Tensor形状: {img.shape}")
    
    # 模型推理
    t1 = time_synchronized()
    try:
        pred = model(img)[0]
        t2 = time_synchronized()
        logger.info(f"模型推理耗时: {(t2-t1)*1000:.2f} ms")
    except Exception as e:
        logger.error(f"模型推理错误: {str(e)}")
        return []
    
    # 应用NMS
    try:
        pred = non_max_suppression_face(pred, conf_thres, iou_thres)
        logger.info(f"NMS后检测数量: {len(pred[0]) if len(pred) > 0 else 0}")
    except Exception as e:
        logger.error(f"NMS处理错误: {str(e)}")
        return []
    
    # 如果没有检测到任何目标，尝试多尺度检测
    if len(pred[0]) == 0:
        logger.warning("没有检测到任何车牌或车辆，尝试多尺度检测策略")
        
        multi_scale_results = []
        scales = [0.5, 0.75, 1.25, 1.5]  # 多种缩放尺度
        
        try:
            # 逐个尺度尝试
            for scale in scales:
                logger.info(f"尝试使用尺度缩放倍数: {scale}")
                # 调整图像大小
                h0, w0 = orgimg.shape[:2]  # 原始图像高宽
                h, w = int(h0 * scale), int(w0 * scale)
                resized_img = cv2.resize(orgimg, (w, h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
                
                # 保存缩放后的图像用于分析
                scaled_filename = os.path.join(debug_dir, f"scaled_{scale}_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
                cv2.imwrite(scaled_filename, resized_img)
                logger.info(f"已保存缩放后的图像: {scaled_filename}")
                
                # 将缩放的检测结果转换为原始坐标系，使用同样的conf_thres值
                scaled_results = detect_Recognition_plate(model, resized_img, device, plate_rec_model, img_size, car_rec_model, conf_thres=conf_thres)
                
                # 如果有检测结果，调整坐标回原始图像
                if scaled_results:
                    logger.info(f"在尺度 {scale} 下检测到 {len(scaled_results)} 个结果")
                    for result in scaled_results:
                        # 调整坐标回原始图像大小
                        if 'rect' in result:
                            x1, y1, x2, y2 = result['rect']
                            result['rect'] = [int(x1/scale), int(y1/scale), int(x2/scale), int(y2/scale)]
                            
                        if 'landmarks' in result:
                            adjusted_landmarks = []
                            for point in result['landmarks']:
                                adjusted_landmarks.append([int(point[0]/scale), int(point[1]/scale)])
                            result['landmarks'] = adjusted_landmarks
                            
                        # 增加一个尺度信息标记
                        result['scale_factor'] = scale
                        multi_scale_results.append(result)
            
            # 如果多尺度检测有结果
            if multi_scale_results:
                logger.info(f"多尺度检测成功: 共找到 {len(multi_scale_results)} 个结果")
                return multi_scale_results
                
            # 如果多尺度仍然失败，再尝试图像增强
            logger.warning("多尺度检测失败，尝试图像增强策略")
            enhanced = cv2.convertScaleAbs(orgimg, alpha=1.5, beta=10)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            lab[:,:,0] = clahe.apply(lab[:,:,0])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # 保存增强后的图像用于分析
            enhanced_filename = os.path.join(debug_dir, f"enhanced_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
            cv2.imwrite(enhanced_filename, enhanced)
            logger.info(f"已保存增强后的图像: {enhanced_filename}")
            
            # 尝试用增强后的图像再次识别
            enhanced_dict_list = detect_Recognition_plate(model, enhanced, device, plate_rec_model, img_size, car_rec_model)
            if enhanced_dict_list:
                logger.info(f"增强图像成功识别车牌: 找到 {len(enhanced_dict_list)} 个结果")
                return enhanced_dict_list
                
        except Exception as e:
            logger.error(f"多尺度检测和图像增强失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return []
    
    # 查看检测结果
    dict_list = []
    for i, det in enumerate(pred):  # detections per image
        if len(det) == 0:
            continue
            
        # 信息汇总
        det_count = len(det)
        logger.info(f"检测到 {det_count} 个可能的车牌或车辆")
        
        # 检查模型类别名称
        model_classes = None
        if hasattr(model, 'names') and model.names:
            model_classes = model.names
            logger.info(f"模型包含以下类别: {model_classes}")
            
        # 根据类别统计数量
        class_counts = {}
        abnormal_classes = []
        
        for *xyxy, conf, cls in det:
            cls_val = cls.item()
            
            # 如果类别值异常，则收集一下
            if isinstance(cls_val, (int, float)) and (cls_val > 10 or cls_val < 0):
                if cls_val not in abnormal_classes:
                    abnormal_classes.append(cls_val)
            
            # 映射到标准类别ID
            std_cls_val = map_class_num(cls_val)
            logger.info(f"类别ID映射: 原始={cls_val} => 标准={std_cls_val}")
            
            # 使用标准类别ID计数
            if std_cls_val not in class_counts:
                class_counts[std_cls_val] = 0
            class_counts[std_cls_val] += 1
            
        # 打印各类别数量
        for cls, count in class_counts.items():
            logger.info(f"类别 {cls} 检测数量: {count}")
            
        # 如果发现异常类别，记录日志
        if abnormal_classes:
            logger.warning(f"检测到异常类别 ID: {abnormal_classes}\n"
                         f"请检查模型文件是否与代码版本匹配")

        # 重新缩放边界框
        det[:, :4] = scale_coords(img.shape[2:], det[:, :4], orgimg.shape).round()
            
        # 打印各类别数量
        for c in det[:, -1].unique():
            n = (det[:, -1] == c).sum()  # detections per class
            logger.info(f"类别 {int(c)} 检测数量: {n}")
            
        # 重新缩放关键点坐标
        det[:, 5:13] = scale_coords_landmarks(img.shape[2:], det[:, 5:13], orgimg.shape).round()
        
        # 逻个处理检测结果
        for j in range(det.size()[0]):
            try:
                xyxy = det[j, :4].view(-1).tolist()
                conf = det[j, 4].cpu().numpy()
                landmarks = det[j, 5:13].view(-1).tolist()
                class_num = det[j, 13].cpu().numpy()
                
                # 映射类别ID到标准ID
                orig_class_num = class_num
                class_num = map_class_num(class_num)
                logger.info(f"检测 #{j+1}: 原始类别={orig_class_num}, 映射后类别={class_num}, 置信度={conf:.4f}")
                logger.info(f"  位置: x1={xyxy[0]:.1f}, y1={xyxy[1]:.1f}, x2={xyxy[2]:.1f}, y2={xyxy[3]:.1f}")
                
                # 保存检测到的区域
                roi = orgimg[int(xyxy[1]):int(xyxy[3]), int(xyxy[0]):int(xyxy[2])]
                if roi.size > 0:
                    roi_filename = os.path.join(debug_dir, f"roi_{j}_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
                    cv2.imwrite(roi_filename, roi)
                    logger.info(f"  ROI已保存: {roi_filename}")
                
                # 已经在前面应用了类别映射，确保类别ID在有效范围（0-2）内
                if not isinstance(class_num, (int, np.int32, np.int64)) or class_num < 0 or class_num > 2:
                    # 如果类别ID仍然异常，将其约束到有效范围
                    logger.warning(f"类别ID约束: {class_num} => {min(2, max(0, int(class_num)))}")
                    class_num = min(2, max(0, int(class_num)))
                
                # 处理conf，确保它是一个合理的浮点数（0-1之间）
                if conf > 1.0:
                    # 如果置信度异常大，将其调整到合理范围
                    logger.warning(f"置信度异常: {conf}，将其调整为0.95")
                    conf = 0.95
                
                # 识别车牌
                result_dict = get_plate_rec_landmark(orgimg, xyxy, conf, landmarks, class_num, device, plate_rec_model, car_rec_model)
                
                # 打印识别结果
                if 'plate_no' in result_dict:
                    logger.info(f"  识别结果: 车牌={result_dict['plate_no']}, 颜色={result_dict.get('plate_color', '未知')}")
                elif 'car_color' in result_dict:
                    logger.info(f"  识别结果: 车辆颜色={result_dict['car_color']}")
                else:
                    logger.info("  识别结果: 未能识别车牌")
                
                dict_list.append(result_dict)
            except Exception as e:
                logger.error(f"处理检测结果 #{j+1} 时出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning("处理后没有检测结果")
    
    # 计算总耗时
    total_time = time.time() - t0
    logger.info(f"车牌识别总耗时: {total_time*1000:.2f} ms")
    logger.info("―――――――― 车牌识别结束 ――――――――\n")
    
    return dict_list

def draw_result(orgimg, dict_list, highlight_plate=None):
    """
    绘制检测识别结果，增强版

    参数:
        orgimg: 原始图像
        dict_list: 识别结果列表
        highlight_plate: 需要高亮的目标车牌号，如果不为None，则只显示该车牌

    返回:
        processed_img: 处理后的图像
    """
    processed_img = orgimg.copy()

    if dict_list is None or len(dict_list) == 0:
        # 使用中文渲染函数显示未检测到车牌
        processed_img = draw_chinese_text(processed_img, "未检测到车牌", (50, 50), font_size=40, color=(0, 0, 255), thickness=2)
        return processed_img

    # 设置车牌类型颜色映射
    plate_type_colors = {
        '蓝牌': (255, 140, 0),  # 橙色
        '绿牌': (0, 255, 0),   # 绿色
        '黄牌': (0, 215, 255), # 黄色
        '白牌': (255, 255, 255), # 白色
        '未知': (180, 180, 180)  # 灰色
    }

    found_match = False  # 记录是否找到目标车牌

    # 先为高亮车牌保留一个列表
    highlighted_items = []
    normal_items = []

    # 分类所有项
    for item in dict_list:
        if highlight_plate is not None and 'plate_no' in item and item['plate_no'] == highlight_plate:
            highlighted_items.append(item)
            found_match = True
        else:
            normal_items.append(item)

    # 排序列表，优先渲染非高亮项，然后是高亮项
    items_to_draw = normal_items + highlighted_items if highlighted_items else dict_list

    # 如果要求高亮特定车牌但未找到匹配
    if highlight_plate is not None and not found_match:
        text = f"未找到车牌: {highlight_plate}"
        # 使用中文渲染函数替代cv2.putText
        processed_img = draw_chinese_text(processed_img, text, (50, 50), font_size=30, color=(0, 0, 255), thickness=2)

    # 如果要求高亮但仅显示高亮项，则只渲染高亮项
    if highlight_plate is not None and not found_match and len(items_to_draw) == len(normal_items):
        return processed_img

    # 逐一绘制所有项
    for item in items_to_draw:
        # 跳过没有rect的项
        if 'rect' not in item:
            continue

        rect = item['rect']
        x, y, w, h = int(rect[0]), int(rect[1]), int(rect[2]) - int(rect[0]), int(rect[3]) - int(rect[1])

        # 确定颜色
        is_highlighted = highlight_plate is not None and 'plate_no' in item and item['plate_no'] == highlight_plate

        # 设置边框颜色和粗细
        if is_highlighted:
            # 目标车牌的高亮边框 - 始终使用红色
            border_color = (0, 0, 255)  # 红色
            border_thickness = 3
            text_color = (0, 0, 255)  # 红色文本
            font_size = 35  # 较大字体
            
            # 增加额外的高亮效果 - 双重边框
            # 先画一个外部边框
            outer_padding = 2
            cv2.rectangle(processed_img, 
                         (x-outer_padding, y-outer_padding), 
                         (x+w+outer_padding, y+h+outer_padding), 
                         (0, 140, 255), 2)  # 橙红色外框
            
            box = item['rect']
            # 计算更准确的车牌边框 - 根据图像的实际大小进行调整
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            
            # 增加宽度稍微调整，使边框更精确地围绕车牌
            plate_width = x2 - x1
            plate_height = y2 - y1
            
            # 高宽比异常时进行调整
            if plate_width > 0 and plate_height > 0:
                aspect_ratio = plate_width / plate_height
                
                # 如果车牌宽度过大，可能是识别有偏差
                if aspect_ratio > 5.0:  # 正常车牌宽高比应为3-4
                    # 减小边框宽度，集中在中间区域
                    mid_x = (x1 + x2) // 2
                    new_half_width = int(plate_height * 2.5)  # 合理的宽高比
                    x1 = mid_x - new_half_width
                    x2 = mid_x + new_half_width
                
                # 如果车牌过小，稍微扩大
                if plate_width < 30 or plate_height < 10:
                    grow_factor = 1.5
                    mid_x = (x1 + x2) // 2
                    mid_y = (y1 + y2) // 2
                    half_width = int(plate_width * grow_factor / 2)
                    half_height = int(plate_height * grow_factor / 2)
                    x1 = mid_x - half_width
                    x2 = mid_x + half_width
                    y1 = mid_y - half_height
                    y2 = mid_y + half_height
            
            # 红色精细框标记目标车牌
            # 绘制双重边框：外框橙红色，内框红色
            cv2.rectangle(processed_img, 
                        (max(0, x1), max(0, y1)), 
                        (min(processed_img.shape[1], x2), min(processed_img.shape[0], y2)), 
                        (0, 0, 255), 2)  # 红色内框
        else:
            # 非目标车牌使用青绿色边框
            border_color = (54, 197, 238)  # 青绿色（BGR格式）
            border_thickness = 2
            text_color = (54, 197, 238)  # 青绿色文本
            font_size = 30  # 标准字体

        # 绘制检测框
        cv2.rectangle(processed_img, (x, y), (x+w, y+h), border_color, border_thickness)
        
        # 显示车牌号码（如果有）
        if 'plate_no' in item and item['plate_no']:
            # 计算文本位置 - 在车牌下方居中显示
            plate_text = item['plate_no']
            text_x = max(0, x)
            text_y = min(processed_img.shape[0]-10, y+h+30)  # 车牌下方30像素
            
            # 使用中文渲染函数绘制清晰的车牌号码
            processed_img = draw_chinese_text(
                processed_img, 
                plate_text, 
                (text_x, text_y), 
                font_size=font_size, 
                color=text_color, 
                thickness=2
            )

        # 根据用户要求，移除所有的文本标签和关键点标记
        # 不显示置信度、关键点、车牌号码、车牌类型、车牌颜色等信息
        # 只保留对车牌位置的框选

    # 移除总结信息显示，只保留纯净的车牌框标记

    return processed_img

def get_second(capture):
    """获取视频秒数"""
    if capture.isOpened():
        rate = capture.get(5)  # 帧速率
        frame_num = capture.get(7)  # 总帧数
        duration = frame_num/rate  # 视频时间
        return duration
    return 0
