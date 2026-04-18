# 路由配置中心
# 本文件定义了整个应用程序的所有API路由
# 使用显式定义而非动态生成的方式管理所有路由

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 定义所有可用的API路由模块及其配置
# 格式：模块名称: {前缀, 标签列表, 描述, 是否启用}
API_ROUTES: Dict[str, Dict[str, Any]] = {
    # 核心功能路由
    "plate_recognition": {
        "prefix": "/api/plate-recognition",
        "tags": ["车牌识别"],
        "description": "车牌识别与分析功能",
        "enabled": False,  # 禁用原外部服务版本
        "frontend_path": "/plate-recognition"
    },
    "plate_recognition_integrated": {
        "prefix": "/api/plate-recognition",
        "tags": ["车牌识别(集成版)"],
        "description": "车牌识别与分析功能(集成版)",
        "enabled": True,
        "frontend_path": "/plate-recognition"
    },
    "plate_monitoring": {
        "prefix": "/api/plate-monitoring",
        "tags": ["车牌监控"],
        "description": "车牌监控报警功能",
        "enabled": True,
        "frontend_path": "/plate-recognition"
    },
    "route_planning": {
        "prefix": "/api/route",
        "tags": ["路径规划"],
        "description": "智能路径规划与优化",
        "enabled": True,
        "frontend_path": "/route-planning"
    },
    "image_recognition": {
        "prefix": "/api/image-recognition",
        "tags": ["图像识别"],
        "description": "图像目标检测与分析",
        "enabled": True,
        "frontend_path": "/image-recognition"
    },
    "video_tracking": {
        "prefix": "/api/video-tracking",
        "tags": ["视频追踪"],
        "description": "视频中的目标追踪与分析",
        "enabled": True,
        "frontend_path": "/video-tracking"
    },
    "knowledge_chat": {
        "prefix": "/api/knowledge-chat",
        "tags": ["知识库聊天"],
        "description": "基于知识库的智能对话",
        "enabled": True,
        "frontend_path": "/knowledge-base-chat"
    },
    "night_detection": {
        "prefix": "/api/night-detection",
        "tags": ["低光图像增强与目标检测"],
        "description": "夜间低光图像增强与目标检测",
        "enabled": True,
        "frontend_path": "/night-detection"
    },
    "rgbt_detection": {
        "prefix": "/api/rgbt-detection",
        "tags": ["可见光-热微小物体检测"],
        "description": "可见光-热红外微小物体检测",
        "enabled": True,
        "frontend_path": "/rgbt-detection"
    },
    "night_guardian": {
        "prefix": "/api/night-guardian",
        "tags": ["夜间保卫者"],
        "description": "红外视频行为检测系统",
        "enabled": True,
        "frontend_path": "/night-guardian"
    },
    
    # 辅助功能路由
    "image_analysis_chat": {
        "prefix": "/api/image-analysis-chat",
        "tags": ["图片分析聊天"],
        "description": "基于图像的对话与分析",
        "enabled": True,
        "frontend_path": None  # 没有对应的专门前端页面，集成在其他页面
    },
    "chat": {
        "prefix": "/api/chat",
        "tags": ["聊天"],
        "description": "通用聊天服务",
        "enabled": True,
        "frontend_path": None  # 没有对应的专门前端页面，集成在其他页面
    },
    
    # 测试模块
    "test": {
        "prefix": "/api/test",
        "tags": ["测试接口"],
        "description": "系统测试功能",
        "enabled": True,
        "frontend_path": "/test-fusion"
    },
    
    # 以下是为domain前端项目添加的路由别名，复用已有的处理逻辑
    # 路径规划
    "domain_route_planning": {
        "prefix": "/api/route-planning",
        "alias_for": "route_planning",
        "tags": ["路径规划(domain)"],
        "description": "智能路径规划与优化(domain前端)",
        "enabled": True,
        "frontend_path": "/domain/path-planning"
    },
    # 图像识别
    "domain_image_recognition": {
        "prefix": "/api/image-recognition",
        "alias_for": "image_recognition", 
        "tags": ["图像识别(domain)"],
        "description": "图像目标检测与分析(domain前端)",
        "enabled": True,
        "frontend_path": "/domain/person-recognition"
    },
    # 知识库聊天
    "domain_knowledge_chat": {
        "prefix": "/api/knowledge-chat",
        "alias_for": "knowledge_chat",
        "tags": ["知识库聊天(domain)"],
        "description": "基于知识库的智能对话(domain前端)",
        "enabled": True,
        "frontend_path": "/domain/knowledge-graph"
    },
    # 夜间低光图像增强与目标检测
    "domain_night_detection": {
        "prefix": "/api/night-detection",
        "alias_for": "night_detection",
        "tags": ["低光图像增强与目标检测(domain)"],
        "description": "夜间低光图像增强与目标检测(domain前端)",
        "enabled": True,
        "frontend_path": "/domain/night-enhanced-recognition"
    },
    # 可见光-热红外微小物体检测
    "domain_rgbt_detection": {
        "prefix": "/api/rgbt-detection",
        "alias_for": "rgbt_detection",
        "tags": ["可见光-热微小物体检测(domain)"],
        "description": "可见光-热红外微小物体检测(domain前端)",
        "enabled": True,
        "frontend_path": "/domain/long-range-identification"
    },
    # 车牌识别
    "domain_plate_recognition": {
        "prefix": "/api/plate-recognition",
        "alias_for": "plate_recognition_integrated",
        "tags": ["车牌识别(domain)"],
        "description": "车牌识别与分析功能(domain前端)",
        "enabled": True,
        "frontend_path": "/domain/vehicle-monitoring"
    }
}

# 模块备选列表，当主模块不可用时使用
MODULE_FALLBACKS = {
    "image_recognition": ["mock_image_recognition", "real_image_recognition"]
}

# 全局系统端点（不属于特定模块的API）
GLOBAL_ENDPOINTS = [
    {"path": "/api", "methods": ["GET"], "name": "root", "description": "获取系统基本信息"},
    {"path": "/api/health", "methods": ["GET"], "name": "health_check", "description": "系统健康检查"}
]

def get_module_config(module_name: str) -> Optional[Dict[str, Any]]:
    """获取指定模块的路由配置"""
    return API_ROUTES.get(module_name)

def get_enabled_modules() -> List[str]:
    """获取所有启用的模块名称"""
    return [name for name, config in API_ROUTES.items() if config.get("enabled", False)]

def get_fallbacks(module_name: str) -> List[str]:
    """获取模块的备选实现列表"""
    return MODULE_FALLBACKS.get(module_name, [])

def is_alias_module(module_name: str) -> bool:
    """检查是否为别名模块"""
    config = API_ROUTES.get(module_name, {})
    return "alias_for" in config

def get_aliased_module(module_name: str) -> Optional[str]:
    """获取别名模块对应的实际模块名"""
    config = API_ROUTES.get(module_name, {})
    return config.get("alias_for")

def print_all_routes() -> None:
    """打印所有路由信息（调试用）"""
    print("\n==== API路由配置信息 ====")
    for name, config in API_ROUTES.items():
        status = "✅ 启用" if config.get("enabled") else "❌ 禁用"
        frontend = config.get("frontend_path") or "无对应前端页面"
        print(f"模块: {name} [{status}]")
        print(f"  API前缀: {config.get('prefix')}")
        print(f"  前端路径: {frontend}")
        print(f"  描述: {config.get('description')}")
        if "alias_for" in config:
            print(f"  别名模块，实际指向: {config.get('alias_for')}")
        if name in MODULE_FALLBACKS:
            print(f"  备选实现: {', '.join(MODULE_FALLBACKS[name])}")
        print()
        
    print("\n==== 全局系统端点 ====")
    for endpoint in GLOBAL_ENDPOINTS:
        print(f"{endpoint['path']} [{', '.join(endpoint['methods'])}] - {endpoint['description']}")
