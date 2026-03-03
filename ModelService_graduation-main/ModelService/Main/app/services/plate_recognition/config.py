"""
车牌识别服务配置模块
定义路径、权重文件位置等常量
"""
import os
import logging
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)

# 获取模块的基础路径
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))).absolute()
WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weights")

# 确保权重目录存在
os.makedirs(WEIGHTS_DIR, exist_ok=True)

# 权重文件路径
WEIGHTS = {
    # 使用设计竹赛子项目中的车牌检测模型
    'plate_detector': os.path.join(WEIGHTS_DIR, 'detect.pt'),
    'plate_detector_light': os.path.join(WEIGHTS_DIR, 'detect.pt'),  # 轻量版也使用编译优化版本
    'plate_recognizer': os.path.join(WEIGHTS_DIR, 'plate_rec.pth'),
    'plate_color': os.path.join(WEIGHTS_DIR, 'plate_rec_color.pth'),
    'car_color': os.path.join(WEIGHTS_DIR, 'car_rec_color.pth')
}

logger.info(f"车牌识别服务配置加载完成，基础路径: {BASE_DIR}")
logger.info(f"车牌识别权重目录: {WEIGHTS_DIR}")
