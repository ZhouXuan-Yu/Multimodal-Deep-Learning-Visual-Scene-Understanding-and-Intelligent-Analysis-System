import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path
import torch

# 数据集路径
DATASET_PATH = "D:/Desktop/RGBT-Tiny/data/RGBT-Tiny"
IMAGES_PATH = os.path.join(DATASET_PATH, "images")
ANNOTATIONS_COCO_PATH = os.path.join(DATASET_PATH, "annotations_coco")
ANNOTATIONS_VOC_PATH = os.path.join(DATASET_PATH, "annotations_voc")

# 检查GPU是否可用
def check_cuda():
    print("CUDA是否可用:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("CUDA版本:", torch.version.cuda)
        print("GPU数量:", torch.cuda.device_count())
        print("GPU型号:", torch.cuda.get_device_name(0))
    else:
        print("CUDA不可用，将使用CPU运行")
    print("-----------------------------------")

# 列出数据集中的所有序列
def list_sequences():
    sequences = sorted([d for d in os.listdir(IMAGES_PATH) if os.path.isdir(os.path.join(IMAGES_PATH, d))])
    print(f"数据集共包含 {len(sequences)} 个序列")
    return sequences

# 加载一对可见光-热成像图像
def load_image_pair(sequence_name, frame_idx):
    # 可见光图像 (00文件夹)
    visible_path = os.path.join(IMAGES_PATH, sequence_name, "00", f"{frame_idx:05d}.jpg")
    # 热成像图像 (01文件夹)
    thermal_path = os.path.join(IMAGES_PATH, sequence_name, "01", f"{frame_idx:05d}.jpg")
    
    if not os.path.exists(visible_path) or not os.path.exists(thermal_path):
        print(f"找不到图像: {visible_path} 或 {thermal_path}")
        return None, None
    
    visible_img = cv2.imread(visible_path)
    thermal_img = cv2.imread(thermal_path)
    
    # 转换BGR到RGB格式用于显示
    if visible_img is not None:
        visible_img = cv2.cvtColor(visible_img, cv2.COLOR_BGR2RGB)
    if thermal_img is not None:
        thermal_img = cv2.cvtColor(thermal_img, cv2.COLOR_BGR2RGB)
    
    return visible_img, thermal_img

# 简单显示图像对
def display_image_pair(sequence_name, frame_idx):
    visible_img, thermal_img = load_image_pair(sequence_name, frame_idx)
    if visible_img is None or thermal_img is None:
        return
    
    # 创建两个子图 (一个用于可见光图像，一个用于热成像图像)
    fig, axs = plt.subplots(1, 2, figsize=(15, 7))
    
    # 显示可见光图像
    axs[0].imshow(visible_img)
    axs[0].set_title(f"Visible Image - {sequence_name} - Frame {frame_idx}")
    axs[0].axis('off')
    
    # 显示热成像图像
    axs[1].imshow(thermal_img)
    axs[1].set_title(f"Thermal Image - {sequence_name} - Frame {frame_idx}")
    axs[1].axis('off')
    
    plt.tight_layout()
    plt.show()

# 加载COCO格式的注释
def load_coco_annotations():
    print("正在加载COCO格式注释文件...")
    # 检查是否加载训练集或测试集（这里以训练集为例）
    visible_ann_file = os.path.join(ANNOTATIONS_COCO_PATH, "instances_00_train2017.json")
    thermal_ann_file = os.path.join(ANNOTATIONS_COCO_PATH, "instances_01_train2017.json")
    
    if not os.path.exists(visible_ann_file):
        print(f"找不到可见光注释文件: {visible_ann_file}")
        return None, None
    
    if not os.path.exists(thermal_ann_file):
        print(f"找不到热成像注释文件: {thermal_ann_file}")
        return None, None
    
    with open(visible_ann_file, 'r') as f:
        visible_coco_data = json.load(f)
    
    with open(thermal_ann_file, 'r') as f:
        thermal_coco_data = json.load(f)
    
    print("成功加载COCO格式注释:")
    print(f"  可见光数据: {len(visible_coco_data['images'])} 张图像和 {len(visible_coco_data['annotations'])} 个标注")
    print(f"  热成像数据: {len(thermal_coco_data['images'])} 张图像和 {len(thermal_coco_data['annotations'])} 个标注")
    
    return visible_coco_data, thermal_coco_data

# 查找特定序列和帧的图像ID
def find_image_ids(coco_data, sequence_name, frame_idx):
    image_ids = []
    img_filename = "{:05d}.jpg".format(frame_idx)
    # 使用序列名称和帧编号在COCO数据中查找匹配的图像
    
    for img in coco_data['images']:
        file_name = img['file_name']
        if sequence_name in file_name and img_filename in file_name:
            image_ids.append(img['id'])
    
    return image_ids

# 显示带有边界框的图像对（使用训练集注释）
def display_train_with_bbox(sequence_name, frame_idx):
    # 加载图像对
    visible_img, thermal_img = load_image_pair(sequence_name, frame_idx)
    if visible_img is None or thermal_img is None:
        print("无法加载图像对，将只显示图像而不加载边界框")
        display_image_pair(sequence_name, frame_idx)
        return
    
    # 加载注释
    visible_coco, thermal_coco = load_coco_annotations()
    if visible_coco is None or thermal_coco is None:
        print("无法加载注释，将只显示图像而不加载边界框")
        display_image_pair(sequence_name, frame_idx)
        return
    
    # 查找可见光图像的ID
    visible_img_ids = find_image_ids(visible_coco, sequence_name, frame_idx)
    thermal_img_ids = find_image_ids(thermal_coco, sequence_name, frame_idx)
    
    if not visible_img_ids or not thermal_img_ids:
        print(f"在注释中找不到对应的图像ID，序列: {sequence_name}, 帧: {frame_idx}")
        print("将只显示图像而不加载边界框")
        display_image_pair(sequence_name, frame_idx)
        return
    
    # 获取可见光图像的注释
    visible_annotations = []
    for img_id in visible_img_ids:
        visible_annotations.extend([ann for ann in visible_coco['annotations'] if ann['image_id'] == img_id])
    
    # 获取热成像图像的注释
    thermal_annotations = []
    for img_id in thermal_img_ids:
        thermal_annotations.extend([ann for ann in thermal_coco['annotations'] if ann['image_id'] == img_id])
    
    # 创建两个子图
    fig, axs = plt.subplots(1, 2, figsize=(15, 7))
    
    # 显示可见光图像
    axs[0].imshow(visible_img)
    axs[0].set_title(f"Visible Image - {sequence_name} - Frame {frame_idx}")
    axs[0].axis('off')
    
    # 显示热成像图像
    axs[1].imshow(thermal_img)
    axs[1].set_title(f"Thermal Image - {sequence_name} - Frame {frame_idx}")
    axs[1].axis('off')
    
    # 在可见光图像上绘制边界框
    for ann in visible_annotations:
        bbox = ann['bbox']  # COCO格式: [x, y, width, height]
        category_id = ann['category_id']
        # 随机颜色以区分不同目标
        color = np.random.rand(3)
        rect = plt.Rectangle((bbox[0], bbox[1]), bbox[2], bbox[3], 
                            linewidth=1, edgecolor=color, facecolor='none')
        axs[0].add_patch(rect)
    
    # 在热成像图像上绘制边界框
    for ann in thermal_annotations:
        bbox = ann['bbox']  # COCO格式: [x, y, width, height]
        category_id = ann['category_id']
        # 随机颜色以区分不同目标
        color = np.random.rand(3)
        rect = plt.Rectangle((bbox[0], bbox[1]), bbox[2], bbox[3], 
                            linewidth=1, edgecolor=color, facecolor='none')
        axs[1].add_patch(rect)
    
    plt.tight_layout()
    plt.show()
    
    print(f"可见光图像上有 {len(visible_annotations)} 个目标")
    print(f"热成像图像上有 {len(thermal_annotations)} 个目标")

# 主函数
def main():
    print("\n=== RGBT-Tiny 数据集启动程序 ===\n")
    check_cuda()
    
    # 列出所有序列
    sequences = list_sequences()
    print("前10个序列: {}".format(sequences[:10]))
    print("-----------------------------------")
    
    # 选择一个示例序列和帧进行显示
    example_sequence = "DJI_0028_5"  # 示例序列，用户可以修改
    example_frame = 100  # 示例帧，用户可以修改
    
    print("\n显示序列 {} 的第 {} 帧".format(example_sequence, example_frame))
    
    # 尝试先只显示图像对（不带边界框）
    display_image_pair(example_sequence, example_frame)
    
    # 自动尝试加载边界框（无需用户输入）
    print("\n正在尝试加载边界框标注...这可能需要一点时间")
    display_train_with_bbox(example_sequence, example_frame)

if __name__ == "__main__":
    main()
