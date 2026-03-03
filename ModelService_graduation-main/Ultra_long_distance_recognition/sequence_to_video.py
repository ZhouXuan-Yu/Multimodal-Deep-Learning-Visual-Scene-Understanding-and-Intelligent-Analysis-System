import os
import cv2
import glob
import numpy as np

def get_available_sequences():
    """获取数据集中所有可用的序列"""
    base_dir = "D:/Desktop/ModelService_graduation-main/RGBT-Tiny"
    dataset_path = os.path.join(base_dir, "data/RGBT-Tiny/images")
    
    # 列出images目录下的所有文件夹（每个文件夹代表一个序列）
    sequences = [d for d in os.listdir(dataset_path) 
                if os.path.isdir(os.path.join(dataset_path, d))]
    
    return sequences

def convert_frames_to_video(input_dir, output_path, fps=30, img_ext='jpg'):
    """将图像序列转换为视频文件
    
    Args:
        input_dir: 包含图像帧的目录
        output_path: 输出视频的路径
        fps: 视频帧率
        img_ext: 图像文件扩展名
    """
    # 获取所有图像帧的路径
    img_array = []
    file_pattern = os.path.join(input_dir, f'*.{img_ext}')
    files = sorted(glob.glob(file_pattern))
    
    if not files:
        # 如果没有找到指定扩展名的文件，尝试其他可能的扩展名
        for ext in ['png', 'jpeg', 'bmp']:
            if ext != img_ext:
                file_pattern = os.path.join(input_dir, f'*.{ext}')
                files = sorted(glob.glob(file_pattern))
                if files:
                    print(f"找到 {ext} 格式文件而不是 {img_ext}，将使用这些文件")
                    break
    
    if not files:
        raise ValueError(f"在 {input_dir} 中没有找到任何图像文件")
    
    print(f"找到 {len(files)} 个图像文件")
    
    # 读取第一个图像以获取尺寸
    sample_img = cv2.imread(files[0])
    if sample_img is None:
        raise ValueError(f"无法读取图像文件: {files[0]}")
    
    height, width, layers = sample_img.shape
    size = (width, height)
    
    # 创建VideoWriter对象
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 使用MP4编码
    out = cv2.VideoWriter(output_path, fourcc, fps, size)
    
    # 逐帧添加到视频
    for filename in files:
        img = cv2.imread(filename)
        if img is not None:
            out.write(img)
        else:
            print(f"警告: 无法读取 {filename}")
    
    # 释放VideoWriter
    out.release()
    print(f"视频已保存到: {output_path}")

def convert_sequence(sequence_name, fps=30):
    """将单个序列的可见光和热成像图像帧转换为视频"""
    base_dir = "D:/Desktop/ModelService_graduation-main/RGBT-Tiny"
    dataset_path = os.path.join(base_dir, "data/RGBT-Tiny/images")
    
    # 创建输出目录
    output_dir = os.path.join(base_dir, "output", sequence_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # 可见光图像路径
    visible_path = os.path.join(dataset_path, sequence_name, "00")
    # 热成像图像路径
    thermal_path = os.path.join(dataset_path, sequence_name, "01")
    
    # 检查目录是否存在
    if not os.path.exists(visible_path):
        print(f"错误: 可见光图像目录不存在: {visible_path}")
        return None, None
    
    if not os.path.exists(thermal_path):
        print(f"错误: 热成像图像目录不存在: {thermal_path}")
        return None, None
    
    # 输出视频路径
    visible_video_path = os.path.join(output_dir, f"{sequence_name}_visible.mp4")
    thermal_video_path = os.path.join(output_dir, f"{sequence_name}_thermal.mp4")
    
    try:
        print(f"正在将 {sequence_name} 的可见光图像转换为视频...")
        convert_frames_to_video(visible_path, visible_video_path, fps)
        
        print(f"正在将 {sequence_name} 的热成像图像转换为视频...")
        convert_frames_to_video(thermal_path, thermal_video_path, fps)
        
        return visible_video_path, thermal_video_path
    except Exception as e:
        print(f"转换过程中发生错误: {e}")
        return None, None

def main():
    """主函数"""
    print("=== 图像序列转视频工具 ===\n")
    
    # 获取可用序列列表
    sequence_list = get_available_sequences()
    
    if not sequence_list:
        print("错误: 未找到任何可用序列！")
        return
    
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
            
            if visible_video and thermal_video:
                print(f"\n转换完成!")
                print(f"可见光视频: {visible_video}")
                print(f"热成像视频: {thermal_video}")
        else:
            print("无效的选择!")
    except ValueError as e:
        print(f"错误: {e}")
        print("请输入有效的数字!")

if __name__ == "__main__":
    main()
