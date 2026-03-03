"""
火灾检测系统 - YOLOv8版本
专为YOLOv8模型优化的火灾检测启动脚本
"""
import os
import sys
import cv2
import numpy as np
import argparse
from tqdm import tqdm
import time

# 导入火灾报警工具
from fire_alarm_utils import FireAlarmManager

# 尝试导入ultralytics库
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    print("已成功导入YOLOv8，可以使用YOLO模型进行火灾检测")
except ImportError:
    YOLO_AVAILABLE = False
    print("错误：未能导入ultralytics库。请先安装：pip install ultralytics")
    print("安装后重试")
    sys.exit(1)

class FireDetector:
    """使用YOLOv8的火灾检测器"""
    
    def __init__(self, 
                detection_model_path="Output/yolov8x/final_model.h5.pt", 
                segmentation_model_path="Output/yolov8x-seg/final_model.h5.pt",
                confidence_threshold=0.25,
                enable_alarm=False,
                alarm_threshold=0.5,
                alarm_interval=60,
                use_qq_mail=True):
        """
        初始化火灾检测器
        
        Args:
            detection_model_path: 检测模型路径
            segmentation_model_path: 分割模型路径
            confidence_threshold: 置信度阈值
            enable_alarm: 是否启用报警功能
            alarm_threshold: 报警阈值
            alarm_interval: 报警间隔(秒)
            use_qq_mail: 是否使用QQ邮箱发送报警(True为内网，False为外网)
        """
        self.confidence_threshold = confidence_threshold
        self.detection_model = None
        self.segmentation_model = None
        
        # 初始化报警相关配置
        self.enable_alarm = enable_alarm
        self.alarm_manager = None
        if self.enable_alarm:
            self.alarm_manager = FireAlarmManager(
                use_qq_mail=use_qq_mail,
                alarm_threshold=alarm_threshold,
                alarm_interval=alarm_interval
            )
            print(f"已启用火灾报警功能! 阈值: {alarm_threshold}, 间隔: {alarm_interval}秒, 使用{'QQ邮箱(内网)' if use_qq_mail else 'Gmail(外网)'}")
        
        # 加载检测模型
        if os.path.exists(detection_model_path):
            try:
                self.detection_model = YOLO(detection_model_path)
                print(f"成功加载检测模型: {detection_model_path}")
            except Exception as e:
                print(f"检测模型加载失败: {e}")
        else:
            print(f"检测模型文件不存在: {detection_model_path}")
        
        # 加载分割模型
        if os.path.exists(segmentation_model_path):
            try:
                self.segmentation_model = YOLO(segmentation_model_path)
                print(f"成功加载分割模型: {segmentation_model_path}")
            except Exception as e:
                print(f"分割模型加载失败: {e}")
        else:
            print(f"分割模型文件不存在: {segmentation_model_path}")
    
    def process_image(self, img, display=False, save_path=None):
        """
        处理单张图像
        
        Args:
            img: 输入图像
            display: 是否显示结果
            save_path: 保存结果路径
            
        Returns:
            处理后的图像
        """
        # 保存原始图像
        original_img = img.copy()
        result_img = original_img.copy()
        
        fire_detected = False
        fire_confidence = 0.0
        fire_areas = []
        fire_percentage = 0.0
        
        # 使用检测模型
        if self.detection_model is not None:
            # 检测结果
            detection_results = self.detection_model(img, verbose=False, conf=self.confidence_threshold)
            
            # 处理检测结果
            for result in detection_results:
                boxes = result.boxes  # 获取检测框
                
                # 遍历所有检测框
                for box in boxes:
                    # 获取类别ID和置信度
                    cls_id = int(box.cls.item())
                    conf = float(box.conf.item())
                    
                    # 获取类别名称
                    class_name = result.names[cls_id]
                    
                    # 检查是否与火灾相关
                    if ("fire" in class_name.lower() or 
                        "flame" in class_name.lower() or 
                        "smoke" in class_name.lower()):
                        
                        fire_detected = True
                        if conf > fire_confidence:
                            fire_confidence = conf
                        
                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        
                        # 计算面积
                        area = (x2 - x1) * (y2 - y1)
                        fire_areas.append((x1, y1, x2-x1, y2-y1, area))
                        
                        # 在图像上绘制更鲜艳的检测框
                        # 外边框 - 红色粗边框 (BGR顺序，所以是0,0,255)
                        cv2.rectangle(result_img, (x1-3, y1-3), (x2+3, y2+3), (0, 0, 255), 4)
                        # 内边框 - 红色细边框
                        cv2.rectangle(result_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        
                        # 增强标签可见性
                        label = f"{class_name}: {conf:.2f}"
                        # 添加标签背景矩形
                        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                        cv2.rectangle(result_img, (x1-2, y1-text_size[1]-10), (x1+text_size[0]+2, y1), (0, 0, 0), -1)
                        # 文本效果增强
                        cv2.putText(result_img, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.8, (0, 0, 255), 2, cv2.LINE_AA)
        
        # 使用分割模型
        if self.segmentation_model is not None:
            # 分割结果 - 使用较低的置信度阈值来捕获更多潜在火灾区域
            # 降低阈值到极限，确保试图检测所有可能的目标
            lower_threshold = 0.01  # 非常低的阈值
            segmentation_results = self.segmentation_model(img, verbose=False, conf=lower_threshold)
            
            # 创建分割掩码
            mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
            have_masks = False
            
            # 处理分割结果
            for result in segmentation_results:
                if hasattr(result, 'masks') and result.masks is not None and len(result.masks) > 0:
                    have_masks = True
                    for seg_mask in result.masks.data:
                        # 转换并调整掩码尺寸
                        m = seg_mask.cpu().numpy()
                        m = cv2.resize(m, (img.shape[1], img.shape[0]))
                        # 使用更低的阈值，增加分割掩码覆盖范围
                        m = (m > 0.2).astype(np.uint8)  # 降低到0.2，捕获更多可能的火灾区域
                        
                        # 掩码合并
                        mask = cv2.bitwise_or(mask, m)
                    
                    # 计算火灾区域百分比
                    fire_percentage = np.mean(mask) * 100
                
            # 即使没有检测到掩码，也尝试应用基于颜色的检测
            if not have_masks:
                print("未检测到分割掩码，尝试使用颜色检测标记火灾区域...")
                # 转换到HSV色彩空间
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                
                # 火焰颜色范围 (红色-黄色)
                # 红色范围1
                lower_red1 = np.array([0, 50, 50])
                upper_red1 = np.array([20, 255, 255])
                # 黄色范围
                lower_yellow = np.array([20, 50, 50])
                upper_yellow = np.array([40, 255, 255])
                # 红色范围2
                lower_red2 = np.array([160, 50, 50])
                upper_red2 = np.array([180, 255, 255])
                
                # 创建颜色掩码
                mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                mask2 = cv2.inRange(hsv, lower_yellow, upper_yellow)
                mask3 = cv2.inRange(hsv, lower_red2, upper_red2)
                
                # 组合掩码
                color_mask = cv2.bitwise_or(cv2.bitwise_or(mask1, mask2), mask3)
                
                # 应用形态学操作去除噪点
                kernel = np.ones((5, 5), np.uint8)
                color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)
                color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)
                
                # 计算百分比
                fire_percentage = np.mean(color_mask / 255.0) * 100
                
                # 找到轮廓
                contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # 提高检测精度 - 使用更精细的掩码处理
                # 首先使用更小的内核进行形态学操作，保留更多细节
                refined_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
                refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
                
                # 为掩码区域添加边框效果
                # 创建更精细的边框掩码 - 使用多级边缘检测
                edge_mask1 = cv2.Canny(refined_mask, 50, 150)  # 使用Canny边缘检测获取更精细的边缘
                
                # 同时也创建传统边缘（内部区域减去腐蚀）
                eroded = cv2.erode(refined_mask, np.ones((2, 2), np.uint8), iterations=1)
                edge_mask2 = refined_mask - eroded
                
                # 合并两种边缘检测结果
                edge_mask = cv2.bitwise_or(edge_mask1, edge_mask2)
                
                # 创建彩色边框 - 使用红色
                edge_color = np.zeros_like(img)
                edge_color[:,:,0] = 0            # 蓝色通道为0 (OpenCV为BGR顺序)
                edge_color[:,:,1] = 0            # 绿色通道为0
                edge_color[:,:,2] = edge_mask    # 红色通道
                
                # 只应用边框，不添加内部填充
                edge_area = (edge_mask > 0).astype(np.float32)
                for c in range(3):
                    result_img[:,:,c] = result_img[:,:,c] * (1 - edge_area) + edge_color[:,:,c] * edge_area
                
                # 为检测到的火灾区域添加标签
                min_area = 300  # 降低最小面积阈值，检测更小的区域
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > min_area:
                        # 获取边界框用于定位标签
                        x, y, w, h = cv2.boundingRect(contour)
                        
                        # 显示置信度标签
                        confidence_text = f"Fire: {fire_percentage/100:.2f}"
                        # 添加黑色背景增强可读性
                        text_size = cv2.getTextSize(confidence_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                        cv2.rectangle(result_img, (x, y-text_size[1]-10), (x+text_size[0]+2, y), (0, 0, 0), -1)
                        # 文本效果增强
                        cv2.putText(result_img, confidence_text, (x, y-5), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                        
                        fire_detected = True
                        if fire_confidence < fire_percentage/100:
                            fire_confidence = fire_percentage/100
                
                # 添加文本显示检测模式
                cv2.putText(result_img, "High Precision Edge Detection", (10, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
        
        # 火灾区域检测 - 像素级精确检测
        # 创建一个掩码用于标记处理后的火灾区域
        fire_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
        
        # 如果检测到火灾，标记区域
        if len(fire_areas) > 0:
            # 有检测框，使用检测框内的区域进行颜色分析
            for x, y, w, h, area in fire_areas:
                # 提取区域
                roi = img[y:y+h, x:x+w]
                if roi.size == 0:
                    continue  # 跳过空区域
                    
                # 转换为HSV颜色空间进行火灾颜色检测
                roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                
                # 定义火灾颜色范围 (红色和橙色)
                lower_red1 = np.array([0, 100, 100])
                upper_red1 = np.array([10, 255, 255])
                lower_red2 = np.array([160, 100, 100])
                upper_red2 = np.array([179, 255, 255])
                
                # 创建火灾颜色掩码
                mask1 = cv2.inRange(roi_hsv, lower_red1, upper_red1)
                mask2 = cv2.inRange(roi_hsv, lower_red2, upper_red2)
                color_mask = cv2.bitwise_or(mask1, mask2)
                
                # 应用掩码到原始区域
                fire_mask[y:y+h, x:x+w] = color_mask
        else:
            # 没有检测框，对整个图像进行颜色分析
            print("未检测到分割掩码，尝试使用颜色检测标记火灾区域...")
            
            # 转换为HSV颜色空间
            img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # 定义火灾颜色范围（包括更广的橙色和黄色范围）
            lower_red1 = np.array([0, 70, 100])   # 宽松的红色下限
            upper_red1 = np.array([15, 255, 255]) # 宽松的红色上限，包含更多橙色
            lower_red2 = np.array([160, 70, 100]) # 宽松的红色下限
            upper_red2 = np.array([179, 255, 255])
            
            # 检测黄色（可能的火焰区域）
            lower_yellow = np.array([15, 70, 100])
            upper_yellow = np.array([35, 255, 255])
            
            # 创建火灾颜色掩码
            mask1 = cv2.inRange(img_hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(img_hsv, lower_red2, upper_red2)
            mask3 = cv2.inRange(img_hsv, lower_yellow, upper_yellow)
            
            # 合并所有颜色掩码
            color_mask = cv2.bitwise_or(cv2.bitwise_or(mask1, mask2), mask3)
            
            # 如果颜色掩码有足够区域，认为检测到火灾
            color_area_percentage = (cv2.countNonZero(color_mask) / (img.shape[0] * img.shape[1])) * 100
            if color_area_percentage > 5.0:  # 如果至少5%的区域有火灾颜色
                fire_detected = True
                fire_confidence = max(fire_confidence, 0.5)  # 设置最小置信度为0.5
                fire_percentage = max(fire_percentage, color_area_percentage)
                
                # 如果启用了报警功能，检查是否需要基于颜色检测发送报警
                if self.enable_alarm and self.alarm_manager:
                    if self.alarm_manager.should_send_alarm(fire_confidence, fire_percentage):
                        # 发送报警邮件，并附上当前帧图像
                        self.alarm_manager.send_alarm_email(
                            frame=img,  # 使用原始图像，因为还没有加入标记
                            fire_confidence=fire_confidence,
                            fire_percentage=fire_percentage,
                            location="视频监控区域 - 颜色检测触发"
                        )
            
            # 应用掩码
            fire_mask = color_mask
        
        # 添加文本信息
        # 创建半透明背景条
        bg_height = 40
        bg_width = 350
        overlay = result_img[0:bg_height, 0:bg_width].copy()
        
        # 根据检测结果选择颜色
        if fire_detected:
            bg_color = (0, 0, 180)  # 红色背景条
            text_color = (255, 255, 255)  # 白色文字
            label_text = f"Fire: {fire_confidence:.2f}"
            
            # 如果启用了报警功能，检查是否需要发送报警
            if self.enable_alarm and self.alarm_manager:
                if self.alarm_manager.should_send_alarm(fire_confidence, fire_percentage):
                    # 发送报警邮件，并附上当前帧图像
                    self.alarm_manager.send_alarm_email(
                        frame=result_img,
                        fire_confidence=fire_confidence,
                        fire_percentage=fire_percentage,
                        location="视频监控区域"
                    )
        else:
            bg_color = (0, 180, 0)  # 绿色背景条
            text_color = (255, 255, 255)  # 白色文字
            label_text = "No Fire"
        
        # 填充背景条
        cv2.rectangle(result_img, (0, 0), (bg_width, bg_height), bg_color, -1)
        # 添加半透明效果
        alpha = 0.7
        cv2.addWeighted(overlay, 1-alpha, result_img[0:bg_height, 0:bg_width], alpha, 0, 
                      result_img[0:bg_height, 0:bg_width])
        
        # 添加文字信息
        cv2.putText(result_img, label_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                   1.0, text_color, 2, cv2.LINE_AA)
        
        # 如果检测到火灾，添加火灾区域百分比
        if fire_percentage > 0:
            # 为火灾区域百分比添加半透明背景
            bg_height = 35
            bg_width = 220
            bg_top = 45
            overlay = result_img[bg_top:bg_top+bg_height, 0:bg_width].copy()
            # 添加背景条
            cv2.rectangle(result_img, (0, bg_top), (bg_width, bg_top+bg_height), (0, 0, 180), -1)
            # 半透明效果
            alpha = 0.7
            cv2.addWeighted(overlay, 1-alpha, result_img[bg_top:bg_top+bg_height, 0:bg_width], alpha, 0, 
                          result_img[bg_top:bg_top+bg_height, 0:bg_width])
            
            # 添加文字 - 复印字体效果增强可读性
            fire_area_text = f"Fire area: {fire_percentage:.1f}%"
            # 先画黑色轮廓
            cv2.putText(result_img, fire_area_text, (12, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 3, cv2.LINE_AA)
            # 再画主要颜色
            cv2.putText(result_img, fire_area_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        
        # 显示结果
        if display:
            try:
                cv2.imshow("Fire Detection Result (YOLOv8)", result_img)
                cv2.waitKey(1)  # 短暂显示
            except Exception as e:
                print(f"警告: 无法显示图像: {e}")
        
        # 保存结果
        if save_path:
            cv2.imwrite(save_path, result_img)
            print(f"已保存处理结果到: {save_path}")
        
        return result_img, fire_detected, fire_confidence, fire_percentage
    
    def process_video(self, video_path, output_path=None, display=False, save_interval=1):
        """
        处理视频文件
        
        Args:
            video_path: 视频文件路径
            output_path: 输出视频路径
            display: 是否显示结果
            save_interval: 每隔多少帧保存一次结果
        """
        print("\n正在使用增强的分割效果处理视频...")
        """
        处理视频文件
        
        Args:
            video_path: 视频文件路径
            output_path: 输出视频路径
            display: 是否显示结果
            save_interval: 每隔多少帧保存一次结果
        """
        # 检查文件是否存在
        if not os.path.exists(video_path):
            print(f"错误: 视频文件不存在: {video_path}")
            return
        
        # 创建视频显示窗口 - 禁用显示
        use_display = display and sys.platform != 'win32'  # 在Windows上默认禁用显示
        if use_display:
            try:
                cv2.namedWindow("Fire Detection Result (YOLOv8)", cv2.WINDOW_NORMAL)
            except Exception as e:
                print(f"警告: 无法创建显示窗口: {e}")
                use_display = False
        
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
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # 处理进度条
        time_start = time.time()
        frame_count = 0
        
        try:
            with tqdm(total=total_frames, desc="处理视频", unit="帧") as pbar:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # 每一帧都处理和保存，不再跳过帧
                    # 处理当前帧
                    result_img, fire_detected, confidence, fire_percentage = self.process_image(
                        frame, display=False
                    )
                    
                    # 显示处理后的帧
                    if use_display:
                        try:
                            cv2.imshow("Fire Detection Result (YOLOv8)", result_img)
                            key = cv2.waitKey(1) & 0xFF
                            if key == ord('q'):
                                print("\n用户按键退出视频播放")
                                break
                        except Exception as e:
                            print(f"警告: 无法显示图像: {e}")
                            use_display = False
                    
                    # 写入输出视频 - 确保每一帧都写入
                    if out:
                        out.write(result_img)
                    
                    frame_count += 1
                    pbar.update(1)
                    
                    # 计算和显示处理速度
                    if frame_count % 10 == 0:
                        time_elapsed = time.time() - time_start
                        if time_elapsed > 0:
                            processing_speed = frame_count / time_elapsed
                            pbar.set_postfix(处理速度=f"{processing_speed:.1f} fps")
        
        finally:
            # 释放资源
            cap.release()
            if out:
                out.release()
            # 安全地尝试销毁窗口
            try:
                cv2.destroyAllWindows()
            except Exception as e:
                print(f"注意: 无法销毁窗口: {e}")  # 忽略错误
            
            if output_path and os.path.exists(output_path):
                print(f"已保存处理后的视频到: {output_path}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='YOLOv8火灾检测工具 - 支持图像和视频分析')
    parser.add_argument('--input', type=str, help='输入图像或视频路径')
    parser.add_argument('--output', type=str, help='输出文件路径（可选）')
    parser.add_argument('--detection_model', type=str, default="Output/yolov8x/final_model.h5.pt", 
                      help='YOLOv8检测模型路径')
    parser.add_argument('--segmentation_model', type=str, default="Output/yolov8x-seg/final_model.h5.pt",
                      help='YOLOv8分割模型路径')
    parser.add_argument('--confidence', type=float, default=0.25, 
                      help='检测置信度阈值（默认0.25，较低以捕获更多可能区域）')
    parser.add_argument('--save_interval', type=int, default=1, 
                      help='视频处理保存帧间隔（默认1）')
    parser.add_argument('--display', action='store_true',
                      help='启用结果显示窗口(可能在某些环境下不可用)')
    
    # 添加火灾报警相关参数
    parser.add_argument('--enable_alarm', action='store_true',
                      help='启用火灾报警功能')
    parser.add_argument('--alarm_threshold', type=float, default=0.5,
                      help='火灾报警阈值（默认0.5）')
    parser.add_argument('--alarm_interval', type=int, default=60,
                      help='报警时间间隔，秒（默认60）')
    parser.add_argument('--use_qq_mail', action='store_true',
                      help='使用QQ邮箱发送报警邮件(内网)，否则使用Gmail(外网)')
    
    args = parser.parse_args()
    
    # 检查是否提供了输入
    if not args.input:
        parser.print_help()
        print("\n错误: 必须提供输入文件路径")
        return
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        return
    
    # 创建检测器
    detector = FireDetector(
        detection_model_path=args.detection_model,
        segmentation_model_path=args.segmentation_model,
        confidence_threshold=args.confidence,
        enable_alarm=args.enable_alarm,
        alarm_threshold=args.alarm_threshold,
        alarm_interval=args.alarm_interval,
        use_qq_mail=args.use_qq_mail
    )
    
    # 确定输出路径
    if not args.output:
        filename, ext = os.path.splitext(args.input)
        args.output = f"{filename}_processed{ext}"
    
    # 根据文件类型处理
    if args.input.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
        # 处理单张图像
        img = cv2.imread(args.input)
        if img is None:
            print(f"错误: 无法读取图像: {args.input}")
            return
        
        detector.process_image(img, display=args.display, save_path=args.output)
        
        if args.display:
            print("按任意键退出...")
            try:
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            except Exception as e:
                print(f"注意: GUI功能不可用: {e}")  # 忽略错误
    
    else:
        # 处理视频
        detector.process_video(
            args.input,
            output_path=args.output,
            display=args.display,
            save_interval=args.save_interval
        )

if __name__ == "__main__":
    main()
