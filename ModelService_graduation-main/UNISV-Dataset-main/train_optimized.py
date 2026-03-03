"""
针对RTX 3050(4GB显存)优化的训练脚本
专注于最大化危险行为识别准确率
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.cuda import amp
import numpy as np
import time
import json
from datetime import datetime
from tqdm import tqdm
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
import seaborn as sns
import random

from config import *
from data_loader import get_dataloaders
from optimized_models import get_optimized_model
from train_utils import (MaxAccuracyLoss, GradualWarmupScheduler, 
                        set_random_seed, get_free_gpu_memory)


def train_optimized_model(model, train_loader, val_loader, criterion, optimizer, scheduler, device, num_epochs, grad_accumulation=1, classes=None, dangerous_ids=[0, 1], use_amp=False):
    """
    针对RTX 3050 4GB显存优化的训练函数
    使用梯度累积、自动混合精度和动态批量大小
    
    Args:
        model: 模型
        train_loader: 训练数据加载器
        val_loader: 验证数据加载器
        criterion: 损失函数
        optimizer: 优化器
        scheduler: 学习率调度器
        device: 设备('cuda'或'cpu')
        num_epochs: 训练轮数
        grad_accumulation: 梯度累积步数
        classes: 类别列表
        dangerous_ids: 危险行为类别ID列表
        use_amp: 是否使用自动混合精度
    """
    # 创建保存目录
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    # 混合精度训练 - 兼容PyTorch 2.0.1版本
    device_type = 'cuda' if torch.cuda.is_available() else 'cpu'
    scaler = amp.GradScaler() if use_amp and device_type == 'cuda' else None
    
    # 确认实际设备
    if device == 'cuda' and not torch.cuda.is_available():
        print('警告: CUDA不可用，回退到CPU运行')
        device = 'cpu'
    
    print(f'实际使用设备: {device}')
    
    # 记录训练历史
    history = {
        'train_loss': [], 'train_acc': [],
        'val_loss': [], 'val_acc': [],
        'dangerous_acc': []
    }
    
    # 最佳指标
    best_val_acc = 0.0
    best_dangerous_acc = 0.0
    
    # 危险类别(推人、打架)
    danger_classes = [ACTION_CATEGORIES['pushpeople'], ACTION_CATEGORIES['fight']]
    
    # 早停计数器
    early_stop_counter = 0
    
    # 打印初始显存状态
    if device == 'cuda':
        print(f"训练开始前可用显存: {get_free_gpu_memory()} MB")
    
    # 开始训练
    start_time = time.time()
    for epoch in range(num_epochs):
        print(f"\n[轮次 {epoch+1}/{num_epochs}]")
        
        # 训练模式
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        # 测量每个批次前后的显存使用情况
        if device == 'cuda' and epoch == 0:
            print(f"第一轮开始前可用显存: {get_free_gpu_memory()} MB")
        
        # 动态调整梯度累积步数(如果显存不足)
        current_grad_accumulation = grad_accumulation
        if device == 'cuda' and epoch > 0:
            free_mem = get_free_gpu_memory()
            if free_mem < 300:  # 如果剩余显存不足300MB
                current_grad_accumulation = min(grad_accumulation * 2, 16)  # 最多增加到16
                print(f"显存不足({free_mem}MB)，增加梯度累积步数到{current_grad_accumulation}")
            elif free_mem > 1000 and current_grad_accumulation > grad_accumulation:
                current_grad_accumulation = max(grad_accumulation, current_grad_accumulation // 2)
                print(f"显存充足({free_mem}MB)，减少梯度累积步数到{current_grad_accumulation}")
        
        # 使用tqdm显示进度条
        train_bar = tqdm(train_loader, desc=f"训练 [梯度累积={current_grad_accumulation}]")
        
        # 每个批次的梯度累积
        optimizer.zero_grad()
        
        # 训练一个轮次
        for batch_idx, (inputs, labels) in enumerate(train_bar):
            inputs, labels = inputs.to(device), labels.to(device)
            
            # 为少数类别应用数据增强
            if random.random() < 0.5:  # 50%的概率应用特殊增强
                for idx, label in enumerate(labels):
                    if label.item() in dangerous_ids:
                        # 为危险行为类别提供更多增强
                        if random.random() < 0.7:
                            # 随机亮度和对比度调整
                            brightness_factor = 1.0 + random.uniform(-0.3, 0.3)
                            contrast_factor = 1.0 + random.uniform(-0.3, 0.3)
                            inputs[idx] = torch.clamp(inputs[idx] * brightness_factor, 0, 1)
                            inputs[idx] = torch.clamp((inputs[idx] - 0.5) * contrast_factor + 0.5, 0, 1)
                            
                            # 随机水平和垂直翻转
                            if random.random() < 0.5:
                                inputs[idx] = torch.flip(inputs[idx], dims=[2])  # 水平翻转
                            if random.random() < 0.3:
                                inputs[idx] = torch.flip(inputs[idx], dims=[1])  # 垂直翻转
            
            # 前向传播 - 兼容PyTorch 2.0.1版本
            with amp.autocast():
                outputs = model(inputs)
                loss = criterion(outputs, labels) / current_grad_accumulation
            
            # 梯度缓存并更新
            loss = loss / grad_accumulation  # 缓存多次梯度
            try:
                if use_amp and device_type == 'cuda':
                    scaler.scale(loss).backward()
                else:
                    loss.backward()
                
                # 检查是否有NaN梯度
                for param in model.parameters():
                    if param.grad is not None and torch.isnan(param.grad).any():
                        print("警告: 检测到NaN梯度，跳过此批次")
                        optimizer.zero_grad()
                        continue
            except Exception as e:
                print(f"反向传播异常: {str(e)}")
                optimizer.zero_grad()
                continue
            
            # 梯度累积与裁剪
            if (batch_idx + 1) % current_grad_accumulation == 0:
                try:
                    if use_amp and device_type == 'cuda':
                        # 添加梯度裁剪，防止梯度爆炸
                        scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                        scaler.step(optimizer)
                        scaler.update()
                    else:
                        # 添加梯度裁剪，防止梯度爆炸
                        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                        optimizer.step()
                    
                    optimizer.zero_grad()
                except Exception as e:
                    print(f"优化器步骤异常: {str(e)}")
                    optimizer.zero_grad()
                    # 清理CUDA缓存
                    if device == 'cuda':
                        torch.cuda.empty_cache()
            
            # 统计
            running_loss += loss.item() * current_grad_accumulation
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
            
            # 更新进度条
            train_bar.set_postfix({"损失": loss.item() * current_grad_accumulation, 
                                  "准确率": 100. * correct / total})
            
            # 监控显存使用情况
            if device == 'cuda' and batch_idx % 10 == 0 and epoch == 0:
                free_mem = get_free_gpu_memory()
                if free_mem < 200:  # 如果剩余显存不足200MB
                    print(f"警告: 显存低({free_mem}MB)，尝试清理缓存...")
                    torch.cuda.empty_cache()
        
        # 处理最后一个不完整的梯度累积批次
        try:
            if use_amp and device_type == 'cuda' and (len(train_loader) % current_grad_accumulation != 0):
                # 梯度裁剪
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
            elif not use_amp and (len(train_loader) % current_grad_accumulation != 0):
                # 梯度裁剪
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                optimizer.zero_grad()
        except Exception as e:
            print(f"处理最后一批次异常: {str(e)}")
            optimizer.zero_grad()
            if device == 'cuda':
                torch.cuda.empty_cache()
            
        # 更新学习率
        if scheduler is not None:
            scheduler.step()
        
        # 计算训练损失和准确率
        train_loss = running_loss / len(train_loader)
        train_acc = 100. * correct / total
        
        # 验证
        # 执行验证
        # 初始化验证指标
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        danger_correct = 0
        danger_total = 0
        all_preds = []
        all_labels = []
        
        # 验证步骤
        model.eval()
        with torch.no_grad():
            val_bar = tqdm(val_loader, desc="验证中")
            for i, (inputs, labels) in enumerate(val_bar):
                inputs, labels = inputs.to(device), labels.to(device)
                
                # 应用标签平滑和随机翻转，增强模型对少数类别的学习
                if epoch > 0 and random.random() < 0.3:  # 30%的概率应用数据增强
                    # 对于少见类别的样本进行特别增强
                    for idx, label in enumerate(labels):
                        if label.item() in dangerous_ids and random.random() < 0.7:
                            # 随机水平和垂直翻转以增加样本多样性
                            if random.random() < 0.5:
                                inputs[idx] = torch.flip(inputs[idx], dims=[2])  # 水平翻转
                            if random.random() < 0.5:
                                inputs[idx] = torch.flip(inputs[idx], dims=[1])  # 垂直翻转
                
                # PyTorch 2.0.1兼容的autocast调用方式
                try:
                    if use_amp and torch.cuda.is_available():
                        with amp.autocast():
                            outputs = model(inputs)
                            loss = criterion(outputs, labels)
                    else:
                        outputs = model(inputs)
                        loss = criterion(outputs, labels)
                    
                    val_loss += loss.item()
                    _, preds = torch.max(outputs, 1)
                    val_total += labels.size(0)
                    val_correct += (preds == labels).sum().item()
                    
                    # 收集预测结果
                    all_preds.extend(preds.cpu().numpy())
                    all_labels.extend(labels.cpu().numpy())
                    
                    # 危险行为验证（推人和打架）
                    if dangerous_ids:
                        for danger_id in dangerous_ids:
                            danger_mask = (labels == danger_id)
                            danger_total += danger_mask.sum().item()
                            danger_correct += ((preds == labels) & danger_mask).sum().item()
                    
                    # 更新进度条
                    cur_val_acc = 100. * val_correct / max(1, val_total)
                    cur_val_loss = val_loss / max(1, (i+1))
                    val_bar.set_postfix(损失=f"{cur_val_loss:.2f}", 准确率=f"{cur_val_acc:.1f}")
                    
                except Exception as e:
                    print(f"验证过程中出错: {str(e)}")
                    continue
                
                # 定期保存验证检查点
                if (i+1) % 50 == 0 or i == len(val_loader) - 1:
                    print(f"定期验证检查点 - 已处理 {(i+1)*val_loader.batch_size} 样本")
                    
                    # 保存临时检查点
                    temp_checkpoint = {
                        'epoch': epoch,
                        'model_state_dict': model.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict(),
                        'val_acc': val_correct / max(1, val_total),
                        'val_loss': val_loss / max(1, (i+1))
                    }
                    torch.save(temp_checkpoint, os.path.join(SAVE_DIR, f'temp_checkpoint_epoch{epoch}.pth'))
                    
                # 如果显存不足，清理缓存
                if device == 'cuda' and i % 20 == 0:
                    free_mem = get_free_gpu_memory()
                    if free_mem < 200:
                        torch.cuda.empty_cache()
        
        # 计算验证损失和准确率
        val_loss = val_loss / max(1, len(val_loader))
        if val_total > 0:
            val_acc = 100. * val_correct / val_total
        else:
            print("警告: 验证集处理样本为0，可能因为所有样本都出现异常")
            val_acc = 0.0
        
        # 计算危险类别准确率
        danger_acc = 100. * danger_correct / max(1, danger_total)
        
        # 更新历史
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)
        history['dangerous_acc'].append(danger_acc)
        
        # 打印统计信息
        print(f"训练损失: {train_loss:.4f}, 训练准确率: {train_acc:.2f}%")
        print(f"验证损失: {val_loss:.4f}, 验证准确率: {val_acc:.2f}%")
        print(f"危险行为准确率: {danger_acc:.2f}% [{danger_correct}/{danger_total}]")
        
        # 学习率信息
        current_lr = optimizer.param_groups[0]['lr']
        print(f"当前学习率: {current_lr:.6f}")
        
        # 是否保存最佳模型(基于验证准确率)
        if val_acc > best_val_acc:
            print(f"验证准确率提高: {best_val_acc:.2f}% -> {val_acc:.2f}%")
            best_val_acc = val_acc
            # 保存模型
            torch.save(model.state_dict(), os.path.join(SAVE_DIR, 'best_model.pth'))
            early_stop_counter = 0
        else:
            early_stop_counter += 1
            print(f"验证准确率未提高，早停计数: {early_stop_counter}/{EARLY_STOPPING_PATIENCE}")
        
        # 是否保存危险行为识别最佳模型
        if danger_acc > best_dangerous_acc and danger_total > 0:
            print(f"危险行为准确率提高: {best_dangerous_acc:.2f}% -> {danger_acc:.2f}%")
            best_dangerous_acc = danger_acc
            # 保存模型
            torch.save(model.state_dict(), os.path.join(SAVE_DIR, 'best_danger_model.pth'))
        
        # 混淆矩阵
        if (epoch + 1) % 5 == 0 or epoch == num_epochs - 1:
            plot_confusion_matrix(np.array(all_labels), np.array(all_preds),
                                 os.path.join(SAVE_DIR, f'confusion_matrix_epoch_{epoch+1}.png'))
        
        # 早停
        if early_stop_counter >= EARLY_STOPPING_PATIENCE:
            print(f"早停触发，{EARLY_STOPPING_PATIENCE}轮未提高验证准确率")
            break
        
        # 轮次结束，清理GPU缓存
        if device == 'cuda':
            torch.cuda.empty_cache()
            print(f"轮次结束后可用显存: {get_free_gpu_memory()} MB")
    
    # 训练结束，加载最佳模型
    print("\n加载最佳模型进行评估...")
    model.load_state_dict(torch.load(os.path.join(SAVE_DIR, 'best_model.pth')))
    
    # 测试集评估
    test_results = evaluate_model(model, test_loader, criterion, device, danger_classes, use_amp)
    
    # 计算训练时间
    total_time = time.time() - start_time
    print(f"训练完成，总时间: {total_time/60:.2f}分钟")
    
    # 绘制训练历史
    plot_training_history(history, os.path.join(SAVE_DIR, 'training_history.png'))
    
    # 保存最终混淆矩阵
    plot_confusion_matrix(test_results['true_labels'], test_results['predictions'],
                         os.path.join(SAVE_DIR, 'final_confusion_matrix.png'))
    
    # 保存训练历史和测试结果
    with open(os.path.join(SAVE_DIR, 'training_history.json'), 'w') as f:
        # 将NumPy数组转为列表便于JSON序列化
        history_json = {k: [float(v) for v in vals] for k, vals in history.items()}
        json.dump(history_json, f, indent=2)
    
    with open(os.path.join(SAVE_DIR, 'test_results.json'), 'w') as f:
        test_results_json = {}
        for k, v in test_results.items():
            if k in ['confusion_matrix', 'true_labels', 'predictions']:
                continue  # 跳过大型数组
            elif k == 'classification_report':
                test_results_json[k] = str(v)
            else:
                test_results_json[k] = float(v) if isinstance(v, (np.float32, np.float64)) else v
        json.dump(test_results_json, f, indent=2)
    
    return model, history, test_results


def evaluate_model(model, dataloader, criterion, device, danger_classes=None, use_amp=True):
    """在测试集上评估模型性能"""
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_labels = []
    
    # 危险行为统计
    danger_correct = 0
    danger_total = 0
    
    # 分类别统计
    class_correct = [0] * NUM_CLASSES
    class_total = [0] * NUM_CLASSES
    
    with torch.no_grad():
        for inputs, labels in tqdm(dataloader, desc="评估中"):
            inputs, labels = inputs.to(device), labels.to(device)
            
            # 前向传播
            with amp.autocast(enabled=use_amp):
                outputs = model(inputs)
                loss = criterion(outputs, labels)
            
            running_loss += loss.item()
            _, preds = outputs.max(1)
            
            # 收集预测和标签
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
            # 计算危险类别准确率
            if danger_classes is not None:
                for danger_class in danger_classes:
                    danger_mask = (labels == danger_class)
                    if danger_mask.sum() > 0:
                        danger_total += danger_mask.sum().item()
                        danger_correct += ((preds == labels) & danger_mask).sum().item()
            
            # 分类别统计
            for i in range(NUM_CLASSES):
                mask = (labels == i)
                class_total[i] += mask.sum().item()
                class_correct[i] += ((preds == i) & mask).sum().item()
            
            # 每次迭代后清理GPU缓存
            if device == 'cuda' and get_free_gpu_memory() < 200:
                torch.cuda.empty_cache()
    
    # 计算整体损失和准确率
    avg_loss = running_loss / len(dataloader)
    accuracy = accuracy_score(all_labels, all_preds) * 100
    
    # 危险类别准确率
    danger_accuracy = 100. * danger_correct / max(1, danger_total) if danger_classes is not None else 0.0
    
    # 混淆矩阵
    cm = confusion_matrix(all_labels, all_preds)
    
    # 详细分类报告
    report = classification_report(all_labels, all_preds, output_dict=True)
    
    # 计算分类别准确率
    class_accuracy = [100. * correct / max(1, total) for correct, total in zip(class_correct, class_total)]
    
    # 打印结果
    print(f"\n测试损失: {avg_loss:.4f}, 测试准确率: {accuracy:.2f}%")
    print(f"危险行为准确率: {danger_accuracy:.2f}% [{danger_correct}/{danger_total}]")
    
    # 打印各类别准确率
    print("\n各类别准确率:")
    for i, (acc, total) in enumerate(zip(class_accuracy, class_total)):
        if total > 0:
            class_name = [k for k, v in ACTION_CATEGORIES.items() if v == i][0]
            print(f"{class_name}: {acc:.2f}% [{class_correct[i]}/{class_total[i]}]")
    
    result = {
        'loss': avg_loss,
        'accuracy': accuracy,
        'danger_accuracy': danger_accuracy,
        'danger_correct': danger_correct,
        'danger_total': danger_total,
        'class_accuracy': class_accuracy,
        'class_correct': class_correct,
        'class_total': class_total,
        'confusion_matrix': cm,
        'classification_report': report,
        'predictions': all_preds,
        'true_labels': all_labels
    }
    
    return result


def plot_confusion_matrix(y_true, y_pred, save_path=None):
    """绘制混淆矩阵"""
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(12, 10))
    
    class_names = list(ACTION_CATEGORIES.keys())
    
    # 使用归一化混淆矩阵
    cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    
    # 绘制热力图
    sns.heatmap(cm_normalized, annot=True, fmt='.2f', cmap='Blues',
               xticklabels=class_names, yticklabels=class_names)
    
    plt.xlabel('预测标签')
    plt.ylabel('真实标签')
    plt.title('归一化混淆矩阵')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=200)
        print(f"混淆矩阵已保存至 {save_path}")
    
    plt.close()


def plot_training_history(history, save_path='training_history.png'):
    """绘制训练历史图表"""
    plt.figure(figsize=(12, 10))
    
    # 确保history是字典而非元组
    if isinstance(history, tuple):
        history_dict = {
            'train_loss': history[0],
            'train_acc': history[1],
            'val_loss': history[2],
            'val_acc': history[3],
            'dangerous_acc': history[4]
        }
    else:
        history_dict = history
    
    # 画损失曲线
    plt.subplot(2, 1, 1)
    plt.plot(history_dict['train_loss'], label='训练损失')
    plt.plot(history_dict['val_loss'], label='验证损失')
    plt.title('训练和验证损失')
    plt.xlabel('轮次')
    plt.ylabel('损失')
    plt.legend()
    
    # 画准确率曲线
    plt.subplot(2, 1, 2)
    plt.plot(history_dict['train_acc'], label='训练准确率')
    plt.plot(history_dict['val_acc'], label='验证准确率')
    plt.plot(history_dict['dangerous_acc'], label='危险行为准确率')
    plt.title('训练和验证准确率')
    plt.xlabel('轮次')
    plt.ylabel('准确率')
    plt.legend()
    
    # 保存图表
    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()
