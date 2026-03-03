import os
import cv2
import glob
import numpy as np
from tqdm import tqdm

def create_video_from_frames(frames_dir, output_video_path, fps=30, extensions=('jpg', 'png'), file_pattern=None):
    """
    将图像帧合成为视频文件，支持多种图像格式。
    
    Args:
        frames_dir: 包含图像帧的目录路径
        output_video_path: 输出视频文件路径
        fps: 视频帧率，默认30
        extensions: 图像文件扩展名元组，默认支持jpg和png
        file_pattern: 自定义文件模式，默认为None
        
    Returns:
        bool: 成功返回True，失败返回False
    """
    # 检查目录是否存在
    if not os.path.exists(frames_dir):
        print(f"错误: 帧目录不存在: {frames_dir}")
        return False
    
    # 获取所有图像帧的路径
    image_files = []
    
    # 使用自定义文件模式或默认扩展名模式
    if file_pattern:
        # 使用自定义模式（如*_visible.jpg）
        pattern = os.path.join(frames_dir, file_pattern)
        files = sorted(glob.glob(pattern))
        print(f"使用自定义文件模式: {pattern}，找到 {len(files)} 个文件")
    else:
        # 使用默认扩展名模式
        for ext in extensions:
            # 对每个扩展名进行查找
            pattern = os.path.join(frames_dir, f"*.{ext}")
            files = sorted(glob.glob(pattern))
            if files:
                print(f"找到 {len(files)} 个 {ext} 格式的文件")
                image_files.extend(files)
    
    # 检查是否找到图像文件
    if not image_files:
        print(f"警告: 在 {frames_dir} 中没有找到任何图像文件 (支持格式: {extensions})")
        return False
    
    # 对文件进行排序
    # 按照数字顺序排序，假设文件名格式为 xxxxx_result.jpg
    image_files.sort(key=lambda x: int(os.path.basename(x).split('_')[0]))
    
    print(f"准备处理 {len(image_files)} 个图像帧...")
    
    # 读取第一帧获取分辨率
    first_frame = cv2.imread(image_files[0])
    if first_frame is None:
        print(f"错误: 无法读取图像: {image_files[0]}")
        return False
    
    height, width, channels = first_frame.shape
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 使用MP4编码
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    # 逐帧写入
    for img_file in tqdm(image_files, desc="合成视频"):
        frame = cv2.imread(img_file)
        if frame is not None:
            video_writer.write(frame)
        else:
            print(f"警告: 无法读取图像: {img_file}")
    
    # 释放资源
    video_writer.release()
    
    # 验证视频文件是否创建成功
    if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
        print(f"视频成功创建: {output_video_path}")
        print(f"视频文件大小: {os.path.getsize(output_video_path) / (1024*1024):.2f} MB")
        return True
    else:
        print(f"错误: 视频创建失败或文件大小为0")
        return False

if __name__ == "__main__":
    # 测试函数
    import argparse
    
    parser = argparse.ArgumentParser(description="将图像帧合成为视频")
    parser.add_argument("--frames_dir", required=True, help="包含图像帧的目录路径")
    parser.add_argument("--output", required=True, help="输出视频文件路径")
    parser.add_argument("--fps", type=int, default=30, help="视频帧率，默认30")
    
    args = parser.parse_args()
    
    create_video_from_frames(args.frames_dir, args.output, args.fps)
