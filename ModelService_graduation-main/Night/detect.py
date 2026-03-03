import argparse
import os
import sys
import time
import torch
import cv2
import numpy as np
from torch.autograd import Variable
from PIL import Image, ImageEnhance
from ultralytics import YOLO

# 图像处理工具函数

def apply_clahe(img):
    """应用自适应直方图均衡化(CLAHE)增强图像对比度"""
    # 转换为LAB色彩空间
    if isinstance(img, np.ndarray):
        # 如果是NumPy数组（OpenCV格式）
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 对L通道应用CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        
        # 合并通道
        merged = cv2.merge((cl, a, b))
        
        # 转回原始色彩空间
        enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        return enhanced
    else:
        # 如果是PIL图像
        img_np = np.array(img)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)  # PIL是RGB格式
        enhanced = apply_clahe(img_np)  # 递归调用
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)  # 转回RGB
        return Image.fromarray(enhanced)

def denoise_image(img):
    """应用去噪算法减少图像噪点"""
    if isinstance(img, np.ndarray):
        # 对OpenCV格式的图像进行处理
        return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
    else:
        # 如果是PIL图像
        img_np = np.array(img)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)  # PIL是RGB格式
        denoised = denoise_image(img_np)  # 递归调用
        denoised = cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB)  # 转回RGB
        return Image.fromarray(denoised)

def adjust_gamma(img, gamma=1.5):
    """调整图像的gamma值提高亮度"""
    if isinstance(img, np.ndarray):
        # 创建查询表
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
        
        # 应用查询表
        return cv2.LUT(img, table)
    else:
        # 如果是PIL图像
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(gamma)

def increase_contrast(img, factor=1.5):
    """增强图像对比度"""
    if isinstance(img, np.ndarray):
        # 使用OpenCV处理
        alpha = factor  # 对比度控制
        beta = 10       # 亮度控制
        return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    else:
        # 如枟是PIL图像
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(factor)

def create_night_vision_effect(img):
    """创建夜视仪效果"""
    if isinstance(img, np.ndarray):
        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 应用CLAHE增强对比度
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # 转换回彩色（绿色调）
        green_tint = np.zeros_like(img)
        green_tint[:, :, 0] = 0    # B通道
        green_tint[:, :, 1] = enhanced  # G通道
        green_tint[:, :, 2] = 0    # R通道
        
        # 增加噪点
        noise = np.zeros_like(img)
        cv2.randn(noise, 0, 25)  # 添加高斯噪声
        
        # 合并噪声和夜视效果
        result = cv2.add(green_tint, noise)
        return result
    else:
        # 如果是PIL图像
        img_np = np.array(img)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)  # PIL是RGB格式
        night_vision = create_night_vision_effect(img_np)  # 递归调用
        night_vision = cv2.cvtColor(night_vision, cv2.COLOR_BGR2RGB)  # 转回RGB
        return Image.fromarray(night_vision)


# u5bfcu5165u81eau5b9au4e49u6a21u5757
sys.path.append('./Night-vehicle-detection-system/new_detection/main')
from model import Network
from video_utils import video2frame, frame2video
from enhance_methods import advanced_enhance

# 导入自定义视频处理模块
from video_processor import frames_to_video


# u53c2u6570u89e3u6790
parser = argparse.ArgumentParser(description="u4f4eu5149u7167u56feu50cfu589eu5f3au4e0eYOLOv8u76eeu6807u68c0u6d4bu7cfbu7edf")
parser.add_argument('--input_image', type=str, default="", help='u8f93u5165u56feu50cfu8defu5f84')
parser.add_argument('--input_video', type=str, default="", help='u8f93u5165u89c6u9891u8defu5f84')
parser.add_argument('--input_stream', type=str, default="", help='u8f93u5165u6d41uff0cu4f7fu7528"camera"u8868u793au6444u50cfu5934')
parser.add_argument('--output_video', type=str, default="output.mp4", help='u8f93u51fau89c6u9891u8defu5f84')
parser.add_argument('--e_model', type=str, default='./Night-vehicle-detection-system/new_detection/weights/enhance_weights/medium.pt', help='u589eu5f3au6a21u578bu8defu5f84')
parser.add_argument('--d_model', type=str, default="./Night-vehicle-detection-system/new_detection/weights/detect_weights/yolov8s.pt", help='u68c0u6d4bu6a21u578bu8defu5f84')
parser.add_argument('--gpu', type=int, default=0, help='gpuu8bbeu5907ID')
parser.add_argument('--conf', type=float, default=0.25, help='u68c0u6d4bu7f6eu4fe1u5ea6u9608u503c')
parser.add_argument('--night_vision', action='store_true', help='u542fu7528u591cu89c6u6a21u5f0fuff0cu7c7bu4f3cu591cu89c6u4eeau6548u679c')
parser.add_argument('--enhance_method', type=str, default='retinex', 
                    choices=['deep', 'clahe', 'gamma', 'all', 'retinex', 'zero_dce', 'enlightengan', 'kind'], 
                    help='u56feu50cfu589eu5f3au65b9u6cd5: deep(u6df1u5ea6u5b66u4e60), clahe(CLAHE), gamma(gamma), all(u7ec4u5408u65b9u6cd5), retinex(Retinexu7b97u6cd5), zero_dce(Zero-DCE), enlightengan(EnlightenGAN), kind(KinD)')
args = parser.parse_args()


def enhance_image(image_path, enhance_model, night_vision_mode=False, enhance_method='retinex'):
    """增强单张图像，支持多种增强方式和夜视模式"""
    print(f"u6b63u5728u589eu5f3au56feu50cf: {image_path}")
    print(f"使用增强方法: {enhance_method}, 夜视模式: {'开启' if night_vision_mode else '关闭'}")
    
    # 读取原始图像
    orig_img = cv2.imread(image_path)
    
    # 选择不同的增强方法
    if enhance_method in ['retinex', 'zero_dce', 'enlightengan', 'kind']:
        # 使用高级增强算法 (Retinex, Zero-DCE, EnlightenGAN, KinD)
        print(f"应用{enhance_method}高级增强算法...")
        enhanced_img = advanced_enhance(orig_img, enhance_method)
    else:
        # 使用传统或深度学习方法
        # 先应用传统图像处理方法（根据选择）
        if enhance_method in ['clahe', 'all']:
            # 应用CLAHE
            print("应用CLAHE增强...")
            orig_img = apply_clahe(orig_img)
            
        if enhance_method in ['gamma', 'all']:
            # 应用Gamma矩正
            print("应用Gamma矩正...")
            orig_img = adjust_gamma(orig_img, 1.8)
        
        # 应用去噪
        orig_img = denoise_image(orig_img)
        
        # 图像标准化用于深度学习模型
        img = cv2.cvtColor(orig_img, cv2.COLOR_BGR2RGB)
        img = img / 255.0
        img = torch.from_numpy(img.transpose(2, 0, 1)).float().unsqueeze(0)
        
        # 如果选择深度学习方法或组合方法
        if enhance_method in ['deep', 'all']:
            # 使用深度学习增强模型
            print("应用深度学习增强...")
            with torch.no_grad():
                enhanced_img = enhance_model(img, night_vision_mode=night_vision_mode)
        else:
            # 如果不使用深度学习方法，直接转为PIL并应用夜视模式（如果选择）
            if night_vision_mode:
                # 如果需要夜视模式而不使用深度学习
                orig_img_rgb = cv2.cvtColor(orig_img, cv2.COLOR_BGR2RGB)
                enhanced_img = Image.fromarray(create_night_vision_effect(orig_img_rgb))
            else:
                # 否则直接使用处理后的图像
                enhanced_img = Image.fromarray(cv2.cvtColor(orig_img, cv2.COLOR_BGR2RGB))
    
    # 返回处理后的PIL图像
    return enhanced_img


def detect_image(image, detect_model, conf=0.25, save_path=None):
    """u5728u56feu50cfu4e0au6267u884cu76eeu6807u68c0u6d4b"""
    # 创建保存目录
    output_dir = os.path.join(os.getcwd(), "picture", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取原始图像文件名并使用同名但添加_detected后缀
    if isinstance(image, str):
        # 如果是图像路径字符串
        original_filename = os.path.basename(image)
        basename, ext = os.path.splitext(original_filename)
    else:
        # 如果是PIL图像对象，使用默认名
        basename = "enhanced"
        ext = ".jpg"
    
    # 确定输出文件名
    output_filename = os.path.join(output_dir, f"{basename}_detected{ext}")
    
    # 如果传入的是PIL图像（增强后），保留PIL用于保存，同时转换为OpenCV格式再传给检测模型
    from PIL import Image as PILImage
    input_for_predict = image
    enhanced_to_save = None
    if not isinstance(image, str):
        # 如果是PIL对象，保留并转换为BGR numpy数组
        if isinstance(image, PILImage.Image):
            enhanced_to_save = image
            img_np = np.array(image)
            # PIL是RGB，转换为BGR供OpenCV/YOLO使用
            input_for_predict = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        else:
            # 如果已经是numpy数组，直接使用（假定为BGR）
            input_for_predict = image

    # 调用检测模型。确保传入的是路径或numpy数组（BGR）
    results = detect_model.predict(source=input_for_predict, conf=conf, save=True, 
                                   project=output_dir, name="")
    
    # 保存带检测框的图像
    detected_img = results[0].plot()
    cv2.imwrite(output_filename, detected_img)
    
    # 保存原始增强图像（如果有PIL对象）
    if enhanced_to_save is not None:
        enhanced_filename = os.path.join(output_dir, f"{basename}{ext}")
        try:
            enhanced_to_save.save(enhanced_filename)
            print(f"增强图像已保存到: {enhanced_filename}")
        except Exception as e:
            print(f"保存增强图像失败: {e}")
    
    print(f"检测结果已保存到: {output_filename}")
    
    # u8fd4u56deu68c0u6d4bu7ed3u679cu548cu5904u7406u540eu7684u56feu50cf
    return results


def process_video(video_path, enhance_model, detect_model, output_path, conf=0.25, night_vision_mode=False, enhance_method='deep'):
    """u5904u7406u89c6u9891u6587u4ef6"""
    print(f"u6b63u5728u5904u7406u89c6u9891: {video_path}")
    
    # u5b9au4e49u8f93u51fau6587u4ef6u5939u7684u8defu5f84
    output_folders = ["video/output_folder_1/", "video/output_folder_2/", "video/output_folder_3/",
                    "video/output_folder_4/", "video/output_folder_5/", "video/output_folder_6/"]

    enhance_folders = ["result/enhance/output_folder_1/", "result/enhance/output_folder_2/",
                    "result/enhance/output_folder_3/", "result/enhance/output_folder_4/", 
                    "result/enhance/output_folder_5/", "result/enhance/output_folder_6/"]
    
    # u521bu5efau5fc5u8981u7684u76eeu5f55
    for folder in output_folders + enhance_folders:
        os.makedirs(folder, exist_ok=True)
    
    # u5b9au4e49u8f93u51fau56feu7247u7684u8defu5f84
    out_frame_path = "video/output_frames/"
    os.makedirs(out_frame_path, exist_ok=True)
    
    # u89c6u9891u8f6cu5e27
    width, height, fps = video2frame(video_path, out_frame_path, output_folders)
    
    # u5b9au4e49u589eu5f3au56feu50cfu7684u51fdu6570
    def enhance(data_path, model, save_path):
        os.makedirs(save_path, exist_ok=True)
        files = [f for f in os.listdir(data_path) if f.endswith(('.jpg', '.png', '.jpeg'))]
        files.sort()
        
        for file in files:
            input_path = os.path.join(data_path, file)
            # 使用增强函数处理图像
            enhanced_img = enhance_image(
                input_path, 
                model, 
                night_vision_mode=night_vision_mode, 
                enhance_method=enhance_method
            )
            
            # u4fddu5b58u589eu5f3au540eu7684u56feu50cf
            output_path = os.path.join(save_path, file.split('.')[0] + '.png')
            enhanced_img.save(output_path, "png")
            print(f'u5904u7406 {file}')
    
    # u589eu5f3au6bcfu4e2au6587u4ef6u5939u4e2du7684u56feu50cf
    for i in range(len(output_folders)):
        enhance(output_folders[i], enhance_model, enhance_folders[i])
    
    # u5c06u589eu5f3au540eu7684u56feu50cfu5408u6210u89c6u9891
    # 确保路径存在
    os.makedirs("video", exist_ok=True)
    # 使用AVI格式，并确保路径绝对正确
    enhanced_video_path = os.path.abspath(os.path.join(os.getcwd(), "video", "enhanced_video.avi"))
    print(f"增强视频路径: {enhanced_video_path}")
    
    # 使用新的视频合成函数
    success = False
    
    # 首先尝试合并所有文件夹中的帧
    all_frames = []
    for folder in enhance_folders:
        # 确保路径存在并且包含文件
        if os.path.exists(folder):
            files = [f for f in os.listdir(folder) if f.endswith(('.jpg', '.png'))]  
            if files:
                all_frames.append(folder)
                print(f"找到 {len(files)} 个帧图像在 {folder}")
    
    if all_frames:
        # 尝试使用新的合成方法
        try:
            print("尝试使用改进的视频合成方法...")
            # 确保fps大于或等于1
            safe_fps = max(1.0, fps) if fps else 30.0
            print(f"使用帧率: {safe_fps} fps")
            # 合并第一个文件夹中的帧以获取视频
            first_success = frames_to_video(all_frames[0], enhanced_video_path, safe_fps)
            if first_success:
                success = True
                print(f"成功合成视频: {enhanced_video_path}")
            elif len(all_frames) > 1:
                # 如果第一个文件夹失败，尝试其他文件夹
                for folder in all_frames[1:]:
                    alt_path = enhanced_video_path.replace(".avi", f"_{os.path.basename(folder.rstrip('/'))}.avi")
                    if frames_to_video(folder, alt_path, safe_fps):
                        enhanced_video_path = alt_path
                        success = True
                        print(f"成功使用备用文件夹合成视频: {enhanced_video_path}")
                        break
        except Exception as e:
            print(f"改进的视频合成方法失败: {str(e)}")
    
    # 如果新方法失败，回退到原始方法
    if not success:
        try:
            print("尝试使用原始视频合成方法...")
            # 确保宽高参数顺序正确（视频工具类中期望的是width,height而不是相反）
            frame2video(enhance_folders, width, height, fps, enhanced_video_path)
            if os.path.exists(enhanced_video_path) and os.path.getsize(enhanced_video_path) > 0:
                success = True
                print("原始方法成功合成视频")
        except Exception as e:
            print(f"原始视频合成方法也失败: {str(e)}")
    
    # 检查增强后的视频文件是否存在
    if not success or not os.path.exists(enhanced_video_path) or os.path.getsize(enhanced_video_path) == 0:
        print(f"警告！所有视频合成方法均失败")
        print("尝试直接处理原始视频...")
        # 如果合成视频不存在，直接使用原始视频进行检测
        enhanced_video_path = video_path
        
    # u5bf9u589eu5f3au540eu7684u89c6u9891u8fdbu884cu76eeu6807u68c0u6d4b
    print(f"u5f00u59cbu68c0u6d4bu89c6u9891: {enhanced_video_path}")
    
    try:
        results = detect_model.predict(source=enhanced_video_path, save=True, conf=conf,
                                    project="result/predict", name="video")
        
        # u79fbu52a8u68c0u6d4bu7ed3u679cu5230u6307u5b9au8f93u51fau8defu5f84
        detected_video = os.path.join("result/predict/video", os.path.basename(enhanced_video_path))
        if os.path.exists(detected_video):
            import shutil
            shutil.copy(detected_video, output_path)
            print(f"u68c0u6d4bu7ed3u679cu5df2u4fddu5b58u81f3: {output_path}")
    except Exception as e:
        print(f"视频检测失败: {str(e)}")
        print("尝试直接处理增强后的帧...")
        
        # 如果视频检测失败，尝试直接处理关键帧
        try:
            # 选择几个关键帧进行检测
            key_frames = []
            for folder in all_frames:
                files = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(('.png', '.jpg'))])
                if files:
                    # 每隔50帧选择一个关键帧
                    key_frames.extend([files[i] for i in range(0, len(files), 50)])
            
            if key_frames:
                print(f"对 {len(key_frames)} 个关键帧进行检测...")
                results = []
                for frame in key_frames:
                    result = detect_model.predict(source=frame, save=True, conf=conf,
                                              project="result/predict/frames", name="key_frames")
                    results.extend(result)
                
                # 创建一个文件夹保存检测结果
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path.replace(".mp4", "_detection_results.txt"), "w") as f:
                    f.write(f"处理时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"共检测关键帧: {len(key_frames)} 个\n")
                    f.write("\n检测结果汇总:\n")
                    
                    # 汇总检测到的目标数量
                    objects_count = {}
                    for result in results:
                        for box in result.boxes:
                            cls_id = int(box.cls[0].item())
                            cls_name = result.names[cls_id]
                            if cls_name in objects_count:
                                objects_count[cls_name] += 1
                            else:
                                objects_count[cls_name] = 1
                    
                    for obj, count in objects_count.items():
                        f.write(f"{obj}: {count} 个\n")
                
                print(f"关键帧检测结果已保存到: {output_path.replace('.mp4', '_detection_results.txt')}")
            else:
                print("未找到可用的关键帧进行检测")
                results = []
        except Exception as e:
            print(f"关键帧检测也失败: {str(e)}")
            results = []
    
    return results


def process_camera(enhance_model, detect_model, conf=0.25, night_vision_mode=False, enhance_method='deep'):
    """u5904u7406u5b9eu65f6u6444u50cfu5934u89c6u9891u6d41"""
    print("u5f00u59cbu5904u7406u6444u50cfu5934u89c6u9891u6d41...")
    
    # u6253u5f00u6444u50cfu5934
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("u65e0u6cd5u6253u5f00u6444u50cfu5934")
        return
    
    while True:
        # u8bfbu53d6u5e27
        ret, frame = cap.read()
        if not ret:
            print("u65e0u6cd5u63a5u6536u5e27uff0cu9000u51fa...")
            break
        
        # u8f6cu6362u56feu50cfu683cu5f0f
        # 将帧保存为临时文件
        temp_frame_path = "temp_frame.jpg"
        cv2.imwrite(temp_frame_path, frame)
        
        # 使用增强函数处理图像
        enhanced_img = enhance_image(
            temp_frame_path, 
            enhance_model, 
            night_vision_mode=night_vision_mode, 
            enhance_method=enhance_method
        )
        
        # PIL转换为NumPy数组
        enhanced_np = np.array(enhanced_img)
        
        # 删除临时文件
        if os.path.exists(temp_frame_path):
            os.remove(temp_frame_path)
        
        # u76eeu6807u68c0u6d4b
        results = detect_model.predict(source=enhanced_np, conf=conf, verbose=False)
        
        # u5728u589eu5f3au540eu7684u56feu50cfu4e0au7ed8u5236u68c0u6d4bu7ed3u679c
        annotated_frame = results[0].plot()
        
        # u663eu793au7ed3u679c
        cv2.imshow('Enhanced Detection', annotated_frame)
        
        # u6309'q'u9000u51fa
        if cv2.waitKey(1) == ord('q'):
            break
    
    # u91cau653eu8d44u6e90
    cap.release()
    cv2.destroyAllWindows()


def main():
    s_t = time.time()
    
    # u52a0u8f7du589eu5f3au6a21u578b
    print("u52a0u8f7du589eu5f3au6a21u578b...")
    enhance_model = Network(args.e_model).to("cpu")
    enhance_model.eval()
    
    # u52a0u8f7du68c0u6d4bu6a21u578b
    print("u52a0u8f7du68c0u6d4bu6a21u578b...")
    detect_model = YOLO(args.d_model)
    
    # u5904u7406u4e0du540cu7c7bu578bu7684u8f93u5165
    if args.input_image:
        # u5904u7406u5355u5f20u56feu50cf
        enhanced_img = enhance_image(
            args.input_image, 
            enhance_model, 
            night_vision_mode=args.night_vision,
            enhance_method=args.enhance_method
        )
        results = detect_image(enhanced_img, detect_model, args.conf)
        # 输出消息已经在detect_image函数中显示
    
    elif args.input_video:
        # 更新过程信息
        print(f"使用 {args.enhance_method} 增强方法处理视频")
        if args.night_vision:
            print("启用夜视模式！")
        # u5904u7406u89c6u9891
        results = process_video(
            args.input_video, 
            enhance_model, 
            detect_model, 
            args.output_video, 
            conf=args.conf,
            night_vision_mode=args.night_vision,
            enhance_method=args.enhance_method
        )
        print(f"u89c6u9891u5904u7406u5b8cu6210uff0cu7ed3u679cu4fddu5b58u5728 {args.output_video}")
    
    elif args.input_stream == "camera":
        # 更新过程信息
        print(f"使用 {args.enhance_method} 增强方法处理摄像头视频流")
        if args.night_vision:
            print("启用夜视模式！")
        # u5904u7406u6444u50cfu5934
        process_camera(
            enhance_model, 
            detect_model, 
            conf=args.conf,
            night_vision_mode=args.night_vision,
            enhance_method=args.enhance_method
        )
    
    else:
        print("u9519u8befuff1au8bf7u6307u5b9au8f93u5165u6e90 (--input_image, --input_video, u6216 --input_stream camera)")
        return
    
    print(f"u603bu8017u65f6: {time.time() - s_t:.2f} u79d2")


if __name__ == '__main__':
    # u786eu4fddu521bu5efau5fc5u8981u7684u76eeu5f55
    os.makedirs("video", exist_ok=True)
    os.makedirs("video/output_frames", exist_ok=True)
    os.makedirs("result/predict", exist_ok=True)
    os.makedirs("result/enhance", exist_ok=True)
    
    main()
