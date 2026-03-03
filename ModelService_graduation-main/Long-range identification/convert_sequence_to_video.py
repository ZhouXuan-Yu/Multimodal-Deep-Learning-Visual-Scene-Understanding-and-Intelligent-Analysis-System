import os
import cv2
import numpy as np
from integrated_processing import frames_to_video, get_sequence_list

def convert_sequence(sequence_name, fps=30):
    """将单个序列的图像帧转换为视频"""
    base_dir = "D:/Desktop/ModelService_graduation-main/RGBT-Tiny"
    dataset_path = os.path.join(base_dir, "data/RGBT-Tiny")
    images_path = os.path.join(dataset_path, "images")
    
    # 创建输出目录
    output_dir = os.path.join(base_dir, "output", sequence_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # 可见光图像路径
    visible_path = os.path.join(images_path, sequence_name, "00")
    # 热成像图像路径
    thermal_path = os.path.join(images_path, sequence_name, "01")
    
    # 输出视频路径
    visible_video_path = os.path.join(output_dir, f"{sequence_name}_visible.mp4")
    thermal_video_path = os.path.join(output_dir, f"{sequence_name}_thermal.mp4")
    
    print(f"正在将 {sequence_name} 的可见光图像转换为视频...")
    frames_to_video(visible_path, visible_video_path, fps=fps)
    
    print(f"正在将 {sequence_name} 的热成像图像转换为视频...")
    frames_to_video(thermal_path, thermal_video_path, fps=fps)
    
    print(f"转换完成。视频保存在: {output_dir}")
    return visible_video_path, thermal_video_path

if __name__ == "__main__":
    # 获取可用序列列表
    sequence_list = get_sequence_list()
    
    print("可用序列列表:")
    for i, seq in enumerate(sequence_list):
        print(f"{i+1}. {seq}")
    
    try:
        choice = int(input("\n请选择要转换的序列 (输入编号): "))
        if 1 <= choice <= len(sequence_list):
            selected_sequence = sequence_list[choice-1]
            
            # 选择帧率
            fps = int(input("请输入视频帧率 (默认30): ") or "30")
            
            # 执行转换
            visible_video, thermal_video = convert_sequence(selected_sequence, fps)
            print(f"\n转换完成!")
            print(f"可见光视频: {visible_video}")
            print(f"热成像视频: {thermal_video}")
        else:
            print("无效的选择!")
    except ValueError:
        print("请输入有效的数字!")
