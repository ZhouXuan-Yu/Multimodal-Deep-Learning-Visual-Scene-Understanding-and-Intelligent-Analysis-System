"""
配置文件，包含模型训练和推理的各种参数
"""

import os

# 数据相关配置
DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'UNISV-Dataset-main', 'UNISV')
TRAIN_SPLIT = 0.7
VAL_SPLIT = 0.15
TEST_SPLIT = 0.15
NUM_CLASSES = 10
CLIP_LENGTH = 12  # 减少帧数以降低显存使用
FRAME_HEIGHT = 224
FRAME_WIDTH = 224
BATCH_SIZE = 4  # 减小批量大小以降低显存使用

# 行为类别设置 - 根据实际目录名称调整
ACTION_CATEGORIES = {
    'pushpeople': 0,   # 红色警报：推人
    'fight': 1,       # 红色警报：战斗
    'jogging': 2,     # 黄色警报：慢跑
    'shakehands': 3,  # 黄色警报：握手
    'embrace': 4,     # 黄色警报：拥抱
    'walk': 5,        # 绿色：行走
    'singlewave': 6,  # 绿色：单手挥手
    'doublewave': 7,  # 绿色：双手挥手
    'jump': 8,        # 绿色：跳跃
    'squat': 9        # 绿色：下蹲
}

# 警报级别设置
ACTION_ALERT_LEVEL = {
    0: 'red',    # 推人 - 红色警报
    1: 'red',    # 战斗 - 红色警报
    2: 'yellow', # 慢跑 - 黄色警报
    3: 'yellow', # 握手 - 黄色警报
    4: 'yellow', # 拥抱 - 黄色警报
    5: 'green',  # 行走 - 绿色（正常）
    6: 'green',  # 单手挥手 - 绿色（正常）
    7: 'green',  # 双手挥手 - 绿色（正常）
    8: 'green',  # 跳跃 - 绿色（正常）
    9: 'green'   # 下蹲 - 绿色（正常）
}

# 警报颜色设置 (BGR格式)
ALERT_COLORS = {
    'red': (0, 0, 255),      # 红色
    'yellow': (0, 255, 255), # 黄色
    'green': (0, 255, 0)     # 绿色
}

# 模型相关配置
MODEL_TYPE = 'I3D'  # 支持 'I3D', 'SlowFast', 'X3D'
PRETRAINED = True
DROPOUT_PROB = 0.5
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-5
NUM_EPOCHS = 30  # 减少训练轮数
EARLY_STOPPING_PATIENCE = 5  # 减少早停耐心
SAVE_DIR = os.path.join(DATA_ROOT, 'checkpoints')
LOG_DIR = os.path.join(DATA_ROOT, 'logs')
USE_MIXED_PRECISION = True  # 使用混合精度训练以减少显存使用

# 数据增强配置
USE_AUGMENTATION = True
RANDOM_FLIP_PROB = 0.5
RANDOM_CROP_SIZE = (224, 224)
BRIGHTNESS_CONTRAST_ADJUSTMENT = 0.3  # 亮度和对比度调整范围 [-0.3, 0.3]
NOISE_LEVEL = 0.05  # 随机噪声水平

# 推理相关配置
CONFIDENCE_THRESHOLD = 0.3  # 降低置信度阈值以增强检测率
IOU_THRESHOLD = 0.5
USE_TEMPORAL_SMOOTHING = False  # 禁用时序平滑以便看到原始预测
TEMPORAL_WINDOW_SIZE = 5  # 时序平滑窗口大小

# 人体检测和目标跟踪配置
DETECTION_INTERVAL = 5  # 每隔5帧执行一次人体检测
TRACKING_CONFIDENCE = 0.3  # 人体检测置信度阈值
BOX_SMOOTH_FACTOR = 0.7  # 方框平滑因子 (0-1), 越大越平滑

# 确保相关目录存在
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
