# 这个文件使 routers 成为一个 Python 包
# 避免在这里导入模块，防止循环导入问题

# 定义一个延迟导入函数，仅在需要时导入模块
def load_module(module_name):
    """在需要时延迟加载模块，避免循环导入"""
    import importlib
    import sys
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # 构建完整模块路径
        full_module_name = f"app.routers.{module_name}"
        
        # 检查模块是否已加载
        if full_module_name in sys.modules:
            return sys.modules[full_module_name]
            
        # 动态导入模块
        module = importlib.import_module(f".{module_name}", package="app.routers")
        logger.info(f"✅ 成功加载模块: {module_name}")
        return module
    except Exception as e:
        # 不要因为某个模块（例如模型权重/依赖）加载失败而导致整个服务无法启动
        # 记录完整堆栈，方便排查
        logger.exception(f"❌ 无法导入模块 {module_name}: {str(e)}")
        return None

# 不要在这里导入任何模块，让main.py去导入它们