"""
基于OpenCV的轻量级火灾检测工具 - 不依赖TensorFlow
支持图像和视频分析，使用颜色和亮度特征检测火灾
"""
import os
import cv2
import numpy as np
import argparse
import time
from tqdm import tqdm
import matplotlib.pyplot as plt

def detect_fire_by_color(image, min_area_percentage=0.01, sensitivity=50):
    """
    使用颜色特征检测火灾
    
    参数:
        image: 输入BGR图像
        min_area_percentage: 最小火灾区域占比
        sensitivity: 敏感度，值越高检测越灵敏（但可能有更多误报）
    
    返回:
        (is_fire, fire_mask, fire_percentage, confidence)
    """
    # 转换到HSV颜色空间，更容易检测颜色
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 提取图像尺寸
    height, width, _ = image.shape
    total_pixels = height * width
    
    # 红色的HSV范围（火焰和火灾通常呈红色、橙色或黄色）
    # 低敏感度设置
    lower_red1 = np.array([0, 70, 70])
    upper_red1 = np.array([10 + sensitivity//10, 255, 255])
    
    # 暗红/橙色
    lower_red2 = np.array([160, 70, 70])
    upper_red2 = np.array([180, 255, 255])
    
    # 创建掩码
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    
    # 增强特征 - 删除小区域并填充空洞
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # 计算火灾区域比例
    fire_pixels = cv2.countNonZero(mask)
    fire_percentage = (fire_pixels / total_pixels) * 100
    
    # 使用亮度作为附加特征
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = cv2.mean(gray)[0]  # 平均亮度
    
    # 检查相应颜色区域的亮度
    brightened_region = cv2.bitwise_and(gray, gray, mask=mask)
    if fire_pixels > 0:
        fire_brightness = cv2.mean(brightened_region, mask=mask)[0]
    else:
        fire_brightness = 0
        
    # 根据检测到的火灾区域和亮度计算置信度
    if fire_percentage > min_area_percentage and fire_brightness > brightness:
        confidence = min(1.0, (fire_percentage / 10.0) * (fire_brightness / 200.0))
        is_fire = confidence > 0.2
    else:
        confidence = 0
        is_fire = False
    
    return is_fire, mask, fire_percentage, confidence

def process_image(img, display=True, save_path=None, sensitivity=50):
    """
    处理单张图像，检测火灾
    """
    # 如果图像太大，调整大小以加快处理速度
    height, width = img.shape[:2]
    max_dimension = 800
    
    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)
        img = cv2.resize(img, None, fx=scale, fy=scale)
    
    # 检测火灾
    is_fire, fire_mask, fire_percentage, confidence = detect_fire_by_color(img, 
                                                                           sensitivity=sensitivity)
    
    # 可视化结果
    result_img = img.copy()
    
    # 创建彩色掩码显示
    fire_mask_colored = cv2.cvtColor(fire_mask, cv2.COLOR_GRAY2BGR)
    fire_mask_colored[:,:,0] = 0  # 蓝色通道为0
    fire_mask_colored[:,:,1] = 0  # 绿色通道为0
    # 只保留红色通道中的掩码值
    
    # 将掩码半透明叠加到图像上
    overlay = cv2.addWeighted(result_img, 1.0, fire_mask_colored, 0.5, 0)
    
    # 添加文本信息
    status = "Fire Detected!" if is_fire else "No Fire"
    color = (0, 0, 255) if is_fire else (0, 255, 0)
    cv2.putText(overlay, f"Status: {status}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(overlay, f"Confidence: {confidence:.2f}", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(overlay, f"Fire Area: {fire_percentage:.1f}%", (10, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    # 显示或保存结果
    if display:
        try:
            cv2.imshow("Fire Detection", overlay)
            cv2.waitKey(1)
        except Exception as e:
            print(f"无法显示图像: {e}")
    
    if save_path:
        cv2.imwrite(save_path, overlay)
        
    return {
        "is_fire": is_fire,
        "confidence": confidence,
        "fire_percentage": fire_percentage,
        "result_image": overlay
    }

def process_video(video_path, output_path=None, display=True, save_interval=1, 
                 save_frames=False, frames_dir=None, sensitivity=50):
    """
    处理视频文件，检测火灾
    """
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"无法打开视频: {video_path}")
        return
    
    # 获取视频属性
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"\n处理视频: {video_path}")
    print(f"分辨率: {width}x{height}, FPS: {fps}, 总帧数: {total_frames}")
    
    # 准备输出视频
    out = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 或尝试 'XVID'
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 创建保存帧的目录
    if save_frames:
        if frames_dir is None:
            frames_dir = os.path.splitext(output_path)[0] + "_frames"
        os.makedirs(frames_dir, exist_ok=True)
        print(f"\n将保存处理后的帧到: {frames_dir}")
    
    # 处理进度条
    time_start = time.time()
    frame_count = 0
    
    try:
        with tqdm(total=total_frames, desc="处理视频", unit="帧") as pbar:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 每隔save_interval帧处理一次
                if frame_count % save_interval == 0:
                    # 处理当前帧
                    results = process_image(
                        frame, 
                        display=display,
                        sensitivity=sensitivity
                    )
                    
                    # 获取处理后的图像
                    output_frame = results["result_image"]
                    
                    # 写入输出视频
                    if out:
                        out.write(output_frame)
                    
                    # 保存当前帧图像
                    if save_frames:
                        frame_filename = os.path.join(frames_dir, f"frame_{frame_count:06d}.jpg")
                        cv2.imwrite(frame_filename, output_frame)
                        
                        # 每10帧或每秒打印一次处理信息
                        if frame_count % 10 == 0:
                            fire_status = "火灾" if results["is_fire"] else "无火灾"
                            print(f"帧 #{frame_count}: {fire_status}, 置信度: {results['confidence']:.2f}, 火灾区域: {results['fire_percentage']:.1f}%")
                
                frame_count += 1
                pbar.update(1)
                
                # 每100帧更新一次进度信息
                if frame_count % 100 == 0:
                    elapsed_time = time.time() - time_start
                    frames_remaining = total_frames - frame_count
                    if frame_count > 0:
                        time_per_frame = elapsed_time / frame_count
                        est_time_remaining = frames_remaining * time_per_frame
                        pbar.set_postfix({
                            "处理速度": f"{1/time_per_frame:.1f} fps",
                            "剩余时间": f"{est_time_remaining/60:.1f} 分钟"
                        })
    
    finally:
        # 清理资源
        cap.release()
        if out:
            out.release()
        if display:
            try:
                cv2.destroyAllWindows()
            except:
                pass
    
    print(f"\n视频处理完成，总计 {frame_count} 帧")
    if output_path:
        print(f"已保存处理后的视频到: {output_path}")

def main():
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='OpenCV火灾检测工具 - 支持图像和视频')
    
    # 输入输出参数
    parser.add_argument('--input', required=True, help='输入图像或视频的路径')
    parser.add_argument('--output', help='输出文件路径 (可选)')
    
    # 其他选项
    parser.add_argument('--sensitivity', type=int, default=50, help='检测敏感度 (0-100), 默认: 50')
    parser.add_argument('--no_display', action='store_true', help='不显示处理结果窗口')
    parser.add_argument('--save_interval', type=int, default=1, help='视频模式下，每隔多少帧保存一次结果 (默认: 1)')
    parser.add_argument('--save_frames', action='store_true', help='是否保存处理后的视频帧到文件夹')
    parser.add_argument('--frames_dir', help='保存处理后帧的文件夹路径 (可选)')
    
    args = parser.parse_args()
    
    # 检查输入是图像还是视频
    input_path = args.input
    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在: {input_path}")
        return
    
    # 确定输入类型并处理
    is_video = input_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv'))
    
    if is_video:
        # 处理视频
        output_path = args.output if args.output else os.path.splitext(input_path)[0] + "_processed.mp4"
        process_video(
            input_path,
            output_path=output_path,
            display=not args.no_display,
            save_interval=args.save_interval,
            save_frames=args.save_frames,
            frames_dir=args.frames_dir,
            sensitivity=args.sensitivity
        )
    else:
        # 处理图像
        img = cv2.imread(input_path)
        if img is None:
            print(f"错误: 无法读取图像: {input_path}")
            return
        
        output_path = args.output if args.output else os.path.splitext(input_path)[0] + "_processed.jpg"
        process_image(
            img,
            display=not args.no_display,
            save_path=output_path,
            sensitivity=args.sensitivity
        )
        
        if not args.no_display:
            print("按任意键退出...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
