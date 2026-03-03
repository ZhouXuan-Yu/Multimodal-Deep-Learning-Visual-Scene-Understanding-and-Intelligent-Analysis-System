import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os
from matplotlib.patches import Rectangle

class TrackingVisualizer:
    """用于可视化跟踪结果的工具类"""
    
    def __init__(self, max_tracks=100):
        """初始化跟踪可视化器"""
        # 为每个跟踪ID生成唯一的颜色
        self.max_tracks = max_tracks
        self.colors = self._generate_colors(max_tracks)
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.line_thickness = 2
        self.text_scale = 0.5
        
    def _generate_colors(self, n):
        """生成n个不同的颜色"""
        # 使用HSV色彩空间，确保颜色足够区分
        colors = []
        for i in range(n):
            hue = i / n
            # 使用高饱和度和高亮度以保证颜色可见性
            colors.append(tuple(int(c * 255) for c in mcolors.hsv_to_rgb([hue, 0.9, 0.9])))
        return colors
    
    def draw_tracks(self, image, tracks, confidence_threshold=0.5):
        """在图像上绘制跟踪结果
        
        Args:
            image: 输入图像
            tracks: 跟踪结果列表，每个元素包含 [x1, y1, x2, y2, track_id, confidence]
            confidence_threshold: 置信度阈值，低于此值的跟踪不显示
        
        Returns:
            带有跟踪框和ID的图像
        """
        result = image.copy()
        
        for track in tracks:
            if len(track) < 6 or track[5] < confidence_threshold:
                continue
                
            x1, y1, x2, y2 = map(int, track[:4])
            track_id = int(track[4])
            confidence = track[5]
            
            # 获取该ID对应的颜色
            color = self.colors[track_id % self.max_tracks]
            
            # 绘制边界框
            cv2.rectangle(result, (x1, y1), (x2, y2), color, self.line_thickness)
            
            # 添加ID和置信度标签
            label = f"ID:{track_id} {confidence:.2f}"
            text_size = cv2.getTextSize(label, self.font, self.text_scale, 1)[0]
            cv2.rectangle(result, (x1, y1 - text_size[1] - 5), (x1 + text_size[0], y1), color, -1)
            cv2.putText(result, label, (x1, y1 - 5), self.font, self.text_scale, (0, 0, 0), 1)
            
        return result
    
    def draw_detections(self, image, detections, confidence_threshold=0.5, classes=None, draw_low_confidence=True):
        """在图像上绘制检测结果
        
        Args:
            image: 输入图像
            detections: 检测结果列表，每个元素包含 [x1, y1, x2, y2, class_id, confidence]
            confidence_threshold: 置信度阈值，低于此值的检测不显示
            classes: 类别名称列表
            draw_low_confidence: 是否绘制低置信度目标（低于阈值的目标）
        
        Returns:
            带有检测框的图像
        """
        result = image.copy()
        detected_count = 0
        
        # 最低显示阈值 - 避免显示过多废弱的检测结果
        min_confidence = 0.1 if draw_low_confidence else confidence_threshold
        
        # 首先计算有多少检测结果能够达到阈值
        valid_detections = [det for det in detections if len(det) >= 6 and det[5] >= min_confidence]
        
        # 如果没有达到标准置信度的目标，但有低置信度目标，则显示最高置信度的几个
        if draw_low_confidence and not any(det[5] >= confidence_threshold for det in valid_detections) and valid_detections:
            # 按置信度排序
            valid_detections.sort(key=lambda x: x[5], reverse=True)
            # 只显示前3个最高置信度的目标
            valid_detections = valid_detections[:3]
            print(f"\n显示{len(valid_detections)}个低置信度目标 (原因: 无置信度>{confidence_threshold}的目标)")
        
        for det in valid_detections:
            x1, y1, x2, y2 = map(int, det[:4])
            class_id = int(det[4])
            confidence = det[5]
            detected_count += 1
            
            # 计算目标大小
            w, h = x2-x1, y2-y1
            area = w * h
            is_small_object = area < 400  # 小物体的面积阈值
            
            # 小目标使用不同颜色和宽度
            if is_small_object:
                # 小目标使用亮红色
                color = (0, 0, 255) if confidence < confidence_threshold else (0, 255, 255)
                thickness = 2  # 加粗边框使小目标更明显
            else:
                # 其他目标使用原先的类别颜色
                color = self.colors[class_id % self.max_tracks]
                # 低置信度目标使用虚线和更细的线条
                thickness = self.line_thickness if confidence >= confidence_threshold else 1
            
            # 绘制边界框 - 使用line_type参数
            if is_small_object or confidence >= confidence_threshold:
                cv2.rectangle(result, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)
            else:
                # 低置信度目标使用虚线边框
                # 绘制虚线边框
                for i in range(x1, x2, 5):
                    cv2.line(result, (i, y1), (min(i+3, x2), y1), color, thickness)
                    cv2.line(result, (i, y2), (min(i+3, x2), y2), color, thickness)
                for i in range(y1, y2, 5):
                    cv2.line(result, (x1, i), (x1, min(i+3, y2)), color, thickness)
                    cv2.line(result, (x2, i), (x2, min(i+3, y2)), color, thickness)
            
            # 添加类别和置信度标签
            class_name = classes[class_id] if classes and class_id < len(classes) else f"类别:{class_id}"
            label = f"{class_name} {confidence:.2f}{' (small)' if is_small_object else ''}"
            text_size = cv2.getTextSize(label, self.font, self.text_scale, 1)[0]
            cv2.rectangle(result, (x1, y1 - text_size[1] - 5), (x1 + text_size[0], y1), color, -1)
            cv2.putText(result, label, (x1, y1 - 5), self.font, self.text_scale, (255, 255, 255), 1)
        
        if detected_count > 0:
            print(f"\n已绘制 {detected_count} 个检测目标到图像上")
            
        return result
    
    def create_side_by_side_view(self, visible_img, thermal_img, 
                                 visible_tracks=None, thermal_tracks=None, 
                                 visible_detections=None, thermal_detections=None,
                                 confidence_threshold=0.5, classes=None,
                                 title_left="Visible", title_right="Thermal"):
        """创建可见光和热成像的并排视图，可选择显示跟踪或检测结果
        
        Args:
            visible_img: 可见光图像
            thermal_img: 热成像图像
            visible_tracks: 可见光图像上的跟踪结果
            thermal_tracks: 热成像图像上的跟踪结果
            visible_detections: 可见光图像上的检测结果
            thermal_detections: 热成像图像上的检测结果
            confidence_threshold: 置信度阈值
            classes: 类别名称列表
        
        Returns:
            并排显示的图像
        """
        # 确保两张图像尺寸相同
        if visible_img.shape != thermal_img.shape:
            thermal_img = cv2.resize(thermal_img, (visible_img.shape[1], visible_img.shape[0]))
        
        # 如果有跟踪结果，绘制跟踪框
        if visible_tracks is not None:
            visible_img = self.draw_tracks(visible_img, visible_tracks, confidence_threshold)
        if visible_detections is not None:
            visible_img = self.draw_detections(visible_img, visible_detections, confidence_threshold, classes)
        if thermal_detections is not None:
            # 为热成像使用更低的阈值，提高检测率
            thermal_img = self.draw_detections(thermal_img, thermal_detections, confidence_threshold * 0.6, classes)
        elif thermal_tracks is not None:
            thermal_img = self.draw_tracks(thermal_img, thermal_tracks, confidence_threshold)
        
        # 创建并排视图
        result = np.hstack((visible_img, thermal_img))
        
        # 在上方添加标题
        h, w = result.shape[:2]
        title_bar = np.zeros((50, w, 3), dtype=np.uint8)
        # 使用传入的标题参数
        cv2.putText(title_bar, title_left, (w//4 - 50, 30), self.font, 1, (255, 255, 255), 2)
        cv2.putText(title_bar, title_right, (3*w//4 - 50, 30), self.font, 1, (255, 255, 255), 2)
        
        return np.vstack((title_bar, result))
    
    def save_visualization(self, image, output_path, filename, save_separate=False, visible_img=None, thermal_img=None):
        """保存可视化结果
        
        Args:
            image: 合并后的图像
            output_path: 输出目录
            filename: 输出文件名
            save_separate: 是否单独保存可见光和热成像结果
            visible_img: 可见光图像（带检测/跟踪结果）
            thermal_img: 热成像图像（带检测/跟踪结果）
        """
        os.makedirs(output_path, exist_ok=True)
        
        # 保存合并视图
        cv2.imwrite(os.path.join(output_path, filename), image)
        
        # 单独保存可见光和热成像结果（如果需要）
        if save_separate and visible_img is not None and thermal_img is not None:
            # 从filename中提取基本名称（例如从00001_result.jpg提取00001）
            base_name = filename.split('_')[0] if '_' in filename else filename.split('.')[0]
            
            # 保存可见光结果
            visible_filename = f"{base_name}_visible.jpg"
            cv2.imwrite(os.path.join(output_path, visible_filename), visible_img)
            
            # 保存热成像结果
            thermal_filename = f"{base_name}_thermal.jpg"
            cv2.imwrite(os.path.join(output_path, thermal_filename), thermal_img)
    
    def display_matplotlib(self, visible_img, thermal_img, title="RGBT-Tiny 双模态可视化"):
        """使用Matplotlib显示双模态图像"""
        # 转换BGR到RGB
        visible_rgb = cv2.cvtColor(visible_img, cv2.COLOR_BGR2RGB)
        thermal_rgb = cv2.cvtColor(thermal_img, cv2.COLOR_BGR2RGB)
        
        # 创建图像
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        ax1.imshow(visible_rgb)
        ax1.set_title("可见光")
        ax1.axis("off")
        
        ax2.imshow(thermal_rgb)
        ax2.set_title("热成像")
        ax2.axis("off")
        
        plt.suptitle(title)
        plt.tight_layout()
        plt.show()
    
    def display_tracks_matplotlib(self, visible_img, thermal_img, visible_tracks=None, 
                               thermal_tracks=None, title="RGBT-Tiny 跟踪结果"):
        """使用Matplotlib显示带有跟踪结果的双模态图像"""
        # 转换BGR到RGB
        visible_rgb = cv2.cvtColor(visible_img, cv2.COLOR_BGR2RGB)
        thermal_rgb = cv2.cvtColor(thermal_img, cv2.COLOR_BGR2RGB)
        
        # 创建图像
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        ax1.imshow(visible_rgb)
        ax1.set_title("可见光")
        
        ax2.imshow(thermal_rgb)
        ax2.set_title("热成像")
        
        # 绘制跟踪框
        if visible_tracks is not None:
            for track in visible_tracks:
                if len(track) < 6 or track[5] < 0.5:
                    continue
                    
                x1, y1, x2, y2 = map(int, track[:4])
                track_id = int(track[4])
                confidence = track[5]
                
                # 获取该ID对应的颜色
                color = self.colors[track_id % self.max_tracks]
                color_norm = tuple(c/255.0 for c in color)
                
                # 绘制矩形和标签
                rect = Rectangle((x1, y1), x2-x1, y2-y1, linewidth=2, 
                               edgecolor=color_norm, facecolor='none')
                ax1.add_patch(rect)
                ax1.text(x1, y1-5, f"ID:{track_id} {confidence:.2f}", 
                       color=color_norm, fontsize=9, weight='bold')
        
        if thermal_tracks is not None:
            for track in thermal_tracks:
                if len(track) < 6 or track[5] < 0.5:
                    continue
                    
                x1, y1, x2, y2 = map(int, track[:4])
                track_id = int(track[4])
                confidence = track[5]
                
                # 获取该ID对应的颜色
                color = self.colors[track_id % self.max_tracks]
                color_norm = tuple(c/255.0 for c in color)
                
                # 绘制矩形和标签
                rect = Rectangle((x1, y1), x2-x1, y2-y1, linewidth=2, 
                               edgecolor=color_norm, facecolor='none')
                ax2.add_patch(rect)
                ax2.text(x1, y1-5, f"ID:{track_id} {confidence:.2f}", 
                       color=color_norm, fontsize=9, weight='bold')
        
        ax1.axis("off")
        ax2.axis("off")
        plt.suptitle(title)
        plt.tight_layout()
        plt.show()
