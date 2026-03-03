"""
路由管理器
负责统一管理和注册FastAPI应用程序中的所有路由
确保路由配置的一致性和可维护性
"""

import logging
import importlib
from typing import Dict, List, Optional, Any, Set
from fastapi import FastAPI, APIRouter
from .route_config import API_ROUTES, get_fallbacks, GLOBAL_ENDPOINTS

logger = logging.getLogger(__name__)

class RouterManager:
    """路由管理器类，负责注册和管理所有FastAPI路由"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.registered_routes: Set[str] = set()
        self.modules: Dict[str, Any] = {}
        self.loaded_routers: Dict[str, APIRouter] = {}
    
    def register_all_routes(self) -> None:
        """注册所有在route_config中配置的路由"""
        # 首先注册核心路由 - 车牌识别是必须的服务
        self._register_module('plate_recognition')
        
        # 注册其他配置的路由
        for module_name, config in API_ROUTES.items():
            if module_name != 'plate_recognition' and config.get('enabled', True):
                self._register_module(module_name)
        
        # 打印路由注册状态摘要
        self._print_route_summary()
    
    def get_module(self, module_name: str) -> Optional[Any]:
        """获取已加载的模块对象"""
        return self.modules.get(module_name)
    
    def get_router(self, module_name: str) -> Optional[APIRouter]:
        """获取已注册的路由器对象"""
        return self.loaded_routers.get(module_name)
    
    def _register_module(self, module_name: str) -> bool:
        """
        注册单个模块的路由
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 是否成功注册
        """
        if module_name in self.registered_routes:
            logger.info(f"模块 {module_name} 已经注册")
            return True
        
        config = API_ROUTES.get(module_name)
        if not config:
            logger.error(f"模块 {module_name} 没有配置信息")
            return False
        
        # 获取路由配置
        prefix = config.get('prefix', '')
        tags = config.get('tags', [])
        
        # 尝试加载模块
        try:
            module = self._import_module(f"app.routers.{module_name}")
            if module and hasattr(module, 'router'):
                router = module.router
                
                # 注册路由
                self.app.include_router(
                    router,
                    prefix=prefix,
                    tags=tags
                )
                
                # 记录已注册的路由和模块
                self.registered_routes.add(module_name)
                self.modules[module_name] = module
                self.loaded_routers[module_name] = router
                
                # 打印路由端点
                self._print_endpoints(router, prefix)
                logger.info(f"✅ 成功注册 {module_name} 路由")
                return True
            else:
                logger.error(f"❌ 模块 {module_name} 没有router属性")
        except Exception as e:
            logger.error(f"❌ 注册 {module_name} 路由失败: {str(e)}")
            logger.exception(e)
            
            # 尝试使用备选实现
            return self._try_fallbacks(module_name)
        
        return False
    
    def _try_fallbacks(self, module_name: str) -> bool:
        """尝试使用模块的备选实现"""
        fallbacks = get_fallbacks(module_name)
        for fallback in fallbacks:
            logger.info(f"尝试使用 {fallback} 作为 {module_name} 的备选")
            try:
                module = self._import_module(f"app.routers.{fallback}")
                if module and hasattr(module, 'router'):
                    config = API_ROUTES.get(module_name)  # 使用原始模块的配置
                    prefix = config.get('prefix', '')
                    tags = config.get('tags', [])
                    
                    # 注册备选路由
                    self.app.include_router(
                        module.router,
                        prefix=prefix,
                        tags=tags
                    )
                    
                    # 记录已注册
                    self.registered_routes.add(module_name)
                    self.modules[module_name] = module  # 使用原始模块名称作为键
                    self.modules[fallback] = module     # 同时也记录备选名称
                    self.loaded_routers[module_name] = module.router
                    
                    logger.info(f"✅ 成功使用 {fallback} 注册 {module_name} 路由")
                    return True
            except Exception as e:
                logger.error(f"❌ 尝试使用备选 {fallback} 失败: {str(e)}")
        
        return False
    
    def _import_module(self, module_path: str) -> Optional[Any]:
        """安全地导入模块"""
        try:
            return importlib.import_module(module_path)
        except ImportError as e:
            logger.error(f"导入模块 {module_path} 失败: {str(e)}")
            return None
    
    def _print_endpoints(self, router: APIRouter, prefix: str) -> None:
        """打印路由器中的所有端点"""
        try:
            if hasattr(router, 'routes'):
                for route in router.routes:
                    path = f"{prefix}{route.path}" if not route.path.startswith('/') else f"{prefix}{route.path}"
                    logger.info(f"📌 端点: {path}, 方法: {route.methods}")
        except Exception as e:
            logger.error(f"打印端点信息失败: {str(e)}")
    
    def _print_route_summary(self) -> None:
        """打印路由注册状态摘要"""
        logger.info("====== 路由注册状态摘要 ======")
        for module_name, config in API_ROUTES.items():
            status = "✅ 已注册" if module_name in self.registered_routes else "❌ 未注册"
            logger.info(f"{status} - {module_name}: {config.get('prefix')}")
        logger.info("=============================")


def register_global_endpoints(app: FastAPI) -> None:
    """注册全局系统端点（不属于特定模块的API）"""
    for endpoint in GLOBAL_ENDPOINTS:
        # 这些端点需要在main.py中直接实现
        logger.info(f"全局端点: {endpoint['path']}, 方法: {endpoint['methods']}, 名称: {endpoint['name']}")
