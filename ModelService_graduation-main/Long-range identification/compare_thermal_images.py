import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def process_thermal_img(img, use_enhancement=False):
    """处理热成像图像，展示原始与增强版本的区别"""
    # 基本归一化处理(无论哪种模式都需要)
    img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
    
    # 如果需要增强，应用CLAHE和对比度调整
    if use_enhancement:
        # CLAHE增强
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced_gray = clahe.apply(gray)
        img = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
        
        # 对比度和亮度增强
        alpha = 1.5  # 对比度因子
        beta = 10    # 亮度因子
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    
    return img

def main():
    # 加载一个示例热成像图像
    data_dir = Path("D:/Desktop/ModelService_graduation-main/RGBT-Tiny/data/RGBT-Tiny/images")
    # 查找一个序列
    for seq_dir in data_dir.iterdir():
        if seq_dir.is_dir():
            thermal_dir = seq_dir / "01"
            if thermal_dir.exists():
                for img_file in thermal_dir.glob("*.jpg"):
                    # 找到第一个jpg图像
                    thermal_img_path = str(img_file)
                    print(f"使用样例图像: {thermal_img_path}")
                    break
                break
                    
    if not os.path.exists(thermal_img_path):
        print("未找到样例热成像图像")
        return
        
    # 读取热成像图像
    original_img = cv2.imread(thermal_img_path)
    if original_img is None:
        print(f"无法读取图像: {thermal_img_path}")
        return
    
    # 处理图像的两个版本
    # 版本1: 只进行基本归一化
    basic_processed = process_thermal_img(original_img.copy(), use_enhancement=False)
    
    # 版本2: 使用完整增强处理
    enhanced_processed = process_thermal_img(original_img.copy(), use_enhancement=True)
    
    # 将BGR转换为RGB以便显示
    original_rgb = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
    basic_rgb = cv2.cvtColor(basic_processed, cv2.COLOR_BGR2RGB)
    enhanced_rgb = cv2.cvtColor(enhanced_processed, cv2.COLOR_BGR2RGB)
    
    # 显示比较结果
    plt.figure(figsize=(15, 5))
    
    plt.subplot(1, 3, 1)
    plt.imshow(original_rgb)
    plt.title("原始图像(未处理)")
    plt.axis('off')
    
    plt.subplot(1, 3, 2)
    plt.imshow(basic_rgb)
    plt.title("基本处理(仅归一化)")
    plt.axis('off')
    
    plt.subplot(1, 3, 3)
    plt.imshow(enhanced_rgb)
    plt.title("增强处理(CLAHE+对比度)")
    plt.axis('off')
    
    plt.tight_layout()
    plt.savefig("thermal_processing_comparison.png", dpi=200)
    print("比较图像已保存为: thermal_processing_comparison.png")
    
    # 保存单独的图像以便检查
    cv2.imwrite("thermal_original.jpg", original_img)
    cv2.imwrite("thermal_basic.jpg", basic_processed)
    cv2.imwrite("thermal_enhanced.jpg", enhanced_processed)
    print("各版本图像已单独保存")

if __name__ == "__main__":
    main()
