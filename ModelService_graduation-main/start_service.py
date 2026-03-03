#!/usr/bin/env python
"""
ModelService 统一启动脚本
使用uvicorn启动FastAPI应用，提供所有集成功能的统一访问接口
所有服务统一在8000端口运行，解决跨域问题
"""
import uvicorn
import argparse
import logging
import os
import sys
import socket
import time
import subprocess
import signal
import json
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("startup")

# 确保目录结构
BASE_DIR = Path(__file__).resolve().parent
MAIN_DIR = BASE_DIR / "ModelService" / "Main"  # ModelService_graduation-main/ModelService/Main/

MODEL_DIRS = [
    MAIN_DIR / "models" / "night_detection",
    MAIN_DIR / "models" / "fire_detection",
    MAIN_DIR / "models" / "plate_recognition",
    MAIN_DIR / "models" / "rgbt_fusion",
    MAIN_DIR / "models" / "video_tracking",
]

OUTPUT_DIRS = [
    MAIN_DIR / "output" / "night_detection",
    MAIN_DIR / "output" / "fire_detection",
    MAIN_DIR / "output" / "plate_recognition",
    MAIN_DIR / "output" / "rgbt_fusion",
    MAIN_DIR / "output" / "video_tracking",
]

# 子服务端口配置 - 采用固定端口方案
PORT_CONFIG = {
    "main": 8081,           # 主服务端口（按用户要求固定为8081）
    "plate_recognition": 5001,  # 车牌识别服务单独端口
    "frontend": 8080       # 前端开发服务器端口
}

# 检查端口是否被占用
def is_port_in_use(port):
    """检查指定端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# 终止占用指定端口的进程
def kill_process_on_port(port):
    """终止占用指定端口的进程"""
    try:
        if os.name == 'nt':  # Windows
            # 查找占用端口的进程PID
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, text=True, capture_output=True
            )
            if result.stdout:
                # 提取PID并终止进程
                for line in result.stdout.splitlines():
                    if f':{port}' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                        parts = line.strip().split()
                        pid = parts[-1]
                        try:
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
                            logger.info(f"已终止占用端口 {port} 的进程 (PID: {pid})")
                            return True
                        except subprocess.CalledProcessError:
                            logger.error(f"无法终止进程 {pid}")
        else:  # Linux/Mac
            # 查找占用端口的进程PID
            result = subprocess.run(
                f'lsof -i :{port} -t',
                shell=True, text=True, capture_output=True
            )
            if result.stdout:
                pid = result.stdout.strip()
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    logger.info(f"已终止占用端口 {port} 的进程 (PID: {pid})")
                    return True
                except ProcessLookupError:
                    logger.error(f"无法终止进程 {pid}")
    except Exception as e:
        logger.error(f"终止进程出错: {str(e)}")
    return False

# 确保端口可用
def ensure_port_available(port):
    """确保指定端口可用，如果被占用则尝试释放"""
    if is_port_in_use(port):
        logger.warning(f"端口 {port} 已被占用，尝试释放...")
        if kill_process_on_port(port):
            # 等待端口释放
            for _ in range(5):
                if not is_port_in_use(port):
                    logger.info(f"端口 {port} 已成功释放")
                    return True
                time.sleep(1)
            logger.error(f"端口 {port} 释放失败")
            return False
        else:
            logger.error(f"无法释放端口 {port}")
            return False
    return True

# 写入端口配置文件
def write_port_config():
    """将端口配置写入文件，供前端和其他服务使用"""
    config_path = BASE_DIR / "port_config.json"
    try:
        with open(config_path, 'w') as f:
            json.dump(PORT_CONFIG, f, indent=4)
        logger.info(f"端口配置已写入: {config_path}")
        
        # 为车牌识别服务创建flask_port.txt文件
        flask_port_path = BASE_DIR / "flask_port.txt"
        with open(flask_port_path, 'w') as f:
            f.write(str(PORT_CONFIG["plate_recognition"]))
        logger.info(f"车牌识别服务端口配置已写入: {flask_port_path}")
        
        return True
    except Exception as e:
        logger.error(f"写入端口配置失败: {str(e)}")
        return False

def setup_environment():
    """设置运行环境，创建必要的目录"""
    logger.info("正在设置运行环境...")
    
    # 创建模型目录
    for model_dir in MODEL_DIRS:
        model_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"模型目录已就绪: {model_dir}")
    
    # 创建输出目录
    for output_dir in OUTPUT_DIRS:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"输出目录已就绪: {output_dir}")
    
    # 确保static目录存在
    static_dir = MAIN_DIR / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"静态文件目录已就绪: {static_dir}")
    
    # 设置Python模块搜索路径
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
        logger.info(f"添加到Python路径: {BASE_DIR}")
    
    # 确保端口可用
    main_port = PORT_CONFIG["main"]
    if not ensure_port_available(main_port):
        logger.error(f"无法释放端口 {main_port}，请手动关闭占用该端口的程序")
        sys.exit(1)
    
    # 写入端口配置
    write_port_config()
    
    logger.info("环境设置完成")

def start_server(host, port, reload):
    """启动服务器"""
    # 另一重检测端口是否被占用
    if is_port_in_use(port):
        logger.error(f"端口 {port} 已被占用，无法启动服务。正在尝试强制释放...")
        # 尝试强制释放端口
        if kill_process_on_port(port):
            logger.info(f"端口 {port} 已被强制释放")
            # 等待端口实际释放 (有时候杀死进程后端口仍需要一些时间释放)
            for _ in range(10):
                if not is_port_in_use(port):
                    logger.info(f"端口 {port} 已完全释放，可以继续")
                    break
                logger.info(f"等待端口 {port} 释放...")
                time.sleep(1)
        else:
            logger.error(f"无法强制释放端口 {port}，请手动终止占用此端口的进程")
            logger.info("您可以使用以下命令查找占用端口的进程：")
            logger.info(f"    netstat -ano | findstr :{port}")
            logger.info("然后使用以下命令终止相应进程：")
            logger.info("    taskkill /F /PID <PID号>")
            sys.exit(1)
    
    logger.info(f"正在启动统一服务，地址: {host}:{port}, 热重载: {'开启' if reload else '关闭'}")
    logger.info(f"API文档: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/api/docs")
    
    # 设置环境变量，确保Python能找到正确的模块路径
    sys_path = str(BASE_DIR)
    if sys_path not in sys.path:
        sys.path.append(sys_path)
    
    # 设置端口环境变量，确保子服务使用相同端口
    os.environ["PLATE_RECOGNITION_PORT"] = str(PORT_CONFIG["plate_recognition"])
    os.environ["MAIN_SERVICE_PORT"] = str(PORT_CONFIG["main"])
    
    # 创建port.txt文件供前端读取
    port_txt_path = BASE_DIR / "port.txt"
    try:
        with open(port_txt_path, 'w') as f:
            f.write(str(port))
        logger.info(f"已创建port.txt文件: {port_txt_path}")
    except Exception as e:
        logger.warning(f"创建port.txt文件失败: {e}")
    
    try:
        # 启动FastAPI应用
        logger.info("开始启动FastAPI应用...因为包含多个模型，首次加载可能需要一些时间")

        # 确保路径正确
        main_app_dir = MAIN_DIR / "app"
        if str(main_app_dir) not in sys.path:
            sys.path.insert(0, str(main_app_dir))
        # 确保主目录也在路径中
        if str(MAIN_DIR) not in sys.path:
            sys.path.insert(0, str(MAIN_DIR))

        # 导入FastAPI应用
        from main import app

        # 使用uvicorn启动
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            timeout_keep_alive=65,  # 增加keep-alive超时时间
            workers=1
        )
        logger.info(f"FastAPI应用已成功启动在 {host}:{port}")
    except Exception as e:
        logger.error(f"FastAPI应用启动失败: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ModelService统一服务启动脚本")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8081, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="是否启用热重载(仅开发环境建议开启)")
    parser.add_argument("--force", action="store_true", help="强制关闭占用端口的进程")
    
    args = parser.parse_args()
    
    # 更新端口配置
    PORT_CONFIG["main"] = args.port
    PORT_CONFIG["plate_recognition"] = args.port  # 确保车牌识别服务使用相同端口
    
    logger.info(f"统一服务端口: {args.port}")
    
    try:
        # 设置环境
        setup_environment()
        
        # 启动服务
        start_server(args.host, args.port, args.reload)
    except KeyboardInterrupt:
        logger.info("服务已手动停止")
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
