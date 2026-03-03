import os
import cv2
import glob
import numpy as np

def frames_to_video(frame_folder, output_video_path, fps=30.0):
    """
    简单的帧到视频转换函数
    """
    try:
        # 确保FPS大于等于1，这是OpenCV的要求
        if fps < 1.0:
            print(f"警告: FPS设置过低 ({fps}), 已自动调整为1.0")
            fps = 1.0
            
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
        
        # 获取所有图像
        frames = []
        for ext in ['*.jpg', '*.png']:
            pattern = os.path.join(frame_folder, ext)
            frames.extend(sorted(glob.glob(pattern)))
        
        if not frames:
            print(f"错误: 在 {frame_folder} 中没有找到图像帧")
            return False
        
        print(f"找到 {len(frames)} 个图像，开始合成视频...")
        
        # 读取第一帧获取尺寸
        first_frame = cv2.imread(frames[0])
        if first_frame is None:
            print(f"错误: 无法读取第一帧")
            return False
            
        h, w, _ = first_frame.shape
        
        # 使用最基本的编解码器
        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        
        # 确保输出路径是绝对路径且格式正确
        output_video_path = os.path.abspath(output_video_path)
        # 确保目录存在
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
        
        # Windows下确保视频编解码器能正常工作的扩展名
        if not output_video_path.lower().endswith(('.avi')):
            output_video_path = output_video_path + '.avi'
            print(f"为确保兼容性，输出文件已修改为: {output_video_path}")
            
        # 使用临时文件避免路径问题
        temp_dir = os.path.dirname(output_video_path)
        temp_output = os.path.join(temp_dir, 'temp_video.avi')
        
        # 确保使用兼容的fourcc编解码器
        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')  # 最常用的AVI编解码器
        print(f"尝试使用MJPG编解码器创建视频: {temp_output}，尺寸: {w}x{h}，帧率: {fps}")
        
        out = cv2.VideoWriter(temp_output, fourcc, fps, (w, h))
        if not out.isOpened():
            print("MJPG编解码器失败，尝试无压缩格式")
            fourcc = 0  # 无压缩
            out = cv2.VideoWriter(temp_output, fourcc, fps, (w, h))
            
        if not out.isOpened():
            print("所有编解码器尝试均失败")
            return False
            
        # 写入帧
        success_count = 0
        total_frames = len(frames)
        
        print(f"开始写入 {total_frames} 帧到视频文件...")
        for i, frame_path in enumerate(frames):
            try:
                frame = cv2.imread(frame_path)
                if frame is not None:
                    # 确保帧尺寸正确
                    if frame.shape[1] != w or frame.shape[0] != h:
                        frame = cv2.resize(frame, (w, h))
                    out.write(frame)
                    success_count += 1
                    # 每处理10%的帧显示一次进度
                    if success_count % max(1, total_frames // 10) == 0:
                        progress_percent = (success_count/total_frames*100)
                        print(f"进度: {success_count}/{total_frames} 帧 ({progress_percent:.1f}%)")
            except Exception as e:
                print(f"处理帧 {frame_path} 时出错: {str(e)}")
                
        # 释放资源
        out.release()
        
        # 检查输出文件
        if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
            # 重命名为最终文件
            try:
                if os.path.exists(output_video_path):
                    os.remove(output_video_path)
                os.rename(temp_output, output_video_path)
                print(f"视频成功创建: {output_video_path} (共写入 {success_count}/{total_frames} 帧)")
                # 验证文件可读性
                cap = cv2.VideoCapture(output_video_path)
                if cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        print("视频文件已验证，可以正常读取")
                    else:
                        print("警告：视频文件创建成功但无法读取帧，可能是编解码器问题")
                return True
            except Exception as e:
                print(f"重命名文件时出错: {str(e)}")
                if os.path.exists(temp_output):
                    print(f"临时文件已创建并保留: {temp_output}")
                    return True
        else:
            print("视频创建失败，未生成有效文件")
            return False
            
    except Exception as e:
        print(f"视频合成错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False