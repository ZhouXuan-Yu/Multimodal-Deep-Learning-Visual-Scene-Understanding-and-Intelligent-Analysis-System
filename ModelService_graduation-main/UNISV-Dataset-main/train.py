"""
训练脚本，用于训练红外视频行为识别模型
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.cuda.amp import GradScaler, autocast
import numpy as np
import time
import json
from datetime import datetime
from tqdm import tqdm
import matplotlib
matplotlib.use('Agg')  # 设置为非交互式后端
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
import seaborn as sns

from config import *
from data_loader import get_dataloaders
from models import get_model
from utils import EarlyStopping, LabelSmoothingLoss, FocalLoss


def train_model(train_loader, val_loader, test_loader, model, criterion, optimizer, 
                scheduler=None, num_epochs=NUM_EPOCHS, device='cuda', 
                save_dir=SAVE_DIR, early_stopping_patience=EARLY_STOPPING_PATIENCE,
                mixed_precision=USE_MIXED_PRECISION):
    """训练模型函数"""
    
    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)
    
    # 初始化早停
    early_stopping = EarlyStopping(patience=early_stopping_patience, verbose=True, 
                                  path=os.path.join(save_dir, 'best_model.pth'))
    
    # 初始化混合精度训练的scaler
    scaler = GradScaler() if mixed_precision else None
    
    # 记录训练和验证的损失和准确率
    history = {
        'train_loss': [], 'train_acc': [],
        'val_loss': [], 'val_acc': []
    }
    
    best_acc = 0.0  # 记录最佳准确率
    
    # 开始训练
    start_time = time.time()
    
    for epoch in range(num_epochs):
        print(f'Epoch {epoch+1}/{num_epochs}')
        print('-' * 10)
        
        # 训练阶段
        model.train()
        train_loss = 0.0
        train_corrects = 0
        train_samples = 0
        
        # 使用tqdm创建进度条
        train_bar = tqdm(train_loader, desc=f"Training Epoch {epoch+1}")
        
        for inputs, labels in train_bar:
            inputs = inputs.to(device)
            labels = labels.to(device)
            
            # 清零梯度
            optimizer.zero_grad()
            
            # 前向传播
            with autocast() if mixed_precision else torch.no_grad():
                outputs = model(inputs)
                loss = criterion(outputs, labels)
            
            # 反向传播和优化
            if mixed_precision:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()
            
            # 统计
            train_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            train_corrects += torch.sum(preds == labels.data)
            train_samples += inputs.size(0)
            
            # 更新进度条
            train_bar.set_postfix({
                'loss': loss.item(),
                'acc': (torch.sum(preds == labels.data) / inputs.size(0)).item()
            })
        
        if scheduler is not None:
            scheduler.step()
        
        epoch_train_loss = train_loss / train_samples
        epoch_train_acc = train_corrects.double() / train_samples
        
        # 验证阶段
        model.eval()
        val_loss = 0.0
        val_corrects = 0
        val_samples = 0
        
        val_preds = []
        val_labels_list = []
        
        with torch.no_grad():
            val_bar = tqdm(val_loader, desc=f"Validation Epoch {epoch+1}")
            
            for inputs, labels in val_bar:
                inputs = inputs.to(device)
                labels = labels.to(device)
                
                # 前向传播
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                
                # 统计
                val_loss += loss.item() * inputs.size(0)
                _, preds = torch.max(outputs, 1)
                val_corrects += torch.sum(preds == labels.data)
                val_samples += inputs.size(0)
                
                # 收集预测和标签，用于计算混淆矩阵
                val_preds.extend(preds.cpu().numpy())
                val_labels_list.extend(labels.cpu().numpy())
                
                # 更新进度条
                val_bar.set_postfix({
                    'loss': loss.item(),
                    'acc': (torch.sum(preds == labels.data) / inputs.size(0)).item()
                })
        
        epoch_val_loss = val_loss / val_samples
        epoch_val_acc = val_corrects.double() / val_samples
        
        # 打印结果
        print(f'Train Loss: {epoch_train_loss:.4f} Acc: {epoch_train_acc:.4f}')
        print(f'Val Loss: {epoch_val_loss:.4f} Acc: {epoch_val_acc:.4f}')
        
        # 绘制混淆矩阵
        if (epoch + 1) % 5 == 0 or epoch == num_epochs - 1:
            plot_confusion_matrix(val_labels_list, val_preds, 
                                 save_path=os.path.join(save_dir, f'confusion_matrix_epoch_{epoch+1}.png'))
        
        # 更新历史记录
        history['train_loss'].append(epoch_train_loss)
        history['train_acc'].append(epoch_train_acc.item())
        history['val_loss'].append(epoch_val_loss)
        history['val_acc'].append(epoch_val_acc.item())
        
        # 保存最佳模型
        if epoch_val_acc > best_acc:
            best_acc = epoch_val_acc
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'accuracy': epoch_val_acc,
            }, os.path.join(save_dir, 'best_model.pth'))
            print(f"Saved best model with accuracy: {epoch_val_acc:.4f}")
        
        # 保存每个epoch的模型
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'accuracy': epoch_val_acc,
        }, os.path.join(save_dir, f'model_epoch_{epoch+1}.pth'))
        
        # 早停检查
        early_stopping(epoch_val_loss, model)
        if early_stopping.early_stop:
            print("Early stopping triggered!")
            break
    
    # 保存训练历史记录
    with open(os.path.join(save_dir, 'training_history.json'), 'w') as f:
        json.dump(history, f)
    
    # 绘制训练历史
    plot_training_history(history, save_path=os.path.join(save_dir, 'training_history.png'))
    
    # 加载最佳模型进行测试
    # 添加异常处理以适应不同的模型保存格式
    try:
        checkpoint = torch.load(os.path.join(save_dir, 'best_model.pth'))
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
            print("成功加载包含model_state_dict的检查点文件")
        else:
            # 直接加载state_dict
            model.load_state_dict(checkpoint)
            print("成功加载state_dict格式的检查点文件")
    except Exception as e:
        print(f"加载模型失败，使用当前模型进行测试: {e}")
    
    # 测试集评估
    test_results = evaluate_model(model, test_loader, criterion, device)
    
    # 保存测试结果
    with open(os.path.join(save_dir, 'test_results.json'), 'w') as f:
        json.dump(test_results, f, indent=4)
    
    # 绘制测试集混淆矩阵
    plot_confusion_matrix(test_results['true_labels'], test_results['predictions'], 
                         save_path=os.path.join(save_dir, 'test_confusion_matrix.png'))
    
    print(f"\nTraining completed in {(time.time() - start_time) / 60:.2f} minutes")
    print(f"Best validation accuracy: {best_acc:.4f}")
    print(f"Test accuracy: {test_results['accuracy']:.4f}")
    
    return model, history, test_results


def evaluate_model(model, dataloader, criterion, device):
    """评估模型在给定数据集上的性能"""
    model.eval()
    
    all_preds = []
    all_labels = []
    total_loss = 0.0
    total_corrects = 0
    total_samples = 0
    
    with torch.no_grad():
        for inputs, labels in tqdm(dataloader, desc="Evaluating"):
            inputs = inputs.to(device)
            labels = labels.to(device)
            
            # 前向传播
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            # 统计
            total_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            total_corrects += torch.sum(preds == labels.data)
            total_samples += inputs.size(0)
            
            # 收集预测和标签
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    # 计算总体指标
    accuracy = total_corrects.double().item() / total_samples
    loss = total_loss / total_samples
    
    # 获取分类报告
    class_names = list(ACTION_CATEGORIES.keys())
    classification_rep = classification_report(all_labels, all_preds, 
                                             target_names=class_names, 
                                             output_dict=True)
    
    # 结果字典
    results = {
        'accuracy': accuracy,
        'loss': loss,
        'classification_report': classification_rep,
        'true_labels': all_labels,
        'predictions': all_preds
    }
    
    return results


def plot_confusion_matrix(y_true, y_pred, save_path=None):
    """绘制混淆矩阵"""
    # 设置Matplotlib使用Agg后端，避免需要Tkinter
    import matplotlib
    matplotlib.use('Agg')
    
    class_names = list(ACTION_CATEGORIES.keys())
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
               xticklabels=class_names, yticklabels=class_names)
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.title('Confusion Matrix')
    
    # 始终保存图表到文件
    if not save_path:
        save_path = os.path.join(SAVE_DIR, f'confusion_matrix_{time.strftime("%Y%m%d_%H%M%S")}.png')
        
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()


def plot_training_history(history, save_path=None):
    """绘制训练历史"""
    # 设置Matplotlib使用Agg后端，避免需要Tkinter
    import matplotlib
    matplotlib.use('Agg')
    
    plt.figure(figsize=(12, 5))
    
    # 损失子图
    plt.subplot(1, 2, 1)
    plt.plot(history['train_loss'], label='Training Loss')
    plt.plot(history['val_loss'], label='Validation Loss')
    plt.title('Loss Over Epochs')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True)
    
    # 准确率子图
    plt.subplot(1, 2, 2)
    plt.plot(history['train_acc'], label='Training Accuracy')
    plt.plot(history['val_acc'], label='Validation Accuracy')
    plt.title('Accuracy Over Epochs')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # 始终保存图表到文件
    if not save_path:
        save_path = os.path.join(SAVE_DIR, f'training_history_{time.strftime("%Y%m%d_%H%M%S")}.png')
        
    plt.savefig(save_path)
    plt.close()


def main():
    """主函数"""
    # 设置随机种子，确保可重复性
    seed = 42
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    
    # 检查GPU可用性
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # 获取数据加载器
    train_loader, val_loader, test_loader = get_dataloaders()
    print(f"Dataset sizes: Train={len(train_loader.dataset)}, "
          f"Val={len(val_loader.dataset)}, Test={len(test_loader.dataset)}")
    
    # 创建模型实例
    model = get_model(model_type=MODEL_TYPE, num_classes=NUM_CLASSES, 
                     dropout_prob=DROPOUT_PROB, pretrained=PRETRAINED)
    
    # 将模型移动到设备
    model = model.to(device)
    
    # 定义损失函数和优化器
    if MODEL_TYPE == 'SlowFast' or MODEL_TYPE == 'X3D':
        # 使用标签平滑正则化损失，提高泛化能力
        criterion = LabelSmoothingLoss(num_classes=NUM_CLASSES, smoothing=0.1)
    else:
        # 使用Focal Loss处理类别不平衡
        criterion = FocalLoss(gamma=2.0)
    
    # 优化器
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    
    # 学习率调度器
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS, eta_min=LEARNING_RATE/100)
    
    # 训练模型
    print("Starting model training...")
    model, history, test_results = train_model(
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        model=model,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        num_epochs=NUM_EPOCHS,
        device=device,
        save_dir=SAVE_DIR,
        early_stopping_patience=EARLY_STOPPING_PATIENCE,
        mixed_precision=USE_MIXED_PRECISION
    )
    
    print("Training completed!")
    print(f"Final test accuracy: {test_results['accuracy']:.4f}")
    
    # 打印详细分类报告
    print("\nClassification Report:")
    for class_name, metrics in test_results['classification_report'].items():
        if class_name in ['accuracy', 'macro avg', 'weighted avg']:
            continue
        action_name = list(ACTION_CATEGORIES.keys())[int(class_name)] if class_name.isdigit() else class_name
        print(f"{action_name}: Precision={metrics['precision']:.4f}, Recall={metrics['recall']:.4f}, F1-Score={metrics['f1-score']:.4f}")
    
    print("\nOverall Metrics:")
    print(f"Macro Avg: Precision={test_results['classification_report']['macro avg']['precision']:.4f}, "
          f"Recall={test_results['classification_report']['macro avg']['recall']:.4f}, "
          f"F1-Score={test_results['classification_report']['macro avg']['f1-score']:.4f}")


if __name__ == "__main__":
    main()
