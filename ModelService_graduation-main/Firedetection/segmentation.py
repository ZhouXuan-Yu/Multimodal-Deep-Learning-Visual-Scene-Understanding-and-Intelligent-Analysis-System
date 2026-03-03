"""
#################################
 Fire Segmentation on Fire Class to extract fire pixels from each frame based on the Ground Truth data (masks)
 Training, Validation, Test Data: Items (9) and (10) on https://ieee-dataport.org/open-access/flame-dataset-aerial-imagery-pile-burn-detection-using-drones-uavs
 Keras version: 2.4.0
 Tensorflow Version: 2.3.0
 GPU: Nvidia RTX 2080 Ti
 OS: Ubuntu 18.04
################################
"""

#########################################################
# 在导入TensorFlow前配置环境变量
import os
import random
import numpy as np
from tqdm import tqdm

# 先设置环境变量，然后才导入TensorFlow
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'
os.environ['TF_MEMORY_ALLOCATION'] = '0.5'  # 限制使用一半的内存

# 现在才导入TensorFlow
import tensorflow as tf
import matplotlib.pyplot as plt

# 限制TensorFlow内存使用
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        # 先设置内存增长
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"已检测到 {len(gpus)} 个GPU设备，并启用内存增长模式")
        
        # 设置内存限制
        tf.config.set_logical_device_configuration(
            gpus[0],
            [tf.config.LogicalDeviceConfiguration(memory_limit=5000)]
        )
        print("已限制GPU内存使用为5GB")
    except RuntimeError as e:
        print(f"GPU配置错误: {e}")
else:
    print("警告: 未检测到GPU，分割模型训练将使用CPU进行，这可能会很慢")

# 设置内存优化器
tf.keras.mixed_precision.set_global_policy('mixed_float16')  # 使用混合精度

# 导入其他必要模块
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input
from tensorflow.keras.layers import concatenate
from tensorflow.keras.layers import MaxPooling2D
from tensorflow.keras.layers import Dropout, Lambda
from tensorflow.keras.layers import Conv2D, Conv2DTranspose

from config import config_segmentation
from config import segmentation_new_size
from plotdata import plot_segmentation_test

#########################################################
# Global parameters and definition

METRICS = [
    tf.keras.metrics.AUC(name='auc'),
    tf.keras.metrics.Recall(name='recall'),
    tf.keras.metrics.TruePositives(name='tp'),
    tf.keras.metrics.TrueNegatives(name='tn'),
    tf.keras.metrics.FalsePositives(name='fp'),
    tf.keras.metrics.FalseNegatives(name='fn'),
    tf.keras.metrics.Accuracy(name='accuracy'),
    tf.keras.metrics.Precision(name='precision'),
    tf.keras.metrics.MeanIoU(num_classes=2, name='iou'),
    tf.keras.metrics.BinaryAccuracy(name='bin_accuracy'),
]


#########################################################
# Function definition

def segmentation_keras_load(resume=False, checkpoint_dir=None, epochs_override=None):
    """
    训练和加载分割模型用于火灾图像分割，基于U-Net结构。
    支持断点续训和高级可视化功能。
    
    参数:
        resume: 是否从检查点续训
        checkpoint_dir: 检查点目录，如果为None则自动创建或查找
        epochs_override: 覆盖配置文件中的轮次数
    返回:
        None, 保存模型并生成高级可视化图表
    """
    # 导入断点续训相关工具
    from checkpoint_utils import get_checkpoint_dir, create_callbacks, save_training_config, load_model_from_checkpoint
    from plotdata import plot_training, plot_metrics

    """ 初始化参数和检查点目录 """
    # 从配置获取基本参数
    batch_size = config_segmentation.get('batch_size')
    img_size = (segmentation_new_size.get("width"), segmentation_new_size.get("height"))
    img_width = img_size[0]
    img_height = img_size[1]
    img_channels = config_segmentation.get('CHANNELS')
    dir_images = "frames/Segmentation/Data/Images"
    dir_masks = "frames/Segmentation/Data/Masks"
    num_classes = config_segmentation.get("num_class")
    # 获取保存模型设置（可用于兼容旧版模型路径）
    use_early_stopping = config_segmentation.get('UseEarlyStopping', False)
    
    # 如果有轮次覆盖，使用覆盖值
    if epochs_override is not None:
        epochs = epochs_override
    else:
        epochs = config_segmentation.get('Epochs')
    
    # 创建或获取检查点目录
    if checkpoint_dir is None:
        if resume:
            # 正在从断点续训，但没有指定目录，默认使用最新的
            # TODO: 这里可以添加查找最新检查点的逻辑
            checkpoint_dir = get_checkpoint_dir("segmentation")
            print(f"将使用新检查点目录: {checkpoint_dir}")
        else:
            # 新建检查点目录
            checkpoint_dir = get_checkpoint_dir("segmentation")
            print(f"创建新检查点目录: {checkpoint_dir}")
    else:
        # 使用指定的检查点目录
        os.makedirs(checkpoint_dir, exist_ok=True)
        print(f"使用指定的检查点目录: {checkpoint_dir}")
    
    print("-" * 50)
    print("火灾图像分割训练")
    print("训练参数:")
    print(f"- 图像尺寸: {img_width}x{img_height}")
    print(f"- 批大小: {batch_size}")
    print(f"- 总轮次: {epochs}")
    print(f"- 是否从检查点续训: {'是' if resume else '否'}")
    print(f"- 是否使用早停: {'是' if use_early_stopping else '否'}")
    print("-" * 50)

    """ Start reading data (Frames and masks) and save them in Numpy array for Training, Validation and Test"""
    allfiles_image = sorted(
        [
            os.path.join(dir_images, fname)
            for fname in tqdm(os.listdir(dir_images))
            if fname.endswith(".jpg")
        ]
    )
    allfiles_mask = sorted(
        [
            os.path.join(dir_masks, fname)
            for fname in tqdm(os.listdir(dir_masks))
            if fname.endswith(".png") and not fname.startswith(".")
        ]
    )

    print("Number of samples:", len(allfiles_image))
    for input_path, target_path in tqdm(zip(allfiles_image[:10], allfiles_mask[:10])):
        print(input_path, "|", target_path)
    total_samples = len(allfiles_mask)
    train_ratio = config_segmentation.get("train_set_ratio")
    val_samples = int(total_samples * (1 - train_ratio))
    random.Random(1337).shuffle(allfiles_image)
    random.Random(1337).shuffle(allfiles_mask)
    train_img_paths = allfiles_image[:-val_samples]
    train_mask_paths = allfiles_mask[:-val_samples]
    val_img_paths = allfiles_image[-val_samples:]
    val_mask_paths = allfiles_mask[-val_samples:]

    x_train = np.zeros((len(train_img_paths), img_height, img_width, img_channels), dtype=np.uint8)
    y_train = np.zeros((len(train_mask_paths), img_height, img_width, 1), dtype=np.bool_)

    x_val = np.zeros((len(val_img_paths), img_height, img_width, img_channels), dtype=np.uint8)
    y_val = np.zeros((len(val_mask_paths), img_height, img_width, 1), dtype=np.bool_)
    print('\nLoading training images: ', len(train_img_paths), 'images ...')
    for n, file_ in tqdm(enumerate(train_img_paths)):
        img = tf.keras.preprocessing.image.load_img(file_, target_size=img_size)
        x_train[n] = img

    print('\nLoading training masks: ', len(train_mask_paths), 'masks ...')
    for n, file_ in tqdm(enumerate(train_mask_paths)):
        img = tf.keras.preprocessing.image.load_img(file_, target_size=img_size, color_mode="grayscale")
        y_train[n] = np.expand_dims(img, axis=2)
        # y_train[n] = y_train[n] // 255

    print('\nLoading test images: ', len(val_img_paths), 'images ...')
    for n, file_ in tqdm(enumerate(val_img_paths)):
        img = tf.keras.preprocessing.image.load_img(file_, target_size=img_size)
        x_val[n] = img

    print('\nLoading test masks: ', len(val_mask_paths), 'masks ...')
    for n, file_ in tqdm(enumerate(val_mask_paths)):
        img = tf.keras.preprocessing.image.load_img(file_, target_size=img_size, color_mode="grayscale")
        y_val[n] = np.expand_dims(img, axis=-1)
        # y_val[n] = y_val[n] // 255

    """ Plot some random data: frame and mask (gTruth)"""
    idx_rand = random.randint(0, len(train_img_paths))
    plt.figure(figsize=(13, 5))
    plt.subplot(1, 2, 1)
    plt.imshow(x_train[idx_rand])
    plt.axis('off')
    plt.subplot(1, 2, 2)
    plt.imshow(np.squeeze(y_train[idx_rand]))
    plt.axis('off')
    plt.show()

    tf.keras.backend.clear_session()

    """ 训练模型，支持断点续训 """
    # 获取模型大小配置，默认使用更节省内存的小型模型
    use_small_model = config_segmentation.get('UseSmallModel', True)
    
    # 情景1: 从检查点续训
    if resume:
        print("\n尝试从检查点加载模型...")
        model, config = load_model_from_checkpoint(checkpoint_dir, "segmentation")
        if model is not None:
            print("\n成功加载检查点模型")
            print(f"\n加载的训练配置: {config}")
        else:
            print("\n无法加载断点模型，创建新模型")
            if use_small_model:
                # 使用小型模型以减少内存使用
                model = model_unet_small(img_height, img_width, img_channels, num_classes)
                print("\n使用小型模型进行训练（节省内存）")
            else:
                model = model_unet_kaggle(img_height, img_width, img_channels, num_classes)
                print("\n使用完整模型进行训练（需要更多内存）")
    # 情景2: 创建新模型
    else:
        print("\n创建新分割模型...")
        if use_small_model:
            # 使用小型模型以减少内存使用
            model = model_unet_small(img_height, img_width, img_channels, num_classes)
            print("\n使用小型模型进行训练（节省内存）")
        else:
            model = model_unet_kaggle(img_height, img_width, img_channels, num_classes)
            print("\n使用完整模型进行训练（需要更多内存）")
    
    # 保存模型架构图
    model_fig_file = os.path.join(checkpoint_dir, 'segmentation_model_u_net.png')
    tf.keras.utils.plot_model(model, to_file=model_fig_file, show_shapes=True, show_dtype=True, 
                           show_layer_names=True, rankdir="TB", dpi=150)
    print(f"\n模型架构图已保存至: {model_fig_file}")
    
    # 保存训练配置
    config_dict = {
        "img_size": img_size,
        "batch_size": batch_size,
        "epochs": epochs,
        "train_samples": len(train_img_paths),
        "val_samples": len(val_img_paths),
        "model_params": {"layers": len(model.layers)}
    }
    save_training_config(checkpoint_dir, "segmentation", **config_dict)
    
    # 编译模型
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=METRICS)
    model.summary()
    
    # 创建回调函数
    callbacks = create_callbacks(
        checkpoint_dir=checkpoint_dir,
        monitor='val_loss',
        patience=5,
        save_best_only=True,
        use_early_stopping=use_early_stopping
    )
    
    # 训练模型
    print("\n开始训练分割模型...")
    history = model.fit(x_train, y_train, 
                      validation_data=(x_val, y_val), 
                      epochs=epochs, 
                      batch_size=batch_size,
                      callbacks=callbacks,
                      verbose=1)
    
    # 保存最终模型
    final_model_path = os.path.join(checkpoint_dir, "final_model.h5")
    model.save(final_model_path)
    print(f"\n最终模型已保存至: {final_model_path}")
    
    # 生成训练过程可视化
    print("\n生成学术级可视化图表...")
    
    # 绘制训练曲线
    plot_training(history, 'FireSegmentation', len(model.layers))
    
    # 绘制训练指标详细图表
    plot_metrics(history)
    
    # 运行验证集预测
    print("\n在验证集上进行预测...")
    preds_val = model.predict(x_val, verbose=1)
    preds_val_t = (preds_val > 0.5).astype(np.uint8)
    
    # 计算IoU分数
    val_iou_scores = []
    for i in range(len(y_val)):
        # 计算每个样本的IoU
        y_true = y_val[i].flatten()
        y_pred = preds_val_t[i].flatten()
        intersection = np.logical_and(y_true, y_pred).sum()
        union = np.logical_or(y_true, y_pred).sum()
        iou_score = intersection / union if union > 0 else 0
        val_iou_scores.append(iou_score)
    
    # 输出平均IoU
    mean_iou = np.mean(val_iou_scores)
    print(f"\n验证集平均IoU: {mean_iou:.4f}")
    
    # 生成分割结果可视化
    print("\n生成分割结果可视化...")
    result_path = os.path.join(checkpoint_dir, "segmentation_results")
    # 绘制原始图像、真实标签和预测标签的对比图
    plot_segmentation_test(xval=x_val, yval=y_val, ypred=preds_val_t, 
                          num_samples=6, 
                          save_path=result_path)
    
    print("\n训练和可视化完成, 结果已保存至:")
    print(f"- {checkpoint_dir}")
    
    return model, history


def model_unet_small(img_height, img_width, img_channel, num_classes):
    """
    更小型的U-Net模型，用于分割任务，调整了通道数量和深度以减少内存使用
    
    参数:
        img_height: 图像高度
        img_width: 图像宽度
        img_channel: 图像通道数
        num_classes: 类别数量
    返回:
        基于TensorFlow和Keras的一个U-Net模型
    """
    inputs = Input((img_height, img_width, img_channel))
    s = Lambda(lambda x: x / 255)(inputs)
    
    # 编码器部分 - 比原始模型使用更少的通道数
    c1 = Conv2D(8, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(s)
    c1 = Dropout(0.1)(c1)
    c1 = Conv2D(8, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c1)
    p1 = MaxPooling2D((2, 2))(c1)
    
    c2 = Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p1)
    c2 = Dropout(0.1)(c2)
    c2 = Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c2)
    p2 = MaxPooling2D((2, 2))(c2)
    
    c3 = Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p2)
    c3 = Dropout(0.2)(c3)
    c3 = Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c3)
    p3 = MaxPooling2D((2, 2))(c3)
    
    # 桥接层 - 编码器和解码器之间的连接
    c4 = Conv2D(64, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p3)
    c4 = Dropout(0.2)(c4)
    c4 = Conv2D(64, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c4)
    
    # 解码器部分 - 上采样和跨连接
    u5 = Conv2DTranspose(32, (2, 2), strides=(2, 2), padding='same')(c4)
    u5 = concatenate([u5, c3])
    c5 = Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u5)
    c5 = Dropout(0.2)(c5)
    c5 = Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c5)
    
    u6 = Conv2DTranspose(16, (2, 2), strides=(2, 2), padding='same')(c5)
    u6 = concatenate([u6, c2])
    c6 = Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u6)
    c6 = Dropout(0.1)(c6)
    c6 = Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c6)
    
    u7 = Conv2DTranspose(8, (2, 2), strides=(2, 2), padding='same')(c6)
    u7 = concatenate([u7, c1])
    c7 = Conv2D(8, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u7)
    c7 = Dropout(0.1)(c7)
    c7 = Conv2D(8, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c7)
    
    # 输出层
    outputs = Conv2D(1, (1, 1), activation='sigmoid')(c7)
    
    model = Model(inputs=[inputs], outputs=[outputs])
    return model


def model_unet_kaggle(img_hieght, img_width, img_channel, num_classes):
    """
    This function returns a U-Net Model for this binary fire segmentation images:
    Arxiv Link for U-Net: https://arxiv.org/abs/1505.04597
    :param img_hieght: Image Height
    :param img_width: Image Width
    :param img_channel: Number of channels in each image
    :param num_classes: Number of classes based on the Ground Truth Masks
    :return: A convolutional NN based on Tensorflow and Keras
    """
    inputs = Input((img_hieght, img_width, img_channel))
    s = Lambda(lambda x: x / 255)(inputs)

    c1 = Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(s)
    c1 = Dropout(0.1)(c1)
    c1 = Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c1)
    p1 = MaxPooling2D((2, 2))(c1)

    c2 = Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p1)
    c2 = Dropout(0.1)(c2)
    c2 = Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c2)
    p2 = MaxPooling2D((2, 2))(c2)

    c3 = Conv2D(64, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p2)
    c3 = Dropout(0.2)(c3)
    c3 = Conv2D(64, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c3)
    p3 = MaxPooling2D((2, 2))(c3)

    c4 = Conv2D(128, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p3)
    c4 = Dropout(0.2)(c4)
    c4 = Conv2D(128, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c4)
    p4 = MaxPooling2D(pool_size=(2, 2))(c4)

    c5 = Conv2D(256, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p4)
    c5 = Dropout(0.3)(c5)
    c5 = Conv2D(256, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c5)

    u6 = Conv2DTranspose(128, (2, 2), strides=(2, 2), padding='same')(c5)
    u6 = concatenate([u6, c4])
    c6 = Conv2D(128, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u6)
    c6 = Dropout(0.2)(c6)
    c6 = Conv2D(128, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c6)

    u7 = Conv2DTranspose(64, (2, 2), strides=(2, 2), padding='same')(c6)
    u7 = concatenate([u7, c3])
    c7 = Conv2D(64, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u7)
    c7 = Dropout(0.2)(c7)
    c7 = Conv2D(64, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c7)

    u8 = Conv2DTranspose(32, (2, 2), strides=(2, 2), padding='same')(c7)
    u8 = concatenate([u8, c2])
    c8 = Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u8)
    c8 = Dropout(0.1)(c8)
    c8 = Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c8)

    u9 = Conv2DTranspose(16, (2, 2), strides=(2, 2), padding='same')(c8)
    u9 = concatenate([u9, c1], axis=3)
    c9 = Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u9)
    c9 = Dropout(0.1)(c9)
    c9 = Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c9)

    outputs = Conv2D(1, (1, 1), activation='sigmoid')(c9)

    model = Model(inputs=[inputs], outputs=[outputs])
    return model
