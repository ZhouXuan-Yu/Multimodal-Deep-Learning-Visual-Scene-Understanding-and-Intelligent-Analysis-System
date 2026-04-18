from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import sys
import shutil
import cv2
import uuid
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("design-competition")

# 添加模块路径以便导入
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 创建路由器
router = APIRouter(
    prefix="/api/design-competition",
    tags=["design-competition"],
    responses={404: {"description": "Not found"}},
)

# 设置上传和静态文件目录
UPLOAD_FOLDER = os.path.join(parent_dir, "uploads", "design_competition")
STATIC_FOLDER = os.path.join(parent_dir, "static", "design_competition")

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# 导入设计比赛项目的核心功能
try:
    from design_competition.car_recognition.car_rec import init_car_rec_model, get_color_and_score
    from design_competition.plate_recognition.plate_rec import get_plate_result, init_model
    import torch
    
    # 设置设备
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device("cpu")
    
    # 设置模型路径
    plate_model_path = os.path.join(parent_dir, "design_competition", "weights", "plate_rec.pth")
    car_model_path = os.path.join(parent_dir, "design_competition", "weights", "car_rec_color.pth")
    
    # 初始化模型
    plate_model = init_model(device, plate_model_path)
    car_model = init_car_rec_model(car_model_path, device)
    
    logger.info(f"车牌识别和车辆识别模型加载成功，使用设备: {device}")
except Exception as e:
    logger.error(f"导入或初始化设计比赛模型时出错: {str(e)}")
    plate_model = None
    car_model = None

# 保存上传文件的辅助函数
def save_upload_file(upload_file: UploadFile) -> str:
    """保存上传的文件并返回文件路径"""
    try:
        # 生成唯一文件名
        file_extension = os.path.splitext(upload_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        logger.info(f"文件已保存至: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"保存上传文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

# API端点: 车牌识别
@router.post("/recognize-plate")
async def recognize_plate(file: UploadFile = File(...)):
    """车牌识别API，上传一张图片，返回识别的车牌信息"""
    if not plate_model:
        raise HTTPException(status_code=500, detail="车牌识别模型未成功加载")
    
    try:
        # 保存上传的图片
        file_path = save_upload_file(file)
        
        # 进行车牌识别
        result = get_plate_result(file_path, plate_model)
        
        # 如果识别成功，返回结果
        if result:
            return {"success": True, "plate_number": result.get("plate_number", "未识别"), 
                    "color": result.get("color", "未识别"), 
                    "confidence": result.get("confidence", 0),
                    "file_path": file_path}
        else:
            return {"success": False, "error": "未能识别车牌"}
            
    except Exception as e:
        logger.error(f"车牌识别过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"车牌识别失败: {str(e)}")

# API端点: 车辆识别
@router.post("/recognize-car")
async def recognize_car(file: UploadFile = File(...)):
    """车辆识别API，上传一张图片，返回识别的车辆信息"""
    if not car_model:
        raise HTTPException(status_code=500, detail="车辆识别模型未成功加载")
    
    try:
        # 保存上传的图片
        file_path = save_upload_file(file)
        
        # 进行车辆识别
        img = cv2.imread(file_path)
        if img is None:
            raise HTTPException(status_code=400, detail="无法读取上传的图片")
            
        color, score = get_color_and_score(img, car_model)
        
        # 返回识别结果
        return {"success": True, "color": color, "confidence": float(score), "file_path": file_path}
            
    except Exception as e:
        logger.error(f"车辆识别过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"车辆识别失败: {str(e)}")

# API端点: 健康检查
@router.get("/health")
async def health_check():
    """API健康检查"""
    status = {
        "plate_model": plate_model is not None,
        "car_model": car_model is not None
    }
    return {"status": "ok", "models": status}
