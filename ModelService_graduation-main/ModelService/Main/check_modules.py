import sys
sys.path.insert(0, r"D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main")

# 检查高级版本
print("="*50)
print("检查高级版本route_planning:")
try:
    from ModelService.Main.app.routers import route_planning as rp1
    print(f"  文件: {rp1.__file__}")
    print(f"  有stream_with_thinking: {hasattr(rp1, 'stream_with_thinking')}")
    print(f"  POST路由: {[x for x in dir(rp1.router) if 'path' in str(x).lower()]}")
except Exception as e:
    print(f"  错误: {e}")

# 检查fallback版本
print("\n检查fallback版本route_planning:")
try:
    from app.routers import route_planning_fallback as rp2
    print(f"  文件: {rp2.__file__}")
    print(f"  有stream_with_thinking: {hasattr(rp2, 'stream_with_thinking')}")
except Exception as e:
    print(f"  错误: {e}")




