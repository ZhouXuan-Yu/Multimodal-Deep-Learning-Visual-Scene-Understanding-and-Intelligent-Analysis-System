# 服务模块初始化文件
# 用于提供功能模块服务接口的统一导入点

import logging

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.info("服务模块初始化...")
