"""
主应用程序入口文件
"""
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute  # 添加APIRoute导入
from starlette.middleware.base import BaseHTTPMiddleware

# 导入路由配置模块，用于处理路由别名
# 使用相对导入以保证在作为包 (app) 导入时能正确解析模块
from .route_config import is_alias_module, get_aliased_module, get_module_config, get_enabled_modules

import os
import sys
import time
import json
import uuid
import logging
import asyncio
import traceback
import threading
import contextlib
import subprocess
import urllib.parse
import signal
import socket
import atexit
import platform
import shutil
import random
import datetime
import tempfile
import re  # 添加re模块的导入
import httpx  # 添加httpx模块的导入
from typing import List, Dict, Optional, Any, Union, Callable, Awaitable, Type
from pathlib import Path
from contextlib import asynccontextmanager

# OpenCV导入
try:
    import cv2
    import numpy as np
except ImportError:
    # OpenCV未安装时提供友好提示
    print("OpenCV或NumPy未安装，图像处理功能将不可用")
    cv2 = None
    np = None

# 设置环境变量标记主应用程序正在运行
# 这将防止车牌识别服务检测机制错误地关闭主应用程序
os.environ['RUNNING_MAIN_APP'] = 'true'

# 关键修复: 设置环境变量表示不允许关闭服务
os.environ['PREVENT_SERVER_SHUTDOWN'] = 'true'

# 安装全局异常处理器，防止sys.excepthook错误导致程序崩溃
_original_excepthook = sys.excepthook

def enhanced_excepthook(exc_type, exc_value, exc_traceback):
    """增强型异常处理器，确保即使异常处理出错也不会导致程序崩溃"""
    try:
        # 首先记录异常信息到日志
        logger.error("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
        
        # 尝试使用原始的excepthook
        _original_excepthook(exc_type, exc_value, exc_traceback)
    except Exception as e:
        # 如果原始excepthook失败，使用基本的异常处理
        print(f"Error in exception handler: {e}")
        print(f"Original exception: {exc_type.__name__}: {exc_value}")
        traceback_str = ''.join(traceback.format_tb(exc_traceback))
        print(f"Traceback:\n{traceback_str}")

# 安装增强型异常处理器
sys.excepthook = enhanced_excepthook

# 获取当前脚本的绝对路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # ModelService_graduation-main/
MAIN_DIR = BASE_DIR / "ModelService" / "Main"  # ModelService_graduation-main/ModelService/Main/

# 添加项目根目录到Python路径
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 添加Main目录到Python路径
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

# 初始化变量
HAS_IMAGE_RECOGNITION = False

# 设置日志记录器
logger = logging.getLogger("app")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 定义可用模块字典
modules = {}

# 加载测试端点模块
try:
    from ModelService.Main.app.test_endpoints import router as test_router
    logger.info("✅ 成功加载测试端点模块")
except Exception as e:
    logger.error(f"❗ 加载测试端点模块失败: {str(e)}")

# 单独导入每个模块，避免一个模块的错误影响所有模块
try:
    from ModelService.Main.app.routers import chat
    modules['chat'] = chat
    print("成功加载 chat 模块")
except ImportError as e:
    print(f"无法加载 chat 模块: {str(e)}")

try:
    from ModelService.Main.app.routers import route_planning
    modules['route_planning'] = route_planning
    print("✅ 成功加载 route_planning 模块 (高级版本)")
except Exception as e:
    print(f"❌ 无法加载 route_planning 模块: {str(e)}")
    print("🔄 尝试加载回退实现...")
    # 尝试加载回退实现以保证路由可用（当依赖缺失时使用）
    try:
        from app.routers import route_planning_fallback as route_planning
        modules['route_planning'] = route_planning
        print("⚠️ 已加载 route_planning 回退实现 (fallback) - 功能受限")
    except Exception as fe:
        print(f"❌ 无法加载 route_planning 回退实现: {str(fe)}")

try:
    from ModelService.Main.app.routers import video_tracking
    modules['video_tracking'] = video_tracking
    print("成功加载 video_tracking 模块")
except ImportError as e:
    print(f"无法加载 video_tracking 模块: {str(e)}")

try:
    from ModelService.Main.app.routers import image_analysis_chat
    modules['image_analysis_chat'] = image_analysis_chat
    print("成功加载 image_analysis_chat 模块")
except ImportError as e:
    print(f"无法加载 image_analysis_chat 模块: {str(e)}")

# 标记无人机知识图谱模块是否成功加载
uav_knowledge_loaded = False

# 以安全方式尝试导入无人机知识图谱模块
try:
    # 直接尝试导入无人机知识图谱模块，跳过sentence_transformers
    try:
        from ModelService.Main.app.routers import uav_knowledge_graph
        modules['uav_knowledge_graph'] = uav_knowledge_graph
        uav_knowledge_loaded = True
        print("成功加载 uav_knowledge_graph 模块")
    except ImportError as e:
        print(f"无法加载 uav_knowledge_graph 模块: {str(e)}")
        print("知识图谱功能将不可用，但不影响其他功能")
except Exception as e:
    print(f"无人机知识图谱导入错误: {str(e)}")
    print("知识图谱功能将不可用，但不影响其他功能")


# 普通知识图谱模块已禁用
# 仅保留无人机知识图谱和知识库聊天模块

try:
    from ModelService.Main.app.routers import night_detection
    modules['night_detection'] = night_detection
    print("成功加载 night_detection 模块")
except ImportError as e:
    print(f"无法加载 night_detection 模块: {str(e)}")

try:
    from ModelService.Main.app.routers import rgbt_detection
    modules['rgbt_detection'] = rgbt_detection
    print("成功加载 rgbt_detection 模块")
except ImportError as e:
    print(f"无法加载 rgbt_detection 模块: {str(e)}")

# 导入RGBT视频处理模块
try:
    from app.routers import rgbt_video  # 使用相对导入路径
    modules['rgbt_video'] = rgbt_video  # 将模块添加到模块字典中
    print("成功加载 rgbt_video 模块")
except ImportError as e:
    print(f"无法加载 rgbt_video 模块: {str(e)}")

try:
    from ModelService.Main.app.routers import plate_recognition
    modules['plate_recognition'] = plate_recognition
    print("成功加载 plate_recognition 模块")
except ImportError as e:
    print(f"无法加载 plate_recognition 模块: {str(e)}")

try:
    from ModelService.Main.app.routers import plate_monitoring
    modules['plate_monitoring'] = plate_monitoring
    print("成功加载 plate_monitoring 模块")
except ImportError as e:
    print(f"无法加载 plate_monitoring 模块: {str(e)}")

try:
    from ModelService.Main.app.routers import fire_detection
    modules['fire_detection'] = fire_detection
    # 同时获取直接访问路由器
    if hasattr(fire_detection, 'direct_router'):
        modules['fire_detection_direct'] = fire_detection.direct_router
        print("成功加载 fire_detection 模块和直接访问路由")
    else:
        print("成功加载 fire_detection 模块，但无直接访问路由")
except ImportError as e:
    print(f"无法加载 fire_detection 模块: {str(e)}")

try:
    from ModelService.Main.app.routers import design_competition
    modules['design_competition'] = design_competition
    print("成功加载 design_competition 模块")
except ImportError as e:
    print(f"无法加载 design_competition 模块: {str(e)}")

# 使用延迟加载方式处理图像识别模块
import sys
import importlib.util
from app.routers import load_module

# 检查是否在modelapp环境中
# 尝试加载常见的conda环境依赖路径
potential_paths = [
    "D:\\anaconda3\\envs\\modelapp\\Lib\\site-packages",
    "C:\\Users\\%USERNAME%\\anaconda3\\envs\\modelapp\\Lib\\site-packages",
    # 添加其他可能的路径
]

for path in potential_paths:
    expanded_path = os.path.expandvars(path)
    if os.path.exists(expanded_path) and expanded_path not in sys.path:
        sys.path.append(expanded_path)
        logger.info(f"✨ 添加路径到Python环境: {expanded_path}")

# 检测torch是否可用
has_torch = False
try:
    import torch
    has_torch = True
    logger.info("✅ torch模块可用，版本: " + torch.__version__)
except ImportError:
    logger.warning("❌ torch模块不可用，将使用替代方案")

# 尝试首先加载真实的image_recognition模块
if has_torch:
    # 使用延迟加载函数加载模块
    real_module = load_module('image_recognition')
    if real_module:
        modules['image_recognition'] = real_module
        modules['real_image_recognition'] = real_module
        HAS_IMAGE_RECOGNITION = True
        logger.info("✅ 成功加载真实的image_recognition模块")
    else:
        logger.warning("❌ 无法加载真实的image_recognition模块，将尝试加载模拟模块")
        HAS_IMAGE_RECOGNITION = False
else:
    logger.warning("❌ torch不可用，跳过加载真实的image_recognition模块")
    HAS_IMAGE_RECOGNITION = False

# 如果真实模块加载失败，尝试加载模拟模块
if not HAS_IMAGE_RECOGNITION:
    # 尝试加载模拟模块
    mock_module = load_module('mock_image_recognition')
    if mock_module:
        modules['mock_image_recognition'] = mock_module
        modules['image_recognition'] = mock_module  # 将模拟模块作为默认图像识别模块
        HAS_IMAGE_RECOGNITION = True
        logger.info("✅ 成功加载模拟的image_recognition模块")
    else:
        logger.error("❌ 无法加载真实或模拟的image_recognition模块，图像识别功能将不可用")
        HAS_IMAGE_RECOGNITION = False

import uvicorn
from typing import Dict
import platform
import sys
import datetime
import logging
from contextlib import asynccontextmanager
import signal
import os
import asyncio

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建一个自定义格式化日志的函数
def log_service_status(service_name, status, details=None):
    """打印服务状态日志，使用高亮显示"""
    border = "=" * 60
    if status == "success":
        status_text = "✅ 成功"
    elif status == "warning":
        status_text = "⚠️ 警告"
    elif status == "error":
        status_text = "❌ 错误"
    else:
        status_text = status
    
    logger.info(border)
    logger.info(f"  服务: {service_name}")
    logger.info(f"  状态: {status_text}")
    if details:
        logger.info(f"  详情: {details}")
    logger.info(border)

# 存储子进程对象
external_services = {}

# 添加一个全局变量来跟踪基本的信号处理状态
global SIGNAL_COUNT
SIGNAL_COUNT = 0

# 添加一个标志来控制是否允许服务退出
ALLOW_EXIT = False


def signal_handler(signum, frame):
    """处理进程信号 - 允许正常退出"""
    global SIGNAL_COUNT, ALLOW_EXIT
    SIGNAL_COUNT += 1
    
    signal_name = {
        signal.SIGINT: "SIGINT (Ctrl+C)",
        signal.SIGTERM: "SIGTERM (Termination)",
        signal.SIGABRT: "SIGABRT (Abort)",
    }.get(signum, f"Unknown Signal ({signum})")
    
    logger.warning(f"收到关闭信号 #{SIGNAL_COUNT}: {signal_name}")
    
    # 如果允许退出或者收到多次信号，则正常退出
    if ALLOW_EXIT or SIGNAL_COUNT >= 3:
        logger.warning("正在停止服务...")
        # 执行清理工作
        try:
            stop_external_services()
        except Exception:
            pass
        # 退出程序
        os._exit(0)
    else:
        # 第一次或第二次信号时，提示用户
        logger.warning(f"按 {'Ctrl+C ' * (3 - SIGNAL_COUNT)}次来强制退出服务")
        logger.warning("正在继续运行服务...")


# 注册信号处理器 - 注意：在开发模式下需要允许正常退出
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # 终止信号

def start_external_services():
    """启动外部项目服务"""
    try:
        # 启动夜间低光图像增强与目标检测服务
        night_detection_status = night_detection.start_night_detection_service()
        if night_detection_status:
            log_service_status("夜间低光图像增强与目标检测服务", "success")
        else:
            log_service_status("夜间低光图像增强与目标检测服务", "warning", "服务启动但有警告")
        
        # 启动可见光-热微小物体检测服务
        rgbt_detection_status = rgbt_detection.start_rgbt_detection_service()
        if rgbt_detection_status:
            log_service_status("可见光-热微小物体检测服务", "success")
        else:
            log_service_status("可见光-热微小物体检测服务", "warning", "服务启动但有警告")
        
        # 设置当前状态
        setattr(app.state, "plate_recognition_loaded", False)
        
        # 自动启动车牌识别服务
        try:
            # 使用异步器所以不会阻塞主线程
            asyncio.create_task(plate_recognition.start_plate_recognition_service(None))
            log_service_status("车牌识别服务", "success", "服务已开始自动启动")
        except Exception as e:
            log_service_status("车牌识别服务", "warning", f"自动启动失败: {str(e)}")
        
        log_service_status("所有外部服务", "success", "基础服务启动成功，车牌识别服务正在启动")
        return True
    except Exception as e:
        logger.error(f"启动外部服务失败: {str(e)}")
        return False

def stop_external_services():
    """停止所有外部服务"""
    logger.info("正在停止外部服务...")
    for route in app.routes:
        # 过滤掉标准的webservice相关路由，只输出API路由
        if route.path.startswith("/api"):
            if hasattr(route, "methods"):
                methods = route.methods
                path = route.path
                logger.info(f"✨ 可用路由: {path}, 方法: {methods}")
                
    # 特别检查图像识别路由
    image_routes = [r for r in app.routes if r.path.startswith("/api/image-recognition")]
    if image_routes:
        logger.info(f"✅ 找到 {len(image_routes)} 个图像识别相关路由")
        for r in image_routes:
            if hasattr(r, "methods"):
                logger.info(f"⭐ 图像识别路由: {r.path}, 方法: {r.methods}")
    else:
        logger.error("⛔ 没有找到任何图像识别路由！")
    for service_name, process in external_services.items():
        if process and process.poll() is None:  # 如果进程还在运行
            try:
                process.terminate()
                logger.info(f"已终止服务: {service_name}")
            except Exception as e:
                logger.error(f"终止服务时出错 {service_name}: {str(e)}")

# 在模块级别创建一个标志变量来控制服务是否应该保持运行
KEEP_APP_RUNNING = True

# 设置深度调试日志级别
DEBUG_MODE = True

# 全局服务状态标志
global SERVICE_STATE
SERVICE_STATE = {
    "startup_complete": False,  # 标记服务是否完成了启动
    "initialized_modules": set(),  # 记录哪些模块已经被初始化
    "pid": os.getpid(),  # 记录主进程 ID
}

# 在FastAPI主应用程序中预先初始化所有需要的服务，而不依赖路由级别的startup事件
def initialize_all_services():
    """在主应用程序生命周期中预先初始化所有服务"""
    global SERVICE_STATE
    
    # 这里从app.routers包中导入所有需要的模块并手动初始化它们
    # 这避免了依赖路由器级别的startup事件
    
    # 1. 初始化火灾检测服务
    logger.info("预先初始化火灾检测服务...")
    try:
        # 直接导入并调用初始化函数
        from app.routers.fire_detection import initialize_fire_detection
        initialize_fire_detection()
        SERVICE_STATE["initialized_modules"].add("fire_detection")
        logger.info("火灾检测服务预先初始化成功")
    except Exception as e:
        logger.error(f"在主生命周期初始化火灾检测服务失败: {str(e)}")
        # 继续初始化其他服务，不允许单个服务的失败影响整体
    
    # 2. 初始化其他可能需要主动准备的服务
    # 如其他服务也有使用on_event("startup")装饰器的，应该在这里手动调用它们
    # 比如车牌识别服务等
    
    # 标记服务已完成预先初始化
    SERVICE_STATE["startup_complete"] = True
    logger.info("所有服务已预先初始化完成")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    从根本解决生命周期问题的方法
    不依赖任何阻塞线程或其他变通方法
    """
    # 日志配置
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - [%(processName)s:%(process)d] - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)
    
    logger.info("\n\n=============== ModelService后端启动 ===============")
    logger.info(f"[进程信息] PID: {os.getpid()}, 工作目录: {os.getcwd()}")
    
    # 设置关键环境变量
    os.environ["PREVENT_SERVER_SHUTDOWN"] = "true"
    os.environ["APPLICATION_READY"] = "false"  # 开始时设置为false
    
    # 清除和准备原始服务状态
    logger.info("准备服务状态...")
    global KEEP_APP_RUNNING
    KEEP_APP_RUNNING = True
    
    # 1. 提前准备并初始化所有服务
    logger.info("开始预先初始化所有服务...")
    initialize_all_services()  # 这是这个解决方案的关键部分
    
    # 2. 禁用所有router级别的on_event("startup")事件
    logger.info("禁用路由器级别的startup事件...")
    # 通过覆盖路由器的on_event方法实现
    from fastapi.routing import APIRouter
    
    # 保存原始方法
    original_on_event = APIRouter.on_event
    
    # 覆盖on_event方法，截获startup事件
    def safe_on_event(self, event_type: str):
        if event_type == "startup":
            # 对于startup事件，返回一个不执行任何操作的装饰器
            def empty_decorator(func):
                logger.info(f"已禁用路由器的startup事件: {func.__name__}")
                return func
            return empty_decorator
        else:
            # 其他事件类型使用原始方法
            return original_on_event(self, event_type)
    
    # 应用新的方法
    APIRouter.on_event = safe_on_event
    
    logger.info("应用准备就绪，准备返回控制权给uvicorn...")
    os.environ["APPLICATION_READY"] = "true"
    
    # 3. 将控制权返回给uvicorn
    try:
        logger.info("将控制权移交给ASGI服务器... (yield)")
        yield  # 移交控制权给ASGI服务器
        logger.info("控制权返回到lifespan函数 (uvicorn准备关闭)")
    except Exception as e:
        # 即使发生异常也不影响服务运行
        logger.error(f"生命周期异常: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # 4. 清理工作，但不中断服务
        logger.info("\n生命周期结束，但不影响服务继续运行")
        # 如果还需要执行其他清理，请在这里添加代码

# 全局限制器 - 强制防止应用程序停止
import atexit
import threading
import time

# 退出计数器
global EXIT_ATTEMPTS
EXIT_ATTEMPTS = 0

# 保护线程 - 最后的防线，但允许错误信息正常输出
def service_protector():
    logger.warning("启动服务保护线程 - 保持服务运行同时允许错误信息正常输出")
    try:
        # 保持服务运行的循环，但不干扰正常输出
        last_log_time = time.time()
        error_count = 0
        max_errors = 100  # 最大错误允许数
        
        while True:
            # 每60秒输出一次状态日志（改为 debug，避免在默认控制台刷屏）
            current_time = time.time()
            if current_time - last_log_time > 60:
                logger.debug(f"服务已运行 {int((current_time - last_log_time) // 60)} 分钟 | 错误计数: {error_count}")
                last_log_time = current_time
                
            # 轻量级睡眠以减少CPU占用
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.warning("保护线程收到键盘中断，但程序将继续运行")
        # 重新启动保护线程
        service_protector()
    except Exception as e:
        error_count += 1
        logger.error(f"保护线程异常: {str(e)}，计数: {error_count}")
        
        # 如果错误数超过限制，则重启保护线程
        if error_count > max_errors:
            logger.warning(f"错误数超过限制 ({max_errors})，重新启动保护线程")
            time.sleep(1)  # 等待一秒后重新启动
            error_count = 0
            
        # 尝试继续运行
        service_protector()

# 启动保护线程 - 使用新的service_protector函数
protector = threading.Thread(target=service_protector, daemon=False)
protector.start()

# 改进的退出防护函数 - 允许错误日志输出同时防止服务关闭
def prevent_exit():
    global EXIT_ATTEMPTS
    EXIT_ATTEMPTS += 1
    
    try:
        import inspect
        frame = inspect.currentframe().f_back
        caller_info = "unknown"
        if frame:
            caller_info = f"{frame.f_code.co_filename}:{frame.f_lineno} -> {frame.f_code.co_name}"
        
        logger.warning(f"\n!!! 检测到第 {EXIT_ATTEMPTS} 次退出尝试 (来源: {caller_info}) !!!")
        
        # 如果这是正常的进程结束，不进行拦截，允许正常的错误日志输出
        if EXIT_ATTEMPTS <= 3 and "uvicorn" in caller_info:
            logger.warning("!!! 正常的uvicorn请求处理，允许日志输出但不中断服务")
            # 允许处理器返回，但不停止服务
            return
        
        if "exit" in caller_info.lower() or "shutdown" in caller_info.lower():
            logger.warning("!!! 检测到明确的退出请求，强制拦截 !!!")
            # 如果是明确的退出请求则拦截
    except Exception as e:
        logger.error(f"!!! 退出分析异常: {str(e)}")
    
    logger.info("服务继续运行中 - 重新处理请求")
    
    # 如果是第10次及以上的退出尝试，启动强力阻止退出机制
    if EXIT_ATTEMPTS >= 10:
        logger.warning(f"!!! 多次退出尝试 ({EXIT_ATTEMPTS}) - 启动防护模式 !!!")
        try:
            # 重新注册信号处理器
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except Exception as e:
            logger.warning(f"!!! 信号处理器注册失败: {str(e)}")
        
        # 不阻塞主线程，而是创建新线程
        threading.Thread(target=lambda: time.sleep(3600), daemon=False).start()

# 注册强力退出防护函数
atexit.register(prevent_exit)

# 初始化FastAPI应用
app = FastAPI(
    title="ModelService API",
    description="""ModelService API - 毕业设计项目后端服务。
    支持车牌识别、图像分析、图像处理等功能。""",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"defaultModelsExpandDepth": 0},
)

# 增加文件上传大小限制
from starlette.middleware.base import BaseHTTPMiddleware

# 创建一个中间件来处理大文件上传
class LargeFileHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 对于视频上传接口增加特殊处理
        if request.url.path.startswith("/api/fire-detection/upload-video"):
            logger.info(f"LargeFileHandlingMiddleware: 处理大文件上传 - {request.url.path}")
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("multipart/form-data"):
                # 增加错误处理和日志
                try:
                    response = await call_next(request)
                    return response
                except Exception as e:
                    logger.error(f"处理大文件上传出错: {str(e)}")
                    return JSONResponse(
                        status_code=500,
                        content={"detail": f"处理文件上传时出错: {str(e)}"}
                    )
        return await call_next(request)

# 添加大文件处理中间件
app.add_middleware(LargeFileHandlingMiddleware)

# 服务器配置
import uvicorn

# 自定义异常和处理程序
class CustomException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

# 配置跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
    expose_headers=["*"],  # 暴露所有头部
)

# 配置特殊的超大文件处理中间件
@app.middleware("http")
async def process_large_files_middleware(request: Request, call_next):
    # 特殊处理视频上传请求
    content_length = request.headers.get("content-length")
    content_type = request.headers.get("content-type", "")
    
    if "/api/fire-detection/upload-video" in request.url.path:
        logger.info(f"检测到视频上传请求: {request.url.path}, 内容类型: {content_type}, 内容长度: {content_length}")
        # 完全移除请求大小限制
        request._body_size_limit = None

    try:
        # 增加请求处理超时时间
        response = await asyncio.wait_for(call_next(request), timeout=600.0)
        return response
    except asyncio.TimeoutError:
        logger.error(f"请求处理超时: {request.url.path}")
        return JSONResponse(
            status_code=504,
            content={"detail": "请求处理超时"}
        )
    except Exception as e:
        logger.exception(f"处理请求时出错: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"服务器内部错误: {str(e)}"}
        )

# 添加静态文件服务
app.mount("/static", StaticFiles(directory=MAIN_DIR / "static"), name="static")

# CORS配置
origins = [
    "http://localhost:8889",  # 增加前端端口 8889
    "http://localhost:8082",
    "http://localhost:8081", 
    "http://localhost:8890",
    "http://localhost:8891",
    "http://localhost:5173",  # Vite默认端口(前端项目1)
    "http://127.0.0.1:5173",  # Vite默认端口(IP形式)
    "http://localhost:8080",  # 前端项目2端口
    "http://127.0.0.1:8080",  # 前端项目2端口(IP形式)
    "http://127.0.0.1:8889", 
    "http://127.0.0.1:8082",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:8890",
    "http://127.0.0.1:8891",
    "http://localhost:8083",  # Vite开发服务器端口
    "http://127.0.0.1:8083",  # Vite开发服务器端口
    "*"   # 允许所有源，仅在开发环境使用
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 添加路由别名中间件，处理两套前端项目的路由
class RouteAliasMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 提取请求路径
        path = request.url.path
        
        # 如果是API请求
        if path.startswith('/api/'):
            # 提取模块名称，例如：从 /api/route-planning/... 提取 route-planning
            parts = path.split('/')
            if len(parts) > 2:
                module_path = parts[2]  # 获取第三段作为模块路径
                logger.info(f"API请求: {path}, 模块路径: {module_path}")
                
                # 查找所有启用的模块配置
                enabled_modules = get_enabled_modules()
                for module_name in enabled_modules:
                    config = get_module_config(module_name)
                    # 检查是否为别名模块
                    if is_alias_module(module_name):
                        # 如果当前请求路径匹配别名模块的前缀
                        prefix = config.get("prefix", "").rstrip('/')
                        if prefix.endswith(f"/{module_path}"):
                            # 找到真实模块
                            real_module = get_aliased_module(module_name)
                            if real_module:
                                real_config = get_module_config(real_module)
                                real_prefix = real_config.get("prefix", "").rstrip('/')
                                # 构建新的路径
                                new_path = path.replace(prefix, real_prefix)
                                logger.info(f"别名路由重定向: {path} -> {new_path}")
                                # 更新请求的URL路径
                                request.scope["path"] = new_path
                                # 更新原始路径，保留原始请求信息
                                if "original_path" not in request.scope:
                                    request.scope["original_path"] = path
                                break
        
        # 继续处理请求
        return await call_next(request)

# 添加路由别名中间件
app.add_middleware(RouteAliasMiddleware)

# 使用动态写法注册可用的路由
# 验证modules不为空
if not modules:
    logger.error("❗ 没有可用的模块被加载")

# 注册可用的模块路由
for module_name, module in modules.items():
    try:
        if hasattr(module, 'router'):
            # 确保有前缀
            prefix = getattr(module, 'API_PREFIX', f'/api/{module_name.replace("_", "-")}')
            # 注册路由
            app.include_router(module.router, prefix=prefix)
            logger.info(f"✅ 成功注册路由: {prefix} 从模块 {module_name}")
        else:
            logger.warning(f"⚠️ 模块 {module_name} 没有路由器")
    except Exception as e:
        logger.error(f"❗ 注册路由失败 {module_name}: {str(e)}")

# 注册测试路由
try:
    app.include_router(test_router, prefix="/api/test")
    logger.info("✅ 成功注册测试路由: /api/test")
except Exception as e:
    logger.error(f"❗ 注册测试路由失败: {str(e)}")


# 健康检查端点：返回已注册模块与 API 路由（便于调试）
@app.get("/api/health")
async def health():
    try:
        # 仅返回以 /api 开头的路由，简化输出
        api_routes = []
        for route in app.routes:
            try:
                path = getattr(route, "path", None)
                methods = list(getattr(route, "methods", []))
                if path and str(path).startswith("/api"):
                    api_routes.append({"path": path, "methods": methods})
            except Exception:
                continue

        return {
            "status": "ok",
            "modules_loaded": list(modules.keys()),
            "api_routes": api_routes
        }
    except Exception as e:
        logger.error(f"health endpoint error: {str(e)}")
        return {"status": "error", "error": str(e)}


# 挂载静态文件 - 使用绝对路径
static_dir = MAIN_DIR / "static"
output_dir = MAIN_DIR / "output"

# 确保目录存在
static_dir.mkdir(exist_ok=True)
output_dir.mkdir(exist_ok=True)

# 挂载静态文件
# 定义原始目录和应用目录
app_static_dir = MAIN_DIR / "app" / "static"

# 确保目录存在
app_static_dir.mkdir(exist_ok=True)

# 挂载全部静态文件路径
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 如果存在，挂载应用目录的静态文件路径
if app_static_dir.exists():
    # 优先使用app/static目录作为/api/static的挂载点
    # 这使得/api/static/rgbt_detection直接对应到app/static/rgbt_detection
    app.mount("/api/static", StaticFiles(directory=str(app_static_dir)), name="api_static")
    
    # 兼容性挂载 - 保留旧路径以防有其他代码依赖
    app.mount("/static/app", StaticFiles(directory=str(app_static_dir)), name="app_static")
    app.mount("/api/static/app", StaticFiles(directory=str(app_static_dir)), name="api_app_static")
    print(f"应用静态文件目录: {app_static_dir}")
else:
    # 如果app/static不存在，使用普通static目录
    app.mount("/api/static", StaticFiles(directory=str(static_dir)), name="api_static")

app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")
print(f"静态文件目录: {static_dir}")
print(f"输出文件目录: {output_dir}")

# 直接在main.py中添加视频上传路由，确保能被正确注册
@app.post("/api/plate-recognition/upload-video")
async def upload_video_direct(request: Request):
    """直接处理视频上传的路由 - 处理任何形式的文件上传"""
    logger.info("收到视频上传请求 - API路径: /api/plate-recognition/upload-video")
    
    try:
        # 尝试解析multipart表单数据
        form = await request.form()
        logger.info(f"表单数据键: {list(form.keys())}")
        
        # 从表单中查找文件 - 支持多种字段名
        file = None
        for field_name in ["file", "video", "files[]"]:
            if field_name in form:
                file = form[field_name]
                logger.info(f"找到文件字段: {field_name}")
                break
        
        if not file:
            logger.error("未找到文件字段")
            return JSONResponse({"success": False, "message": "未找到文件"}, status_code=400)
            
        # 处理文件
        logger.info(f"处理文件: {getattr(file, 'filename', '未知文件名')}")
        # 这里缺少了具体的处理逻辑...
        return JSONResponse({"success": True, "message": "文件上传成功"})
    except Exception as e:
        logger.error(f"处理文件上传时出错: {str(e)}")
        return JSONResponse({"success": False, "message": f"处理出错: {str(e)}"}, status_code=500)

# 注册必备的车牌识别模块
if 'plate_recognition_integrated' in modules:
    app.include_router(modules['plate_recognition_integrated'].router, prefix="/api/plate-recognition", tags=["车牌识别(集成版)"])
    logger.info("✨ 车牌识别模块(集成版)已加载")
    
    # 异步初始化车牌识别服务
    try:
        from app.services.plate_recognition.startup import init_service_async
        
        # 使用应用启动事件替代bg_tasks
        @app.on_event("startup")
        async def startup_plate_recognition_init():
            try:
                await init_service_async()
                logger.info("✨ 车牌识别服务初始化完成")
            except Exception as e:
                logger.error(f"❌ 车牌识别服务初始化失败: {str(e)}")
        
        logger.info("✨ 车牌识别服务初始化任务已注册到应用启动事件")
    except Exception as e:
        logger.error(f"❌ 车牌识别服务初始化配置失败: {str(e)}")

elif 'plate_recognition' in modules:
    app.include_router(modules['plate_recognition'].router, prefix="/api/plate-recognition", tags=["车牌识别"])
    logger.info("车牌识别模块已加载")

# 注册车牌监控模块
if 'plate_monitoring' in modules:
    app.include_router(modules['plate_monitoring'].router, prefix="/api/plate-monitoring", tags=["车牌监控"])
    logger.info("✨ 车牌监控模块已加载")
    
    # 导入并注册车牌识别URL修复模块
    try:
        from app.routers.plate_recognition_url_fix import router as plate_rec_url_router
        app.include_router(plate_rec_url_router, prefix="/api/plate-recognition", tags=["车牌识别URL修复"])
        logger.info("✅ 车牌识别URL修复模块已加载")
    except Exception as e:
        logger.error(f"❌ 车牌识别URL修复模块加载失败: {str(e)}")
else:
    logger.error("车牌识别模块加载失败，系统核心功能不可用")

# 手动注册知识库聊天模块
if 'knowledge_chat' in modules:
    try:
        app.include_router(
            modules['knowledge_chat'].router,
            tags=["知识库聊天"]
        )
        logger.info("✨ 知识库聊天模块已成功注册")
        
        # 初始化Neo4j连接
        try:
            from app.routers.knowledge_chat import neo4j_connection
            if neo4j_connection:
                logger.info("✅ Neo4j数据库连接成功")
            else:
                logger.warning("⚠️ Neo4j数据库连接未初始化")
        except Exception as neo4j_err:
            logger.warning(f"⚠️ Neo4j连接检查失败: {str(neo4j_err)}")
    except Exception as e:
        logger.error(f"❌ 知识库聊天模块注册失败: {str(e)}")

# 注册知识图谱增强模块
try:
    from app.routers import knowledge_graph_enhanced
    app.include_router(
        knowledge_graph_enhanced.router,
        prefix="/api/knowledge-graph",
        tags=["知识图谱"]
    )
    # 也注册到旧的API路径，确保兼容性
    app.include_router(
        knowledge_graph_enhanced.router,
        prefix="/api/knowledge-chat",
        tags=["知识库聊天"]
    )
    logger.info("✨ 知识图谱增强模块已成功注册")
    logger.info("  * 支持Neo4j图谱存储和可视化")
    logger.info("  * 支持FAISS向量检索")
    logger.info("  * 兼容旧API路径")
    logger.info("  * 支持Ollama本地大模型问答")
except Exception as e:
    logger.error(f"❌ 知识图谱增强模块注册失败: {str(e)}")

# 注册无人机知识图谱路由模块
try:
    from app.routers import uav_knowledge
    app.include_router(
        uav_knowledge.router,
        prefix="/api/uav-knowledge",
        tags=["无人机知识图谱"]
    )
    logger.info("✨ 无人机知识图谱模块已成功注册")
    logger.info("  * 支持无人机数据查询和可视化")
    logger.info("  * 提供无人机知识图谱API")
except Exception as e:
    logger.error(f"❌ 无人机知识图谱模块注册失败: {str(e)}")

# 根据模块可用性注册其他路由
route_handlers = {
    'chat': {
        "prefix": "/api/chat", 
        "tags": ["聊天机器人"]
    },
    'route_planning': {
        "prefix": "/api/route-planning", 
        "tags": ["路线规划"]
    },
    'video_tracking': {
        "prefix": "/api/video-tracking", 
        "tags": ["视频追踪"]
    },
    'image_analysis_chat': {
        "prefix": "/api/image-analysis-chat", 
        "tags": ["图片分析聊天"]
    },
    'knowledge_chat': {
        "prefix": "/api/knowledge-chat", 
        "tags": ["知识库聊天"]
    },
    'night_detection': {
        "prefix": "/api/night-detection", 
        "tags": ["夜视车辆检测"]
    },
    'rgbt_detection': {
        "prefix": "/api/rgbt-detection", 
        "tags": ["RGBT检测"]
    },
    'rgbt_video': {
        "prefix": "/api/rgbt-video", 
        "tags": ["RGBT视频处理"]
    },
    'plate_recognition': {
        "prefix": "/api/plate-recognition", 
        "tags": ["车牌识别"]
    },
    'plate_monitoring': {
        "prefix": "/api/plate-monitoring", 
        "tags": ["车牌监控"]
    },
    'fire_detection': {
        "prefix": "/api/fire-detection", 
        "tags": ["火灾检测"]
    }
}

# 注册图像识别路由 - 增强的调试方法（保证至少有一个可用路由）
logger.info("===== 正在注册图像识别路由... =====")

# 输出所有可用的模块，便于排查 /api/image-recognition 404 问题
all_modules = list(modules.keys())
logger.info(f"当前加载的模块: {all_modules}")

# 目标：优先使用真实图像识别模块，真实不可用时使用模拟模块；
# 同时增加兜底逻辑，保证至少 mock_image_recognition 一定会被挂载，避免前端 404

HAS_IMAGE_RECOGNITION_ROUTER = False

# 1. 优先尝试使用已加载的真实 image_recognition 模块
if 'image_recognition' in modules:
    logger.info("⚡️ 尝试使用 image_recognition 模块处理图像识别请求")
    try:
        image_router = modules['image_recognition'].router
        app.include_router(
            image_router,
            prefix="/api/image-recognition",
            tags=["图像识别"]
        )
        logger.info("✅ 成功注册真实 image_recognition 路由")

        for route in image_router.routes:
            logger.info(f"✨ 图像识别端点: {route.path}, 方法: {route.methods}")

        HAS_IMAGE_RECOGNITION_ROUTER = True
    except Exception as e:
        logger.error(f"❗ 注册真实 image_recognition 路由失败: {str(e)}")
        logger.exception(e)

# 2. 如果上一步失败，尝试使用 real_image_recognition（兼容旧逻辑）
if not HAS_IMAGE_RECOGNITION_ROUTER and 'real_image_recognition' in modules:
    logger.info("⚡️ 尝试使用 real_image_recognition 模块处理图像识别请求")
    try:
        real_router = modules['real_image_recognition'].router
        app.include_router(
            real_router,
            prefix="/api/image-recognition",
            tags=["图像识别"]
        )
        logger.info("✅ 成功注册真实 real_image_recognition 路由")

        for route in real_router.routes:
            logger.info(f"✨ 图像识别端点: {route.path}, 方法: {route.methods}")

        HAS_IMAGE_RECOGNITION_ROUTER = True
    except Exception as e:
        logger.error(f"❗ 注册真实 real_image_recognition 路由失败: {str(e)}")
        logger.exception(e)

# 3. 如果真实模块都不可用，尝试使用已加载的 mock_image_recognition 模块
if not HAS_IMAGE_RECOGNITION_ROUTER and 'mock_image_recognition' in modules:
    logger.info("⚡️ 尝试使用已加载的 mock_image_recognition 模块（模拟数据）")
    try:
        mock_router = modules['mock_image_recognition'].router
        app.include_router(
            mock_router,
            prefix="/api/image-recognition",
            tags=["图像识别（模拟）"]
        )
        logger.info("✅ 成功注册 mock_image_recognition 路由（模拟数据）")

        for route in mock_router.routes:
            logger.info(f"✨ 图像识别端点: {route.path}, 方法: {route.methods}")

        HAS_IMAGE_RECOGNITION_ROUTER = True
    except Exception as e:
        logger.error(f"❗ 使用 modules['mock_image_recognition'] 注册路由失败: {str(e)}")
        logger.exception(e)

# 4. 兜底：即使前面的动态模块加载都失败，也直接导入 mock_image_recognition 并挂载，
#    以彻底避免 /api/image-recognition/analyze 404
if not HAS_IMAGE_RECOGNITION_ROUTER:
    try:
        from app.routers import mock_image_recognition as _mock_image_recognition

        logger.info("⚡️ 使用兜底方案直接导入 mock_image_recognition 并注册路由")
        app.include_router(
            _mock_image_recognition.router,
            prefix="/api/image-recognition",
            tags=["图像识别（模拟兜底）"]
        )

        for route in _mock_image_recognition.router.routes:
            logger.info(f"✨ 兜底图像识别端点: {route.path}, 方法: {route.methods}")

        HAS_IMAGE_RECOGNITION_ROUTER = True
    except Exception as e:
        logger.error(f"⛔ 兜底导入 mock_image_recognition 并注册路由仍然失败: {str(e)}")
        logger.exception(e)

# 5. 最终确认：输出所有 /api/image-recognition 相关路由，帮助排查
image_routes = [r for r in app.routes if r.path.startswith("/api/image-recognition")]
if image_routes:
    logger.info(f"✅ 最终确认：找到 {len(image_routes)} 个 /api/image-recognition 路由")
    for r in image_routes:
        logger.info(f"⭐ 路由: {r.path}, 方法: {getattr(r, 'methods', None)}")
else:
    logger.error("⛔ 最终确认：仍然没有任何 /api/image-recognition 路由，前端会出现 404，请检查依赖环境")

# 注册测试端点模块
try:
    app.include_router(
        test_router,
        prefix="/api/test",
        tags=["测试接口"]
    )
    logger.info("✅ 成功注册测试端点路由")
except Exception as e:
    logger.error(f"❗ 注册测试端点路由失败: {str(e)}")

# 导入路径规划路由模块 - 使用已加载的模块或回退到 fallback
try:
    # 检查是否已经加载了高级版本的 route_planning 模块
    if 'route_planning' in modules and modules['route_planning'] is not None:
        route_planning = modules['route_planning']
        logger.info('✅ 使用已加载的高级路径规划模块')
    else:
        # 尝试导入高级版本
        from ModelService.Main.app.routers import route_planning
        modules['route_planning'] = route_planning
        logger.info('✅ 成功导入高级路径规划模块')
    
    # 注册路由
    app.include_router(
        route_planning.router,
        prefix=getattr(route_planning, 'API_PREFIX', '/api/route'),
        tags=['路径规划']
    )
    logger.info('✅ 成功注册路径规划路由')
    
    # 兼容性：确保 /api/route/plan/stream 明确可用
    if hasattr(route_planning, 'stream_route_plan'):
        app.add_api_route("/api/route/plan/stream", route_planning.stream_route_plan, methods=["GET"])
        logger.info("✅ 明确注册流式路线规划端点: /api/route/plan/stream")
        
except Exception as e:
    logger.error(f'❌ 注册路径规划路由失败: {str(e)}')
    # 尝试加载回退实现
    try:
        from app.routers import route_planning_fallback as route_planning
        modules['route_planning'] = route_planning
        app.include_router(
            route_planning.router,
            prefix='/api/route',
            tags=['路径规划(回退)']
        )
        logger.warning('⚠️ 已加载 route_planning 回退实现 - 功能受限')
    except Exception as fe:
        logger.error(f'❌ 无法加载路径规划回退模块: {str(fe)}')

# 导入UAV前端项目路径规划路由模块
try:
    from app.routers import uav_route_planning
    app.include_router(
        uav_route_planning.router,
        tags=['UAV路径规划']
    )
    logger.info('✅ 成功注册UAV路径规划路由')
except Exception as e:
    logger.error(f'❌ 注册UAV路径规划路由失败: {str(e)}')

# 动态注册路由
for module_name, config in route_handlers.items():
    if module_name in modules:
        try:
            app.include_router(
                modules[module_name].router, 
                prefix=config["prefix"], 
                tags=config["tags"]
            )
            logger.info(f"成功注册路由: {module_name}")
        except Exception as e:
            logger.error(f"注册路由失败 {module_name}: {str(e)}")
    else:
        logger.warning(f"模块不可用，跳过路由注册: {module_name}")
# 这些端点只在路由注册完全失败时才会被使用
# 为了避免冲突，将路径改为不同的名称

# 直接定义端点响应前端请求 - 极简化版，只有最必要的代码
# 注释掉这个直接处理图像分析的路由处理器，避免与mock_image_recognition.py中的路由冲突
# @app.post("/api/image-recognition/analyze") 
# async def analyze_image_direct(
#     file: UploadFile = File(...),
#     mode: str = Form("pose_detection"),
# ):
#     # 打印详细的请求信息
#     logger.info(f"⚡️ 收到图像分析请求: 文件={file.filename}, 模式={mode}")
#     
#     try:
#         # 读取上传的文件内容
#         content = await file.read()
#         file_size = len(content)
#         logger.info(f"文件大小: {file_size} 字节")
#         
#         # 简化的模拟响应数据
#         base64_image = base64.b64encode(content).decode('utf-8')
#         
#         # 直接返回最简单的数据结构
#         result = {
#             "detected": True,
#             "persons": [
#                 {
#                     "keypoints": [
#                         {"x": 0.5, "y": 0.2, "confidence": 0.95, "name": "nose"}
#                     ],
#                     "confidence": 0.92
#                 }
#             ],
#             "processedImage": base64_image
#         }
#         
#         logger.info("✅ 图像分析完成，返回结果")
#         return result
#         
#     except Exception as e:
#         error_msg = f"图像分析失败: {str(e)}"
#         logger.error(error_msg)
#         logger.exception(e)  # 输出完整堆栈跟踪
#         return {"error": error_msg}

# 直接添加模型列表端点作为后备方案
# 为了避免与模块路由冲突，使用不同的路径
@app.get("/api/image-recognition/models", tags=["图像识别(直接)"])
async def get_available_models_direct():
    logger.info("HTTP请求路径: /api/image-recognition/models")
    """获取可用模型列表的模拟实现 - 直接实现"""
    logger.info("使用直接定义的模型列表端点处理请求")
    models = [
        {"id": "pose_detection", "name": "姿态检测", "description": "检测人体姿态和关键点"},
        {"id": "object_detection", "name": "物体检测", "description": "检测图像中的物体"},
        {"id": "segmentation", "name": "图像分割", "description": "对图像进行语义分割"}
    ]
    
    return {"success": True, "message": "成功获取可用模型列表 (直接响应)", "data": models}

# 注释掉这个直接处理图像分析的路由处理器，避免与mock_image_recognition.py中的路由冲突
# @app.post("/api/image-recognition/analyze", summary="分析图像(直接实现)")
# async def analyze_image_direct(
#     file: UploadFile = File(...),
#     mode: str = Form("pose_detection"),
# ):
#     """
#     图像识别的直接FastAPI实现
#     添加此端点是为了确保即使模块加载失败，仍然有一个工作的图像分析端点
#     """
#     try:
#         logger.info(f"🔍 [直接端点] 接收到图像分析请求 - 文件: {file.filename}, 模式: {mode}")
#         
#         # 读取上传的文件内容
#         content = await file.read()
#         file_size = len(content)
#         logger.info(f"📥 [直接端点] 成功读取文件 - 大小: {file_size} 字节")
#         
#         # 将图片转为base64编码（用于前端展示）
#         base64_image = base64.b64encode(content).decode('utf-8')
#         logger.info("✅ [直接端点] 图像已转换为base64格式")
#         
#         # 创建一个明确包含所有必要属性的person对象
#         person = {
#             "keypoints": [
#                 {"x": 0.5, "y": 0.2, "z": 0, "confidence": 0.95, "name": "nose"},
#                 {"x": 0.48, "y": 0.18, "z": 0, "confidence": 0.93, "name": "left_eye"},
#                 {"x": 0.52, "y": 0.18, "z": 0, "confidence": 0.94, "name": "right_eye"}
#             ],
#             "confidence": 0.92,
#             "bbox": [100, 50, 300, 350],  # [x1, y1, x2, y2] 格式
#             "id": 1,
#             "age": 30,
#             "age_confidence": 0.85,
#             "gender": "male",
#             "gender_confidence": 0.88,
#             "upper_color": "blue", 
#             "upper_color_confidence": 0.85,
#             "lower_color": "black",
#             "lower_color_confidence": 0.82
#         }
#         
#         # 构建最终响应
#         response = {
#             "detected": True,
#             "persons": [person],
#             "processedImage": base64_image,
#             "objects": [
#                 {"class": "person", "confidence": 0.95, "bbox": [100, 50, 300, 350]},
#                 {"class": "chair", "confidence": 0.87, "bbox": [300, 200, 450, 350]}
#             ],
#             "analysis": {
#                 "scene": "indoor",
#                 "time": "daytime",
#                 "weather": "clear"
#             }
#         }
#         
#         # 验证并日志记录关键字段
#         logger.info(f"👤 [直接端点] 已识别人物数量: {len(response['persons'])}")
#         for i, p in enumerate(response['persons']):
#             logger.info(f"  人物 #{i+1} 数据验证:")
#             logger.info(f"    - ID: {p.get('id')}")
#             logger.info(f"    - 边界框(bbox): {p.get('bbox')}")
#             logger.info(f"    - 年龄: {p.get('age')}，置信度: {p.get('age_confidence')}")
#             logger.info(f"    - 性别: {p.get('gender')}，置信度: {p.get('gender_confidence')}")
#         
#         logger.info("📤 [直接端点] 返回分析结果到前端")
#         return response
# 注释掉孤立的except块
# except Exception as e:
#     logger.error(f"❌ [直接端点] 图像分析过程中出错: {str(e)}")
#     import traceback
#     logger.error(f"详细错误堆栈:\n{traceback.format_exc()}")
#     raise HTTPException(status_code=500, detail=f"图像分析失败: {str(e)}")

@app.get("/", tags=["系统信息"])
async def root() -> Dict:
    """获取系统基本信息"""
    try:
        return {
            "message": "Welcome to AI Assistant API",
            "version": "1.0.0",
            "system_info": {
                "python_version": sys.version,
                "platform": platform.platform()
            },
            "api_docs": {
                "swagger": "/api/docs",
                "redoc": "/api/redoc"
            }
        }
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统信息失败")

@app.get("/health", tags=["健康检查"])
async def health_check() -> Dict:
    """系统健康检查"""
    try:
        # 检查外部服务状态
        night_detection_status = "up" if os.path.exists("../../Night-vehicle-detection-system-main") else "down"
        rgbt_detection_status = "up" if os.path.exists("../../RGBT-Tiny") else "down"
        
        return {
            "status": "healthy",
            "services": {
                "api": "up",
                "database": "up",
                "ollama": "up",  # 本地大模型服务状态
                "night_detection": night_detection_status,
                "rgbt_detection": rgbt_detection_status
            },
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/test")
async def test():
    """测试接口"""
    try:
        return {"status": "ok", "message": "API服务正常运行"}
    except Exception as e:
        logger.error(f"测试接口失败: {str(e)}")
        raise HTTPException(status_code=500, detail="测试接口失败")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    error_detail = str(exc)
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        error_detail = exc.detail
    else:
        status_code = 500
    logger.error(f"Exception: {error_detail}")
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": error_detail}
    )

# 添加中间件来记录车牌识别服务的状态
@app.middleware("http")
async def plate_recognition_middleware(request: Request, call_next):
    # 检查是否是车牌识别相关请求
    if request.url.path.startswith("/plate-recognition") and request.url.path != "/plate-recognition/status":
        # 查看服务是否已经加载
        if not getattr(app.state, "plate_recognition_loaded", False):
            # 尝试启动车牌识别服务
            try:
                # 先获取当前状态
                result = await plate_recognition.get_plate_recognition_status(None)
                if result.get("status") != "started":
                    # 如果服务未运行，则启动它
                    await plate_recognition.start_plate_recognition_service(None)
                    log_service_status("车牌识别服务", "success", "服务已自动启动")
            except Exception as e:
                # 启动失败
                logger.error(f"自动启动车牌识别服务失败: {str(e)}")
    
    # 继续正常请求处理
    response = await call_next(request)
    return response

# 移除if __name__ == "__main__"块，使应用只能通过uvicorn命令行方式启动
# 这样可以避免应用在启动后自动关闭的问题

# 设置默认环境变量，确保服务不会自动关闭
# 这将作为后备保护措施
if "PREVENT_SERVER_SHUTDOWN" not in os.environ:
    os.environ["PREVENT_SERVER_SHUTDOWN"] = "true"
    logger.info("已自动设置PREVENT_SERVER_SHUTDOWN=true以防止服务器自动关闭")

# 通知用户正确的启动方式
logger.info("请使用以下命令启动服务:")
logger.info("python -m uvicorn app.main:app --host 0.0.0.0 --port 8081")

# ... 其他路由和代码

# 添加测试端点用于验证代理配置是否正常工作
@app.get("/api/plate-recognition/test-endpoint")
async def test_endpoint():
    """测试端点，仅用于验证代理配置"""
    logger.info("测试端点被访问 - /api/plate-recognition/test-endpoint")
    return JSONResponse({
        "status": "success",
        "message": "测试端点正常工作",
        "time": str(datetime.datetime.now())
    })

# 为upload-video创建一个简化版的GET测试端点
@app.get("/api/plate-recognition/upload-video-test")
async def upload_video_test():
    """视频上传测试端点 - 仅用于验证路由是否被正确注册"""
    logger.info("视频上传测试端点被访问 - /api/plate-recognition/upload-video-test")
    return JSONResponse({
        "status": "success",
        "message": "视频上传测试端点正常工作",
        "time": str(datetime.datetime.now())
    })

# 增加文件上传大小限制
from fastapi import UploadFile, File, Form
import shutil
from starlette.requests import Request
from starlette.responses import Response
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware

# 创建一个中间件来处理大文件上传
class LargeFileHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 对于视频上传接口增加特殊处理
        if request.url.path.startswith("/api/fire-detection/upload-video"):
            logger.info(f"LargeFileHandlingMiddleware: 处理大文件上传 - {request.url.path}")
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("multipart/form-data"):
                # 增加错误处理和日志
                try:
                    response = await call_next(request)
                    return response
                except Exception as e:
                    logger.error(f"处理大文件上传出错: {str(e)}")
                    return JSONResponse(
                        status_code=500,
                        content={"detail": f"处理文件上传时出错: {str(e)}"}
                    )
        return await call_next(request)

# 添加大文件处理中间件
app.add_middleware(LargeFileHandlingMiddleware)

# 添加视频上传专用路由
@app.post("/video_upload_test", summary="视频上传测试专用入口")
async def video_upload_test(file: UploadFile = File(...)):
    """
    视频上传测试专用入口，验证视频文件接收功能
    """
    filename = file.filename
    file_size = 0
    
    # 创建临时文件保存上传内容
    temp_file = f"temp_upload_test_{uuid.uuid4()}.mp4"
    with open(temp_file, "wb") as buffer:
        # 分块读取和写入文件
        chunk_size = 1024 * 1024  # 1MB
        chunk = await file.read(chunk_size)
        while chunk:
            file_size += len(chunk)
            buffer.write(chunk)
            chunk = await file.read(chunk_size)
    
    # 记录文件信息并删除临时文件
    logger.info(f"收到测试视频文件: {filename}, 大小: {file_size/1024/1024:.2f}MB")
    os.remove(temp_file)
    
    return {
        "filename": filename, 
        "size": file_size, 
        "size_mb": f"{file_size/1024/1024:.2f}MB",
        "message": "测试视频上传成功"
    }

# 为火灾检测添加简单测试端点
@app.get("/api/fire-detection/test", summary="火灾检测服务测试")
async def fire_detection_test():
    """
    测试火灾检测服务是否正常运行
    """
    try:
        # 导入火灾检测初始化函数
        from app.routers.fire_detection import initialize_fire_detection
        
        # 尝试初始化火灾检测服务
        if initialize_fire_detection():
            return {
                "status": "success",
                "message": "火灾检测服务运行正常",
                "time": str(datetime.datetime.now())
            }
        else:
            return {
                "status": "error",
                "message": "火灾检测服务初始化失败",
                "time": str(datetime.datetime.now())
            }
    except Exception as e:
        logger.error(f"测试火灾检测服务时出错: {str(e)}")
        return {
            "status": "error",
            "message": f"测试火灾检测服务时出错: {str(e)}",
            "time": str(datetime.datetime.now())
        }

# 为火灾检测添加直接的视频上传路由，绕过所有中间件和复杂的代理配置
@app.post("/api/fire_detection_direct/upload-video")
async def fire_detection_upload_video_direct(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    save_frames: bool = Form(True),
    enable_alarm: bool = Form(False),
    email: str = Form(""),
    frame_skip: int = Form(5)
):
    """直接处理火灾检测视频上传的路由 - 绕过所有中间件"""
    from app.routers.fire_detection import OUTPUT_DIR
    
    logger.info(f"Direct fire detection video upload: filename={file.filename}, content_type={file.content_type}, frame_skip={frame_skip}")
    
    try:
        # 确保初始化fire_detector
        from app.routers.fire_detection import initialize_fire_detection, fire_detector
        if fire_detector is None:
            logger.info("Fire detector not initialized, initializing now...")
            initialize_fire_detection()
            from app.routers.fire_detection import fire_detector
            if fire_detector is None:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Failed to initialize fire detector"}
                )
        
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Generate process ID
        process_id = str(uuid.uuid4())
        logger.info(f"Generated process ID: {process_id}")
        
        # Get original file extension
        if file.filename:
            original_extension = os.path.splitext(file.filename)[1].lower()
            if not original_extension:
                original_extension = ".mp4"
        else:
            original_extension = ".mp4"
            
        # Generate safe filename
        safe_filename = f"fire_detection_{process_id}{original_extension}"
        file_path = os.path.join(OUTPUT_DIR, safe_filename)
        logger.info(f"Created file path: {file_path}")
        
        # Create progress file
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        with open(progress_path, "w") as progress_file:
            json.dump({
                "status": "uploading",
                "progress": 0,
                "message": "Uploading video",
                "process_id": process_id,
                "file_name": safe_filename
            }, progress_file)
        logger.info(f"Created progress file: {progress_path}")
        
        # Save uploaded file
        with open(file_path, "wb") as f:
            # Read and write in chunks to handle large files
            chunk_size = 1024 * 1024  # 1MB chunks
            content = await file.read(chunk_size)
            while content:
                f.write(content)
                content = await file.read(chunk_size)
        
        logger.info(f"Saved file: {file_path}")
        
        # Update progress file
        with open(progress_path, "w") as progress_file:
            json.dump({
                "status": "uploaded",
                "progress": 10,
                "message": "Video uploaded, preparing for processing",
                "process_id": process_id,
                "file_name": safe_filename,
                "file_path": file_path,
                "frame_skip": frame_skip
            }, progress_file)
        
        # Start background task to process video
        from app.routers.fire_detection import process_video_task
        logger.info(f"Starting background task to process video: {file_path}, frame_skip={frame_skip}")
        
        try:
            # 确保函数存在且可调用
            if not callable(process_video_task):
                logger.error("process_video_task不是一个可调用函数")
                return JSONResponse(
                    status_code=500,
                    content={"detail": "内部服务错误：视频处理函数不可用"}
                )
            
            # 注意：我们需要添加一个包装函数来处理异步函数
            async def process_video_wrapper():
                try:
                    await process_video_task(
                        file_path=file_path,
                        process_id=process_id,
                        alarm_config={
                            "enabled": enable_alarm,
                            "email": email,
                            "interval": 60,
                            "threshold": 0.6  # 降低火灾检测的置信度阈值以增强检测效果
                        },
                        frame_skip=frame_skip,
                        save_frames=save_frames
                    )
                except Exception as e:
                    logger.exception(f"视频处理过程中出错: {str(e)}")
                    # 更新进度文件标记为失败
                    try:
                        with open(progress_path, "r") as f:
                            progress_data = json.load(f)
                        
                        progress_data.update({
                            "status": "failed",
                            "message": f"处理失败: {str(e)}",
                            "error": str(e)
                        })
                        
                        with open(progress_path, "w") as f:
                            json.dump(progress_data, f)
                    except Exception as write_err:
                        logger.error(f"更新进度文件失败: {str(write_err)}")
                
            # 添加包装函数到后台任务
            background_tasks.add_task(process_video_wrapper)
            
        except Exception as task_err:
            logger.exception(f"添加后台任务时出错: {str(task_err)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"启动视频处理任务失败: {str(task_err)}"}
            )
        
        return {
            "status": "success",
            "message": "Video upload successful, starting background processing",
            "process_id": process_id,
            "file_name": safe_filename
        }
    
    except Exception as e:
        logger.exception(f"Error processing video upload: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error processing video: {str(e)}"}
        )

# 添加视频处理状态获取路由
@app.get("/api/fire_detection_direct/video-status/{process_id}")
async def fire_detection_video_status_direct(process_id: str):
    """Direct route to get fire detection video processing status"""
    from app.routers.fire_detection import OUTPUT_DIR
    logger.info(f"Direct request for fire detection video status: {process_id}")
    
    try:
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        
        if not os.path.exists(progress_path):
            return JSONResponse(
                status_code=404,
                content={"detail": f"Video with process ID {process_id} not found"}
            )
        
        with open(progress_path, "r") as f:
            status = json.load(f)
            
        return status
    except Exception as e:
        logger.exception(f"Error getting video status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting video status: {str(e)}"}
        )

@app.get("/api/fire_detection_direct/result-video/{process_id}")
async def fire_detection_get_result_video_direct(process_id: str):
    """Direct route to get processed fire detection video"""
    from app.routers.fire_detection import OUTPUT_DIR
    logger.info(f"Direct request for fire detection result video: {process_id}")
    
    try:
        # 导入转码函数
        from app.routers.fire_detection import convert_video_for_web
        
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        
        if not os.path.exists(progress_path):
            logger.error(f"Progress file not found: {progress_path}")
            return JSONResponse(
                status_code=404,
                content={"detail": "Processing record not found"}
            )
        
        # 读取进度文件
        with open(progress_path, "r") as f:
            progress = json.load(f)
            logger.info(f"Progress data for {process_id}: status={progress.get('status')}")
        
        # 首先查找已转码的网页兼容视频
        web_dir = os.path.join(OUTPUT_DIR, "web_videos")
        os.makedirs(web_dir, exist_ok=True)
        web_video_path = os.path.join(web_dir, f"web_{process_id}.mp4")
        
        # 如果网页视频存在且有效，直接返回
        if os.path.exists(web_video_path) and os.path.getsize(web_video_path) > 0:
            logger.info(f"Found existing web-compatible video: {web_video_path}, size: {os.path.getsize(web_video_path)/1024/1024:.2f}MB")
            return FileResponse(
                path=web_video_path,
                media_type="video/mp4",
                filename=f"fire_detection_{process_id}.mp4",
                headers={
                    "Content-Disposition": f"inline; filename=fire_detection_{process_id}.mp4",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
            
        # 获取处理后的视频路径
        output_path = progress.get("output_path")
        
        # 检查是否有处理完成的视频文件
        if not output_path or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.warning(f"Output video not found or empty: {output_path}")
            
            # 尝试找到原始视频并转码
            file_path = progress.get("file_path")
            if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                logger.info(f"Attempting to convert original video: {file_path}")
                
                # 转码原始视频
                web_video_path = convert_video_for_web(file_path, process_id)
                if web_video_path and os.path.exists(web_video_path):
                    logger.info(f"Successfully converted original video: {web_video_path}")
                    
                    # 更新进度文件
                    progress["web_video_path"] = web_video_path
                    with open(progress_path, "w") as f:
                        json.dump(progress, f)
                    
                    return FileResponse(
                        path=web_video_path,
                        media_type="video/mp4",
                        filename=f"fire_detection_{process_id}.mp4",
                        headers={
                            "Content-Disposition": f"inline; filename=fire_detection_{process_id}.mp4",
                            "Accept-Ranges": "bytes",
                            "Cache-Control": "no-cache, no-store, must-revalidate",
                            "Pragma": "no-cache",
                            "Expires": "0"
                        }
                    )
                
                # 转码失败，返回原始视频
                logger.warning(f"Conversion failed, returning original video: {file_path}")
                return FileResponse(
                    path=file_path,
                    media_type="video/mp4",
                    filename=os.path.basename(file_path),
                    headers={
                        "Content-Disposition": f"inline; filename={os.path.basename(file_path)}",
                        "Accept-Ranges": "bytes",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache"
                    }
                )
            else:
                # 查找任何可能的视频文件
                logger.warning("No valid original video file found, searching for alternatives")
                alternative_videos = []
                
                # 在OUTPUT_DIR中查找与process_id相关的视频文件
                for filename in os.listdir(OUTPUT_DIR):
                    if process_id in filename and filename.endswith((".mp4", ".avi")):
                        potential_path = os.path.join(OUTPUT_DIR, filename)
                        if os.path.exists(potential_path) and os.path.getsize(potential_path) > 0:
                            alternative_videos.append(potential_path)
                            
                if alternative_videos:
                    # 使用找到的第一个可用视频
                    alt_video = alternative_videos[0]
                    logger.info(f"Using alternative video file: {alt_video}")
                    
                    # 转码备选视频
                    web_video_path = convert_video_for_web(alt_video, process_id)
                    if web_video_path and os.path.exists(web_video_path):
                        logger.info(f"Successfully converted alternative video: {web_video_path}")
                        
                        # 更新进度文件
                        progress["web_video_path"] = web_video_path
                        progress["output_path"] = alt_video
                        with open(progress_path, "w") as f:
                            json.dump(progress, f)
                        
                        return FileResponse(
                            path=web_video_path,
                            media_type="video/mp4",
                            filename=f"fire_detection_{process_id}.mp4",
                            headers={
                                "Content-Disposition": f"inline; filename=fire_detection_{process_id}.mp4",
                                "Accept-Ranges": "bytes",
                                "Cache-Control": "no-cache",
                                "Pragma": "no-cache"
                            }
                        )
                    
                    # 转码失败，直接返回备选视频
                    return FileResponse(
                        path=alt_video,
                        media_type="video/mp4",
                        filename=os.path.basename(alt_video),
                        headers={
                            "Content-Disposition": f"inline; filename={os.path.basename(alt_video)}",
                            "Accept-Ranges": "bytes",
                            "Cache-Control": "no-cache",
                            "Pragma": "no-cache"
                        }
                    )
                
                # 如果所有方法都失败，返回错误
                logger.error(f"No valid video file found for {process_id}")
                return JSONResponse(
                    status_code=404,
                    content={"detail": "No valid video file found"}
                )
        
        # 如果有处理后的视频，尝试转码
        logger.info(f"Attempting to convert processed video: {output_path}")
        web_video_path = convert_video_for_web(output_path, process_id)
        
        if web_video_path and os.path.exists(web_video_path):
            logger.info(f"Successfully converted processed video: {web_video_path}")
            
            # 更新进度文件
            progress["web_video_path"] = web_video_path
            with open(progress_path, "w") as f:
                json.dump(progress, f)
            
            return FileResponse(
                path=web_video_path,
                media_type="video/mp4",
                filename=f"fire_detection_{process_id}.mp4",
                headers={
                    "Content-Disposition": f"inline; filename=fire_detection_{process_id}.mp4",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache, no-store, must-revalidate", 
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        
        # 如果转码失败，尝试返回原始的处理后视频
        logger.warning(f"Conversion failed, returning original processed video: {output_path}")
        
        # 检查视频文件大小
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            logger.error(f"Video file is empty: {output_path}")
            return JSONResponse(
                status_code=404,
                content={"detail": "Video file is empty"}
            )
        
        logger.info(f"Returning original processed video: {output_path}, size: {file_size/1024/1024:.2f}MB")
        
        # 使用Range方式支持的响应头
        return FileResponse(
            path=output_path,
            media_type="video/mp4",  # 使用通用视频MIME类型
            filename=os.path.basename(output_path),
            headers={
                "Content-Disposition": f"inline; filename={os.path.basename(output_path)}",
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        logger.exception(f"Error getting result video: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting result video: {str(e)}"}
        )

# 添加一个超级简单的静态文件视频访问端点
@app.get("/api/fire_detection_direct/simple-video/{process_id}")
async def fire_detection_get_simple_video(process_id: str):
    """最简单的静态文件方式获取视频，确保浏览器兼容性"""
    from app.routers.fire_detection import OUTPUT_DIR
    logger.info(f"简单静态文件方式获取视频: {process_id}")
    
    try:
        # 读取进度文件获取视频路径
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        if not os.path.exists(progress_path):
            return JSONResponse(
                status_code=404, 
                content={"detail": "处理记录不存在"}
            )
        
        with open(progress_path, "r") as f:
            progress = json.load(f)
        
        # 视频静态文件的输出目录
        static_video_dir = os.path.join(OUTPUT_DIR, "static_videos")
        os.makedirs(static_video_dir, exist_ok=True)
        static_video_path = os.path.join(static_video_dir, f"{process_id}.mp4")
        
        # 如果已经有静态文件，直接返回
        if os.path.exists(static_video_path) and os.path.getsize(static_video_path) > 0:
            logger.info(f"找到静态视频文件: {static_video_path}")
            # 直接返回静态文件
            return FileResponse(
                path=static_video_path,
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f"inline; filename={process_id}.mp4",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache"
                }
            )
        
        # 尝试不同的视频源
        video_sources = []
        
        # 1. 已经转码的网页视频
        web_video_path = os.path.join(OUTPUT_DIR, "web_videos", f"web_{process_id}.mp4")
        if os.path.exists(web_video_path) and os.path.getsize(web_video_path) > 0:
            video_sources.append(web_video_path)
        
        # 2. 处理后的视频
        output_path = progress.get("output_path")
        if output_path and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            video_sources.append(output_path)
        
        # 3. 原始视频
        file_path = progress.get("file_path")
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            video_sources.append(file_path)
        
        # 4. 查找其他可能的视频文件
        for filename in os.listdir(OUTPUT_DIR):
            if process_id in filename and filename.endswith((".mp4", ".avi")):
                potential_path = os.path.join(OUTPUT_DIR, filename)
                if os.path.exists(potential_path) and os.path.getsize(potential_path) > 0:
                    video_sources.append(potential_path)
        
        # 如果没有找到任何视频源
        if not video_sources:
            return JSONResponse(
                status_code=404,
                content={"detail": "没有找到可用的视频文件"}
            )
        
        # 使用第一个可用的视频源创建静态视频文件
        source_video = video_sources[0]
        logger.info(f"使用视频源: {source_video} 创建静态视频文件")
        
        # 简单地复制文件而不是转码，以确保速度和稳定性
        try:
            shutil.copy2(source_video, static_video_path)
            logger.info(f"成功创建静态视频文件: {static_video_path}")
        except Exception as copy_err:
            logger.error(f"复制视频文件失败: {str(copy_err)}")
            # 如果复制失败，直接返回源视频
            return FileResponse(
                path=source_video,
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f"inline; filename={os.path.basename(source_video)}",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache"
                }
            )
        
        # 返回静态视频文件
        return FileResponse(
            path=static_video_path,
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"inline; filename={process_id}.mp4",
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        logger.exception(f"获取简单视频文件失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取视频文件失败: {str(e)}"}
        )

# 添加原始视频获取路由
@app.get("/api/fire_detection_direct/original-video/{process_id}")
async def fire_detection_get_original_video_direct(process_id: str):
    """Direct route to get original fire detection video"""
    from app.routers.fire_detection import OUTPUT_DIR
    logger.info(f"Direct request for original fire detection video: {process_id}")
    
    try:
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        
        if not os.path.exists(progress_path):
            logger.error(f"No progress file found for {process_id} at {progress_path}")
            return JSONResponse(
                status_code=404,
                content={"detail": f"No video record found for process ID {process_id}"}
            )
            
        # Read progress file
        with open(progress_path, "r") as f:
            progress = json.load(f)
        
        # Get original file path
        file_path = progress.get("file_path")
        if not file_path:
            logger.error(f"No file_path in progress data for {process_id}")
            
            # 尝试查找原始视频的各种可能路径
            possible_paths = []
            
            # 1. 尝试直接在OUTPUT_DIR中查找原始文件
            filename = progress.get("file_name", f"fire_detection_{process_id}.mp4")
            possible_paths.append(os.path.join(OUTPUT_DIR, filename))
            
            # 2. 尝试从输出路径推断原始文件路径
            if "output_path" in progress:
                output_path = progress.get("output_path")
                if output_path:
                    output_dir = os.path.dirname(output_path)
                    original_name = os.path.basename(output_path).replace("processed_", "")
                    possible_paths.append(os.path.join(output_dir, original_name))
            
            # 3. 尝试查找任何可能的匹配文件
            for file in os.listdir(OUTPUT_DIR):
                if file.startswith(f"fire_detection_{process_id}") and file.endswith((".mp4", ".avi", ".mov")):
                    possible_paths.append(os.path.join(OUTPUT_DIR, file))
            
            logger.info(f"Looking for alternative paths: {possible_paths}")
            
            # 检查所有可能的路径
            for path in possible_paths:
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    logger.info(f"Found alternative file path: {path}")
                    file_path = path
                    break
            
            if not file_path:
                logger.error(f"No valid file path found for {process_id} after checking alternatives")
            return JSONResponse(
                status_code=404,
                    content={"detail": "Original video file path not found in progress data"}
                )
            
        if not os.path.exists(file_path):
            logger.error(f"Original video file not found at {file_path}")
            # 如果原始文件不存在，尝试在OUTPUT_DIR中查找原始文件
            filename = progress.get("file_name", f"fire_detection_{process_id}.mp4")
            alternative_path = os.path.join(OUTPUT_DIR, filename)
            
            if os.path.exists(alternative_path):
                logger.info(f"Found alternative file path: {alternative_path}")
                file_path = alternative_path
            else:
                # 如果仍然找不到，则尝试找任意以process_id开头的视频文件
                for file in os.listdir(OUTPUT_DIR):
                    if file.startswith(f"fire_detection_{process_id}") and file.endswith((".mp4", ".avi", ".mov")):
                        logger.info(f"Found matching video file: {file}")
                        file_path = os.path.join(OUTPUT_DIR, file)
                        break
                
                if not os.path.exists(file_path):
                    logger.error(f"No viable original video file found for {process_id}")
                    return JSONResponse(
                        status_code=404,
                        content={"detail": f"Original video file not found at {file_path} or any alternative location"}
                    )
        
        # 返回文件前记录信息
        file_size = os.path.getsize(file_path)
        logger.info(f"Returning original video: {file_path}, size: {file_size} bytes")
        
        # Return original video with improved headers
        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            filename=os.path.basename(file_path),
            headers={
                "Content-Disposition": f"inline; filename={os.path.basename(file_path)}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Accept-Ranges": "bytes"
            }
        )
    except Exception as e:
        logger.exception(f"Error getting original video: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting original video: {str(e)}"}
        )

# 添加视频帧获取路由
@app.get("/api/fire_detection_direct/video-frame/{process_id}/{frame_name}")
async def fire_detection_get_frame_direct(process_id: str, frame_name: str):
    """Direct route to get key frame from fire detection video"""
    from app.routers.fire_detection import OUTPUT_DIR
    logger.info(f"Direct request for fire detection key frame: {process_id}/{frame_name}")
    
    try:
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        
        if not os.path.exists(progress_path):
            return JSONResponse(
                status_code=404,
                content={"detail": "Processing record not found"}
            )
        
        # Read progress file
        with open(progress_path, "r") as f:
            progress = json.load(f)
        
        frames_dir = progress.get("frames_dir")
        if not frames_dir:
            return JSONResponse(
                status_code=404,
                content={"detail": "No frames directory"}
            )
        
        frame_path = os.path.join(frames_dir, frame_name)
        if not os.path.exists(frame_path):
            return JSONResponse(
                status_code=404,
                content={"detail": "Specified frame not found"}
            )
        
        return FileResponse(
            path=frame_path,
            media_type="image/jpeg",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-Disposition": f"inline; filename={frame_name}",
                "Cache-Control": "public, max-age=86400",  # Cache for a day
                "X-Content-Type-Options": "nosniff"
            }
        )
    except Exception as e:
        logger.exception(f"Error getting key frame: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting key frame: {str(e)}"}
        )

# 添加视频帧获取路由 - 兼容旧的前端路径
@app.get("/api/fire_detection_direct/frame/{process_id}/{frame_name}")
async def fire_detection_get_frame_compat_direct(process_id: str, frame_name: str):
    """Route for compatibility with frontend requests for fire detection frames"""
    from app.routers.fire_detection import OUTPUT_DIR
    
    logger.info(f"Direct request for fire detection frame (compat route): {process_id}/{frame_name}")
    
    try:
        # First try to directly find the frame file
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        
        if not os.path.exists(progress_path):
            logger.warning(f"Processing record not found for frame request: {process_id}")
            return JSONResponse(
                status_code=404,
                content={"detail": "Processing record not found"}
            )
        
        # Read progress file
        with open(progress_path, "r") as f:
            progress = json.load(f)
        
        frames_dir = progress.get("frames_dir")
        if not frames_dir:
            logger.warning(f"No frames directory in progress file: {process_id}")
            return JSONResponse(
                status_code=404,
                content={"detail": "No frames directory specified in processing record"}
            )
        
        # Check if frames directory exists
        if not os.path.exists(frames_dir):
            logger.warning(f"Frames directory does not exist: {frames_dir}")
            return JSONResponse(
                status_code=404,
                content={"detail": "Frames directory not found"}
            )
        
        # Log all files in frames directory
        files_in_dir = os.listdir(frames_dir)
        logger.info(f"Files in frames directory ({frames_dir}): {files_in_dir}")
        
        # Try to find the requested frame
        frame_path = os.path.join(frames_dir, frame_name)
        if not os.path.exists(frame_path):
            logger.warning(f"Requested frame not found: {frame_path}")
            
            # Try an alternative approach - search for similar frame by number
            frame_number_match = re.search(r'(\d+)', frame_name)
            if frame_number_match:
                frame_number = frame_number_match.group(1)
                logger.info(f"Trying to find alternative frame with number: {frame_number}")
                
                # Try to find a frame with the same number but different format
                for file in files_in_dir:
                    if frame_number in file and (file.endswith('.jpg') or file.endswith('.png')):
                        alternative_path = os.path.join(frames_dir, file)
                        logger.info(f"Found alternative frame: {file}, path: {alternative_path}")
                        
                        return FileResponse(
                            path=alternative_path,
                            media_type="image/jpeg",
                            headers={
                                "Access-Control-Allow-Origin": "*",
                                "Content-Disposition": f"inline; filename={file}",
                                "Cache-Control": "public, max-age=86400",
                                "X-Content-Type-Options": "nosniff"
                            }
                        )
            
            # If no alternative found, return error
            return JSONResponse(
                status_code=404,
                content={"detail": f"Requested frame not found: {frame_name}"}
            )
        
        # If frame exists, return it
        logger.info(f"Found requested frame: {frame_path}")
        return FileResponse(
            path=frame_path,
            media_type="image/jpeg",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-Disposition": f"inline; filename={frame_name}",
                "Cache-Control": "public, max-age=86400",
                "X-Content-Type-Options": "nosniff"
            }
        )
    except Exception as e:
        logger.exception(f"Error getting key frame in compat route: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting key frame: {str(e)}"}
        )

# 添加图片火灾识别API
@app.post("/api/fire_detection_direct/detect-image")
async def fire_detection_detect_image_direct(
    file: UploadFile = File(...),
    threshold: float = Form(0.5)
):
    """Direct route to detect fire in uploaded image"""
    from app.routers.fire_detection import OUTPUT_DIR, initialize_fire_detection
    from app.routers.fire_detection import fire_detector
    
    logger.info(
        f"[FIRE_DEBUG][IMAGE] Direct image fire detection request: "
        f"filename={file.filename}, content_type={file.content_type}, threshold={threshold}"
    )
    
    # 确保fire_detector已初始化
    if fire_detector is None:
        logger.info("Fire detector not initialized, initializing now...")
        try:
            initialize_fire_detection()
            from app.routers.fire_detection import fire_detector
            if fire_detector is None:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Failed to initialize fire detector"}
                )
        except Exception as e:
            logger.exception(f"Failed to initialize fire detector: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Failed to initialize fire detector: {str(e)}"}
            )
    
    try:
        # Generate a unique ID for this detection
        detection_id = str(uuid.uuid4())
        
        # Create output directory if not exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Save the uploaded image temporarily
        temp_file_path = os.path.join(OUTPUT_DIR, f"temp_{detection_id}_{file.filename}")
        result_file_path = os.path.join(OUTPUT_DIR, f"result_{detection_id}_{file.filename}")
        
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Read image for processing
        try:
            image = cv2.imread(temp_file_path)
            if image is None or image.size == 0:
                raise ValueError("Invalid image data")
                
            # Process the image
            logger.info("[FIRE_DEBUG][IMAGE] Calling fire_detector.process_image for uploaded image")
            result = fire_detector.process_image(image, mode="both")
            
            # Save the processed image with fire detection visualization
            if "output_image" in result:
                cv2.imwrite(result_file_path, result["output_image"])
            
            # Create response
            fire_detected = result.get("fire_detected", False)
            confidence = result.get("confidence", 0.0)
            fire_area_percentage = result.get("fire_area_percentage", 0.0)
            smoke_detected = result.get("smoke_detected", False)
            smoke_area_percentage = result.get("smoke_area_percentage", 0.0)
            
            detection_result = {
                "success": True,
                "detection_id": detection_id,
                "fire_detected": fire_detected,
                "confidence": confidence,
                "fire_area_percentage": fire_area_percentage,
                "smoke_detected": smoke_detected,
                "smoke_area_percentage": smoke_area_percentage,
                "method": result.get("method", "unknown"),
                "processing_time": result.get("processing_time", 0.0),
                "regions_count": len(result.get("fire_regions", [])),
                "original_image": f"/api/fire_detection_direct/image/{detection_id}/original",
                "processed_image": f"/api/fire_detection_direct/image/{detection_id}/result"
            }
            logger.info(
                "[FIRE_DEBUG][IMAGE] Detection result: "
                f"fire={fire_detected}, smoke={smoke_detected}, "
                f"conf={confidence:.3f}, "
                f"fire_area={fire_area_percentage:.4f}, "
                f"smoke_area={smoke_area_percentage:.4f}, "
                f"method={detection_result.get('method')}, "
                f"regions={detection_result.get('regions_count')}"
            )

            return detection_result
            
        except Exception as e:
            logger.exception(f"Error processing image: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Error processing image: {str(e)}"}
            )
    
    except Exception as e:
        logger.exception(f"Error handling image upload: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error handling image upload: {str(e)}"}
        )

# 添加实时摄像头图像火灾检测API
@app.post("/api/fire_detection_direct/detect-camera")
async def fire_detection_detect_camera_direct(
    file: UploadFile = File(...),
    session_id: str = Form(None),
    threshold: float = Form(0.5)
):
    """Direct route to detect fire in camera image frame"""
    from app.routers.fire_detection import OUTPUT_DIR, initialize_fire_detection
    from app.routers.fire_detection import fire_detector
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    logger.info(
        f"[FIRE_DEBUG][CAMERA] Camera fire detection request: "
        f"session_id={session_id}, filename={file.filename}, threshold={threshold}"
    )
    
    # 确保fire_detector已初始化
    if fire_detector is None:
        logger.info("Fire detector not initialized, initializing now...")
        try:
            initialize_fire_detection()
            from app.routers.fire_detection import fire_detector
            if fire_detector is None:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Failed to initialize fire detector"}
                )
        except Exception as e:
            logger.exception(f"Failed to initialize fire detector: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Failed to initialize fire detector: {str(e)}"}
            )
    
    try:
        # Create session directory if not exists
        session_dir = os.path.join(OUTPUT_DIR, f"camera_session_{session_id}")
        os.makedirs(session_dir, exist_ok=True)
        
        # Save the uploaded camera frame
        frame_id = int(time.time() * 1000)  # Use timestamp as frame ID
        temp_file_path = os.path.join(session_dir, f"frame_{frame_id}.jpg")
        result_file_path = os.path.join(session_dir, f"result_{frame_id}.jpg")
        
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Read image for processing
        try:
            image = cv2.imread(temp_file_path)
            if image is None or image.size == 0:
                raise ValueError("Invalid camera image data")
            
            # Process the image
            logger.info(
                f"[FIRE_DEBUG][CAMERA] Calling fire_detector.process_image "
                f"for session={session_id}, frame_id={frame_id}"
            )
            result = fire_detector.process_image(image, mode="both")
            
            # Save the processed image with fire detection visualization
            if "output_image" in result:
                cv2.imwrite(result_file_path, result["output_image"])
            
            # Create response
            fire_detected = result.get("fire_detected", False)
            confidence = result.get("confidence", 0.0)
            fire_area_percentage = result.get("fire_area_percentage", 0.0)
            smoke_detected = result.get("smoke_detected", False)
            smoke_area_percentage = result.get("smoke_area_percentage", 0.0)
            
            # Clean old frames (keep only the most recent 10 frames)
            try:
                all_files = os.listdir(session_dir)
                if len(all_files) > 20:  # 10 original frames + 10 result frames
                    # Sort files by modification time
                    all_files.sort(key=lambda f: os.path.getmtime(os.path.join(session_dir, f)))
                    # Delete oldest files
                    for old_file in all_files[:len(all_files)-20]:
                        old_path = os.path.join(session_dir, old_file)
                        os.remove(old_path)
                        logger.debug(f"Removed old camera frame: {old_path}")
            except Exception as clean_error:
                logger.warning(f"Error cleaning old camera frames: {clean_error}")
            
            detection_result = {
                "success": True,
                "session_id": session_id,
                "frame_id": frame_id,
                "fire_detected": fire_detected,
                "confidence": confidence,
                "fire_area_percentage": fire_area_percentage,
                "smoke_detected": smoke_detected,
                "smoke_area_percentage": smoke_area_percentage,
                "method": result.get("method", "unknown"),
                "processing_time": result.get("processing_time", 0.0),
                "regions_count": len(result.get("fire_regions", [])),
                "original_image": f"/api/fire_detection_direct/camera/{session_id}/{frame_id}/original",
                "processed_image": f"/api/fire_detection_direct/camera/{session_id}/{frame_id}/result"
            }
            logger.info(
                "[FIRE_DEBUG][CAMERA] Detection result: "
                f"session_id={session_id}, frame_id={frame_id}, "
                f"fire={fire_detected}, smoke={smoke_detected}, "
                f"conf={confidence:.3f}, "
                f"fire_area={fire_area_percentage:.4f}, "
                f"smoke_area={smoke_area_percentage:.4f}, "
                f"method={detection_result.get('method')}, "
                f"regions={detection_result.get('regions_count')}"
            )

            return detection_result
            
        except Exception as e:
            logger.exception(f"Error processing camera image: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Error processing camera image: {str(e)}"}
            )
    
    except Exception as e:
        logger.exception(f"Error handling camera upload: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error handling camera upload: {str(e)}"}
        )

# 获取摄像头图像帧
@app.get("/api/fire_detection_direct/camera/{session_id}/{frame_id}/{image_type}")
async def fire_detection_get_camera_frame_direct(session_id: str, frame_id: str, image_type: str):
    """Get camera frame from fire detection session"""
    from app.routers.fire_detection import OUTPUT_DIR
    
    logger.info(f"Request for camera frame: {session_id}/{frame_id}/{image_type}")
    
    try:
        # Validate parameters
        if image_type not in ["original", "result"]:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid image type, must be 'original' or 'result'"}
            )
            
        # Construct file path
        session_dir = os.path.join(OUTPUT_DIR, f"camera_session_{session_id}")
        if not os.path.exists(session_dir):
            return JSONResponse(
                status_code=404,
                content={"detail": f"Camera session not found: {session_id}"}
            )
            
        # Determine file prefix
        prefix = "frame_" if image_type == "original" else "result_"
        
        # Construct file path
        image_path = os.path.join(session_dir, f"{prefix}{frame_id}.jpg")
        
        # Check if file exists and is valid
        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            return JSONResponse(
                status_code=404,
                content={"detail": f"Camera frame not found: {frame_id} ({image_type})"}
            )
            
        # Return the image file with no caching (for real-time updates)
        return FileResponse(
            path=image_path,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"inline; filename={os.path.basename(image_path)}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except Exception as e:
        logger.exception(f"Error getting camera frame: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting camera frame: {str(e)}"}
        )

# 添加兼容性路由，处理双重api的情况
@app.post("/api/api/fire_detection_direct/detect-camera")
async def fire_detection_detect_camera_compat(
    file: UploadFile = File(...),
    session_id: str = Form(None),
    threshold: float = Form(0.5)
):
    """Compatibility route for handling double API prefix in frontend requests"""
    logger.warning(f"Detected request to incorrect path /api/api/fire_detection_direct/detect-camera, redirecting to correct path")
    # 转发到正确的路由
    return await fire_detection_detect_camera_direct(file=file, session_id=session_id, threshold=threshold)

# 添加兼容性路由，处理双重api的情况，用于获取摄像头帧
@app.get("/api/api/fire_detection_direct/camera/{session_id}/{frame_id}/{image_type}")
async def fire_detection_get_camera_frame_compat(session_id: str, frame_id: str, image_type: str):
    """Compatibility route for handling double API prefix in frontend camera frame requests"""
    logger.warning(f"Detected request to incorrect path /api/api/fire_detection_direct/camera/{session_id}/{frame_id}/{image_type}, redirecting to correct path")
    # 转发到正确的路由
    return await fire_detection_get_camera_frame_direct(session_id=session_id, frame_id=frame_id, image_type=image_type)

# 添加兼容性路由，解决路径不匹配问题，用于获取视频帧图像
@app.get("/api/fire_detection_direct/frame/{process_id}/{frame_name}")
async def fire_detection_get_frame_path_compat(process_id: str, frame_name: str):
    """Compatibility route to forward frame requests to the correct endpoint"""
    logger.warning(f"Detected request to path /api/fire_detection_direct/frame/{process_id}/{frame_name}, forwarding to video-frame endpoint")
    # 转发到正确的路由
    return await fire_detection_get_frame_compat_direct(process_id=process_id, frame_name=frame_name)

# 获取原始图片或处理结果图片
@app.get("/api/fire_detection_direct/image/{detection_id}/{image_type}")
async def fire_detection_get_image_direct(detection_id: str, image_type: str):
    """Get original or processed image from fire detection"""
    from app.routers.fire_detection import OUTPUT_DIR
    
    logger.info(f"Direct request for fire detection image: {detection_id}/{image_type}")
    
    try:
        # Find the image file
        if image_type not in ["original", "result"]:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid image type, must be 'original' or 'result'"}
            )
            
        # List files in output directory
        files = os.listdir(OUTPUT_DIR)
        
        # Find matching file
        prefix = "temp_" if image_type == "original" else "result_"
        matching_files = [f for f in files if f.startswith(f"{prefix}{detection_id}")]
        
        if not matching_files:
            return JSONResponse(
                status_code=404,
                content={"detail": f"Image not found for detection ID: {detection_id}"}
            )
            
        # Get the first matching file
        image_path = os.path.join(OUTPUT_DIR, matching_files[0])
        
        # Check if file exists and is valid
        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            return JSONResponse(
                status_code=404,
                content={"detail": "Image file not found or invalid"}
            )
            
        # Return the image file
        return FileResponse(
            path=image_path,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"inline; filename={os.path.basename(image_path)}",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except Exception as e:
        logger.exception(f"Error getting image: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting image: {str(e)}"}
        )

# 添加检查视频处理完成状态的端点
@app.get("/api/fire_detection_direct/check-completion/{process_id}")
async def fire_detection_check_completion_direct(process_id: str):
    """Direct route to check if fire detection video processing is completed"""
    from app.routers.fire_detection import OUTPUT_DIR
    logger.info(f"Direct request to check completion status: {process_id}")
    
    try:
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        
        if not os.path.exists(progress_path):
            return JSONResponse(
                status_code=404,
                content={"detail": f"Video with process ID {process_id} not found"}
            )
        
        with open(progress_path, "r") as f:
            status = json.load(f)
            
        # 如果状态是已完成或失败，则返回详细结果
        if status.get("status") in ["completed", "failed"]:
            return status
        
        # 否则返回当前状态
        return {
            "status": status.get("status", "processing"),
            "progress": status.get("progress", 50),
            "message": status.get("message", "处理中...")
        }
    except Exception as e:
        logger.exception(f"Error checking completion status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error checking completion status: {str(e)}"}
        )

# 添加视频检测结果端点
@app.get("/api/fire_detection_direct/detection-results/{process_id}")
async def fire_detection_detection_results_direct(process_id: str):
    """Direct route to get fire detection results for a video"""
    from app.routers.fire_detection import OUTPUT_DIR
    logger.info(f"Direct request for fire detection results: {process_id}")
    
    try:
        progress_path = os.path.join(OUTPUT_DIR, f"progress_{process_id}.json")
        
        if not os.path.exists(progress_path):
            return JSONResponse(
                status_code=404,
                content={"detail": f"Video with process ID {process_id} not found"}
            )
        
        with open(progress_path, "r") as f:
            status = json.load(f)
        
        # 检查处理是否完成
        if status.get("status") != "completed":
            return JSONResponse(
                status_code=400,
                content={"detail": "Video processing not yet completed"}
            )
        
        # 获取关键帧
        frames = status.get("key_frames", [])
        
        # 为每个帧添加完整URL
        for frame in frames:
            frame_name = frame.get("name")
            if frame_name:
                frame["image_url"] = f"/api/fire_detection_direct/frame/{process_id}/{frame_name}"
        
        return {
            "frames": frames,
            "processing_time": status.get("processing_time", 0),
            "fire_detected": status.get("fire_detected", False),
            "detection_count": status.get("detection_count", 0),
            "output_path": status.get("output_path", ""),
            "fps": status.get("fps", 0)
        }
    except Exception as e:
        logger.exception(f"Error getting detection results: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting detection results: {str(e)}"}
        )

# 确保知识库聊天模块被正确导入
if 'knowledge_chat' in modules:
    # 尝试重新导入以确保最新更改
    try:
        importlib.reload(modules['knowledge_chat'])
        print("已重新加载 knowledge_chat 模块以应用最新更改")
    except Exception as e:
        print(f"重新加载 knowledge_chat 模块时出错: {str(e)}")
        
    # 明确注册知识库聊天路由到应用 - 添加明确的API前缀
    try:
        # 明确无误地注册为/api/knowledge-chat前缀
        app.include_router(
            modules['knowledge_chat'].router,
            prefix="/api/knowledge-chat",
            tags=["知识库聊天"]
        )
        logger.info("✅ 成功显式注册知识库聊天路由 /api/knowledge-chat")
        
        # 输出所有知识库聊天相关路由进行调试
        for route in modules['knowledge_chat'].router.routes:
            logger.info(f"📍 知识库路由: {route.path}, 方法: {route.methods}")
    except Exception as e:
        logger.error(f"❌ 显式注册知识库聊天路由失败: {str(e)}")
    
    # 添加专门的无人机数据导入端点，避免可能的路由注册问题
    try:
        @app.post("/api/knowledge-chat/graph/import-drones")
        async def drone_import_direct(data: dict):
            """直接处理无人机数据导入的备用端点"""
            logger.info("使用备用端点处理无人机数据导入请求")
            from app.routers.knowledge_chat import import_drone_data
            return await import_drone_data(data)
        
        logger.info("✅ 已添加备用无人机数据导入端点")
    except Exception as e:
        logger.error(f"❌ 添加备用无人机数据导入端点失败: {str(e)}")
        
    # 添加测试端点，用于诊断路由问题
    @app.get("/api/knowledge-chat/test-endpoint")
    async def knowledge_chat_test_endpoint():
        """用于诊断路由注册问题的测试端点"""
        return {"status": "ok", "message": "知识图谱测试端点可用"}
        
    logger.info("✅ 添加了知识图谱测试端点")

# 为知识图谱导入接口添加兼容性路由
@app.post("/api/api/knowledge-chat/graph/import-drones")
async def knowledge_graph_import_drones_compat(data: dict):
    """兼容性路由 - 处理前端可能发送的包含重复/api前缀的请求"""
    logger.info("接收到包含重复/api前缀的知识图谱导入请求，转发到正确路径")
    
    # 导入原始处理函数
    try:
        from app.routers.knowledge_chat import import_drone_data
        # 转发请求到正确的处理函数
        return await import_drone_data(data)
    except Exception as e:
        logger.error(f"处理知识图谱导入请求失败: {str(e)}")
        return {"success": False, "error": f"处理请求失败: {str(e)}"}

# 添加知识图谱相关的所有端点 - 显式注册每个路由
@app.get("/api/knowledge-chat/graph")
async def get_knowledge_graph_direct():
    """直接知识图谱获取端点"""
    try:
        from app.routers.knowledge_chat import get_knowledge_graph
        return await get_knowledge_graph()
    except Exception as e:
        logger.error(f"获取知识图谱失败: {str(e)}")
        return {"nodes": [], "links": [], "error": str(e)}

@app.post("/api/knowledge-chat/stream")
async def knowledge_chat_stream_direct(request: Request):
    """直接知识库聊天流式响应端点"""
    try:
        from app.routers.knowledge_chat import knowledge_chat_stream
        return await knowledge_chat_stream(request)
    except Exception as e:
        logger.error(f"知识库聊天请求失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"处理聊天请求失败: {str(e)}"}
        )

@app.get("/api/knowledge-chat/latest-search")
async def get_latest_search_direct(query: str):
    """获取最新的网络搜索结果"""
    try:
        from app.routers.knowledge_chat import get_latest_search_results
        return await get_latest_search_results(query)
    except Exception as e:
        logger.error(f"获取搜索结果失败: {str(e)}")
        return {"results": []}

@app.get("/api/knowledge-chat/latest-local-model-results")
async def get_latest_local_model_results_direct(query: str):
    """获取最新的本地模型搜索结果"""
    try:
        from app.routers.knowledge_chat import get_latest_local_model_results
        return await get_latest_local_model_results(query)
    except Exception as e:
        logger.error(f"获取本地模型搜索结果失败: {str(e)}")
        return {"results": []}

@app.post("/api/knowledge-chat/graph/add")
async def add_to_knowledge_graph_direct(node: dict, links: List = None):
    """添加节点到知识图谱"""
    try:
        from app.routers.knowledge_chat import add_to_knowledge_graph, KnowledgeNode, KnowledgeLink
        
        # 转换为所需类型
        knowledge_node = KnowledgeNode(**node)
        knowledge_links = []
        if links:
            for link in links:
                knowledge_links.append(KnowledgeLink(**link))
        
        return await add_to_knowledge_graph(knowledge_node, knowledge_links)
    except Exception as e:
        logger.error(f"添加到知识图谱失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"添加到知识图谱失败: {str(e)}"}
        )

# 导入路由修复模块
try:
    from app.route_fix import register_knowledge_chat_routes
    # 注册知识库聊天路由
    register_knowledge_chat_routes(app)
    logger.info("✅ 知识库聊天路由修复已应用")
except Exception as e:
    logger.error(f"❌ 知识库聊天路由修复失败: {str(e)}")

# 打印所有已注册的路由以便调试
@app.on_event("startup")
async def print_all_routes():
    """输出所有注册的路由，用于调试"""
    logger.info("\n\n================ 已注册路由列表 ================")
    for route in app.routes:
        if isinstance(route, APIRoute):
            logger.info(f"路由: {route.path} | 方法: {route.methods} | 名称: {route.name}")
    logger.info("================ 路由列表结束 ================\n")

# 启动保护线程 - 使用新的service_protector函数
protector = threading.Thread(target=service_protector, daemon=False)
protector.start()