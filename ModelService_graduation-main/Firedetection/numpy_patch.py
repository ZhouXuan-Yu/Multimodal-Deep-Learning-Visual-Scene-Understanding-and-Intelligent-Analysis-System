"""
为高版本NumPy添加向后兼容性补丁，使其能与TensorFlow 2.3.0配合使用
"""
import numpy as np

# 检查是否缺少np.object属性并添加
if not hasattr(np, 'object'):
    # 在NumPy 1.20+版本中，np.object被移除了，我们添加回来以兼容TensorFlow 2.3.0
    np.object = object
    print("已添加NumPy兼容性补丁，修复np.object缺失问题")
