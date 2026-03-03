"""
车牌检测模块初始化文件
提供车牌检测相关功能
"""
from .detector import load_model, detect_Recognition_plate, draw_result

__all__ = ['load_model', 'detect_Recognition_plate', 'draw_result']
