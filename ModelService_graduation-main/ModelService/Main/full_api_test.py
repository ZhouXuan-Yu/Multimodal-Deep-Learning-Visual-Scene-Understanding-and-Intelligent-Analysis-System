"""
完整测试路由
"""
import requests

def test_api():
    print("="*60)
    print("完整测试路线规划API")
    print("="*60)
    
    # 1. 检查服务
    print("\n1. 检查服务状态...")
    r = requests.get('http://localhost:8082/api/health', timeout=10)
    print(f"   状态: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   已加载模块: {data.get('modules_loaded', [])}")
    
    # 2. 测试check-ollama
    print("\n2. 测试 /api/route/check-ollama...")
    r = requests.get('http://localhost:8082/api/route/check-ollama', timeout=10)
    print(f"   状态: {r.status_code}")
    if r.status_code == 200:
        print(f"   响应: {r.json()}")
    
    # 3. 测试plan/stream (GET)
    print("\n3. 测试 /api/route/plan/stream (GET)...")
    r = requests.get('http://localhost:8082/api/route/plan/stream?text=from Beijing to Shanghai', timeout=60)
    print(f"   状态: {r.status_code}")
    if r.status_code == 200:
        try:
            print(f"   响应: {r.json()}")
        except:
            print(f"   文本响应: {r.text[:200]}")
    
    # 4. 测试plan/stream (POST)
    print("\n4. 测试 /api/route/plan/stream (POST)...")
    r = requests.post('http://localhost:8082/api/route/plan/stream', json={'text': 'from Beijing to Shanghai'}, timeout=60)
    print(f"   状态: {r.status_code}")
    if r.status_code == 200:
        try:
            print(f"   响应: {r.json()}")
        except:
            print(f"   文本响应: {r.text[:200]}")
    
    # 5. 测试thinking路由
    print("\n5. 测试 /api/route/plan/stream/thinking...")
    r = requests.post('http://localhost:8082/api/route/plan/stream/thinking', json={'text': 'from Beijing to Shanghai'}, stream=True, timeout=120)
    print(f"   状态: {r.status_code}")
    print(f"   Content-Type: {r.headers.get('Content-Type')}")
    if r.status_code == 200:
        lines = list(r.iter_lines())
        print(f"   收到行数: {len(lines)}")
        for i, line in enumerate(lines[:10]):
            content = line.decode('utf-8') if line else ''
            print(f"   Line {i+1}: {content[:150]}")
    else:
        print(f"   响应: {r.text[:200]}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_api()




