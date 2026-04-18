from ..models.colorNet import myNet
import torch
import cv2
import torch.nn.functional as F
import os
import logging
import numpy as np

# 配置日志记录器
logger = logging.getLogger(__name__)


# 颜色列表
colors = ['黑色','蓝色','黄色','棕色','绿色','灰色','橙色','粉色','紫色','红色','白色']

def init_car_rec_model(model_path, device):
    """初始化车辆颜色识别模型
    
    Args:
        model_path: 模型权重文件路径
        device: 计算设备 (CPU/GPU)
        
    Returns:
        model: 初始化后的模型
    """
    try:
        logger.info(f"正在加载车辆颜色识别模型: {model_path}")
        
        # 将gpu模型加载到cpu
        check_point = torch.load(model_path, map_location=torch.device('cpu'))
        
        # 获取配置
        if 'cfg' in check_point:
            cfg = check_point['cfg']
            logger.info(f"从权重文件加载配置: {cfg}")
        else:
            logger.warning("权重文件中没有找到配置，使用默认配置")
            cfg = None
            
        # 明确指定model_type为'standard'，使用标准模型结构
        model = myNet(num_classes=len(colors), cfg=cfg, model_type='standard')
        
        # 加载模型权重
        if 'state_dict' in check_point:
            model.load_state_dict(check_point['state_dict'], strict=False)
            logger.info("成功加载模型权重")
        else:
            # 尝试直接加载权重
            model.load_state_dict(check_point, strict=False)
            logger.info("直接加载模型权重成功")
            
        # 将模型移到指定设备并设置为评估模式
        model.to(device)
        model.eval()
        logger.info(f"车辆颜色识别模型初始化完成，移动到设备: {device}")
        return model
        
    except Exception as e:
        logger.error(f"初始化车辆颜色识别模型出错: {str(e)}")
        raise


# 图像预处理
def imge_processing(img, device):
    """对输入图像进行预处理
    
    Args:
        img: 输入图像
        device: 计算设备
        
    Returns:
        processed_img: 预处理后的图像张量
    """
    try:
        # 检查输入图像
        if img is None or img.size == 0:
            logger.error("输入图像为空或无效")
            raise ValueError("Invalid image input")
            
        # 记录原始图像信息 - 这个信息变为DEBUG级别
        logger.debug(f"原始图像形状: {img.shape}, 类型: {img.dtype}")
        
        # 调整图像大小
        img = cv2.resize(img, (64, 64))
        
        # 转换图像格式为CHW
        img = img.transpose([2, 0, 1])
        
        # 转换为PyTorch张量并移动到目标设备
        img = torch.from_numpy(img).float().to(device)
        
        # 归一化
        img = img - 127.5
        
        # 添加批次维度
        img = img.unsqueeze(0)
        
        logger.debug(f"预处理后图像张量形状: {img.shape}")
        return img
    except Exception as e:
        logger.error(f"图像预处理失败: {str(e)}")
        # 在出错时返回一个空的张量，调用处需要检查
        return None
    

    # 获取文件夹下所有文件
def allFilePath(rootPath,allFIleList):
    fileList = os.listdir(rootPath)
    for temp in fileList:
        if os.path.isfile(os.path.join(rootPath,temp)):
            allFIleList.append(os.path.join(rootPath,temp))
        else:
            allFilePath(os.path.join(rootPath,temp),allFIleList)    

# 获取颜色和置信度
# 获取颜色和置信度 - 减少日志输出的版本
def get_color_and_score(model, img, device):
    """
    获取车辆颜色和置信度，直接使用模型识别结果
    
    Args:
        model: 颜色识别模型
        img: 原始车辆图像
        device: 计算设备
        
    Returns:
        car_color: 车辆颜色
        color_conf: 颜色置信度
    """
    try:
        # 检查模型和图像是否有效
        if model is None or img is None or img.size == 0:
            logger.error("模型或图像无效")
            return "未知颜色", 0.0
        
        # 图像预处理
        img_processed = imge_processing(img, device)
        if img_processed is None:
            logger.error("图像预处理失败")
            return "未知颜色", 0.0
        
        # 这些详细的图像处理日志不需要在信息级别输出
        
        # 使用模型进行预测
        with torch.no_grad():
            result = model(img_processed)
            
        # 应用softmax获取概率分布
        out = F.softmax(result, dim=1)
        
        # 获取最高置信度的预测类别
        _, predicted = torch.max(out.data, 1)
        out_cpu = out.data.cpu().numpy().tolist()[0]
        predicted_idx = predicted.item()
        
        # 获取预测结果
        car_color = colors[predicted_idx]
        color_conf = out_cpu[predicted_idx]
        
        # 去除详细的颜色预测日志输出，只保留最终结果的DEBUG输出
        logger.debug(f"车辆颜色预测结果: {car_color} (置信度: {color_conf:.4f})")
        return car_color, color_conf
        
    except Exception as e:
        logger.error(f"车辆颜色识别失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return "未知颜色", 0.0



if __name__ == '__main__':
    # root_file =r"/mnt/Gpan/BaiduNetdiskDownload/VehicleColour/VehicleColour/class/7"
    root_file =r"imgs"
    file_list=[]
    allFilePath(root_file,file_list)
    device = torch.device("cuda" if torch.cuda.is_available else "cpu")
    model_path = r"/mnt/Gpan/Mydata/pytorchPorject/Car_system/car_color/color_model/0.8682285244554049_epoth_117_model.pth"
    model = init_car_rec_model(model_path,device)
    for pic_ in file_list:
        img = cv2.imread(pic_)
        # img = imge_processing(img,device)
        color,conf = get_color_and_score(model,img,device)
        print(pic_,color,conf)
      
    
     
   