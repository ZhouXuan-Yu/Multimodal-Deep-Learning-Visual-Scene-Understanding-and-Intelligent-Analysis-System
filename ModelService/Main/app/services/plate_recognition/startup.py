"""
车牌识别服务启动模块
负责在应用启动时初始化车牌识别服务
"""
import os
import logging
from typing import Dict, Any
import threading

from .service_manager import PlateRecognitionServiceManager

# 配置日志
logger = logging.getLogger(__name__)

# 全局变量
initialized = False
initialization_lock = threading.Lock()
initialization_thread = None

def init_service_thread() -> None:
    """在后台线程中初始化车牌识别服务"""
    global initialized
    
    try:
        logger.info("开始在后台线程中初始化车牌识别服务...")
        
        # 获取服务管理器实例
        service_manager = PlateRecognitionServiceManager()
        
        # 初始化服务
        result = service_manager.init_service()
        
        if result.get("success", False):
            logger.info("车牌识别服务成功初始化")
            initialized = True
        else:
            logger.warning(f"车牌识别服务初始化失败: {result.get('message', '未知错误')}")
            initialized = False
            
    except Exception as e:
        logger.error(f"初始化车牌识别服务时发生错误: {str(e)}")
        initialized = False

async def init_service_async() -> Dict[str, Any]:
    """异步初始化车牌识别服务"""
    global initialized, initialization_thread
    
    # 如果已经初始化，直接返回状态
    if initialized:
        return {"success": True, "message": "车牌识别服务已初始化", "status": "ready"}
    
    # 如果正在初始化，返回等待状态
    if initialization_thread and initialization_thread.is_alive():
        return {"success": True, "message": "车牌识别服务正在初始化", "status": "initializing"}
    
    # 否则开始初始化
    with initialization_lock:
        if not initialized and (not initialization_thread or not initialization_thread.is_alive()):
            logger.info("开始异步初始化车牌识别服务...")
            
            # 创建后台线程初始化服务
            initialization_thread = threading.Thread(target=init_service_thread)
            initialization_thread.daemon = True
            initialization_thread.start()
            
            return {"success": True, "message": "车牌识别服务开始初始化", "status": "initializing"}
    
    return {"success": True, "message": "车牌识别服务初始化状态未知", "status": "unknown"}

def get_initialization_status() -> Dict[str, Any]:
    """获取服务初始化状态"""
    global initialized, initialization_thread
    
    if initialized:
        return {"initialized": True, "message": "车牌识别服务已初始化", "status": "ready"}
    
    if initialization_thread and initialization_thread.is_alive():
        return {"initialized": False, "message": "车牌识别服务正在初始化", "status": "initializing"}
    
    return {"initialized": False, "message": "车牌识别服务未初始化", "status": "not_initialized"}

def check_model_files_exist() -> bool:
    """
    检查模型文件是否存在
    
    返回:
        bool: 是否所有模型文件都存在
    """
    # 获取权重文件路径
    from . import WEIGHTS
    
    # 检查所有模型文件是否存在
    all_exist = True
    for name, path in WEIGHTS.items():
        if not os.path.exists(path):
            logger.warning(f"模型文件不存在: {name} - {path}")
            all_exist = False
    
    return all_exist

# 在模块导入时检查模型文件
model_files_exist = check_model_files_exist()
logger.info(f"车牌识别模型文件状态: {'所有文件已存在' if model_files_exist else '部分文件缺失'}")

# 自动启动初始化过程（可选，取决于配置）
AUTO_INIT = os.environ.get("AUTO_INIT_PLATE_RECOGNITION", "false").lower() == "true"

if AUTO_INIT and model_files_exist:
    logger.info("自动初始化车牌识别服务已启用，即将开始初始化...")
    initialization_thread = threading.Thread(target=init_service_thread)
    initialization_thread.daemon = True
    initialization_thread.start()
else:
    logger.info("车牌识别服务自动初始化未启用或模型文件缺失，等待手动初始化")
