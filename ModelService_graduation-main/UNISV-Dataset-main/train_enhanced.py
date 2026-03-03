"""
增强型红外视频行为识别模型训练脚本
专门针对推人和打架等危险行为优化了训练过程和准确率
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
from enhanced_models import get_enhanced_model
from utils import EarlyStopping, LabelSmoothingLoss, FocalLoss


class DangerClassFocalLoss(nn.Module):
    """
    专为危险类别(推人、打架)设计的Focal Loss
    对危险类别赋予更高权重，提高危险行为识别准确率
    """
    def __init__(self, gamma=2.0, alpha=None, reduction='mean', danger_weight=2.0):
        super(DangerClassFocalLoss, self).__init__()
        self.gamma = gamma
        self.alpha = alpha
        self.reduction = reduction
        self.danger_classes = [ACTION_CATEGORIES['pushpeople'], ACTION_CATEGORIES['fight']]
        self.danger_weight = danger_weight  # 危险类别权重

    def forward(self, input, target):
        ce_loss = nn.functional.cross_entropy(input, target, reduction='none')
        pt = torch.exp(-ce_loss)
        
        # 计算Focal Loss
        focal_loss = (1 - pt) ** self.gamma * ce_loss
        
        # 为危险类别赋予更高权重
        weights = torch.ones_like(target, dtype=torch.float)
        for danger_class in self.danger_classes:
            weights = torch.where(target == danger_class, 
                                 torch.tensor(self.danger_weight, device=target.device), 
                                 weights)
        
        # 应用权重
        weighted_loss = focal_loss * weights
        
        if self.reduction == 'mean':
            return weighted_loss.mean()
        elif self.reduction == 'sum':
            return weighted_loss.sum()
        else:
            return weighted_loss


def train_model(train_loader, val_loader, test_loader, model, criterion, optimizer, 
                scheduler=None, num_epochs=NUM_EPOCHS, device='cuda', 
                save_dir=SAVE_DIR, early_stopping_patience=EARLY_STOPPING_PATIENCE,
                mixed_precision=USE_MIXED_PRECISION, danger_classes_weight=2.0):
    """训练模型函数，特别优化了对危险行为的识别"""
    
    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)
    
    # 初始化早停
    early_stopping = EarlyStopping(patience=early_stopping_patience, verbose=True, 
                                  path=os.path.join(save_dir, 'best_enhanced_model.pth'))
    
    # 初始化混合精度训练的scaler
    scaler = GradScaler() if mixed_precision else None
    
    # 记录训练和验证的损失和准确率
    history = {
        'train_loss': [], 'train_acc': [],
        'val_loss': [], 'val_acc': [],
        'danger_class_acc': []  # 专门记录危险类别的准确率
    }
    
    best_acc = 0.0  # 记录最佳准确率
    best_danger_acc = 0.0  # 记录最佳危险行为准确率
    
    # 危险类别索引
    danger_classes = [ACTION_CATEGORIES['pushpeople'], ACTION_CATEGORIES['fight']]
    
    # 开始训练
    start_time = time.time()
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        
        # 训练阶段
        model.train()
        running_loss = 0.0
        train_correct = 0
        train_total = 0
        
        # 使用tqdm显示进度条
        train_bar = tqdm(train_loader, desc="Training")
        for inputs, labels in train_bar:
            inputs, labels = inputs.to(device), labels.to(device)
            
            # 清零梯度
            optimizer.zero_grad()
            
            # 前向传播
            with autocast(enabled=mixed_precision):
                if hasattr(model, 'training') and model.training:
                    outputs, aux_outputs = model(inputs)
                    
                    # 计算主要损失和辅助损失
                    main_loss = criterion(outputs, labels)
                    aux_loss = nn.functional.cross_entropy(aux_outputs, labels)
                    
                    # 总损失 = 主要损失 + 0.4 * 辅助损失
                    loss = main_loss + 0.4 * aux_loss
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
            
            # 反向传播
            if mixed_precision:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()
            
            # 统计训练损失和准确率
            running_loss += loss.item() * inputs.size(0)
            _, predicted = torch.max(outputs.data, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()
            
            # 更新进度条
            train_bar.set_postfix({"Loss": loss.item(), "Acc": train_correct/train_total})
        
        if scheduler is not None:
            scheduler.step()
            
        # 计算平均训练损失和准确率
        epoch_train_loss = running_loss / len(train_loader.dataset)
        epoch_train_acc = train_correct / train_total
        
        # 验证阶段
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        # 专门用于计算危险类别预测的准确性
        danger_correct = 0
        danger_total = 0
        
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            val_bar = tqdm(val_loader, desc="Validating")
            for inputs, labels in val_bar:
                inputs, labels = inputs.to(device), labels.to(device)
                
                # 前向传播
                with autocast(enabled=mixed_precision):
                    if hasattr(model, 'training') and not model.training:
                        outputs = model(inputs)
                    else:
                        outputs, _ = model(inputs)
                    
                    loss = criterion(outputs, labels)
                
                val_loss += loss.item() * inputs.size(0)
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
                
                # 计算危险类别的准确率
                danger_mask = torch.zeros_like(labels, dtype=torch.bool)
                for danger_class in danger_classes:
                    danger_mask = danger_mask | (labels == danger_class)
                
                if danger_mask.sum() > 0:
                    danger_total += danger_mask.sum().item()
                    danger_correct += ((predicted == labels) & danger_mask).sum().item()
                
                # 收集所有预测和真实标签，用于后续分析
                all_preds.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                
                # 更新进度条
                current_val_acc = val_correct / val_total
                val_bar.set_postfix({"Loss": loss.item(), "Acc": current_val_acc})
        
        # 计算平均验证损失和准确率
        epoch_val_loss = val_loss / len(val_loader.dataset)
        epoch_val_acc = val_correct / val_total
        
        # 计算危险类别准确率
        epoch_danger_acc = danger_correct / max(1, danger_total)  # 避免除零
        
        # 更新历史记录
        history['train_loss'].append(epoch_train_loss)
        history['train_acc'].append(epoch_train_acc)
        history['val_loss'].append(epoch_val_loss)
        history['val_acc'].append(epoch_val_acc)
        history['danger_class_acc'].append(epoch_danger_acc)
        
        # 打印训练和验证的损失和准确率
        print(f"Train Loss: {epoch_train_loss:.4f}, Train Acc: {epoch_train_acc:.4f}")
        print(f"Val Loss: {epoch_val_loss:.4f}, Val Acc: {epoch_val_acc:.4f}")
        print(f"Danger Class Acc: {epoch_danger_acc:.4f} [{danger_correct}/{danger_total}]")
        
        # 检查是否是最佳模型
        if epoch_val_acc > best_acc:
            best_acc = epoch_val_acc
            torch.save(model.state_dict(), os.path.join(save_dir, f"model_epoch_{epoch+1}.pth"))
            print(f"New best model saved with accuracy: {best_acc:.4f}")
        
        # 检查是否是危险类别最佳模型
        if epoch_danger_acc > best_danger_acc and danger_total > 0:
            best_danger_acc = epoch_danger_acc
            torch.save(model.state_dict(), os.path.join(save_dir, f"model_danger_best_epoch_{epoch+1}.pth"))
            print(f"New best model for danger classes saved with accuracy: {best_danger_acc:.4f}")
        
        # 早停
        early_stopping(epoch_val_loss, model)
        if early_stopping.early_stop:
            print("Early stopping triggered")
            break
    
    # 训练完成，加载最佳模型
    model.load_state_dict(torch.load(early_stopping.path))
    
    # 评估模型在测试集上的性能
    print("\nEvaluating model on test set...")
    test_results = evaluate_model(model, test_loader, criterion, device, danger_classes)
    
    # 计算训练总时间
    total_time = time.time() - start_time
    print(f"Training completed in {total_time/60:.2f} minutes")
    
    # 绘制训练历史和混淆矩阵
    plot_training_history(history, os.path.join(save_dir, 'training_history.png'))
    plot_confusion_matrix(np.array(all_labels), np.array(all_preds), 
                         os.path.join(save_dir, 'confusion_matrix.png'))
    
    # 保存训练历史和测试结果
    with open(os.path.join(save_dir, 'training_history.json'), 'w') as f:
        # 将numpy数组转换为列表以便JSON序列化
        history_json = {k: [float(x) for x in v] for k, v in history.items()}
        json.dump(history_json, f)
    
    with open(os.path.join(save_dir, 'test_results.json'), 'w') as f:
        # 删除不可序列化的对象
        serializable_results = {k: v for k, v in test_results.items() 
                               if k != 'confusion_matrix' and k != 'classification_report'}
        # 添加分类报告的可序列化版本
        serializable_results['classification_report_str'] = str(test_results['classification_report'])
        json.dump(serializable_results, f)
    
    return model, history, test_results


def evaluate_model(model, dataloader, criterion, device, danger_classes=None):
    """评估模型在给定数据集上的性能"""
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_labels = []
    
    danger_correct = 0
    danger_total = 0
    
    with torch.no_grad():
        for inputs, labels in tqdm(dataloader, desc="Evaluating"):
            inputs, labels = inputs.to(device), labels.to(device)
            
            # 前向传播
            if hasattr(model, 'training') and not model.training:
                outputs = model(inputs)
            else:
                outputs, _ = model(inputs) 
                
            loss = criterion(outputs, labels)
            running_loss += loss.item() * inputs.size(0)
            
            _, preds = torch.max(outputs, 1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
            # 计算危险类别的准确率
            if danger_classes is not None:
                danger_mask = torch.zeros_like(labels, dtype=torch.bool)
                for danger_class in danger_classes:
                    danger_mask = danger_mask | (labels == danger_class)
                
                if danger_mask.sum() > 0:
                    danger_total += danger_mask.sum().item()
                    danger_correct += ((preds == labels) & danger_mask).sum().item()
    
    # 计算损失
    avg_loss = running_loss / len(dataloader.dataset)
    
    # 计算准确率
    accuracy = accuracy_score(all_labels, all_preds)
    
    # 计算危险类别准确率
    danger_accuracy = danger_correct / max(1, danger_total) if danger_classes is not None else 0.0
    
    # 计算混淆矩阵
    cm = confusion_matrix(all_labels, all_preds)
    
    # 获取详细的分类报告
    report = classification_report(all_labels, all_preds, output_dict=True)
    
    print(f"Test Loss: {avg_loss:.4f}, Test Accuracy: {accuracy:.4f}")
    if danger_classes is not None and danger_total > 0:
        print(f"Danger Class Accuracy: {danger_accuracy:.4f} [{danger_correct}/{danger_total}]")
    
    result = {
        'loss': avg_loss,
        'accuracy': accuracy,
        'danger_accuracy': danger_accuracy,
        'danger_correct': danger_correct,
        'danger_total': danger_total,
        'confusion_matrix': cm,
        'classification_report': report,
        'predictions': all_preds,
        'true_labels': all_labels
    }
    
    return result


def plot_confusion_matrix(y_true, y_pred, save_path=None):
    """绘制混淆矩阵"""
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    
    # 使用seaborn绘制混淆矩阵
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=list(ACTION_CATEGORIES.keys()),
                yticklabels=list(ACTION_CATEGORIES.keys()))
    
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    
    if save_path:
        plt.savefig(save_path)
        print(f"Confusion matrix saved to {save_path}")
    
    plt.close()


def plot_training_history(history, save_path=None):
    """绘制训练历史"""
    plt.figure(figsize=(15, 5))
    
    # 绘制损失
    plt.subplot(1, 3, 1)
    plt.plot(history['train_loss'], label='Train Loss')
    plt.plot(history['val_loss'], label='Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Training and Validation Loss')
    plt.legend()
    
    # 绘制准确率
    plt.subplot(1, 3, 2)
    plt.plot(history['train_acc'], label='Train Accuracy')
    plt.plot(history['val_acc'], label='Validation Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.title('Training and Validation Accuracy')
    plt.legend()
    
    # 绘制危险类别准确率
    plt.subplot(1, 3, 3)
    plt.plot(history['danger_class_acc'], label='Danger Class Accuracy', color='red')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.title('Danger Class Accuracy')
    plt.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"Training history saved to {save_path}")
    
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
    
    # 创建增强型模型实例
    model_type = "InfraredActionNet"  # 或者使用 "InfraredActionNetLite" 获取轻量版本
    model = get_enhanced_model(model_type=model_type, num_classes=NUM_CLASSES, dropout_prob=DROPOUT_PROB)
    
    # 将模型移动到设备
    model = model.to(device)
    
    # 打印模型总参数量
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params:,}")
    
    # 定义损失函数 - 使用专用的危险类别焦点损失
    criterion = DangerClassFocalLoss(gamma=2.0, danger_weight=3.0)
    
    # 优化器
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    
    # 学习率调度器
    scheduler = optim.lr_scheduler.OneCycleLR(
        optimizer, 
        max_lr=LEARNING_RATE * 10,  # 最大学习率
        total_steps=NUM_EPOCHS * len(train_loader),
        pct_start=0.3,  # 在30%的训练过程中达到最大学习率
        div_factor=25,  # 初始学习率 = max_lr / 25
        final_div_factor=1000  # 最终学习率 = max_lr / 1000
    )
    
    # 训练模型
    print("\n========== 开始训练增强型红外视频行为识别模型 ==========")
    print(f"模型类型: {model_type}")
    print(f"训练轮数: {NUM_EPOCHS}")
    print(f"混合精度训练: {'启用' if USE_MIXED_PRECISION else '禁用'}")
    print(f"数据集中的危险行为: 推人(ID={ACTION_CATEGORIES['pushpeople']}), 打架(ID={ACTION_CATEGORIES['fight']})")
    print("===================================================\n")
    
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
        mixed_precision=USE_MIXED_PRECISION,
        danger_classes_weight=3.0  # 为危险类别增加权重
    )
    
    print("\n========== 训练完成! ==========")
    print(f"最终测试集准确率: {test_results['accuracy']:.4f}")
    print(f"危险行为类别准确率: {test_results['danger_accuracy']:.4f}")
    
    # 打印详细分类报告
    print("\n各类别性能报告:")
    for class_name, metrics in test_results['classification_report'].items():
        if class_name in ['accuracy', 'macro avg', 'weighted avg']:
            continue
        action_name = list(ACTION_CATEGORIES.keys())[int(class_name)] if class_name.isdigit() else class_name
        print(f"{action_name}: 精确率={metrics['precision']:.4f}, 召回率={metrics['recall']:.4f}, F1分数={metrics['f1-score']:.4f}")
    
    print("\n总体性能指标:")
    print(f"宏平均: 精确率={test_results['classification_report']['macro avg']['precision']:.4f}, "
          f"召回率={test_results['classification_report']['macro avg']['recall']:.4f}, "
          f"F1分数={test_results['classification_report']['macro avg']['f1-score']:.4f}")
    
    print("\n危险行为(推人、打架)特别报告:")
    danger_classes = ['pushpeople', 'fight']
    for danger_class in danger_classes:
        class_id = str(ACTION_CATEGORIES[danger_class])
        if class_id in test_results['classification_report']:
            metrics = test_results['classification_report'][class_id]
            print(f"{danger_class}: 精确率={metrics['precision']:.4f}, "
                  f"召回率={metrics['recall']:.4f}, F1分数={metrics['f1-score']:.4f}")
    
    print("\n===================================================")
    print(f"模型和训练结果已保存至: {SAVE_DIR}")


if __name__ == "__main__":
    main()
