"""
红外视频行为识别训练启动脚本
针对RTX 3050 4GB显存进行优化
专注于推人和打架等危险行为的准确识别
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
import argparse
import time
from datetime import datetime
import numpy as np
from tqdm import tqdm

# 导入项目模块
from config import *
from simple_dataloader import get_simple_dataloaders
from optimized_models import get_optimized_model
from train_utils import (MaxAccuracyLoss, GradualWarmupScheduler, 
                        set_random_seed, get_free_gpu_memory,
                        get_optimized_training_config)

# 使用importlib修改配置模块变量
import importlib
import config as config_module
from train_optimized import train_optimized_model, evaluate_model, plot_training_history

def main():
    # 命令行参数
    parser = argparse.ArgumentParser(description='针对RTX 3050优化的红外视频行为识别训练脚本')
    parser.add_argument('--model_type', type=str, default='OptimizedActionNetLite',
                       choices=['OptimizedInfraredActionNet', 'OptimizedActionNetLite', 'EnsembleOptimizedNet'],
                       help='模型类型')
    parser.add_argument('--batch_size', type=int, default=4, help='批量大小')
    parser.add_argument('--lr', type=float, default=0.0003, help='学习率')
    parser.add_argument('--num_epochs', type=int, default=30, help='训练轮数')
    parser.add_argument('--grad_accumulation', type=int, default=4, help='梯度累积步数')
    parser.add_argument('--use_amp', action='store_true', help='是否使用自动混合精度')
    parser.add_argument('--dynamic_batch', action='store_true', help='是否使用动态批量大小')
    parser.add_argument('--save_dir', type=str, default=SAVE_DIR, help='模型保存目录')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')
    parser.add_argument('--device', type=str, default='cuda',
                       help='运行设备')
    parser.add_argument('--auto_config', action='store_true', default=True, 
                        help='是否根据GPU自动配置训练参数')
    args = parser.parse_args()
    
    # 设置随机种子
    set_random_seed(args.seed)
    
    # 强制检查CUDA是否可用
    print(f"PyTorch版本: {torch.__version__}")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA可用: {cuda_available}")
    
    if args.device == 'cuda':
        if cuda_available:
            # 初始化CUDA并清空缓存
            torch.cuda.empty_cache()
            print(f"CUDA版本: {torch.version.cuda}")
            print(f'使用CUDA设备: {torch.cuda.get_device_name(0)}')
            # 指定当前设备
            torch.cuda.set_device(0)
            args.device = 'cuda'
        else:
            print('警告: CUDA不可用，回退到CPU')
            args.device = 'cpu'
    
    print(f'最终使用设备: {args.device}')
    
    # 显存信息
    if args.device == 'cuda':
        gpu_name = torch.cuda.get_device_name(0)
        total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
        free_mem = get_free_gpu_memory() / 1024  # GB
        print(f'GPU: {gpu_name}, 总显存: {total_mem:.2f}GB, 可用显存: {free_mem:.2f}GB')
        
        # 如果启用自动配置，根据GPU自动设置参数
        if args.auto_config:
            training_config = get_optimized_training_config(args.device)
            args.batch_size = training_config['batch_size']
            args.grad_accumulation = training_config['grad_accumulation']
            args.use_amp = training_config['use_amp']
            args.dynamic_batch = training_config['dynamic_batch_size']
            args.model_type = training_config['model_type']
            
            print(f"已根据GPU自动配置: 批量大小={args.batch_size}, 梯度累积={args.grad_accumulation}")
            print(f"模型类型={args.model_type}, 混合精度={args.use_amp}, 动态批量={args.dynamic_batch}")
    
    # 数据加载器
    print('准备数据加载器...')
    train_loader, val_loader, test_loader = get_simple_dataloaders(batch_size=args.batch_size, num_workers=2)
    
    # 创建模型
    print(f'创建模型: {args.model_type}')
    model = get_optimized_model(args.model_type, num_classes=NUM_CLASSES)
    model = model.to(args.device)
    
    # 生成分类ID列表
    classes = list(range(NUM_CLASSES))
    dangerous_ids = [ACTION_CATEGORIES['pushpeople'], ACTION_CATEGORIES['fight']]  # 推人和打架
    
    # 损失函数 - 使用专门针对危险行为准确率优化的损失函数
    criterion = MaxAccuracyLoss(num_classes=NUM_CLASSES, danger_weight=3.0).to(args.device)
    
    # 优化器
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    
    # 学习率调度器 - 使用余弦退火
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, 
        T_max=args.num_epochs,
        eta_min=args.lr / 100
    )
    
    # 学习率预热包装
    scheduler = GradualWarmupScheduler(
        optimizer,
        multiplier=1.0,
        warmup_epochs=2,
        after_scheduler=scheduler
    )
    
    # 创建保存目录
    os.makedirs(args.save_dir, exist_ok=True)
    
    # 开始训练
    print('开始训练...')
    
    print(f"实际使用设备: {args.device}")
    
    # 打印GPU信息
    if args.device == 'cuda':
        free_mem = get_free_gpu_memory()
        print(f"训练开始前可用显存: {free_mem} MB")
    
    # 使用优化的训练函数
    history = train_optimized_model(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        device=args.device,
        num_epochs=args.num_epochs,
        grad_accumulation=args.grad_accumulation,
        classes=classes,
        dangerous_ids=dangerous_ids,
        use_amp=args.use_amp
    )
    
    # 绘制训练历史
    plot_training_history(history, save_path=os.path.join(args.save_dir, 'training_history.png'))
    
    # 加载最佳模型
    best_model_path = os.path.join(args.save_dir, 'best_model.pth')
    if os.path.exists(best_model_path):
        checkpoint = torch.load(best_model_path, map_location=args.device)
        
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
    
    # 在测试集上评估
    print('在测试集上评估...')
    test_results = evaluate_model(
        model=model,
        dataloader=test_loader,
        criterion=criterion,
        device=args.device,
        danger_classes=dangerous_ids,
        use_amp=args.use_amp
    )
    
    # 打印最终结果
    print('\n最终评估结果:')
    print(f"测试准确率: {test_results['accuracy']:.2f}%")
    print(f"危险行为准确率: {test_results['danger_accuracy']:.2f}%")
    print(f"危险行为召回率: {test_results['danger_recall']:.2f}%")
    print(f"危险行为F1分数: {test_results['danger_f1']:.2f}%")
    
    print(f'\n模型已保存到 {best_model_path}')
    print('训练完成！')

if __name__ == '__main__':
    main()
