"""
完整测试脚本
"""
import requests
import json
import sys

def test_all():
    print("="*60)
    print("测试路线规划API")
    print("="*60)
    
    # 测试1: 检查服务状态
    print("\n1. 检查服务状态...")
    r = requests.get('http://localhost:8082/api/health', timeout=10)
    print(f"   状态: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   已加载模块: {data.get('modules_loaded', [])}")
    
    # 测试2: 检查路由
    print("\n2. 检查已注册的路由...")
    r = requests.get('http://localhost:8082/api/health', timeout=10)
    if r.status_code == 200:
        data = r.json()
        routes = data.get('api_routes', [])
        plan_routes = [p.get('path') for p in routes if 'plan' in p.get('path', '')]
        print(f"   plan相关路由: {plan_routes}")
    
    # 测试3: 测试plan/stream路由
    print("\n3. 测试 /api/route/plan/stream...")
    r = requests.post('http://localhost:8082/api/route/plan/stream', json={'text': 'from Beijing to Shanghai'}, timeout=60)
    print(f"   状态: {r.status_code}")
    if r.status_code == 200:
        try:
            data = r.json()
            print(f"   事件: {data.get('event')}")
            print(f"   有route_data: {'route_data' in data}")
        except:
            print(f"   响应: {r.text[:200]}")
    
    # 测试4: 测试thinking路由
    print("\n4. 测试 /api/route/plan/stream/thinking...")
    r = requests.post('http://localhost:8082/api/route/plan/stream/thinking', json={'text': 'from Beijing to Shanghai'}, stream=True, timeout=120)
    print(f"   状态: {r.status_code}")
    print(f"   Content-Type: {r.headers.get('Content-Type')}")
    if r.status_code == 200:
        lines = list(r.iter_lines())
        print(f"   收到行数: {len(lines)}")
        for i, line in enumerate(lines[:5]):
            print(f"   Line {i+1}: {line.decode('utf-8')[:100]}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_all()




