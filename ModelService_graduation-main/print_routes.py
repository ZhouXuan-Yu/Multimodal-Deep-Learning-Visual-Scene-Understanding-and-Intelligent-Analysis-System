# 路由配置信息打印工具

# 前端路由列表
FRONTEND_ROUTES = [
    {'path': '/', 'name': 'home', 'component': 'HomeView'},
    {'path': '/route-planning', 'name': 'route-planning', 'component': 'RoutePlanningView'},
    {'path': '/route-records', 'name': 'route-records', 'component': 'RouteRecordsView'},
    {'path': '/image-recognition', 'name': 'image-recognition', 'component': 'ImageRecognitionView'},
    {'path': '/video-tracking', 'name': 'video-tracking', 'component': 'VideoTrackingView'},
    {'path': '/knowledge-base-chat', 'name': 'knowledge-base-chat', 'component': 'KnowledgeBaseChatView'},
    {'path': '/night-detection', 'name': 'night-detection', 'component': 'NightDetectionView'},
    {'path': '/rgbt-detection', 'name': 'rgbt-detection', 'component': 'RGBTDetectionView'},
    {'path': '/test-fusion', 'name': 'test-fusion', 'component': 'TestFusionView'},
    {'path': '/plate-recognition', 'name': 'plate-recognition', 'component': 'PlateRecognitionView'},
]

# 后端API路由定义
BACKEND_ROUTES = {
    'plate_recognition': {'prefix': '/api/plate-recognition', 'tags': ['车牌识别']},
    'chat': {'prefix': '/api/chat', 'tags': ['聊天']},
    'route_planning': {'prefix': '/api/route', 'tags': ['路径规划']},
    'video_tracking': {'prefix': '/api/video-tracking', 'tags': ['视频追踪']},
    'image_analysis_chat': {'prefix': '/api/image-analysis-chat', 'tags': ['图片分析聊天']},
    'knowledge_chat': {'prefix': '/api/knowledge-chat', 'tags': ['知识库聊天']},
    'night_detection': {'prefix': '/api/night-detection', 'tags': ['低光图像增强与目标检测']},
    'rgbt_detection': {'prefix': '/api/rgbt-detection', 'tags': ['可见光-热微小物体检测']},
    'image_recognition': {'prefix': '/api/image-recognition', 'tags': ['图像识别']}
}

def print_frontend_routes():
    print("\n===== 前端路由 =====")
    for route in FRONTEND_ROUTES:
        print(f"路径: {route['path']}, 名称: {route['name']}, 组件: {route['component']}")

def print_backend_routes():
    print("\n===== 后端API路由前缀 =====")
    for module, config in BACKEND_ROUTES.items():
        print(f"模块: {module}, 前缀: {config['prefix']}, 标签: {config['tags']}")

def print_route_mapping():
    print("\n===== 前端路由与后端API映射关系 =====")
    mapping = {
        '/': '/api', # 首页可能使用多个API
        '/route-planning': '/api/route',
        '/route-records': '/api/route',
        '/image-recognition': '/api/image-recognition',
        '/video-tracking': '/api/video-tracking',
        '/knowledge-base-chat': '/api/knowledge-chat',
        '/night-detection': '/api/night-detection',
        '/rgbt-detection': '/api/rgbt-detection',
        '/test-fusion': '/api/test',
        '/plate-recognition': '/api/plate-recognition'
    }
    
    for frontend, backend in mapping.items():
        print(f"前端: {frontend} -> 后端: {backend}")
        
if __name__ == "__main__":
    print("========== 路由映射信息 ==========")
    print_frontend_routes()
    print_backend_routes()
    print_route_mapping()
