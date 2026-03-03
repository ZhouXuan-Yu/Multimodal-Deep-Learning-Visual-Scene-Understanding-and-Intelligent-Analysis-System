"""
#################################
# 断点续训工具 - 用于深度学习模型训练的检查点保存和恢复
# Checkpoint Utilities - For Deep Learning Model Checkpoint Saving and Resuming
#################################
"""
#########################################################
# import libraries
import os
import json
import time
import tensorflow as tf

from config import Config_classification 
from config import config_segmentation

def get_checkpoint_dir(model_type="classification", timestamp=None):
    """
    获取检查点目录
    
    参数:
        model_type: 模型类型 ("classification" 或 "segmentation")
        timestamp: 时间戳，如果为None则自动生成
    返回:
        检查点路径
    """
    # 确保目录存在
    os.makedirs('Output/Checkpoints', exist_ok=True)
    
    # 生成时间戳
    if timestamp is None:
        timestamp = f"{int(time.time())}"
    
    if model_type == "classification":
        checkpoint_dir = f"Output/Checkpoints/classification_{timestamp}"
    else:
        checkpoint_dir = f"Output/Checkpoints/segmentation_{timestamp}" 
    
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    return checkpoint_dir

def create_callbacks(checkpoint_dir, monitor='val_loss', patience=5, save_best_only=True, save_weights_only=False, use_early_stopping=True):
    """
    创建训练回调函数，用于保存检查点、提前停止和学习率降低
    
    参数:
        checkpoint_dir: 检查点保存目录
        monitor: 监控的指标
        patience: 提前停止的耐心值
        save_best_only: 是否只保存最佳模型
        save_weights_only: 是否只保存权重
        use_early_stopping: 是否使用早停机制，设为False可训练固定轮次
    返回:
        回调函数列表
    """
    # Model checkpoint callback - 保存最佳模型
    checkpoint_path = os.path.join(checkpoint_dir, "model_checkpoint.h5")
    checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=checkpoint_path,
        save_weights_only=save_weights_only,
        monitor=monitor,
        mode='auto',
        save_best_only=save_best_only,
        verbose=1
    )
    
    # 准备回调函数列表
    callbacks = [checkpoint_callback]
    
    # 是否使用早停机制
    if use_early_stopping:
        # Early stopping callback - 提前停止
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor=monitor,
            patience=patience,
            mode='auto',
            restore_best_weights=True,
            verbose=1
        )
        callbacks.append(early_stopping)
    
    # Learning rate reducer - 学习率降低
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor=monitor,
        factor=0.2,
        patience=patience // 2 if patience > 2 else 1,
        min_lr=1e-6,
        mode='auto',
        verbose=1
    )
    callbacks.append(reduce_lr)
    
    # TensorBoard callback - TensorBoard可视化
    tensorboard_callback = tf.keras.callbacks.TensorBoard(
        log_dir=os.path.join(checkpoint_dir, "logs"),
        histogram_freq=1,
        update_freq='epoch'
    )
    callbacks.append(tensorboard_callback)
    
    # CSV Logger - 将训练历史记录到CSV文件
    csv_logger = tf.keras.callbacks.CSVLogger(
        os.path.join(checkpoint_dir, 'training_history.csv'),
        separator=',', 
        append=True
    )
    callbacks.append(csv_logger)
    
    # 添加每个轮次保存一次的回调函数（当不使用早停时特别有用）
    if not use_early_stopping:
        # 每个轮次保存检查点
        epoch_checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
            filepath=os.path.join(checkpoint_dir, "epoch_{epoch:02d}.h5"),
            save_weights_only=save_weights_only,
            save_freq='epoch',
            verbose=0  # 不打印太多信息，避免输出混乱
        )
        callbacks.append(epoch_checkpoint_callback)
    
    return callbacks

def save_training_config(checkpoint_dir, model_type="classification", **kwargs):
    """
    保存训练配置信息，用于后续恢复训练
    
    参数:
        checkpoint_dir: 检查点目录
        model_type: 模型类型
        **kwargs: 其他配置参数
    """
    # 基本配置
    if model_type == "classification":
        config = {
            "model_type": model_type,
            "epochs": Config_classification.get('Epochs'),
            "batch_size": Config_classification.get('batch_size'),
            "timestamp": int(time.time()),
            "date": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        config = {
            "model_type": model_type,
            "epochs": config_segmentation.get('Epochs'),
            "batch_size": config_segmentation.get('batch_size'),
            "num_class": config_segmentation.get('num_class'),
            "timestamp": int(time.time()),
            "date": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    # 添加额外参数
    config.update(kwargs)
    
    # 保存到JSON文件
    with open(os.path.join(checkpoint_dir, 'training_config.json'), 'w') as f:
        json.dump(config, f, indent=4)
        
    return config

def load_training_config(checkpoint_dir):
    """
    加载训练配置
    
    参数:
        checkpoint_dir: 检查点目录
    返回:
        配置字典
    """
    config_path = os.path.join(checkpoint_dir, 'training_config.json')
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config

def find_latest_checkpoint(model_type="classification"):
    """
    查找最新的检查点目录
    
    参数:
        model_type: 模型类型
    返回:
        最新检查点的路径，如果没有找到则返回None
    """
    checkpoint_base = "Output/Checkpoints"
    if not os.path.exists(checkpoint_base):
        print(f"未找到检查点目录: {checkpoint_base}")
        return None
        
    # 查找匹配的检查点目录
    prefix = f"{model_type}_"
    matching_dirs = [d for d in os.listdir(checkpoint_base) 
                     if os.path.isdir(os.path.join(checkpoint_base, d)) and d.startswith(prefix)]
    
    if not matching_dirs:
        print(f"未找到{model_type}模型的检查点")
        return None
    
    # 按时间戳排序
    matching_dirs.sort(key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else 0, reverse=True)
    
    # 返回最新的检查点目录
    latest = os.path.join(checkpoint_base, matching_dirs[0])
    
    # 验证检查点文件是否存在
    checkpoint_file = os.path.join(latest, "model_checkpoint.h5")
    if not os.path.exists(checkpoint_file):
        print(f"在最新目录中未找到模型检查点文件: {checkpoint_file}")
        return None
        
    print(f"找到最新的模型检查点: {latest}")
    return latest

def load_model_from_checkpoint(checkpoint_dir=None, model_type="classification", custom_objects=None):
    """
    从检查点加载模型
    
    参数:
        checkpoint_dir: 检查点目录，如果为None则自动查找最新的检查点
        model_type: 模型类型
        custom_objects: 自定义对象字典，用于加载自定义层或损失函数
    返回:
        加载的模型和配置字典
    """
    # 如果没有指定检查点目录，则查找最新的
    if checkpoint_dir is None:
        checkpoint_dir = find_latest_checkpoint(model_type)
        if checkpoint_dir is None:
            print("未找到可用的检查点")
            return None, None
    
    # 加载配置
    config = load_training_config(checkpoint_dir)
    if config is None:
        print("无法加载训练配置")
        return None, None
        
    # 检查检查点文件是否存在
    checkpoint_file = os.path.join(checkpoint_dir, "model_checkpoint.h5")
    if not os.path.exists(checkpoint_file):
        print(f"检查点文件不存在: {checkpoint_file}")
        return None, config
        
    # 加载模型
    try:
        model = tf.keras.models.load_model(checkpoint_file, custom_objects=custom_objects)
        print(f"成功从 {checkpoint_file} 加载模型")
        return model, config
    except Exception as e:
        print(f"加载模型时出错: {e}")
        return None, config

def resume_training_from_checkpoint(model=None, checkpoint_dir=None, model_type="classification", 
                                   train_data=None, val_data=None, epochs=None, custom_objects=None):
    """
    从检查点恢复训练
    
    参数:
        model: 预加载的模型，如果为None则从检查点加载
        checkpoint_dir: 检查点目录，如果为None则查找最新的检查点
        model_type: 模型类型
        train_data: 训练数据
        val_data: 验证数据
        epochs: 要训练的总周期数，如果为None则从配置中获取
        custom_objects: 自定义对象字典
    返回:
        训练历史对象和最终模型
    """
    # 加载模型和配置
    if model is None:
        model, config = load_model_from_checkpoint(checkpoint_dir, model_type, custom_objects)
        if model is None:
            print("无法恢复训练：模型加载失败")
            return None, None
    else:
        if checkpoint_dir is None:
            checkpoint_dir = find_latest_checkpoint(model_type)
        config = load_training_config(checkpoint_dir) if checkpoint_dir else None
    
    # 如果没有提供epochs，则使用配置中的值
    if epochs is None and config:
        epochs = config.get("epochs", 10)
    elif epochs is None:
        epochs = 10  # 默认值
    
    # 检查是否提供了训练数据
    if train_data is None:
        print("未提供训练数据，无法恢复训练")
        return None, model
    
    # 创建新的检查点目录
    new_checkpoint_dir = get_checkpoint_dir(model_type)
    
    # 保存恢复训练的配置
    resume_config = {
        "resumed_from": checkpoint_dir,
        "original_config": config,
        "resume_timestamp": int(time.time()),
        "resume_date": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    save_training_config(new_checkpoint_dir, model_type, **resume_config)
    
    # 创建回调函数
    callbacks = create_callbacks(new_checkpoint_dir)
    
    # 恢复训练
    print(f"从检查点恢复训练，将训练{epochs}个周期")
    if val_data is not None:
        history = model.fit(train_data, validation_data=val_data, epochs=epochs, callbacks=callbacks)
    else:
        history = model.fit(train_data, epochs=epochs, callbacks=callbacks)
    
    # 保存最终模型
    final_model_path = os.path.join(new_checkpoint_dir, "final_model.h5")
    model.save(final_model_path)
    print(f"最终模型已保存至: {final_model_path}")
    
    return history, model
