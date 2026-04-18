# 车牌识别服务模块初始化文件
"""
车牌识别服务模块
提供车牌检测、识别、工作流等功能
"""
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 首先导入配置模块
from .config import WEIGHTS, BASE_DIR, WEIGHTS_DIR

# 导出主要组件
from .detector import load_model, detect_Recognition_plate, draw_result
from .recognizer import init_model, get_plate_result, init_color_model, init_car_rec_model
from .workflow import PlateWorkflow

# 循环导入问题解决后，再导入服务管理器和启动模块
from .service_manager import PlateRecognitionServiceManager
from .startup import get_initialization_status, init_service_async

__all__ = [
    'load_model', 'detect_Recognition_plate', 'draw_result',
    'init_model', 'get_plate_result',
    'init_color_model', 'init_car_rec_model',
    'PlateWorkflow',
    'PlateRecognitionServiceManager',
    'get_initialization_status', 'init_service_async',
    'WEIGHTS_DIR', 'WEIGHTS', 'BASE_DIR'
]

logger.info("车牌识别服务模块初始化完成")
