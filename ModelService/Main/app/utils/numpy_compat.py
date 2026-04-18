"""
NumPy兼容性修复模块
"""
import sys
import importlib

class NumpyTypingModule:
    """为旧版NumPy提供numpy.typing模块的兼容性"""
    NDArray = object
    ArrayLike = object

class NumpyPatch:
    """修补NumPy以兼容新旧API"""
    
    @staticmethod
    def apply():
        """应用NumPy补丁"""
        import numpy as np
        
        # 添加object属性
        if not hasattr(np, 'object'):
            np.object = object
        
        # 如果没有typing模块，创建一个模拟版本
        if not hasattr(np, 'typing'):
            typing_module = NumpyTypingModule()
            sys.modules['numpy.typing'] = typing_module
            np.typing = typing_module
            
        return True

# 自动应用补丁
try:
    NumpyPatch.apply()
except Exception as e:
    print(f"NumPy补丁应用失败: {e}")
