import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import argparse
from ultralytics import YOLO

# 导入自定义模块
sys.path.append('./Night-vehicle-detection-system/new_detection/main')

# 导入图像处理函数
def apply_clahe(img):
    """应用自适应直方图均衡化(CLAHE)增强图像对比度"""
    # 转换为LAB色彩空间
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    
    # 对L通道应用CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)
    
    # 合并通道
    merged = cv2.merge((cl, a, b))
    
    # 转回原始色彩空间
    enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    return enhanced

def adjust_gamma(img, gamma=1.5):
    """调整图像的gamma值提高亮度"""
    # 创建查询表
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
    
    # 应用查询表
    return cv2.LUT(img, table)

def denoise_image(img):
    """应用去噪算法减少图像噪点"""
    return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

def create_night_vision_effect(img):
    """创建夜视仪效果"""
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

# Retinex算法实现
def singleScaleRetinex(img, sigma):
    """单尺度 Retinex 算法"""
    # 确保不会遇到零
    img = np.clip(img, 0.01, 255.0)
    
    blur = cv2.GaussianBlur(img, (0, 0), sigma)
    blur = np.clip(blur, 0.01, 255.0)  # 防止零值
    
    retinex = np.log(img + 0.01) - np.log(blur + 0.01)
    return retinex

def multiScaleRetinex(img, sigma_list=[15, 80, 250]):
    """多尺度 Retinex 算法"""
    retinex = np.zeros_like(img, dtype=np.float32)
    for sigma in sigma_list:
        retinex += singleScaleRetinex(img, sigma)
    retinex = retinex / len(sigma_list)
    return retinex

def apply_retinex(img):
    """应用 Retinex 算法进行图像增强"""
    # 确保图像是 float32 类型
    img_float = img.astype(np.float32)
    
    # 应用 Retinex 算法
    retinex_result = multiScaleRetinex(img_float)
    
    # 缩放到 [0, 255] 范围
    min_val = np.min(retinex_result)
    max_val = np.max(retinex_result)
    retinex_result = (retinex_result - min_val) / (max_val - min_val) * 255.0
    
    # 调整对比度
    enhanced = cv2.convertScaleAbs(retinex_result, alpha=1.2, beta=10)
    
    return enhanced

# EnlightenGAN-inspired增强
# 注意这并不是真正的GAN，而是模拟其效果的简化版本
def apply_enlightengan(img):
    """模拟 EnlightenGAN 的增强效果"""
    # 转换到LAB色彩空间处理亮度
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    
    # 使用CLAHE增强亮度
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)
    
    # 应用自定义 Gamma 调整获得更自然的效果
    gamma = 0.8  # 较小的gamma值可以增强亮度
    cl_gamma = np.array(255 * (cl / 255) ** gamma, dtype=np.uint8)
    
    # 合并回原始LAB图像
    merged = cv2.merge((cl_gamma, a, b))
    enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    
    # 调整最终颜色和对比度
    enhanced = cv2.convertScaleAbs(enhanced, alpha=1.1, beta=5)
    
    return enhanced

# KinD-inspired增强
def apply_kind(img):
    """模拟 KinD 算法的增强效果"""
    # 分解图像（估计照明）
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    illumination = cv2.GaussianBlur(gray, (71, 71), 0)
    illumination = np.maximum(illumination, 1) / 255.0  # 防止降低原图刻度
    
    # 标准化照明约束
    illumination_norm = np.power(illumination, 0.6)  # 调整照明权重
    
    # 拆分通道
    b, g, r = cv2.split(img.astype(np.float32))
    
    # 增强每个通道
    b_enhanced = np.minimum(b * (1.2 / illumination_norm), 255.0)
    g_enhanced = np.minimum(g * (1.2 / illumination_norm), 255.0)
    r_enhanced = np.minimum(r * (1.2 / illumination_norm), 255.0)
    
    # 合并通道
    enhanced = cv2.merge([b_enhanced, g_enhanced, r_enhanced]).astype(np.uint8)
    
    # 最终调整
    enhanced = cv2.convertScaleAbs(enhanced, alpha=1.0, beta=10)
    
    return enhanced

# Zero-DCE-inspired增强
def apply_zero_dce(img):
    """模拟 Zero-DCE 算法的增强效果"""
    # 将图像转换为浮点型并标准化
    img_float = img.astype(np.float32) / 255.0
    
    # 应用多次曲线调整（这是Zero-DCE的简化实现）
    enhanced = img_float.copy()
    
    # 模拟四次迭代调整
    for _ in range(4):
        # 使用 x + x * (x - x^2) 的变换（类似Zero-DCE的曲线映射函数）
        enhanced = enhanced + 0.2 * enhanced * (1 - enhanced)
    
    # 限制在[0,1]范围内
    enhanced = np.clip(enhanced, 0, 1)
    
    # 转回原始范围并进行颜色调整
    enhanced = (enhanced * 255).astype(np.uint8)
    
    # 提高对比度
    lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
    l_channel, a, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)
    merged = cv2.merge((cl, a, b_channel))
    enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    
    return enhanced

# 参数解析
parser = argparse.ArgumentParser(description="低光照图像增强算法对比")
parser.add_argument('--input_image', type=str, required=True, help='输入图像路径')
parser.add_argument('--output_dir', type=str, default="./comparison_results", help='输出目录')
parser.add_argument('--d_model', type=str, default='./Night-vehicle-detection-system/new_detection/weights/detect_weights/yolov8n.pt', help='检测模型路径')
parser.add_argument('--conf', type=float, default=0.25, help='检测置信度阈值')
args = parser.parse_args()

def add_title(img, title, position="top"):
    """为图像添加标题"""
    img_pil = Image.fromarray(img)
    draw = ImageDraw.Draw(img_pil)
    
    # 尝试使用系统字体
    try:
        # 对于Windows系统
        font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        # 如果找不到指定字体，使用默认字体
        font = ImageFont.load_default()
    
    width, height = img_pil.size
    text_width = draw.textlength(title, font=font)
    x = (width - text_width) // 2
    
    if position == "top":
        y = 20
    else:
        y = height - 40
        
    # 绘制黑色阴影（增强可读性）
    draw.text((x+2, y+2), title, fill=(0, 0, 0), font=font)
    # 绘制白色文本
    draw.text((x, y), title, fill=(255, 255, 255), font=font)
    
    return np.array(img_pil)

def create_comparison_grid(original_img, enhanced_images, titles, output_path):
    """创建对比网格图像"""
    # 标准化图像尺寸
    height, width = original_img.shape[:2]
    
    # 添加标题到每个图像
    labeled_images = []
    for img, title in zip([original_img] + enhanced_images, titles):
        # 确保图像是RGB格式
        if isinstance(img, Image.Image):
            img = np.array(img)
        if img.ndim == 2:  # 灰度图
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 3 and img.dtype == np.uint8:  # BGR格式
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 添加标题
        img_with_title = add_title(img, title)
        labeled_images.append(img_with_title)
    
    # 确定网格布局
    num_images = len(labeled_images)
    grid_size = (2, 3)  # 2行3列的网格
    if num_images > 6:
        grid_size = (3, 3)  # 3行3列的网格
    
    # 创建画布
    canvas_height = grid_size[0] * height
    canvas_width = grid_size[1] * width
    canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255
    
    # 放置图像
    for i, img in enumerate(labeled_images):
        if i >= grid_size[0] * grid_size[1]:
            break
            
        row = i // grid_size[1]
        col = i % grid_size[1]
        
        y_start = row * height
        y_end = (row + 1) * height
        x_start = col * width
        x_end = (col + 1) * width
        
        # 调整图像大小
        if img.shape[:2] != (height, width):
            img = cv2.resize(img, (width, height))
        
        canvas[y_start:y_end, x_start:x_end] = img
    
    # 保存对比图像
    cv2.imwrite(output_path, cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR))
    print(f"对比图已保存到: {output_path}")
    return canvas

def apply_custom_method(img):
    """应用自定义的图像增强方法（组合CLAHE和Gamma调整）"""
    # 首先应用去噪
    denoised = denoise_image(img)
    
    # 应用CLAHE增强对比度
    clahe_img = apply_clahe(denoised)
    
    # 然后应用适当的Gamma调整
    gamma_img = adjust_gamma(clahe_img, gamma=1.5)
    
    # 最后再次调整对比度和亮度
    result = cv2.convertScaleAbs(gamma_img, alpha=1.1, beta=5)
    
    return result

def detect_objects(img, model, conf=0.25):
    """使用YOLO模型检测图像中的目标"""
    # 转换OpenCV BGR格式为RGB格式
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 运行推理
    results = model(img_rgb, conf=conf)
    
    # 复制原图像以在其上绘制结果
    result_img = img.copy()
    
    # 绘制检测框
    for result in results:
        boxes = result.boxes
        for box in boxes:
            # 获取框坐标
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            
            # 获取类别和置信度
            cls = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            
            # 获取类别名称
            cls_name = result.names[cls]
            
            # 绘制框和标签
            cv2.rectangle(result_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 添加类别和置信度文本
            label = f'{cls_name}: {conf:.2f}'
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(label, font, 0.5, 1)[0]
            cv2.rectangle(result_img, (x1, y1 - text_size[1] - 5), (x1 + text_size[0], y1), (0, 255, 0), -1)
            cv2.putText(result_img, label, (x1, y1 - 5), font, 0.5, (0, 0, 0), 1)
    
    return result_img

def main():
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 读取输入图像
    original_img = cv2.imread(args.input_image)
    if original_img is None:
        print(f"无法读取图像: {args.input_image}")
        return
    
    print(f"处理图像: {args.input_image}")
    
    # 加载检测模型
    print("加载检测模型...")
    detect_model = YOLO(args.d_model)
    
    # 使用不同方法增强图像并进行检测
    enhanced_images = []
    detected_images = []
    titles = ["(a) Dark (Original)"]  # 原始图像标题
    
    # 对原始图像检测
    print("对原始图像进行目标检测...")
    original_detected = detect_objects(original_img, detect_model, args.conf)
    detected_images.append(original_detected)
    
    # 1. Retinex
    print("应用Retinex算法...")
    retinex_img = apply_retinex(original_img)
    enhanced_images.append(retinex_img)
    # 在增强后的图像上检测
    print("Retinex增强后进行目标检测...")
    retinex_detected = detect_objects(retinex_img, detect_model, args.conf)
    detected_images.append(retinex_detected)
    titles.append("(b) Retinex")
    
    # 2. KinD
    print("应用KinD算法...")
    kind_img = apply_kind(original_img)
    enhanced_images.append(kind_img)
    # 在增强后的图像上检测
    print("KinD增强后进行目标检测...")
    kind_detected = detect_objects(kind_img, detect_model, args.conf)
    detected_images.append(kind_detected)
    titles.append("(c) KinD")
    
    # 3. EnlightenGAN
    print("应用EnlightenGAN算法...")
    enlightengan_img = apply_enlightengan(original_img)
    enhanced_images.append(enlightengan_img)
    # 在增强后的图像上检测
    print("EnlightenGAN增强后进行目标检测...")
    enlightengan_detected = detect_objects(enlightengan_img, detect_model, args.conf)
    detected_images.append(enlightengan_detected)
    titles.append("(d) EnlightenGAN")

    # 4. Zero-DCE
    print("应用Zero-DCE算法...")
    zero_dce_img = apply_zero_dce(original_img)
    enhanced_images.append(zero_dce_img)
    # 在增强后的图像上检测
    print("Zero-DCE增强后进行目标检测...")
    zero_dce_detected = detect_objects(zero_dce_img, detect_model, args.conf)
    detected_images.append(zero_dce_detected)
    titles.append("(e) Zero-DCE")

    # 5. 自定义组合方法
    print("应用自定义组合方法...")
    custom_img = apply_custom_method(original_img)
    enhanced_images.append(custom_img)
    # 在增强后的图像上检测
    print("自定义方法增强后进行目标检测...")
    custom_detected = detect_objects(custom_img, detect_model, args.conf)
    detected_images.append(custom_detected)
    titles.append("(f) Ours")

    # 保存单独的图像（增强图像和检测结果）
    for i, (img, det_img, title) in enumerate(zip(enhanced_images, detected_images[1:], titles[1:])):
        # 提取算法名称作为文件名
        method_name = title.split(' ')[1].lower()
        if method_name.endswith(')'):
            method_name = method_name[:-1]  # 移除结尾的括号
            
        # 保存增强后的原始图像
        if isinstance(img, Image.Image):
            img_save = img
        else:
            img_save = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        save_path = os.path.join(args.output_dir, f"{method_name}.png")
        img_save.save(save_path)
        print(f"增强图像已保存到: {save_path}")
        
        # 保存带检测结果的图像
        det_img_save = Image.fromarray(cv2.cvtColor(det_img, cv2.COLOR_BGR2RGB))
        det_save_path = os.path.join(args.output_dir, f"{method_name}_detected.png")
        det_img_save.save(det_save_path)
        print(f"检测结果已保存到: {det_save_path}")
    
    # 保存原始图像的检测结果
    original_det_img = Image.fromarray(cv2.cvtColor(detected_images[0], cv2.COLOR_BGR2RGB))
    original_det_path = os.path.join(args.output_dir, "original_detected.png")
    original_det_img.save(original_det_path)
    print(f"原始图像检测结果已保存到: {original_det_path}")
    
    # 创建增强效果对比图像
    comparison_path = os.path.join(args.output_dir, "comparison.png")
    create_comparison_grid(original_img, enhanced_images, titles, comparison_path)
    print(f"增强效果对比图已保存到: {comparison_path}")
    
    # 创建检测效果对比图像
    detection_comparison_path = os.path.join(args.output_dir, "detection_comparison.png")
    create_comparison_grid(detected_images[0], detected_images[1:], titles, detection_comparison_path)
    print(f"检测效果对比图已保存到: {detection_comparison_path}")
    
    print("所有处理已完成!")

if __name__ == "__main__":
    main()
