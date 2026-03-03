# -*- coding: utf-8 -*-
# NumPy补丁文件，用于修复NumPy类型警告

import numpy

# 检查是否需要应用补丁
if not hasattr(numpy, 'object'):
    # 添加别名以兼容旧代码
    numpy.object = object

# 应用其他可能需要的NumPy补丁
if not hasattr(numpy, 'bool'):
    numpy.bool = bool

if not hasattr(numpy, 'float'):
    numpy.float = float

if not hasattr(numpy, 'complex'):
    numpy.complex = complex

if not hasattr(numpy, 'str'):
    numpy.str = str
    
# 修复'typeDict'属性缺失的问题
if not hasattr(numpy, 'typeDict'):
    # 创建typeDict属性以兼容旧代码
    numpy.typeDict = {
        'bool': numpy.bool8 if hasattr(numpy, 'bool8') else numpy.bool_,
        'int': numpy.int64 if hasattr(numpy, 'int64') else numpy.int_,
        'float': numpy.float64 if hasattr(numpy, 'float64') else numpy.float_,
        'complex': numpy.complex128 if hasattr(numpy, 'complex128') else numpy.complex_,
        'str': numpy.str_ if hasattr(numpy, 'str_') else str,
        'object': numpy.object_ if hasattr(numpy, 'object_') else object
    }
    print("NumPy typeDict补丁已应用")

# 兼容NumPy 2.0
if not hasattr(numpy, 'float_') and hasattr(numpy, 'float64'):
    numpy.float_ = numpy.float64

if not hasattr(numpy, 'int_') and hasattr(numpy, 'int64'):
    numpy.int_ = numpy.int64

if not hasattr(numpy, 'bool_') and hasattr(numpy, 'bool8'):
    numpy.bool_ = numpy.bool8

if not hasattr(numpy, 'complex_') and hasattr(numpy, 'complex128'):
    numpy.complex_ = numpy.complex128

if not hasattr(numpy, 'object_'):
    numpy.object_ = object

if not hasattr(numpy, 'str_'):
    numpy.str_ = str
