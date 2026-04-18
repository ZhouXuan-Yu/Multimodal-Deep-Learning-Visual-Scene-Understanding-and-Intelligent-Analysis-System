'''
letterbox函数实现 - 用于YOLO模型的图像预处理
'''
import cv2
import numpy as np

def letterbox(img, new_shape=(640, 640), color=(114, 114, 114), auto=True, scaleFill=False, scaleup=True):
    """
    将图像调整为YOLO模型需要的尺寸，包含填充
    
    参数:
    - img: 输入图像
    - new_shape: 新的图像尺寸
    - color: 填充颜色
    - auto: 是否自动调整填充
    - scaleFill: 是否拉伸填充
    - scaleup: 是否允许放大
    
    返回:
    - img: 调整后的图像
    - ratio: 缩放比例
    - (dw, dh): 填充尺寸
    """
    # 获取原始图像形状
    shape = img.shape[:2]  # 当前形状 [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # 计算缩放比例 (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    if not scaleup:  # 只缩小，不放大
        r = min(r, 1.0)

    # 计算填充
    ratio = r, r  # 宽度、高度比例
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # 宽高填充
    if auto:  # 最小矩形
        dw, dh = np.mod(dw, 64), np.mod(dh, 64)  # 宽高填充
    elif scaleFill:  # 拉伸
        dw, dh = 0.0, 0.0
        new_unpad = (new_shape[1], new_shape[0])
        ratio = new_shape[1] / shape[1], new_shape[0] / shape[0]  # 宽度、高度比例

    dw /= 2  # 填充分到两侧
    dh /= 2

    if shape[::-1] != new_unpad:  # 调整大小
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # 添加边框
    return img, ratio, (dw, dh)
