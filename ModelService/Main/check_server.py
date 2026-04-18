"""
测试服务是否启动
"""
import requests
import json

try:
    # 检查健康端点
    resp = requests.get("http://localhost:8081/api/health", timeout=5)
    print(f"服务状态: {resp.status_code}")
    print(f"响应: {resp.text[:500]}")
except Exception as e:
    print(f"服务未启动或无法连接: {e}")




