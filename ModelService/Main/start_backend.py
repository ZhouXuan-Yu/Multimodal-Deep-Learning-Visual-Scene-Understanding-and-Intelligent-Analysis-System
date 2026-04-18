"""
修补NumPy和它的依赖，然后以原始命令启动后端服务
"""
import os
import sys
import subprocess
import importlib.util
import numpy

# 首先尝试修复依赖问题
def fix_dependencies():
    # 修复 NumPy 对 np.object 的过时引用
    if not hasattr(numpy, 'object'):
        numpy.object = object
        print("✅ NumPy补丁已应用")
    
    # 简单的attr桥接实现
    try:
        # 尝试导入attr包
        try:
            import attr
            print(f"attr包已存在，版本: {attr.__version__}")
            return True
        except ImportError:
            # 如果不存在，尝试导入attrs
            try:
                import attrs
                print(f"attrs已安装，版本: {attrs.__version__}")
                
                # 尝试创建简单的attr桥接模块
                site_packages = None
                for path in sys.path:
                    if path.endswith('site-packages'):
                        site_packages = path
                        break
                
                if site_packages:
                    attr_py_path = os.path.join(site_packages, 'attr.py')
                    with open(attr_py_path, 'w') as f:
                        f.write("""
# 简单的attr桥接模块
import attrs as _attrs
import sys

# 导出attrs中的关键内容
__version__ = _attrs.__version__

# 注册模块
sys.modules['attr'] = sys.modules[__name__]

# 关键函数
def s(*args, **kwargs):
    return _attrs.define(*args, **kwargs)

def ib(*args, **kwargs):
    return _attrs.field(*args, **kwargs)
                        """)
                    print(f"✅ 已创建简单attr桥接: {attr_py_path}")
                    return True
                else:
                    print("⚠️ 无法找到site-packages目录")
            except ImportError:
                # attrs也不存在，尝试安装
                try:
                    import subprocess
                    print("正在安装attrs包...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "attrs"])
                    print("✅ attrs包安装成功，请重启脚本")
                    return True
                except Exception as e:
                    print(f"⚠️ 安装attrs失败: {str(e)}")
                    return False
    except Exception as e:
        print(f"⚠️ 修复attr依赖时出错: {str(e)}")
        return False

# 运行依赖修复
fix_dependencies()

# 设置环境变量
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["CHROMADB_TELEMETRY_DISABLED"] = "1"
os.environ["HDF5_DISABLE_VERSION_CHECK"] = "1"  # 抑制HDF5版本不匹配警告


# 创建numpy.typing模块补丁
class NumpyTypingModule:
    NDArray = object
    ArrayLike = object

if 'numpy.typing' not in sys.modules:
    sys.modules['numpy.typing'] = NumpyTypingModule
    numpy.typing = NumpyTypingModule

print("✅ NumPy补丁已应用")
print("===== 使用原始命令启动服务器 =====\n")

# 检查端口是否可用
def check_port(port):
    """检查指定端口是否可用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = True
    try:
        sock.bind(("127.0.0.1", port))
    except socket.error:
        result = False
    finally:
        sock.close()
    return result

# 使用不常用的高位端口，更可能避免冲突
# 尝试端口列表，使用高范围端口12345作为首选，避免与系统进程冲突
port_options = [12345, 10000, 11000, 9000, 9001, 8080, 8088, 8000, 8800, 8880, 8888, 8808, 9080, 8008]

# 选择第一个可用的端口
port = None
for p in port_options:
    if check_port(p):
        port = p
        break

# 如果所有端口都被占用，使用随机高位端口
if port is None:
    import random
    port = random.randint(10000, 65000)
    print(f"警告: 所有预定端口都被占用，尝试随机端口: {port}")
else:    
    print(f"找到可用端口: {port}")

# 使用与原始命令类似的方式启动服务器，但可能使用不同的端口
# 显式指定conda环境的Python解释器路径
conda_python = r"C:\Users\WCQ27\.conda\envs\modelapp\python.exe"

# 检查是否存在conda环境的Python
if os.path.exists(conda_python):
    python_executable = conda_python
    print(f"使用conda环境Python: {conda_python}")
else:
    python_executable = sys.executable
    print(f"警告: 找不到conda环境Python，使用系统Python: {sys.executable}")

cmd = [
    python_executable, "-m", "uvicorn", 
    "app.main:app", 
    "--reload",  # 启用重新加载功能
    "--host", "0.0.0.0", 
    "--port", str(port)
]

print(f"执行命令: {' '.join(cmd)}")

# 将选定端口保存到文件中，便于前端读取
port_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'port.txt')
with open(port_file_path, 'w') as f:
    f.write(str(port))
print(f"端口信息已写入: {port_file_path}")
print(f"请手动将端口 {port} 更新到前端的 vite.config.js 中的代理配置")

# 启动服务的函数
def start_services():
    # 1. 启动FastAPI后端服务
    print("\n===== 启动FastAPI后端服务 =====")
    fastapi_process = subprocess.Popen(cmd)
    print(f"FastAPI服务已启动，进程ID: {fastapi_process.pid}")
    
    # 2. 启动车牌识别服务
    print("\n===== 启动车牌识别服务 =====")
    plate_service_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "License_plate_recognition_tracking", "appPro.py")
    
    if os.path.exists(plate_service_path):
        plate_cmd = [python_executable, plate_service_path]
        print(f"车牌识别服务路径: {plate_service_path}")
        print(f"执行命令: {' '.join(plate_cmd)}")
        
        plate_process = subprocess.Popen(plate_cmd)
        print(f"车牌识别服务已启动，进程ID: {plate_process.pid}")
    else:
        print(f"错误: 找不到车牌识别服务脚本: {plate_service_path}")
        plate_process = None
    
    print("\n===== 所有服务已启动 =====")
    print("FastAPI后端服务运行在端口 {}".format(port))
    print("车牌识别服务运行在端口 5000")
    print("\n按Ctrl+C可以停止所有服务")
    
    # 等待服务运行
    try:
        # 保持主进程运行，等待用户手动中断
        while True:
            # 检查进程是否存活
            if fastapi_process.poll() is not None:
                print("\n警告: FastAPI服务已终止，退出码: {}".format(fastapi_process.returncode))
                break
                
            if plate_process and plate_process.poll() is not None:
                print("\n警告: 车牌识别服务已终止，退出码: {}".format(plate_process.returncode))
                break
                
            # 不要占用过多处理器时间
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n收到用户中断信号，正在终止服务...")
    finally:
        # 终止所有进程
        if fastapi_process.poll() is None:
            fastapi_process.terminate()
            print("FastAPI服务已终止")
            
        if plate_process and plate_process.poll() is None:
            plate_process.terminate()
            print("车牌识别服务已终止")

# 运行所有服务
if __name__ == "__main__":
    start_services()
