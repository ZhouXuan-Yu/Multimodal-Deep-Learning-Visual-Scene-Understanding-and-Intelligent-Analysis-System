"""
火灾检测与报警系统演示脚本

用法:
python demo_fire_alarm.py --input D:\Desktop\ModelService_graduation-main\Fire-Detection-UAV-Aerial-Image-Classification-Segmentation-UnmannedAerialVehicle-main\wildfire.mp4 --output video/processed_video.mp4 --email 2769220120@qq.com
"""

import os
import argparse
import time

# 从fire_detector导入正确的函数
from fire_detector import load_models
from fire_alarm import FireAlarmSystem

def main():
    """主函数，处理命令行参数并运行演示"""
    parser = argparse.ArgumentParser(description="火灾检测与报警系统演示")
    
    # 必要参数
    parser.add_argument("--input", required=True, help="输入视频路径")
    
    # 可选参数
    parser.add_argument("--output", help="输出视频路径(可选)")
    parser.add_argument("--email", default="2769220120@qq.com", help="接收报警邮件的地址")
    parser.add_argument("--use_external", action="store_true", help="使用外网Gmail发送邮件(默认使用QQ邮箱)")
    parser.add_argument("--threshold", type=float, default=0.7, help="火灾检测置信度阈值(默认0.7)")
    parser.add_argument("--area_threshold", type=float, default=5.0, help="火灾面积百分比阈值(默认5.0)")
    parser.add_argument("--cooldown", type=int, default=60, help="报警冷却时间(秒)(默认60)")
    parser.add_argument("--save_frames", action="store_true", help="保存处理后的视频帧")
    parser.add_argument("--frames_dir", help="保存帧的目录(可选)")
    
    args = parser.parse_args()
    
    # 验证输入视频路径
    if not os.path.exists(args.input):
        print(f"错误: 输入视频文件不存在: {args.input}")
        return
    
    # 如果指定了保存帧但未指定目录，创建默认目录
    if args.save_frames and not args.frames_dir:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        args.frames_dir = f"frames_{base_name}_{int(time.time())}"
        print(f"将使用默认帧目录: {args.frames_dir}")
    
    # 加载模型 (使用正确的load_models函数)
    print("正在加载火灾检测模型...")
    try:
        classification_model, segmentation_model = load_models()
        if not classification_model or not segmentation_model:
            print("错误: 模型加载失败，请确保模型文件存在")
            return
    except Exception as e:
        print(f"错误: 模型加载失败 - {str(e)}")
        return
    
    print("模型加载成功!")
    
    # 创建火灾报警系统
    print(f"初始化火灾报警系统 (使用{'外网Gmail' if args.use_external else 'QQ邮箱'}发送报警)")
    alarm_system = FireAlarmSystem(
        use_external=args.use_external,
        cooldown_seconds=args.cooldown
    )
    
    # 开始处理视频
    print("\n开始处理视频并监控火灾...")
    print(f"火灾检测置信度阈值: {args.threshold}")
    print(f"火灾面积百分比阈值: {args.area_threshold}%")
    print(f"报警邮件接收地址: {args.email}")
    print(f"报警冷却时间: {args.cooldown}秒")
    
    # 处理视频
    alarm_system.process_video_with_alarm(
        video_path=args.input,
        output_path=args.output,
        receiver_email=args.email,
        classification_model=classification_model,
        segmentation_model=segmentation_model,
        fire_confidence_threshold=args.threshold,
        fire_area_threshold=args.area_threshold,
        save_frames=args.save_frames,
        frames_dir=args.frames_dir
    )
    
    print("\n演示完成!")

if __name__ == "__main__":
    main()
