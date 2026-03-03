import os
import cv2
import glob
from tqdm import tqdm

def generate_video_from_frames(frames_dir, output_path, file_pattern, fps=30):
    """从图像帧生成视频"""
    # 查找所有匹配的图像文件
    pattern = os.path.join(frames_dir, file_pattern)
    image_files = sorted(glob.glob(pattern))
    
    if not image_files:
        print(f"错误: 未找到匹配的帧文件: {pattern}")
        return False
    
    print(f"找到 {len(image_files)} 个匹配 '{file_pattern}' 的图像文件")
    
    # 读取第一帧以获取尺寸
    first_frame = cv2.imread(image_files[0])
    if first_frame is None:
        print(f"错误: 无法读取图像文件: {image_files[0]}")
        return False
    
    height, width = first_frame.shape[:2]
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 将每一帧写入视频
    print(f"正在生成视频: {output_path}")
    for img_path in tqdm(image_files):
        frame = cv2.imread(img_path)
        if frame is not None:
            video_writer.write(frame)
    
    # 释放资源
    video_writer.release()
    
    # 检查生成的视频文件
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        print(f"视频成功创建: {output_path} (大小: {file_size:.2f} MB)")
        return True
    else:
        print(f"错误: 视频创建失败: {output_path}")
        return False

def main():
    # 设置输出目录
    output_dir = r"D:\Desktop\ModelService_graduation-main\RGBT-Tiny\output\6666"
    sequence_name = "6666"
    
    # 生成原始结果视频
    original_result_video = os.path.join(output_dir, f"{sequence_name}_original_result.mp4")
    generate_video_from_frames(
        output_dir, 
        original_result_video, 
        "*_original_result.jpg"
    )
    
    # 生成原始热成像视频
    original_thermal_video = os.path.join(output_dir, f"{sequence_name}_original_thermal.mp4")
    generate_video_from_frames(
        output_dir, 
        original_thermal_video, 
        "*_original_thermal.jpg"
    )
    
    # 生成标准视频（如果还没有）
    result_video = os.path.join(output_dir, f"{sequence_name}_result.mp4")
    if not os.path.exists(result_video):
        generate_video_from_frames(
            output_dir, 
            result_video, 
            "*_result.jpg"
        )
    
    # 生成可见光视频
    visible_video = os.path.join(output_dir, f"{sequence_name}_visible.mp4")
    generate_video_from_frames(
        output_dir, 
        visible_video, 
        "*_visible.jpg"
    )
    
    # 生成热成像视频
    thermal_video = os.path.join(output_dir, f"{sequence_name}_thermal.mp4")
    generate_video_from_frames(
        output_dir, 
        thermal_video, 
        "*_thermal.jpg"
    )

if __name__ == "__main__":
    main()
