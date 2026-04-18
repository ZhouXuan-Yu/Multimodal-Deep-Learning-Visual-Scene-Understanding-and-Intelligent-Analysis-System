"""
车牌识别模块初始化文件
提供车牌文字识别、颜色识别等功能
"""
from .plate_rec import init_model, get_plate_result, cv_imread
from .color_rec import init_color_model, plate_color_rec
from .car_rec import init_car_rec_model, get_color_and_score
from .double_plate_split_merge import get_split_merge

__all__ = [
    'init_model', 'get_plate_result', 'cv_imread',
    'init_color_model', 'plate_color_rec',
    'init_car_rec_model', 'get_color_and_score',
    'get_split_merge'
]
