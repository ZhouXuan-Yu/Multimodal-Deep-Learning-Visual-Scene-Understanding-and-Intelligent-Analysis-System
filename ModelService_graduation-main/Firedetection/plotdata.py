"""
#################################
# 学术级可视化函数库 - 用于深度学习模型训练与评估
# Academic Visualization Library - For Deep Learning Model Training and Evaluation
#################################
"""
#########################################################
# import libraries

import os
import pickle
import itertools
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as style
from matplotlib.ticker import MaxNLocator
from sklearn.metrics import confusion_matrix, roc_curve, precision_recall_curve, auc
from sklearn.manifold import TSNE
import tensorflow as tf

# 设置全局可视化参数，以符合学术论文要求
# Set global visualization parameters to meet academic paper requirements
style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 300  # 高分辨率输出
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
plt.rcParams['mathtext.fontset'] = 'stix'

def ensure_output_dirs():
    """确保输出目录存在，如果不存在则创建"""
    os.makedirs('Output/FigureObject', exist_ok=True)
    os.makedirs('Output/Figures', exist_ok=True)
    os.makedirs('Output/Models', exist_ok=True)
    os.makedirs('Output/Evaluation', exist_ok=True)
    os.makedirs('Output/Checkpoints', exist_ok=True)
    os.makedirs('Output/Features', exist_ok=True)
    os.makedirs('Output/SamplePredictions', exist_ok=True)


#########################################################
# Function definition

def plot_training(result, type_model, layers_len):
    """
    绘制训练过程中的损失和准确率曲线，符合学术论文标准
    
    参数:
        result: 模型训练的历史记录
        type_model: 模型类型名称
        layers_len: 模型层数
    """
    ensure_output_dirs()
    
    # 创建具有学术风格的图形
    (fig, ax) = plt.subplots(2, 1, figsize=(12, 10))
    epochs = len(result.history['accuracy']) if 'accuracy' in result.history else len(result.history['loss'])
    epoch_range = np.arange(1, epochs+1)
    
    # 绘制损失曲线
    ax[0].set_title("Training and Validation Loss", fontsize=16, fontweight='bold')
    ax[0].set_xlabel("Epochs", fontsize=14, fontweight="bold")
    ax[0].set_ylabel("Loss", fontsize=14, fontweight="bold")
    ax[0].plot(epoch_range, result.history['loss'], label='Training Loss', linewidth=2.5, linestyle='-', 
               marker='o', markersize=8, color='#E41A1C')
    ax[0].plot(epoch_range, result.history['val_loss'], label='Validation Loss', linewidth=2.5, 
               linestyle='--', marker='s', markersize=8, color='#377EB8')
    ax[0].grid(True, linestyle='--', alpha=0.7)
    ax[0].legend(prop={'size': 12, 'weight': 'bold'}, frameon=True, fancybox=True, framealpha=0.8, 
                 shadow=True, loc='upper right')
    ax[0].tick_params(axis='both', which='major', labelsize=12)
    ax[0].spines['top'].set_visible(False)
    ax[0].spines['right'].set_visible(False)
    ax[0].xaxis.set_major_locator(MaxNLocator(integer=True))

    plt.subplots_adjust(hspace=0.3)

    # 确定要使用的准确率指标 - 适应不同的历史记录格式
    acc_metric = 'bin_accuracy' if 'bin_accuracy' in result.history else 'accuracy'
    val_acc_metric = 'val_bin_accuracy' if 'val_bin_accuracy' in result.history else 'val_accuracy'
    
    # 绘制准确率曲线
    ax[1].set_title("Training and Validation Accuracy", fontsize=16, fontweight="bold")
    ax[1].set_xlabel("Epochs", fontsize=14, fontweight="bold")
    ax[1].set_ylabel("Accuracy", fontsize=14, fontweight="bold")
    ax[1].plot(epoch_range, result.history[acc_metric], label='Training Accuracy', linewidth=2.5, 
               linestyle='-', marker='o', markersize=8, color='#E41A1C')
    ax[1].plot(epoch_range, result.history[val_acc_metric], label='Validation Accuracy', 
               linewidth=2.5, linestyle='--', marker='s', markersize=8, color='#377EB8')
    ax[1].grid(True, linestyle='--', alpha=0.7)
    ax[1].legend(prop={'size': 12, 'weight': 'bold'}, frameon=True, fancybox=True, framealpha=0.8, 
                 shadow=True, loc='lower right')
    ax[1].tick_params(axis='both', which='major', labelsize=12)
    ax[1].spines['top'].set_visible(False)
    ax[1].spines['right'].set_visible(False)
    ax[1].xaxis.set_major_locator(MaxNLocator(integer=True))
    
    # 添加水印标记
    fig.text(0.95, 0.05, f'UAV Fire Detection - {type_model}', 
             fontsize=10, color='gray', ha='right', va='bottom', alpha=0.5)
    
    # 保存图形
    timestamp = f"{tf.timestamp():.0f}"
    file_figobj = f'Output/FigureObject/{type_model}_{epochs}_EPOCH_{layers_len}_layers_{timestamp}.fig.pickle'
    file_pdf = f'Output/Figures/{type_model}_{epochs}_EPOCH_{layers_len}_layers_{timestamp}.pdf'
    file_png = f'Output/Figures/{type_model}_{epochs}_EPOCH_{layers_len}_layers_{timestamp}.png'

    pickle.dump(fig, open(file_figobj, 'wb'))
    fig.savefig(file_pdf, bbox_inches='tight', dpi=300)
    fig.savefig(file_png, bbox_inches='tight', dpi=300)
    
    print(f"训练曲线已保存至:\n- {file_pdf}\n- {file_png}")


def plot_metrics(history):
    """
    绘制多个指标的学术级可视化分析图
    
    参数:
        history: 模型训练的历史记录
    返回:
        保存文件的路径列表
    """
    ensure_output_dirs()
    
    # 选择要绘制的指标，根据历史记录中可用的内容调整
    available_metrics = [metric for metric in ['loss', 'auc', 'precision', 'recall', 'accuracy', 'bin_accuracy']
                         if metric in history.history]
    epochs = len(history.history[available_metrics[0]])
    
    # 定义学术风格的颜色方案
    colors = ['#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00', '#FFFF33']
    
    # 根据可用指标数量调整图表布局
    n_metrics = len(available_metrics)
    fig_width = min(20, n_metrics * 4)
    (fig, ax) = plt.subplots(1, n_metrics, figsize=(fig_width, 5), constrained_layout=True)
    
    if n_metrics == 1:
        ax = [ax]  # 保证ax是一个列表
    
    # 绘制每个指标
    for n, metric in enumerate(available_metrics):
        name = metric.replace("_", " ").capitalize()
        
        # 设置图表样式
        ax[n].set_title(f"{name} over Epochs", fontsize=14, fontweight="bold")
        ax[n].plot(np.arange(1, epochs+1), history.history[metric], linewidth=2, linestyle='-', 
               marker='o', markersize=5, color=colors[n % len(colors)], label='Training')
        
        if f'val_{metric}' in history.history:
            ax[n].plot(np.arange(1, epochs+1), history.history[f'val_{metric}'], linewidth=2, 
                   linestyle='--', marker='s', markersize=5, color=colors[(n+1) % len(colors)], 
                   label='Validation')
        
        # 美化图表
        ax[n].grid(True, linestyle='--', alpha=0.7)
        ax[n].set_xlabel("Epochs", fontsize=12, fontweight="bold")
        ax[n].set_ylabel(name, fontsize=12, fontweight="bold")
        ax[n].legend(frameon=True, fancybox=True, framealpha=0.8, shadow=True, loc='best')
        ax[n].tick_params(axis='both', which='major', labelsize=10)
        ax[n].spines['top'].set_visible(False)
        ax[n].spines['right'].set_visible(False)
        ax[n].xaxis.set_major_locator(MaxNLocator(integer=True))
    
    # 添加水印
    timestamp = f"{tf.timestamp():.0f}"
    plt.figtext(0.99, 0.01, f'UAV Fire Detection - {timestamp}', 
              fontsize=8, color='gray', ha='right')
    
    # 保存图表
    file_figobj = f'Output/FigureObject/Metric_{epochs}_EPOCH_{timestamp}.fig.pickle'
    file_pdf = f'Output/Figures/Metric_{epochs}_EPOCH_{timestamp}.pdf'
    file_png = f'Output/Figures/Metric_{epochs}_EPOCH_{timestamp}.png'

    pickle.dump(fig, open(file_figobj, 'wb'))
    fig.savefig(file_pdf, bbox_inches='tight', dpi=300)
    fig.savefig(file_png, bbox_inches='tight', dpi=300)
    
    print(f"训练指标可视化已保存至:\n- {file_pdf}\n- {file_png}")
    
    return [file_pdf, file_png]


def plot_confusion_matrix(y_true, y_pred, classes, normalize=False, title='Confusion matrix', cmap=plt.cm.Blues, save_path=None, timestamp=None):
    """
    绘制并保存符合学术要求的混淆矩阵可视化图
    
    参数:
        y_true: 真实标签
        y_pred: 预测标签
        classes: 类别名称列表
        normalize: 是否标准化混淆矩阵
        title: 图表标题
        cmap: 颜色映射
        save_path: 保存路径
        timestamp: 时间戳
    """
    ensure_output_dirs()
    
    # 计算混淆矩阵
    cm = confusion_matrix(y_true, y_pred)
    
    # 创建高品质图表
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        im = ax.imshow(cm, interpolation='nearest', cmap=cmap, vmin=0, vmax=1)
        title = f'Normalized {title}'
        print("Normalized confusion matrix")
    else:
        im = ax.imshow(cm, interpolation='nearest', cmap=cmap)
        print('Confusion matrix, without normalization')

    # 所有行列的加和
    print(cm)
    
    # 设置图表标题和标签
    ax.set_title(title, fontsize=16, fontweight='bold')
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=10)
    
    # 设置刻度标签
    tick_marks = np.arange(len(classes))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(classes, rotation=45, ha='right', fontsize=10)
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(classes, fontsize=10)
    
    # 添加文本标签
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        value = cm[i, j]
        value_text = f'{value:.2f}' if normalize else f'{value:d}'
        ax.text(j, i, value_text, horizontalalignment="center", verticalalignment="center",
                color="white" if cm[i, j] > thresh else "black", fontsize=10, fontweight='bold')

    # 设置轴标签
    ax.set_ylabel('True Label', fontsize=12, fontweight='bold')
    ax.set_xlabel('Predicted Label', fontsize=12, fontweight='bold')
    
    # 添加网格线
    ax.set_xticks(np.arange(-.5, len(classes), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(classes), 1), minor=True)
    ax.grid(which='minor', color='gray', linestyle=':', linewidth=0.5, alpha=0.3)
    
    # 调整布局
    plt.tight_layout()
    
    # 生成时间戳
    if timestamp is None:
        timestamp = f"{tf.timestamp():.0f}"
    
    # 添加水印
    fig.text(0.99, 0.01, f'UAV Fire Detection - {timestamp}', 
             fontsize=8, color='gray', ha='right', va='bottom', alpha=0.7)
    
    # 保存文件
    if save_path is None:
        file_pdf = f'Output/Figures/confusion_matrix_{timestamp}.pdf'
        file_png = f'Output/Figures/confusion_matrix_{timestamp}.png'
    else:
        file_pdf = f'{save_path}_confusion_matrix.pdf'
        file_png = f'{save_path}_confusion_matrix.png'
    
    fig.savefig(file_pdf, bbox_inches='tight', dpi=300)
    fig.savefig(file_png, bbox_inches='tight', dpi=300)
    print(f"混淆矩阵可视化已保存至:\n- {file_pdf}\n- {file_png}")
    
    return fig, [file_pdf, file_png]


def plot_roc_curve(y_true, y_score, classes=None, title='Receiver Operating Characteristic (ROC) Curve', save_path=None, timestamp=None):
    """
    绘制学术级的ROC曲线
    
    参数:
        y_true: 真实标签
        y_score: 模型预测的概率值
        classes: 类别名称列表
        title: 图表标题
        save_path: 保存路径前缀
        timestamp: 时间戳
    返回:
        图表对象和文件路径列表
    """
    ensure_output_dirs()
    
    # 生成时间戳
    if timestamp is None:
        timestamp = f"{tf.timestamp():.0f}"
    
    # 创建高品质图表
    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    
    # 计算ROC曲线和auc
    if y_score.ndim == 1:
        # 二分类情况
        fpr, tpr, thresholds = roc_curve(y_true, y_score)
        roc_auc = auc(fpr, tpr)
        
        # 绘制ROC曲线
        ax.plot(fpr, tpr, color='#E41A1C', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
        
    else:
        # 多分类情况
        n_classes = y_score.shape[1]
        
        # 设置颜色方案
        colors = plt.cm.tab10(np.linspace(0, 1, n_classes))
        
        # 如果没有提供类别名称，创建默认名称
        if classes is None:
            classes = [f'Class {i}' for i in range(n_classes)]
        
        for i, (color, cls) in enumerate(zip(colors, classes)):
            fpr, tpr, _ = roc_curve(y_true == i, y_score[:, i])
            roc_auc = auc(fpr, tpr)
            ax.plot(fpr, tpr, color=color, lw=2, label=f'{cls} (AUC = {roc_auc:.3f})')
    
    # 绘制随机猿线
    ax.plot([0, 1], [0, 1], 'k--', lw=1.5, color='gray', alpha=0.7)
    
    # 设置图表属性
    ax.set_xlim([-0.01, 1.01])
    ax.set_ylim([-0.01, 1.01])
    ax.set_xlabel('False Positive Rate', fontsize=12, fontweight='bold')
    ax.set_ylabel('True Positive Rate', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(loc="lower right", fontsize=10, frameon=True, fancybox=True, framealpha=0.8, shadow=True)
    
    # 美化图表
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 添加水印
    fig.text(0.99, 0.01, f'UAV Fire Detection - {timestamp}', 
             fontsize=8, color='gray', ha='right', va='bottom', alpha=0.7)
    
    # 保存文件
    if save_path is None:
        file_pdf = f'Output/Figures/ROC_curve_{timestamp}.pdf'
        file_png = f'Output/Figures/ROC_curve_{timestamp}.png'
    else:
        file_pdf = f'{save_path}_ROC_curve.pdf'
        file_png = f'{save_path}_ROC_curve.png'
    
    fig.savefig(file_pdf, bbox_inches='tight', dpi=300)
    fig.savefig(file_png, bbox_inches='tight', dpi=300)
    print(f"ROC曲线可视化已保存至:\n- {file_pdf}\n- {file_png}")
    
    return fig, [file_pdf, file_png]


def plot_precision_recall_curve(y_true, y_score, classes=None, title='Precision-Recall Curve', save_path=None, timestamp=None):
    """
    绘制学术级的精确率-召回率曲线
    
    参数:
        y_true: 真实标签
        y_score: 模型预测的概率值
        classes: 类别名称列表
        title: 图表标题
        save_path: 保存路径前缀
        timestamp: 时间戳
    返回:
        图表对象和文件路径列表
    """
    ensure_output_dirs()
    
    # 生成时间戳
    if timestamp is None:
        timestamp = f"{tf.timestamp():.0f}"
    
    # 创建高品质图表
    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    
    # 计算PR曲线
    if y_score.ndim == 1:
        # 二分类情况
        precision, recall, thresholds = precision_recall_curve(y_true, y_score)
        pr_auc = auc(recall, precision)
        
        # 绘制PR曲线
        ax.plot(recall, precision, color='#4DAF4A', lw=2, label=f'PR curve (AUC = {pr_auc:.3f})')
        
    else:
        # 多分类情况
        n_classes = y_score.shape[1]
        
        # 设置颜色方案
        colors = plt.cm.tab10(np.linspace(0, 1, n_classes))
        
        # 如果没有提供类别名称，创建默认名称
        if classes is None:
            classes = [f'Class {i}' for i in range(n_classes)]
        
        for i, (color, cls) in enumerate(zip(colors, classes)):
            precision, recall, _ = precision_recall_curve(y_true == i, y_score[:, i])
            pr_auc = auc(recall, precision)
            ax.plot(recall, precision, color=color, lw=2, label=f'{cls} (AUC = {pr_auc:.3f})')
    
    # 设置图表属性
    ax.set_xlim([-0.01, 1.01])
    ax.set_ylim([-0.01, 1.01])
    ax.set_xlabel('Recall', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precision', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(loc="lower left", fontsize=10, frameon=True, fancybox=True, framealpha=0.8, shadow=True)
    
    # 美化图表
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 添加水印
    fig.text(0.99, 0.01, f'UAV Fire Detection - {timestamp}', 
             fontsize=8, color='gray', ha='right', va='bottom', alpha=0.7)
    
    # 保存文件
    if save_path is None:
        file_pdf = f'Output/Figures/PR_curve_{timestamp}.pdf'
        file_png = f'Output/Figures/PR_curve_{timestamp}.png'
    else:
        file_pdf = f'{save_path}_PR_curve.pdf'
        file_png = f'{save_path}_PR_curve.png'
    
    fig.savefig(file_pdf, bbox_inches='tight', dpi=300)
    fig.savefig(file_png, bbox_inches='tight', dpi=300)
    print(f"精确率-召回率曲线可视化已保存至:\n- {file_pdf}\n- {file_png}")
    
    return fig, [file_pdf, file_png]


def plot_scheduling():
    obs_int_flight_40 = [5.3589, 5.3589, 5.2759, 4.851, 5.33, 5.29, 2.74, 2.74, 4.25, 2.69, 4.235, 3.292, 3.13, 2.668,
                         1.806, 0.987, 0.987, 0.987, 0.987, 0.987, 0.987]
    obs_int_flight_50 = [5.26, 5.26, 5.23, 4.431, 5.223, 5.104, 3.542, 4.785, 4.785, 2.617, 2.617, 2.617, 2.617, 2.617,
                         2.617, 0.991, 0.991, 0.991, 0.991, 0.991, 0.991]
    obs_int_flight_60 = [5.187, 5.187, 5.437, 5.395, 4.466, 4.466, 5.133, 3.327, 4.212, 1.813, 2.516, 2.516, 2.516,
                         2.397, 2.055, 0.992, 0.992, 0.992, 0.992, 0.992, 0.992]

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111)
    ax.grid(True)
    ax.set_xlabel("Observation Interval (min)", size=12, fontweight="bold")
    ax.set_ylabel("Number of required UAVs", size=12, fontweight="bold")
    ax.plot(np.arange(5, 26), obs_int_flight_40, color="blue", linestyle='-', linewidth=2, label="Flight time: 40min",
            marker='o', markersize=8)

    ax.plot(np.arange(5, 26), obs_int_flight_50, color="red", linestyle='--', linewidth=2, label="Flight time: 50min",
            marker='+', markersize='8')

    ax.plot(np.arange(5, 26), obs_int_flight_60, color="black", linestyle='-', linewidth=2,
            label="Flight time: 60min", marker='+', markersize='8')

    ax.legend(loc='best')
    fig.canvas.draw()

    file_figobj = 'Output/FigureObject/required_UAV.fig.pickle' % ()
    file_pdf = 'Output/Figures/required_UAV.pdf' % ()
    pickle.dump(fig, open(file_figobj, 'wb'))
    fig.savefig(file_pdf, bbox_inches='tight')

    plt.show()


def plot_interval(pile_times):
    number_piles = len(pile_times)
    interval_output = [[] for _ in range(0, number_piles)]
    for i in range(0, number_piles):
        interval_output[i] = [t - s for s, t in zip(pile_times[i], pile_times[i][1:])]

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111)
    ax.grid(True)
    ax.set_xlabel("Number of observations", size=12, fontweight="bold")
    ax.set_ylabel("Consecutive interval for observation (min)", size=12, fontweight="bold")

    ax.plot(np.arange(1, len(interval_output[0])+1), interval_output[0], color="blue", linestyle='--', linewidth=2,
            label="First Pile", marker='o', markersize=8)

    ax.plot(np.arange(1, len(interval_output[1])+1), interval_output[1], color="red", linestyle='--', linewidth=2,
            label="Second Pile", marker='X', markersize=8)

    ax.plot(np.arange(1, len(interval_output[2])+1), interval_output[2], color="black", linestyle='--', linewidth=2,
            label="Third Pile", marker='P', markersize=8)

    ax.plot(np.arange(1, len(interval_output[3])+1), interval_output[3], color="green", linestyle='--', linewidth=2,
            label="Fourth Pile", marker='*', markersize=8)

    ax.plot(np.arange(1, len(interval_output[4])+1), interval_output[4], color="magenta", linestyle='--', linewidth=2,
            label="Fifth Pile", marker='+', markersize=8)

    ax.plot(np.arange(1, len(interval_output[4])+1), interval_output[4], color="brown", linestyle='--', linewidth=2,
            label="Sixth Pile", marker='s', markersize=8)

    ax.legend(loc='best')
    fig.canvas.draw()

    file_figobj = 'Output/FigureObject/Consecutive_interval.fig.pickle' % ()
    file_pdf = 'Output/Figures/Consecutive_interval.pdf' % ()
    pickle.dump(fig, open(file_figobj, 'wb'))
    fig.savefig(file_pdf, bbox_inches='tight')

    plt.show()


def plot_segmentation_test(xval, yval, ypred, num_samples=6, save_path=None, timestamp=None):
    """
    绘制分割模型的预测结果对比可视化，符合学术论文要求
    
    参数:
        xval: 原始图像
        yval: 真实标签掛码
        ypred: 模型预测的分割掛码
        num_samples: 要展示的样本数量
        save_path: 保存路径前缀
        timestamp: 时间戳
    返回:
        图表对象和文件路径列表
    """
    ensure_output_dirs()
    
    # 生成时间戳
    if timestamp is None:
        timestamp = f"{tf.timestamp():.0f}"
    
    # 创建高质量图表
    fig = plt.figure(figsize=(16, 12), dpi=300)
    
    # 生成随机索引以保证可重复性
    np.random.seed(42)
    indices = np.random.randint(0, len(ypred), num_samples)
    
    # 定义子图标题和颜色映射
    titles = ['Input Image', 'Ground Truth Mask', 'Predicted Mask']
    cmaps = [None, 'viridis', 'viridis']
    
    # 绘制每个样本
    for i, idx in enumerate(indices):
        # 原始图像
        ax1 = plt.subplot(3, num_samples, (0 * num_samples) + i + 1)
        ax1.imshow(xval[idx])
        if i == 0:
            ax1.set_ylabel(titles[0], fontsize=14, fontweight='bold')
        ax1.set_title(f'Sample {i+1}', fontsize=10)
        ax1.axis('off')
        
        # 真实掛码
        ax2 = plt.subplot(3, num_samples, (1 * num_samples) + i + 1)
        gt_mask = np.squeeze(yval[idx])
        ax2.imshow(gt_mask, cmap=cmaps[1])
        if i == 0:
            ax2.set_ylabel(titles[1], fontsize=14, fontweight='bold')
        
        # 计算IoU
        binary_gt = gt_mask > 0.5
        binary_pred = np.squeeze(ypred[idx]) > 0.5
        intersection = np.logical_and(binary_gt, binary_pred).sum()
        union = np.logical_or(binary_gt, binary_pred).sum()
        iou = intersection / union if union > 0 else 0
        
        ax2.axis('off')
        
        # 预测掛码
        ax3 = plt.subplot(3, num_samples, (2 * num_samples) + i + 1)
        pred_mask = np.squeeze(ypred[idx])
        ax3.imshow(pred_mask, cmap=cmaps[2])
        if i == 0:
            ax3.set_ylabel(titles[2], fontsize=14, fontweight='bold')
        ax3.set_title(f'IoU: {iou:.3f}', fontsize=10)
        ax3.axis('off')
    
    # 调整布局
    plt.subplots_adjust(wspace=0.05, hspace=0.2)
    
    # 添加全局标题
    plt.suptitle('Fire Segmentation Results - Validation Set', fontsize=16, fontweight='bold', y=0.98)
    
    # 添加说明文本
    fig.text(0.5, 0.01, 'Visualization of Ground Truth vs. Predicted Segmentation Masks', 
             ha='center', va='bottom', fontsize=12)
    
    # 添加水印
    fig.text(0.99, 0.01, f'UAV Fire Detection - {timestamp}', 
             fontsize=8, color='gray', ha='right', va='bottom', alpha=0.7)
    
    # 保存图表
    if save_path is None:
        file_figobj = f'Output/FigureObject/segmentation_results_{timestamp}.fig.pickle'
        file_pdf = f'Output/Figures/segmentation_results_{timestamp}.pdf'
        file_png = f'Output/Figures/segmentation_results_{timestamp}.png'
    else:
        file_figobj = f'{save_path}_segmentation_results.fig.pickle'
        file_pdf = f'{save_path}_segmentation_results.pdf'
        file_png = f'{save_path}_segmentation_results.png'
    
    pickle.dump(fig, open(file_figobj, 'wb'))
    fig.savefig(file_pdf, bbox_inches='tight', dpi=300)
    fig.savefig(file_png, bbox_inches='tight', dpi=300)
    print(f"分割结果可视化已保存至:\n- {file_pdf}\n- {file_png}")
    
    return fig, [file_pdf, file_png]


def plot_tsne_features(features, labels, class_names=None, title='t-SNE Feature Visualization', save_path=None, timestamp=None):
    """
    使用t-SNE对模型提取的特征进行可视化，用于学术论文
    
    参数:
        features: 特征矩阵 [n_samples, n_features]
        labels: 类别标签 [n_samples,]
        class_names: 类别名称列表
        title: 图表标题
        save_path: 保存路径前缀
        timestamp: 时间戳
    返回:
        图表对象和文件路径列表
    """
    ensure_output_dirs()
    
    # 生成时间戳
    if timestamp is None:
        timestamp = f"{tf.timestamp():.0f}"
    
    # 离申式多维缩放 (t-SNE)
    print("Computing t-SNE embedding...")
    tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(features) - 1))
    features_tsne = tsne.fit_transform(features)
    
    # 获取唯一类别
    unique_labels = np.unique(labels)
    n_classes = len(unique_labels)
    
    # 设置颜色和标记
    colors = plt.cm.tab10(np.linspace(0, 1, n_classes))
    markers = ['o', 's', 'D', '^', 'v', '<', '>', 'p', '*', 'h']
    
    # 类别名称
    if class_names is None:
        class_names = [f'Class {i}' for i in unique_labels]
    
    # 创建高品质图表
    fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
    
    # 绘制每个类别的数据点
    for i, (label, color, marker) in enumerate(zip(unique_labels, colors, markers[:n_classes])):
        mask = (labels == label)
        ax.scatter(
            features_tsne[mask, 0], features_tsne[mask, 1],
            c=[color], label=class_names[i], marker=marker,
            alpha=0.7, s=50, edgecolors='k', linewidths=0.5
        )
    
    # 设置图表属性
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_xlabel('t-SNE Dimension 1', fontsize=14, fontweight='bold')
    ax.set_ylabel('t-SNE Dimension 2', fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 添加图例和水印
    legend = ax.legend(loc='best', fontsize=12, markerscale=1.5, frameon=True, 
                 fancybox=True, framealpha=0.8, shadow=True)
    legend.get_frame().set_facecolor('white')
    
    # 添加水印
    fig.text(0.99, 0.01, f'UAV Fire Detection - {timestamp}', 
             fontsize=8, color='gray', ha='right', va='bottom', alpha=0.7)
    
    # 保存图表
    if save_path is None:
        file_pdf = f'Output/Figures/tsne_features_{timestamp}.pdf'
        file_png = f'Output/Figures/tsne_features_{timestamp}.png'
        file_data = f'Output/Features/tsne_features_{timestamp}.npz'
    else:
        file_pdf = f'{save_path}_tsne_features.pdf'
        file_png = f'{save_path}_tsne_features.png'
        file_data = f'{save_path}_tsne_features.npz'
    
    # 保存图片和坐标数据
    fig.savefig(file_pdf, bbox_inches='tight', dpi=300)
    fig.savefig(file_png, bbox_inches='tight', dpi=300)
    np.savez(file_data, features_tsne=features_tsne, labels=labels, class_names=class_names)
    print(f"t-SNE特征可视化已保存至:\n- {file_pdf}\n- {file_png}\n- {file_data} (坐标数据)")
    
    return fig, [file_pdf, file_png, file_data]
