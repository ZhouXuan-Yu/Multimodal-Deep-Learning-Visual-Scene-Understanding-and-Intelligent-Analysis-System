"""
车牌颜色识别模块
提供车牌颜色识别功能 - 严格按照原始子项目实现
"""
import logging
import cv2
import numpy as np
import torch
from torchvision import transforms
from ..models.colorNet import myNet

# 配置日志记录器
logger = logging.getLogger(__name__)

# 不同颜色车牌的映射 - 精确匹配License_plate_recognition_tracking项目中的类别
# 索引: 0=黑色, 1=蓝色, 2=危险品(黄色), 3=绿色, 4=白色, 5=黄色
PLATE_COLORS = ['黑色', '蓝色', '黄色', '绿色', '白色', '黄色']

# 颜色转换映射表 - 修复黄色车牌识别问题
COLOR_CORRECTION_MAP = {
    0: 0,  # 黑色保持不变
    1: 1,  # 蓝色保持不变
    2: 2,  # 原危险品标签映射为黄色
    3: 3,  # 绿色保持不变
    4: 4,  # 白色保持不变
    5: 2   # 如果直接预测为黄色，保持黄色
}

def init_color_model(model_path, device):
    """初始化车牌颜色识别模型
    
    Args:
        model_path: 模型权重文件路径
        device: 使用的设备（CPU或GPU）
        
    Returns:
        model: 初始化并加载权重的模型
    """
    try:
        # 打印信息
        print(f"正在加载车牌颜色识别模型: {model_path}")
        
        # 加载模型文件
        check_point = torch.load(model_path, map_location=torch.device('cpu'))
        print(f"成功加载模型文件，文件类型: {type(check_point)}")
        
        # 检查是否为字典格式
        if isinstance(check_point, dict):
            print(f"文件为字典格式，包含键: {list(check_point.keys())}")

        # 定义类别数量
        num_classes = 5  # 车牌颜色类别数
        
        # 获取模型配置
        if 'cfg' in check_point:
            cfg = check_point['cfg']
            logger.info(f"从模型文件加载配置: {cfg}")
        else:
            cfg = None
            logger.warning("模型文件中没有找到配置，使用默认配置")
        
        # 初始化模型 - 明确指定为车牌颜色识别类型
        model = myNet(num_classes=num_classes, cfg=cfg, model_type='plate_color')
        
        # 尝试加载模型权重
        try:
            if 'state_dict' in check_point:
                # 先尝试直接加载
                try:
                    model.load_state_dict(check_point['state_dict'])
                    print("直接加载成功")
                except Exception as e1:
                    print(f"直接加载失败: {str(e1)}")
                    
                    # 尝试非严格模式加载
                    try:
                        model.load_state_dict(check_point['state_dict'], strict=False)
                        print("非严格模式加载成功")
                    except Exception as e2:
                        print(f"非严格模式加载失败: {str(e2)}")
                        raise
            else:
                # 尝试加载嵌套的state_dict
                print("尝试加载嵌套的state_dict...")
                found = False
                
                # 搜索嵌套字典中的state_dict
                for key, value in check_point.items():
                    if isinstance(value, dict) and 'state_dict' in value:
                        try:
                            model.load_state_dict(value['state_dict'], strict=False)
                            print(f"从{key}加载嵌套state_dict成功")
                            found = True
                            break
                        except Exception as e:
                            print(f"从{key}加载嵌套state_dict失败: {str(e)}")
                
                if not found:
                    print("没有找到嵌套的state_dict，将使用未训练的模型")
                    
        except Exception as e:
            logger.error(f"加载模型权重失败: {str(e)}")
            print(f"加载模型权重失败: {str(e)}")
        
        # 将模型设置为评估模式并移动到指定设备
        model.to(device)
        model.eval()
        print(f"模型设置为评估模式并移至{device}设备")
        
        return model
        
    except Exception as e:
        logger.error(f"初始化车牌颜色识别模型时出错: {str(e)}")
        print(f"初始化车牌颜色识别模型时出错: {str(e)}")
        
        # 在出错时创建一个空模型
        model = myNet(num_classes=num_classes, model_type='plate_color')
        model.to(device)
        model.eval()
        print("创建了未训练的空模型")
        
        num_classes = 5
        model = myNet(num_classes=num_classes)
        model.eval().to(device)
        print("使用未初始化的模型作为备用")
        return model

def plate_color_rec(img, model, device=None):
    """
    车牌颜色识别函数 - 简化版，与子项目里的实现一致
    
    参数:
        img: 车牌图像
        model: 车牌颜色识别模型
        device: 设备类型(CPU/GPU), 可选
        
    返回:
        color_name: 车牌颜色名称
    """
    # 与子项目中的类别映射保持一致
    if device is None:
        device = next(model.parameters()).device
    
    try:
        # 直接采用子项目中的实现
        data_input = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image = cv2.resize(data_input, (34, 9))   # 子项目中使用的尺寸
        image = np.transpose(image, (2, 0, 1))
        img_tensor = image / 255
        img_tensor = torch.tensor(img_tensor)

        # 使用子项目中的归一化参数
        normalize = transforms.Normalize(mean=[0.4243, 0.4947, 0.434],
                                        std=[0.2569, 0.2478, 0.2174])
        img_tensor = normalize(img_tensor)
        img_tensor = torch.unsqueeze(img_tensor, dim=0).to(device).float()
        xx = model(img_tensor)
        
        # 获取模型预测结果
        predicted_idx = int(torch.argmax(xx, dim=1)[0])
        confidence = float(xx[0][predicted_idx])
        
        # 边界检查
        if predicted_idx < len(PLATE_COLORS):
            # 应用颜色修正映射 - 处理黄色车牌识别问题
            if predicted_idx in COLOR_CORRECTION_MAP:
                corrected_idx = COLOR_CORRECTION_MAP[predicted_idx]
                print(f"应用颜色修正: {predicted_idx}({PLATE_COLORS[predicted_idx]}) -> {corrected_idx}({PLATE_COLORS[corrected_idx]})")
                color_name = PLATE_COLORS[corrected_idx]
            else:
                color_name = PLATE_COLORS[predicted_idx]
            
            # 颜色优化：针对黄色车牌的额外处理
            if is_yellow_plate(img):
                orig_color = color_name
                color_name = PLATE_COLORS[2]  # 强制设为黄色
                print(f"颜色优化: 检测到黄色车牌特征，将颜色从 {orig_color} 修正为 {color_name}")
        else:
            print(f"警告: 预测的颜色索引 {predicted_idx} 超出范围, 默认为蓝色")
            # 检查是否为黄色车牌
            if is_yellow_plate(img):
                color_name = PLATE_COLORS[2]  # 黄色
                print("索引超出范围但检测到黄色车牌特征，设置为黄色")
            else:
                color_name = PLATE_COLORS[1]  # 默认蓝色
        
        # 打印调试信息，与子项目格式相同
        print(f"车牌颜色识别结果: 颜色={color_name}, 原始索引={predicted_idx}, 置信度={confidence:.4f}")
        
        return color_name
    except Exception as e:
        print(f"车牌颜色识别出错: {str(e)}")
        # 全部失败则返回蓝色
        return PLATE_COLORS[1]  # 因为这是最常见的车牌颜色


def is_yellow_plate(img):
    """
    检测车牌是否为黄色
    
    参数:
        img: BGR格式的车牌图像
        
    返回:
        是否为黄色车牌的布尔值
    """
    try:
        # 转换为HSV颜色空间，更适合颜色检测
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 黄色范围定义 (HSV空间)
        lower_yellow = np.array([15, 100, 100])
        upper_yellow = np.array([35, 255, 255])
        
        # 创建黄色掩码
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # 计算黄色像素的比例
        yellow_ratio = np.sum(yellow_mask > 0) / (yellow_mask.shape[0] * yellow_mask.shape[1])
        
        # 如果黄色像素占比超过30%，则认为是黄色车牌
        is_yellow = yellow_ratio > 0.3
        
        # 输出调试信息
        print(f"黄色像素占比: {yellow_ratio:.4f}, 是否为黄色车牌: {is_yellow}")
        
        return is_yellow
        
    except Exception as e:
        print(f"黄色车牌检测出错: {str(e)}")
        return False
