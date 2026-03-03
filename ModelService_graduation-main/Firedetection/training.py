"""
#################################
 Training phase after demonstration: This module uses Keras and Tensor flow to train the image classification problem
 for the labeling fire and non-fire data based on the aerial images.
 Training and Validation Data: Item 7 on https://ieee-dataport.org/open-access/flame-dataset-aerial-imagery-pile-burn-detection-using-drones-uavs
 Keras version: 2.4.0
 Tensorflow Version: 2.3.0
 GPU: Nvidia RTX 2080 Ti
 OS: Ubuntu 18.04
#################################
"""

#########################################################
# import libraries

import os.path
import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
import matplotlib.pyplot as plt
from tensorflow.keras import layers
from sklearn.metrics import classification_report

from config import new_size
from plotdata import plot_training, plot_metrics, plot_confusion_matrix, plot_roc_curve
from plotdata import plot_precision_recall_curve, plot_tsne_features, plot_segmentation_test
from config import Config_classification
from checkpoint_utils import get_checkpoint_dir, create_callbacks, save_training_config
from checkpoint_utils import load_model_from_checkpoint, resume_training_from_checkpoint
from checkpoint_utils import find_latest_checkpoint

# 配置GPU使用
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"已检测到 {len(gpus)} 个GPU设备，训练将使用GPU进行")
    except RuntimeError as e:
        print(f"GPU配置错误: {e}")
else:
    print("警告: 未检测到GPU，训练将使用CPU进行，这可能会很慢")

#########################################################
# Global parameters and definition

data_augmentation = keras.Sequential(
        [
            layers.RandomFlip("horizontal"),
            layers.RandomRotation(0.1),
        ]
    )

image_size = (new_size.get('width'), new_size.get('height'))
batch_size = Config_classification.get('batch_size')
save_model_flag = Config_classification.get('Save_Model')
epochs = Config_classification.get('Epochs')

METRICS = [
    keras.metrics.TruePositives(name='tp'),
    keras.metrics.FalsePositives(name='fp'),
    keras.metrics.TrueNegatives(name='tn'),
    keras.metrics.FalseNegatives(name='fn'),
    keras.metrics.Accuracy(name='accuracy'),
    keras.metrics.BinaryAccuracy(name='bin_accuracy'),
    keras.metrics.Precision(name='precision'),
    keras.metrics.Recall(name='recall'),
    keras.metrics.AUC(name='auc')
]


#########################################################
# Function definition

def train_keras(resume=False, checkpoint_dir=None, epochs_override=None):
    """
    训练深度学习模型进行火灾分类，支持断点续训功能和学术级可视化
    
    使用Keras和Tensorflow训练深度神经网络进行无人机航拍图像的火灾分类。支持断点续训，
    生成符合学术论文要求的训练过程可视化，并保存训练过程中的模型检查点。
    
    参数:
        resume: 是否从检查点续训
        checkpoint_dir: 检查点目录，当resume=True时有效
        epochs_override: 如果提供，将覆盖配置文件中的训练轮数
    返回:
        训练历史和模型
    """
    print("【启动火灾检测分类模型训练】")
    print("-" * 50)
    
    # 如果提供了epochs_override，使用该值覆盖配置文件中的轮数设置
    actual_epochs = epochs_override if epochs_override is not None else epochs
    
    # 创建检查点目录
    if resume and checkpoint_dir is None:
        checkpoint_dir = find_latest_checkpoint("classification")
        if not checkpoint_dir:
            print("未找到可用的检查点，将从头开始训练")
            resume = False
    
    if not resume:
        # 创建新的检查点目录
        checkpoint_dir = get_checkpoint_dir("classification")
        print(f"创建新的检查点目录: {checkpoint_dir}")
    else:
        print(f"从检查点续训: {checkpoint_dir}")
    
    # 数据集统计信息
    dir_fire = 'frames/Training/Fire/'
    dir_no_fire = 'frames/Training/No_Fire/'

    # 计算类别权重 (0 is Fire and 1 is NO_Fire)
    fire = len([name for name in os.listdir(dir_fire) if os.path.isfile(os.path.join(dir_fire, name))])
    no_fire = len([name for name in os.listdir(dir_no_fire) if os.path.isfile(os.path.join(dir_no_fire, name))])
    total = fire + no_fire
    weight_for_fire = (1 / fire) * total / 2.0
    weight_for_no_fire = (1 / no_fire) * total / 2.0
    class_weight = {0: weight_for_fire, 1: weight_for_no_fire}

    print("数据集统计:")
    print(f"- 火灾图像: {fire} 张 (权重 {weight_for_fire:.2f})")
    print(f"- 非火灾图像: {no_fire} 张 (权重 {weight_for_no_fire:.2f})")
    print(f"- 总计: {total} 张图像")

    # 加载数据集
    print("加载并准备数据集...")
    train_ds = tf.keras.preprocessing.image_dataset_from_directory(
        "frames/Training", validation_split=0.2, subset="training", seed=1337, 
        image_size=image_size, batch_size=batch_size, shuffle=True,
        label_mode='binary'  # 使用二进制标签，便于ROC/PR曲线计算
    )

    val_ds = tf.keras.preprocessing.image_dataset_from_directory(
        "frames/Training", validation_split=0.2, subset="validation", seed=1337, 
        image_size=image_size, batch_size=batch_size, shuffle=True,
        label_mode='binary'  # 使用二进制标签，便于ROC/PR曲线计算
    )
    
    # 获取类别名称
    class_names = train_ds.class_names
    print(f"类别: {class_names}")

    # 维持原有功能：预览原始图像和数据增强结果
    print("生成训练样本预览...")
    # 绘制原始图像预览
    sample_preview_path = os.path.join(checkpoint_dir, "sample_preview.png")
    plt.figure(figsize=(10, 10))
    for images, labels in train_ds.take(1):
        for i in range(9):
            _ = plt.subplot(3, 3, i+1)
            plt.imshow(images[i].numpy().astype("uint8"))
            plt.title(class_names[int(labels[i][0])])
            plt.axis("off")
    plt.savefig(sample_preview_path, dpi=300, bbox_inches='tight')
    print(f"样本预览已保存至: {sample_preview_path}")
    
    # 绘制数据增强结果预览
    augmented_preview_path = os.path.join(checkpoint_dir, "augmented_preview.png")
    plt.figure(figsize=(10, 10))
    for images, _ in train_ds.take(1):
        for i in range(9):
            augmented_images = data_augmentation(images)
            _ = plt.subplot(3, 3, i+1)
            plt.imshow(augmented_images[i].numpy().astype("uint8"))
            plt.axis("off")
    plt.savefig(augmented_preview_path, dpi=300, bbox_inches='tight')
    print(f"数据增强预览已保存至: {augmented_preview_path}")

    # 设置数据集优化
    train_ds = train_ds.prefetch(buffer_size=batch_size*4)
    val_ds = val_ds.prefetch(buffer_size=batch_size*4)
    
    # 模型构建和训练
    if resume:
        # 从检查点加载模型
        print(f"正在从检查点加载模型...")
        model, config = load_model_from_checkpoint(checkpoint_dir, "classification")
        if model is None:
            # 如果加载失败，创建新模型
            print("加载检查点模型失败，创建新模型...")
            model = make_model_keras(input_shape=image_size + (3,), num_classes=2)
    else:
        # 创建新模型
        print("创建新模型...")
        model = make_model_keras(input_shape=image_size + (3,), num_classes=2)
    
    # 生成并保存模型结构图
    model_plot_path = os.path.join(checkpoint_dir, "model_architecture.png")
    keras.utils.plot_model(model, to_file=model_plot_path, show_shapes=True, show_dtype=True, 
                         show_layer_names=True, rankdir="TB", dpi=150)
    print(f"模型结构图已保存至: {model_plot_path}")
    
    # 模型汇总
    model.summary()
    
    # 保存训练配置
    config_dict = {
        "image_size": image_size,
        "batch_size": batch_size,
        "epochs": actual_epochs,
        "class_names": class_names,
        "class_weights": {"0": float(weight_for_fire), "1": float(weight_for_no_fire)},
        "train_samples": fire + no_fire,
        "model_params": {"layers": len(model.layers)}
    }
    save_training_config(checkpoint_dir, "classification", **config_dict)
    
    # 编译模型
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3), 
        loss="binary_crossentropy", 
        metrics=METRICS
    )
    
    # 从配置文件获取是否使用早停机制
    use_early_stopping = Config_classification.get('UseEarlyStopping', False)
    
    # 创建回调函数
    callbacks = create_callbacks(
        checkpoint_dir=checkpoint_dir,
        monitor='val_loss',
        patience=5,
        save_best_only=True,
        use_early_stopping=use_early_stopping
    )
    
    # 显示训练设置信息
    print("训练设置:")
    print(f"- 总训练轮次: {actual_epochs}")
    print(f"- 是否使用早停: {'是' if use_early_stopping else '否 (将训练完整的' + str(actual_epochs) + '个轮次)'}")
    
    # 训练模型
    print(f"开始训练模型 ({actual_epochs} 个轮次)...")
    history = model.fit(
        train_ds, 
        epochs=actual_epochs, 
        callbacks=callbacks, 
        validation_data=val_ds, 
        class_weight=class_weight, 
        verbose=1
    )

    # 保存模型和训练结果可视化
    layers_len = len(model.layers)
    
    # 保存最终模型
    final_model_path = os.path.join(checkpoint_dir, "final_model.h5")
    model.save(final_model_path)
    print(f"最终模型已保存至: {final_model_path}")
    
    # 如果配置中设置了保存模型，也保存到原本的路径
    if save_model_flag:
        file_model_fire = 'Output/Models/model_fire_resnet_weighted_40_no_metric_simple'
        model.save(file_model_fire)
        print(f"模型同时已保存至: {file_model_fire}")
    
    # 生成训练过程可视化图表
    print("\n生成学术级可视化结果...")
    print("-" * 50)
    
    # 绘制训练曲线（损失和准确率）
    plot_training(history, 'FireClassifier', layers_len)
    
    # 绘制所有训练指标的详细图表
    plot_metrics(history)
    
    # 评估模型在验证集上的性能
    print("\n评估模型在验证集上的性能...")
    y_pred_prob = []
    y_true = []
    
    # 收集验证集上的预测和真实标签
    for images, labels in val_ds:
        pred = model.predict(images, verbose=0)
        y_pred_prob.extend(pred)
        y_true.extend(labels.numpy())
    
    y_pred_prob = np.array(y_pred_prob)
    y_true = np.array(y_true)
    y_pred = (y_pred_prob > 0.5).astype(int)
    
    # 绘制混淆矩阵
    print("生成混淆矩阵...")
    plot_confusion_matrix(y_true, y_pred, class_names, 
                         save_path=os.path.join(checkpoint_dir, "confusion_matrix"))
    
    # 绘制ROC曲线
    print("生成ROC曲线...")
    plot_roc_curve(y_true, y_pred_prob, class_names, 
                 save_path=os.path.join(checkpoint_dir, "roc_curve"))
    
    # 绘制精确率-召回率曲线
    print("生成PR曲线...")
    plot_precision_recall_curve(y_true, y_pred_prob, class_names, 
                               save_path=os.path.join(checkpoint_dir, "pr_curve"))
    
    # 生成分类报告并保存
    print("\n分类报告:")
    report = classification_report(y_true, y_pred, target_names=class_names)
    print(report)
    
    # 保存分类报告到文件
    report_path = os.path.join(checkpoint_dir, "classification_report.txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"分类报告已保存至: {report_path}")
    
    # 在测试样例上进行预测展示
    print("\n在单个测试样本上展示预测结果...")
    try:
        test_img_path = "frames/Training/Fire/resized_frame1801.jpg"
        img = keras.preprocessing.image.load_img(test_img_path, target_size=image_size)
        img_array = keras.preprocessing.image.img_to_array(img)
        img_array = tf.expand_dims(img_array, 0)
        predictions = model.predict(img_array, verbose=0)
        score = predictions[0][0]
        
        # 保存预测结果图
        plt.figure(figsize=(8, 8))
        plt.imshow(img)
        plt.title(f"预测结果: {class_names[int(score > 0.5)]} ({100 * abs(1 - score if score > 0.5 else score):.2f}%)", fontsize=14)
        plt.axis('off')
        
        sample_predict_path = os.path.join(checkpoint_dir, "sample_prediction.png")
        plt.savefig(sample_predict_path, dpi=300, bbox_inches='tight')
        print(f"样本预测图已保存至: {sample_predict_path}")
        print(f"预测结果: 该图像是 {100 * (1 - score):.2f}% 的火灾和 {100 * score:.2f}% 的非火灾")
    except Exception as e:
        print(f"样本预测生成失败: {e}")
    
    print("\n训练和评估完成! 所有结果已保存在:")
    print(f"- {checkpoint_dir}")
    
    return history, model


def make_model_keras(input_shape, num_classes):
    """
    This function define the DNN Model based on the Keras example.
    :param input_shape: The requested size of the image
    :param num_classes: In this classification problem, there are two classes: 1) Fire and 2) Non_Fire.
    :return: The built model is returned
    """
    inputs = keras.Input(shape=input_shape)
    # x = data_augmentation(inputs)  # 1) First option
    x = inputs  # 2) Second option

    x = layers.Rescaling(1.0 / 255)(x)
    # x = layers.Conv2D(32, 3, strides=2, padding="same")(x)
    x = layers.Conv2D(8, 3, strides=2, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)

    previous_block_activation = x

    # for size in [128, 256, 512, 728]:
    for size in [8]:
        x = layers.Activation("relu")(x)
        x = layers.SeparableConv2D(size, 3, padding="same")(x)
        x = layers.BatchNormalization()(x)

        x = layers.Activation("relu")(x)
        x = layers.SeparableConv2D(size, 3, padding="same")(x)
        x = layers.BatchNormalization()(x)

        x = layers.MaxPooling2D(3, strides=2, padding="same")(x)

        residual = layers.Conv2D(size, 1, strides=2, padding="same")(previous_block_activation)

        x = layers.add([x, residual])
        previous_block_activation = x
    x = layers.SeparableConv2D(8, 3, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)

    x = layers.GlobalAveragePooling2D()(x)
    if num_classes == 2:
        activation = "sigmoid"
        units = 1
    else:
        activation = "softmax"
        units = num_classes

    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(units, activation=activation)(x)
    return keras.Model(inputs, outputs, name="model_fire")
