"""
停止所有Python进程并重新启动服务（端口8082）
"""
import os
import subprocess
import signal
import sys

# 停止所有Python进程
os.system('taskkill /F /IM python.exe >nul 2>&1')

# 等待进程完全停止
import time
time.sleep(2)

# 启动新服务
cmd = 'cd "D:\\ModelService_graduation-main\\ModelService_graduation-main\\ModelService\\Main" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8082'
print(f"启动命令: {cmd}")
os.system(cmd)

