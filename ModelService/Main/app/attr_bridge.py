# 创建一个完整的桥接模块，从attrs重新导出所有内容
# 这样mediapipe就可以导入attr模块了
import attrs as _attrs
import sys
import inspect
import logging

logger = logging.getLogger(__name__)
logger.info("加载attr桥接模块...")

# 完整的导出attrs中的所有内容
for attr_name in dir(_attrs):
    if not attr_name.startswith('_') or attr_name in ('__version__'):
        globals()[attr_name] = getattr(_attrs, attr_name)

# 添加attr模块特有的功能或常量
__version__ = _attrs.__version__
logger.info(f"attr桥接模块版本: {__version__}")

# 在sys.modules中注册这个模块，确保其他模块能找到它
# 注意：我们注册为 'attr' 而不是 'attrs'，以避免与attrs包冲突
if 'attr' not in sys.modules:
    sys.modules['attr'] = sys.modules[__name__]
    logger.info("attr桥接模块已注册到sys.modules")
else:
    logger.info("attr模块已存在于sys.modules中，跳过注册")

# 关键函数映射
# attr.s -> attrs.define
def s(*args, **kwargs):
    """桥接到attrs.define"""
    return _attrs.define(*args, **kwargs)

# attr.ib -> attrs.field
def ib(*args, **kwargs):
    """桥接到attrs.field"""
    return _attrs.field(*args, **kwargs)

# 属性验证器和工具函数
class validators:
    """桥接到attrs.validators"""
    # 从attrs.validators导入所有函数
    for name, obj in inspect.getmembers(_attrs.validators):
        if inspect.isfunction(obj) and not name.startswith('_'):
            locals()[name] = obj

# 确保也支持完整的命名空间访问方式
class Factory:
    """工厂函数的桥接"""
    @staticmethod
    def for_optional(factory, *args, **kwargs):
        return _attrs.converters.optional(factory, *args, **kwargs)

# 转换器
class converters:
    """桥接到attrs.converters"""
    # 从attrs.converters导入所有函数
    for name, obj in inspect.getmembers(_attrs.converters):
        if inspect.isfunction(obj) and not name.startswith('_'):
            locals()[name] = obj

logger.info("attr桥接模块加载完成，所有关键函数已映射")
