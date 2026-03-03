import argparse
import os
import sys
import time
import torch
import cv2
import numpy as np
from torch.autograd import Variable
from PIL import Image
from ultralytics import YOLO

# 导入自定义模块
sys.path.append('./Night-vehicle-detection-system-main/new_detection/main')
from model import Network
from video_utils import video2frame, frame2video

# 参数解析
parser = argparse.ArgumentParser(description="低光照图像增强与YOLOv8目标检测系统")
parser.add_argument('--input_image', type=str, default="", help='输入图像路径')
parser.add_argument('--input_video', type=str, default="", help='输入视频路径')
parser.add_argument('--input_stream', type=str, default="", help='输入流，使用"camera"表示摄像头')
parser.add_argument('--output_video', type=str, default="output.mp4", help='输出视频路径')
parser.add_argument('--e_model', type=str, default='./Night-vehicle-detection-system-main/new_detection/weights/enhance_weights/medium.pt', help='增强模型路径')
parser.add_argument('--d_model', type=str, default="./Night-vehicle-detection-system-main/new_detection/weights/detect_weights/yolov8s.pt", help='检测模型路径')
parser.add_argument('--gpu', type=int, default=0, help='gpu设备ID')
parser.add_argument('--conf', type=float, default=0.25, help='检测置信度阈值')
args = parser.parse_args()


def enhance_image(image_path, enhance_model):
    """增强单张图像"""
    print(f"正在增强图像: {image_path}")
    
    # 读取图像
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img / 255.0
    img = torch.from_numpy(img.transpose(2, 0, 1)).float().unsqueeze(0)
    
    # 使用增强模型
    with torch.no_grad():
        enhanced_img = enhance_model(img)
    
    # 返回处理后的PIL图像
    return enhanced_img


def detect_image(image, detect_model, conf=0.25, save_path=None):
    """在图像上执行目标检测"""
    # 对PIL图像进行目标检测
    results = detect_model.predict(source=image, conf=conf, save=True if save_path else False, 
                                  project="result/predict", name="image")
    
    # 返回检测结果和处理后的图像
    return results


def process_video(video_path, enhance_model, detect_model, output_path, conf=0.25):
    """处理视频文件"""
    print(f"正在处理视频: {video_path}")
    
    # 定义输出文件夹的路径
    output_folders = ["video/output_folder_1/", "video/output_folder_2/", "video/output_folder_3/",
                    "video/output_folder_4/", "video/output_folder_5/", "video/output_folder_6/"]

    enhance_folders = ["result/enhance/output_folder_1/", "result/enhance/output_folder_2/",
                    "result/enhance/output_folder_3/", "result/enhance/output_folder_4/", 
                    "result/enhance/output_folder_5/", "result/enhance/output_folder_6/"]
    
    # 创建必要的目录
    for folder in output_folders + enhance_folders:
        os.makedirs(folder, exist_ok=True)
    
    # 定义输出图片的路径
    out_frame_path = "video/output_frames/"
    os.makedirs(out_frame_path, exist_ok=True)
    
    # 视频转帧
    width, height, fps = video2frame(video_path, out_frame_path, output_folders)
    
    # 定义增强图像的函数
    def enhance(data_path, model, save_path):
        os.makedirs(save_path, exist_ok=True)
        files = [f for f in os.listdir(data_path) if f.endswith(('.jpg', '.png', '.jpeg'))]
        files.sort()
        
        for file in files:
            input_path = os.path.join(data_path, file)
            # 读取并增强图像
            img = cv2.imread(input_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img / 255.0
            img = torch.from_numpy(img.transpose(2, 0, 1)).float().unsqueeze(0)
            
            # 使用增强模型
            with torch.no_grad():
                enhanced_img = model(img)
            
            # 保存增强后的图像
            output_path = os.path.join(save_path, file.split('.')[0] + '.png')
            enhanced_img.save(output_path, "png")
            print(f'处理 {file}')
    
    # 增强每个文件夹中的图像
    for i in range(len(output_folders)):
        enhance(output_folders[i], enhance_model, enhance_folders[i])
    
    # 将增强后的图像合成视频
    enhanced_video_path = "video/enhanced_video.mp4"
    frame2video(enhance_folders, height, width, fps, enhanced_video_path)
    
    # 对增强后的视频进行目标检测
    results = detect_model.predict(enhanced_video_path, save=True, conf=conf,
                                 project="result/predict", name="video")
    
    # 移动检测结果到指定输出路径
    detected_video = os.path.join("result/predict/video", os.path.basename(enhanced_video_path))
    if os.path.exists(detected_video):
        import shutil
        shutil.copy(detected_video, output_path)
        print(f"检测结果已保存至: {output_path}")
    
    return results


def process_camera(enhance_model, detect_model, conf=0.25):
    """处理实时摄像头视频流"""
    print("开始处理摄像头视频流...")
    
    # 打开摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    while True:
        # 读取帧
        ret, frame = cap.read()
        if not ret:
            print("无法接收帧，退出...")
            break
        
        # 转换图像格式
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = rgb_frame / 255.0
        img = torch.from_numpy(img.transpose(2, 0, 1)).float().unsqueeze(0)
        
        # 增强图像
        with torch.no_grad():
            enhanced_img = enhance_model(img)
        
        # PIL转换为OpenCV格式
        enhanced_np = np.array(enhanced_img)
        enhanced_cv = cv2.cvtColor(enhanced_np, cv2.COLOR_RGB2BGR)
        
        # 目标检测
        results = detect_model.predict(source=enhanced_np, conf=conf, verbose=False)
        
        # 在增强后的图像上绘制检测结果
        annotated_frame = results[0].plot()
        
        # 显示结果
        cv2.imshow('Enhanced Detection', annotated_frame)
        
        # 按'q'退出
        if cv2.waitKey(1) == ord('q'):
            break
    
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()


def main():
    s_t = time.time()
    
    # 加载增强模型
    print("加载增强模型...")
    enhance_model = Network(args.e_model).to("cpu")
    enhance_model.eval()
    
    # 加载检测模型
    print("加载检测模型...")
    detect_model = YOLO(args.d_model)
    
    # 处理不同类型的输入
    if args.input_image:
        # 处理单张图像
        enhanced_img = enhance_image(args.input_image, enhance_model)
        results = detect_image(enhanced_img, detect_model, args.conf)
        print(f"图像处理完成，结果保存在 result/predict/image/")
    
    elif args.input_video:
        # 处理视频
        results = process_video(args.input_video, enhance_model, detect_model, 
                               args.output_video, args.conf)
        print(f"视频处理完成，结果保存在 {args.output_video}")
    
    elif args.input_stream == "camera":
        # 处理摄像头
        process_camera(enhance_model, detect_model, args.conf)
    
    else:
        print("错误：请指定输入源 (--input_image, --input_video, 或 --input_stream camera)")
        return
    
    print(f"总耗时: {time.time() - s_t:.2f} 秒")


if __name__ == '__main__':
    # 确保创建必要的目录
    os.makedirs("video", exist_ok=True)
    os.makedirs("video/output_frames", exist_ok=True)
    os.makedirs("result/predict", exist_ok=True)
    os.makedirs("result/enhance", exist_ok=True)
    
    main()
