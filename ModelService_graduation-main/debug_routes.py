#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试路由注册问题
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ModelService', 'Main'))

# 初始化模块字典，就像main.py中一样
modules = {}

print("=== 调试模块加载 ===")

# 尝试导入night_detection模块
try:
    from ModelService.Main.app.routers import night_detection
    modules['night_detection'] = night_detection
    print("成功加载 night_detection 模块")
    print(f"   - 模块类型: {type(night_detection)}")
    print(f"   - 包含router属性: {hasattr(night_detection, 'router')}")
    if hasattr(night_detection, 'router'):
        print(f"   - router类型: {type(night_detection.router)}")
        print(f"   - router前缀: {getattr(night_detection.router, 'prefix', 'None')}")
        print(f"   - router路由数量: {len(night_detection.router.routes)}")
        for route in night_detection.router.routes[:3]:  # 只显示前3个路由
            print(f"     - 路由: {route.path}, 方法: {route.methods}")
except Exception as e:
    print(f"无法加载 night_detection 模块: {str(e)}")
    import traceback
    traceback.print_exc()

print(f"\n模块字典中的night_detection: {'night_detection' in modules}")

print("\n=== 模拟路由注册 ===")
if 'night_detection' in modules:
    module = modules['night_detection']
    try:
        if hasattr(module, 'router'):
            prefix = getattr(module, 'API_PREFIX', f'/api/night_detection'.replace('_', '-'))
            print(f"准备注册路由: {prefix}")
            print(f"   - 路由器: {module.router}")
            print(f"   - 路由数量: {len(module.router.routes)}")
        else:
            print("模块没有router属性")
    except Exception as e:
        print(f"路由注册失败: {str(e)}")
