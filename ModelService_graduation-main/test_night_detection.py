#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试night_detection模块导入
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ModelService', 'Main'))

try:
    from app.routers import night_detection
    print('✅ night_detection模块导入成功')
    print('是否有router:', hasattr(night_detection, 'router'))
    if hasattr(night_detection, 'router'):
        print('router类型:', type(night_detection.router))
        print('router前缀:', getattr(night_detection.router, 'prefix', 'None'))
except Exception as e:
    print('❌ 导入失败:', str(e))
    import traceback
    traceback.print_exc()
