"""
可视化模块，用于监控界面和结果展示
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import threading
import queue
from config import *

# 导入报警模块
from alarm import send_red_alert, send_yellow_alert


class MonitoringInterface:
    """
    监控界面类，用于显示实时监控画面和警报信息
    """
    
    def __init__(self, model_path=None, camera_id=0, video_path=None, title="红外监控视频行为识别系统"):
        """
        初始化监控界面
        
        Args:
            model_path: 模型路径，如果为None则使用默认路径
            camera_id: 摄像头ID，仅在video_path为None时使用
            video_path: 视频文件路径，如果为None则使用摄像头
            title: 窗口标题
        """
        # 加载模型
        if model_path is None:
            model_path = os.path.join(DATA_ROOT, 'checkpoints', 'best_model.pth')
        
        model = InfraredActionSystem(model_path=model_path)
        self.model = model
        
        # 设置输出目录
        self.output_dir = os.path.join(os.path.dirname(model_path), 'results')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title(title)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置窗口大小
        self.root.geometry("1280x800")
        
        # 创建UI元素
        self.setup_ui()
        
        # 初始化视频源
        self.cap = None
        self.is_running = False
        self.current_frame = None
        
        # 创建队列用于线程间通信
        self.frame_queue = queue.Queue(maxsize=30)
        self.result_queue = queue.Queue()
        
        # 行为历史记录
        self.action_history = []
        self.max_history_length = 100
        
        # 警报状态
        self.red_alert_count = 0
        self.yellow_alert_count = 0
        
        # 录制状态
        self.is_recording = False
        self.out = None
        self.record_start_time = None
        
        # 类别名称
        self.class_names = list(ACTION_CATEGORIES.keys())
        
        # 创建输出目录
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def setup_ui(self):
        """设置用户界面"""
        # 设置主框架
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧：视频显示区域
        self.left_frame = tk.Frame(main_frame, width=800, height=600)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 视频画布
        self.canvas = tk.Canvas(self.left_frame, bg='black', width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 添加报警系统状态指示灯
        self.alarm_indicator = tk.Canvas(self.left_frame, width=20, height=20, bg='green', highlightthickness=1, highlightbackground="black")
        self.alarm_indicator.place(x=10, y=10)
        
        # 右侧：控制和信息区域
        right_frame = tk.Frame(main_frame, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)
        
        # 状态框
        status_frame = tk.LabelFrame(right_frame, text="系统状态", padx=5, pady=5)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_text = tk.StringVar()
        self.status_text.set("就绪")
        status_label = tk.Label(status_frame, textvariable=self.status_text, font=("Arial", 12))
        status_label.pack(pady=5)
        
        # 当前检测结果框
        detection_frame = tk.LabelFrame(right_frame, text="当前检测", padx=5, pady=5)
        detection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.action_text = tk.StringVar()
        self.action_text.set("无行为检测")
        self.action_label = tk.Label(detection_frame, textvariable=self.action_text, font=("Arial", 14, "bold"))
        self.action_label.pack(pady=5)
        
        self.confidence_text = tk.StringVar()
        self.confidence_text.set("置信度: 0.00")
        confidence_label = tk.Label(detection_frame, textvariable=self.confidence_text, font=("Arial", 12))
        confidence_label.pack(pady=5)
        
        # 警报统计框
        alert_frame = tk.LabelFrame(right_frame, text="警报统计", padx=5, pady=5)
        alert_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.red_alert_text = tk.StringVar()
        self.red_alert_text.set("红色警报: 0")
        red_alert_label = tk.Label(alert_frame, textvariable=self.red_alert_text, fg="red", font=("Arial", 12))
        red_alert_label.pack(pady=3, anchor=tk.W)
        
        self.yellow_alert_text = tk.StringVar()
        self.yellow_alert_text.set("黄色警报: 0")
        yellow_alert_label = tk.Label(alert_frame, textvariable=self.yellow_alert_text, fg="orange", font=("Arial", 12))
        yellow_alert_label.pack(pady=3, anchor=tk.W)
        
        # 控制按钮
        control_frame = tk.LabelFrame(right_frame, text="控制", padx=5, pady=5)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        button_frame = tk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_button = tk.Button(button_frame, text="开始", command=self.start_monitoring, width=10)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(button_frame, text="停止", command=self.stop_monitoring, width=10, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.record_button = tk.Button(button_frame, text="录制", command=self.toggle_recording, width=10)
        self.record_button.pack(side=tk.LEFT, padx=5)
        
        self.test_alarm_button = tk.Button(button_frame, text="测试报警", command=self.test_alarm, width=10)
        self.test_alarm_button.pack(side=tk.LEFT, padx=5)
        
        # 视频源选择
        source_frame = tk.Frame(control_frame)
        source_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(source_frame, text="视频源:").pack(side=tk.LEFT, padx=5)
        
        self.source_var = tk.StringVar()
        self.source_var.set("摄像头")
        
        camera_radio = tk.Radiobutton(source_frame, text="摄像头", variable=self.source_var, value="摄像头", command=self.select_source)
        camera_radio.pack(side=tk.LEFT, padx=5)
        
        file_radio = tk.Radiobutton(source_frame, text="文件", variable=self.source_var, value="文件", command=self.select_source)
        file_radio.pack(side=tk.LEFT, padx=5)
        
        # 摄像头ID/文件路径
        self.source_entry_var = tk.StringVar()
        self.source_entry_var.set("0")  # 默认摄像头ID
        
        source_entry_frame = tk.Frame(control_frame)
        source_entry_frame.pack(fill=tk.X, pady=5)
        
        self.source_label = tk.Label(source_entry_frame, text="摄像头ID:")
        self.source_label.pack(side=tk.LEFT, padx=5)
        
        self.source_entry = tk.Entry(source_entry_frame, textvariable=self.source_entry_var, width=25)
        self.source_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.browse_button = tk.Button(source_entry_frame, text="浏览", command=self.browse_file, state=tk.DISABLED)
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        # 模型参数设置
        param_frame = tk.LabelFrame(right_frame, text="模型参数", padx=5, pady=5)
        param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 置信度阈值
        conf_frame = tk.Frame(param_frame)
        conf_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(conf_frame, text="置信度阈值:").pack(side=tk.LEFT, padx=5)
        
        self.conf_var = tk.DoubleVar()
        self.conf_var.set(CONFIDENCE_THRESHOLD)
        
        self.conf_scale = tk.Scale(conf_frame, from_=0.1, to=1.0, resolution=0.05, orient=tk.HORIZONTAL, 
                                  variable=self.conf_var, length=200)
        self.conf_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 时序平滑开关
        smooth_frame = tk.Frame(param_frame)
        smooth_frame.pack(fill=tk.X, pady=5)
        
        self.smooth_var = tk.BooleanVar()
        self.smooth_var.set(USE_TEMPORAL_SMOOTHING)
        
        self.smooth_check = tk.Checkbutton(smooth_frame, text="启用时序平滑", variable=self.smooth_var)
        self.smooth_check.pack(side=tk.LEFT, padx=5)
        
        # 日志区域
        log_frame = tk.LabelFrame(right_frame, text="系统日志", padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        log_scrollbar = tk.Scrollbar(self.log_text)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        log_scrollbar.config(command=self.log_text.yview)
        
        # 输出信息框
        output_frame = tk.LabelFrame(right_frame, text="输出信息", padx=5, pady=5)
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.output_dir_text = tk.StringVar()
        self.output_dir_text.set(f"输出目录: {self.output_dir}")
        
        output_dir_label = tk.Label(output_frame, textvariable=self.output_dir_text, font=("Arial", 10))
        output_dir_label.pack(pady=3, anchor=tk.W)
        
        # 显示一些初始日志信息
        self.log("系统初始化完成")
        self.log(f"模型类型: {MODEL_TYPE}")
        self.log(f"类别数量: {NUM_CLASSES}")
    
    def log(self, message):
        """添加日志信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def select_source(self):
        """选择视频源"""
        if self.source_var.get() == "摄像头":
            self.source_label.config(text="摄像头ID:")
            self.source_entry_var.set("0")
            self.browse_button.config(state=tk.DISABLED)
        else:
            self.source_label.config(text="文件路径:")
            self.source_entry_var.set("")
            self.browse_button.config(state=tk.NORMAL)
    
    def browse_file(self):
        """浏览文件"""
        file_path = filedialog.askopenfilename(title="选择视频文件", 
                                              filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv")])
        if file_path:
            self.source_entry_var.set(file_path)
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_running:
            return
        
        # 获取视频源
        if self.source_var.get() == "摄像头":
            try:
                self.camera_id = int(self.source_entry_var.get())
                self.video_path = None
                self.log(f"使用摄像头 ID: {self.camera_id}")
            except ValueError:
                messagebox.showerror("错误", "无效的摄像头ID")
                return
        else:
            self.video_path = self.source_entry_var.get()
            if not self.video_path or not os.path.isfile(self.video_path):
                messagebox.showerror("错误", "请选择有效的视频文件")
                return
            self.log(f"使用视频文件: {self.video_path}")
        
        # 更新模型参数
        self.model.conf_threshold = self.conf_var.get()
        self.model.use_smoothing = self.smooth_var.get()
        
        # 开始视频处理线程
        self.is_running = True
        self.video_thread = threading.Thread(target=self.process_video)
        self.video_thread.daemon = True
        self.video_thread.start()
        
        # 开始UI更新线程
        self.update_thread = threading.Thread(target=self.update_ui)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # 更新按钮状态
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log("监控已开始")
        self.status_text.set("正在监控")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 关闭视频源
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        # 停止录制
        if self.is_recording:
            self.toggle_recording()
        
        # 更新按钮状态
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        self.log("监控已停止")
        self.status_text.set("已停止")
        
        # 清空帧
        self.canvas.delete("all")
        self.canvas.create_text(400, 300, text="监控已停止", fill="white", font=("Arial", 24))
    
    def toggle_recording(self):
        """切换录制状态"""
        if not self.is_recording and self.current_frame is not None:
            # 开始录制
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = os.path.join(self.output_dir, f"recording_{timestamp}.mp4")
            
            # 获取当前帧的尺寸
            height, width = self.current_frame.shape[:2]
            
            # 创建VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.out = cv2.VideoWriter(video_filename, fourcc, 20.0, (width, height))
            
            # 更新录制状态
            self.is_recording = True
            self.record_start_time = time.time()
            self.record_button.config(text="停止录制", bg="red")
            
            self.log(f"开始录制视频: {video_filename}")
        
        elif self.is_recording:
            # 停止录制
            if self.out is not None:
                self.out.release()
                self.out = None
            
            self.is_recording = False
            self.record_button.config(text="录制", bg="SystemButtonFace")
            
            self.log("停止录制视频")
    
    def process_video(self):
        """视频处理线程函数"""
        # 打开视频源
        if self.video_path is not None:
            self.cap = cv2.VideoCapture(self.video_path)
        else:
            self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            self.log("无法打开视频源")
            self.is_running = False
            return
        
        # 处理视频帧
        frame_count = 0
        start_time = time.time()
        
        while self.is_running:
            ret, frame = self.cap.read()
            
            if not ret:
                if self.video_path is not None:
                    self.log("视频处理完成")
                    self.is_running = False
                else:
                    self.log("无法从摄像头获取帧")
                    time.sleep(0.1)  # 等待一会再尝试
                    continue
                break
            
            # 保存当前帧
            self.current_frame = frame.copy()
            
            # 如果正在录制，记录当前帧
            if self.is_recording and self.out is not None:
                self.out.write(frame)
            
            # 将帧放入队列
            if not self.frame_queue.full():
                self.frame_queue.put(frame)
            
            frame_count += 1
            
            # 每秒计算一次FPS
            if frame_count % 30 == 0:
                current_time = time.time()
                elapsed = current_time - start_time
                if elapsed > 0:
                    fps = frame_count / elapsed
                    self.result_queue.put({"type": "fps", "value": fps})
                    frame_count = 0
                    start_time = current_time
            
            # 限制处理速度，避免过度消耗资源
            time.sleep(0.01)
        
        # 关闭视频源
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def update_ui(self):
        """UI更新线程函数"""
        last_update_time = time.time()
        
        while self.is_running:
            current_time = time.time()
            
            # 从队列中获取帧并处理
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                
                # 处理帧以识别行为
                processed_frame, prediction, confidence = self.process_frame(frame)
                
                # 更新UI显示
                self.update_frame_display(processed_frame)
                
                # 更新行为检测结果显示
                if prediction is not None:
                    action_name = self.class_names[prediction]
                    self.action_text.set(action_name.capitalize())
                    self.confidence_text.set(f"置信度: {confidence:.2f}")
                    
                    # 更新行为标签的颜色
                    alert_level = ACTION_ALERT_LEVEL[prediction]
                    if alert_level == 'red':
                        self.action_label.config(fg="red")
                    elif alert_level == 'yellow':
                        self.action_label.config(fg="orange")
                    else:
                        self.action_label.config(fg="green")
                    
                    # 记录行为历史
                    self.action_history.append((action_name, confidence, alert_level, current_time))
                    
                    # 保持历史记录长度
                    if len(self.action_history) > self.max_history_length:
                        self.action_history.pop(0)
                    
                    # 更新警报统计并发送邮件
                    if alert_level == 'red' and confidence > 0.8:
                        self.red_alert_count += 1
                        self.red_alert_text.set(f"红色警报: {self.red_alert_count}")
                        
                        # 保存截图并发送红色警报
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        alert_filename = os.path.join(self.output_dir, f"alert_{action_name}_{timestamp}.jpg")
                        cv2.imwrite(alert_filename, self.current_frame)
                        self.log(f"危险行为警报！已保存截图: {os.path.basename(alert_filename)}")
                        send_red_alert(action_name, confidence, alert_filename)
                        
                    elif alert_level == 'yellow' and confidence > 0.75:
                        self.yellow_alert_count += 1
                        self.yellow_alert_text.set(f"黄色警报: {self.yellow_alert_count}")
                        
                        # 保存截图并发送黄色警报
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        alert_filename = os.path.join(self.output_dir, f"warning_{action_name}_{timestamp}.jpg")
                        cv2.imwrite(alert_filename, self.current_frame)
                        self.log(f"警告行为提示！已保存截图: {os.path.basename(alert_filename)}")
                        send_yellow_alert(action_name, confidence, alert_filename)
            
            # 处理其他结果更新
            while not self.result_queue.empty():
                result = self.result_queue.get()
                
                if result["type"] == "fps":
                    self.status_text.set(f"正在监控 ({result['value']:.1f} FPS)")
            
            # 控制更新频率
            elapsed = current_time - last_update_time
            if elapsed < 0.033:  # 约30 FPS
                time.sleep(0.033 - elapsed)
            
            last_update_time = current_time
    
    def process_frame(self, frame):
        """处理单个帧并返回结果"""
        # 这里应调用模型的process_frame方法
        # 但由于示例代码限制，我们简化实现
        # TODO: 实现实际的行为识别逻辑
        
        # 模拟处理结果
        processed_frame = frame.copy()
        prediction = None
        confidence = 0.0
        
        # 返回处理后的帧和预测结果
        return processed_frame, prediction, confidence
        
    def test_alarm(self):
        """测试报警系统"""
        if not self.current_frame is None:
            # 切换报警指示灯颜色
            self.alarm_indicator.config(bg='red')
            
            # 测试红色警报
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_filename = os.path.join(self.output_dir, f"test_alert_{timestamp}.jpg")
            cv2.imwrite(alert_filename, self.current_frame)
            
            # 发送测试警报
            threading.Thread(
                target=self._send_test_alarms,
                args=(alert_filename,)
            ).start()
            
            self.log("已发送测试警报邮件...")
            
            # 2秒后恢复指示灯颜色
            self.root.after(2000, lambda: self.alarm_indicator.config(bg='green'))
        else:
            messagebox.showinfo("提示", "请先启动视频源")
    
    def _send_test_alarms(self, image_path):
        """发送测试警报"""
        # 测试红色警报
        send_red_alert("测试警报", 0.99, image_path)
        
        # 等待2秒
        time.sleep(2)
        
        # 测试黄色警报
        send_yellow_alert("测试警报", 0.95, image_path)
        
        self.log("测试警报发送完成")
    
    def update_frame_display(self, frame):
        """更新UI中的视频帧显示"""
        # 调整大小以适应canvas
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:  # 确保canvas已经被正确初始化
            # 保持宽高比
            frame_height, frame_width = frame.shape[:2]
            ratio = min(canvas_width / frame_width, canvas_height / frame_height)
            new_width = int(frame_width * ratio)
            new_height = int(frame_height * ratio)
            
            resized_frame = cv2.resize(frame, (new_width, new_height))
            
            # 转换为PIL格式
            if len(resized_frame.shape) == 3:
                # 彩色图像
                image = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            else:
                # 灰度图像
                image = cv2.cvtColor(resized_frame, cv2.COLOR_GRAY2RGB)
                
            pil_image = Image.fromarray(image)
            
            # 转换为PhotoImage
            self.photo = ImageTk.PhotoImage(image=pil_image)
            
            # 更新Canvas
            self.canvas.delete("all")
            self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=self.photo)
    
    def on_closing(self):
        """窗口关闭时的处理"""
        if messagebox.askokcancel("退出", "确定要退出吗?"):
            self.stop_monitoring()
            self.root.destroy()
    
    def run(self):
        """运行监控界面"""
        # 开始主循环
        self.root.mainloop()


# 用于可视化训练过程的函数
def visualize_training_progress(train_losses, val_losses, train_accs, val_accs, save_path=None):
    """可视化训练进度"""
    epochs = range(1, len(train_losses) + 1)
    
    plt.figure(figsize=(12, 5))
    
    # 损失子图
    plt.subplot(1, 2, 1)
    plt.plot(epochs, train_losses, 'b-', label='Training Loss')
    plt.plot(epochs, val_losses, 'r-', label='Validation Loss')
    plt.title('Training and Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True)
    
    # 准确率子图
    plt.subplot(1, 2, 2)
    plt.plot(epochs, train_accs, 'b-', label='Training Accuracy')
    plt.plot(epochs, val_accs, 'r-', label='Validation Accuracy')
    plt.title('Training and Validation Accuracy')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()


def visualize_confusion_matrix(cm, class_names, save_path=None):
    """可视化混淆矩阵"""
    import seaborn as sns
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
               xticklabels=class_names, yticklabels=class_names)
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.title('Confusion Matrix')
    
    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def visualize_samples(dataset, num_samples=5, classes=None, save_path=None):
    """可视化数据集样本"""
    # 获取数据集中的样本
    samples = []
    labels = []
    
    for i in range(min(num_samples * len(classes) if classes else num_samples, len(dataset))):
        sample, label = dataset[i]
        samples.append(sample)
        labels.append(label)
    
    # 创建图表
    fig, axes = plt.subplots(len(samples), 1, figsize=(10, 3 * len(samples)))
    
    for i, (sample, label) in enumerate(zip(samples, labels)):
        # 获取样本的中间帧
        if isinstance(sample, torch.Tensor):
            # 对于张量格式的样本
            middle_frame_idx = sample.shape[1] // 2
            frame = sample[:, middle_frame_idx].permute(1, 2, 0).numpy()
            
            # 如果是单通道，转为三通道
            if frame.shape[2] == 1:
                frame = np.repeat(frame, 3, axis=2)
            
            # 反归一化
            frame = np.clip((frame * 0.225 + 0.45) * 255, 0, 255).astype(np.uint8)
        else:
            # 对于numpy数组格式的样本
            middle_frame_idx = len(sample) // 2
            frame = sample[middle_frame_idx]
        
        # 显示帧
        if len(samples) > 1:
            axes[i].imshow(frame)
            axes[i].set_title(f"Class: {class_names[label] if class_names else label}")
            axes[i].axis('off')
        else:
            plt.imshow(frame)
            plt.title(f"Class: {class_names[label] if class_names else label}")
            plt.axis('off')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()


if __name__ == "__main__":
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='红外监控视频行为识别系统')
    parser.add_argument('--model', type=str, default=None, help='模型路径')
    parser.add_argument('--video', type=str, default=None, help='视频文件路径（如果不指定则使用摄像头）')
    parser.add_argument('--camera', type=int, default=0, help='摄像头ID（仅在不指定视频文件时使用）')
    args = parser.parse_args()
    
    # 创建监控界面并运行
    interface = MonitoringInterface(
        model_path=args.model,
        camera_id=args.camera,
        video_path=args.video
    )
    interface.run()
