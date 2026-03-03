"""
系统诊断工具，用于测试模型、报警和视频处理功能
"""

import os
import sys
import torch
import cv2
import numpy as np
from models import get_model
from config import *
from alarm import send_red_alert, send_yellow_alert

def test_model_loading():
    """测试模型加载功能"""
    print("\n=== 测试模型加载 ===")
    
    model_path = os.path.join(DATA_ROOT, 'checkpoints', 'model_epoch_25.pth')
    print(f"尝试加载模型: {model_path}")
    
    if not os.path.exists(model_path):
        print(f"❌ 错误: 模型文件不存在!")
        return False
    
    try:
        model = get_model(MODEL_TYPE, NUM_CLASSES)
        print(f"创建模型架构: {MODEL_TYPE}, 类别数: {NUM_CLASSES}")
        
        checkpoint = torch.load(model_path, map_location='cpu')
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
            print("✓ 成功加载包含model_state_dict的检查点文件")
        else:
            model.load_state_dict(checkpoint)
            print("✓ 成功加载state_dict格式的检查点文件")
        
        print(f"✓ 模型加载成功!")
        return True
    except Exception as e:
        print(f"❌ 错误: 模型加载失败: {str(e)}")
        return False

def test_video_reading():
    """测试视频读取功能"""
    print("\n=== 测试视频读取 ===")
    
    # 测试所有行为类别目录
    for category in ACTION_CATEGORIES.keys():
        category_dir = os.path.join(DATA_ROOT, category.capitalize())
        if not os.path.exists(category_dir):
            print(f"⚠️ 警告: 类别目录不存在: {category_dir}")
            continue
        
        # 查找第一个视频文件
        video_files = []
        for file in os.listdir(category_dir):
            if file.endswith('.mp4') or file.endswith('.avi'):
                video_files.append(os.path.join(category_dir, file))
        
        if not video_files:
            print(f"⚠️ 警告: 在{category_dir}中没有找到视频文件")
            continue
        
        # 测试读取第一个视频文件
        video_path = video_files[0]
        print(f"测试视频: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ 错误: 无法打开视频: {video_path}")
            continue
        
        # 读取一些帧
        frames = []
        for _ in range(min(CLIP_LENGTH, 30)):  # 最多读取30帧
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        
        cap.release()
        
        if len(frames) > 0:
            print(f"✓ 成功读取{len(frames)}帧, 形状: {frames[0].shape}")
        else:
            print(f"❌ 错误: 无法读取视频帧")
    
    return True

def test_alarm_system():
    """测试报警系统"""
    print("\n=== 测试报警系统 ===")
    
    print("测试红色警报...")
    red_result = send_red_alert("战斗", 0.95)
    print(f"红色警报结果: {'成功' if red_result else '失败'}")
    
    print("测试黄色警报...")
    yellow_result = send_yellow_alert("握手", 0.85)
    print(f"黄色警报结果: {'成功' if yellow_result else '失败'}")
    
    return red_result or yellow_result

def check_class_mapping():
    """检查类别映射"""
    print("\n=== 检查类别映射 ===")
    
    print(f"ACTION_CATEGORIES: {ACTION_CATEGORIES}")
    print(f"ACTION_ALERT_LEVEL: {ACTION_ALERT_LEVEL}")
    
    # 检查映射是否匹配
    for class_name, class_id in ACTION_CATEGORIES.items():
        if class_id not in ACTION_ALERT_LEVEL:
            print(f"❌ 错误: 类别ID {class_id} ({class_name})在ACTION_ALERT_LEVEL中没有映射")
        else:
            alert_level = ACTION_ALERT_LEVEL[class_id]
            print(f"类别 {class_id} ({class_name}): 警报级别 {alert_level}")
    
    return True

def main():
    """运行所有测试"""
    print("=================================================")
    print("      红外监控视频行为识别系统 - 诊断工具")
    print("=================================================")
    
    print(f"Python版本: {sys.version}")
    print(f"PyTorch版本: {torch.__version__}")
    print(f"OpenCV版本: {cv2.__version__}")
    print(f"设备: {'CUDA可用' if torch.cuda.is_available() else 'CPU'}")
    
    tests = [
        test_model_loading,
        check_class_mapping,
        test_video_reading,
        test_alarm_system
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试出错: {str(e)}")
            results.append(False)
    
    # 输出总结
    print("\n=================================================")
    print("                  诊断结果总结")
    print("=================================================")
    print(f"模型加载测试: {'通过' if results[0] else '失败'}")
    print(f"类别映射测试: {'通过' if results[1] else '失败'}")
    print(f"视频读取测试: {'通过' if results[2] else '失败'}")  
    print(f"报警系统测试: {'通过' if results[3] else '失败'}")
    
    all_passed = all(results)
    print(f"\n总体诊断结果: {'所有测试通过' if all_passed else '存在问题，请检查上方日志'}")

if __name__ == "__main__":
    main()
