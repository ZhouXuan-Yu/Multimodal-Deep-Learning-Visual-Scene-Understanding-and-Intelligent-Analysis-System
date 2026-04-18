# -*- coding: utf-8 -*-
# 应用初始化文件

# 导入NumPy补丁
from . import __numpy_patch

# 初始化日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 注意: 避免在这里直接导入middlewares或routers，防止循环导入
