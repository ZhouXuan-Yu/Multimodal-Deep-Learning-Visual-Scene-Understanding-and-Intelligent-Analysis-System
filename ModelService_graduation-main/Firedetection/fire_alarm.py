"""
火灾报警模块 - 检测到火灾时通过邮件发送报警信息
"""

import os
import time
import smtplib
import cv2
import numpy as np
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

# 导入火灾检测相关函数
from fire_detector import process_image

class FireAlarmSystem:
    """火灾报警系统，整合火灾检测和邮件报警功能"""
    
    def __init__(self, use_external=True, cooldown_seconds=60):
        """
        初始化火灾报警系统
        
        参数:
            use_external: 是否使用外网邮箱(Gmail)发送邮件，False则使用内网邮箱(QQ)
            cooldown_seconds: 报警冷却时间(秒)，避免频繁发送报警邮件
        """
        self.use_external = use_external
        self.cooldown_seconds = cooldown_seconds
        self.last_alarm_time = 0
        self.alarm_count = 0
        self.temp_image_path = "temp_alarm_image.jpg"
        
        # 配置邮件发送参数
        if self.use_external:
            # 使用Gmail外网发送
            self.sender_email = "zhouxuan4516@gmail.com"
            self.app_password = "qmtg enxt jlli fhng"
            self.smtp_server = "smtp.gmail.com"
            self.smtp_port = 587
            self.use_tls = True
            self.use_ssl = False
        else:
            # 使用QQ邮箱内网发送
            self.sender_email = "1241515924@qq.com"
            self.app_password = "lszowfvdnwwxjged"
            self.smtp_server = "smtp.qq.com"
            self.smtp_port = 465
            self.use_tls = False
            self.use_ssl = True
    
    def process_video_with_alarm(self, video_path, output_path=None, receiver_email="2769220120@qq.com", 
                                classification_model=None, segmentation_model=None, 
                                fire_confidence_threshold=0.7, fire_area_threshold=5.0,
                                save_frames=False, frames_dir=None):
        """
        处理视频并在检测到火灾时发送报警邮件
        
        参数:
            video_path: 输入视频路径
            output_path: 输出视频路径(可选)
            receiver_email: 接收报警邮件的邮箱地址
            classification_model: 分类模型
            segmentation_model: 分割模型
            fire_confidence_threshold: 火灾置信度阈值，高于此值时触发报警
            fire_area_threshold: 火灾面积百分比阈值，高于此值时触发报警
            save_frames: 是否保存处理后的帧
            frames_dir: 保存帧的目录
        """
        # 检查视频文件是否存在
        if not os.path.exists(video_path):
            print(f"错误: 视频文件不存在: {video_path}")
            return
            
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"错误: 无法打开视频文件: {video_path}")
            return
            
        # 获取视频信息
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"\n处理视频: {video_path}")
        print(f"分辨率: {width}x{height}, FPS: {fps:.3f}, 总帧数: {total_frames}")
        
        # 准备输出视频
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        else:
            out = None
            
        # 处理每一帧
        frame_count = 0
        
        # 创建保存帧的目录
        if save_frames and frames_dir and not os.path.exists(frames_dir):
            os.makedirs(frames_dir)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_count += 1
                
                try:
                    # 处理当前帧
                    results = process_image(
                        frame, 
                        classification_model=classification_model,
                        segmentation_model=segmentation_model,
                        mode="both",
                        display=False,
                        confidence_threshold=0.5
                    )
                    
                    # 在访问字典前检查必要的键是否存在
                    if "result_image" not in results:
                        print(f"\n警告: 帧 {frame_count} 缺少'result_image'键")
                        # 使用原始帧作为后备
                        output_frame = frame
                    else:
                        output_frame = results["result_image"]
                    
                    classification_result = results.get("classification", None)
                    classification_confidence = results.get("confidence", 0.0)
                    fire_percentage = results.get("fire_percentage", 0.0)
                    
                    # 每10帧输出进度信息
                    if frame_count % 10 == 0:
                        print(f"\r处理进度: {frame_count}/{total_frames} ({frame_count/total_frames*100:.1f}%)", end="")
                        
                except Exception as e:
                    print(f"\n警告: 处理帧 {frame_count} 时出错: {str(e)}")
                    # 使用原始帧继续
                    output_frame = frame
                    classification_result = None
                    classification_confidence = 0.0
                    fire_percentage = 0.0
                
                # 检查是否触发报警条件
                is_fire_detected = (
                    (classification_result == "火灾" and classification_confidence >= fire_confidence_threshold) or
                    (fire_percentage >= fire_area_threshold)
                )
                
                # 如果检测到火灾，发送报警邮件
                if is_fire_detected:
                    current_time = time.time()
                    # 检查冷却时间，避免频繁报警
                    if current_time - self.last_alarm_time >= self.cooldown_seconds:
                        # 保存当前帧用于邮件附件
                        cv2.imwrite(self.temp_image_path, output_frame)
                        
                        # 发送报警邮件
                        alarm_info = {
                            "video_name": os.path.basename(video_path),
                            "frame_number": frame_count,
                            "classification": "Fire" if classification_result == "火灾" else "No Fire",
                            "confidence": classification_confidence,
                            "fire_area_percentage": fire_percentage,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        success = self.send_alarm_email(
                            receiver_email, 
                            alarm_info, 
                            self.temp_image_path
                        )
                        
                        if success:
                            self.alarm_count += 1
                            print(f"\n🔥 火灾报警 #{self.alarm_count} 已发送! (帧 {frame_count}/{total_frames})")
                            print(f"   分类: {alarm_info['classification']} ({alarm_info['confidence']:.2f})")
                            print(f"   火灾面积: {alarm_info['fire_area_percentage']:.2f}%")
                            
                        # 更新上次报警时间
                        self.last_alarm_time = current_time
                
                # 输出进度信息
                if frame_count % 20 == 0:
                    progress_pct = (frame_count / total_frames) * 100
                    print(f"\r处理进度: {progress_pct:.1f}% ({frame_count}/{total_frames})", end="")
                
                # 保存帧到文件
                if save_frames and frames_dir:
                    try:
                        # 确保帧保存目录存在
                        if not os.path.exists(frames_dir):
                            os.makedirs(frames_dir, exist_ok=True)
                        
                        # 生成帧文件路径，支持jpg和png格式
                        frame_path = os.path.join(frames_dir, f"frame_{frame_count:06d}.jpg")
                        success = cv2.imwrite(frame_path, output_frame)
                        
                        if not success:
                            # 如果jpg失败，尝试png
                            frame_path = os.path.join(frames_dir, f"frame_{frame_count:06d}.png")
                            cv2.imwrite(frame_path, output_frame)
                    except Exception as e:
                        print(f"\n警告: 保存帧 {frame_count} 出错: {str(e)}")
                
                # 写入输出视频
                if out:
                    try:
                        # 确保帧与视频分辨率匹配
                        if output_frame.shape[0] != height or output_frame.shape[1] != width:
                            output_frame = cv2.resize(output_frame, (width, height))
                        out.write(output_frame)
                    except Exception as e:
                        print(f"\n警告: 写入帧 {frame_count} 到视频出错: {str(e)}")
                    
        except KeyboardInterrupt:
            print("\n用户中断处理")
        except Exception as e:
            print(f"\n处理视频时出错: {str(e)}")
        finally:
            # 释放资源
            cap.release()
            if out:
                out.release()
            
            # 删除临时文件
            if os.path.exists(self.temp_image_path):
                try:
                    os.remove(self.temp_image_path)
                except:
                    pass
                    
        # 处理完成信息
        print(f"\n视频处理完成，总计 {frame_count} 帧")
        print(f"发送了 {self.alarm_count} 次火灾报警")
        if output_path and os.path.exists(output_path):
            print(f"处理后的视频已保存至: {output_path}")
    
    def send_alarm_email(self, receiver_email, alarm_info, image_path=None):
        """
        发送火灾报警邮件
        
        参数:
            receiver_email: 收件人邮箱
            alarm_info: 报警信息字典
            image_path: 火灾图像路径(可选)
            
        返回:
            bool: 发送成功返回True，否则返回False
        """
        try:
            # 创建邮件
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = receiver_email
            message["Subject"] = f"🚨 火灾报警通知! - {alarm_info['timestamp']}"
            
            # 构建邮件正文
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ padding: 20px; }}
                    .header {{ color: white; background-color: #e53935; padding: 10px; text-align: center; }}
                    .info-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    .info-table th, .info-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    .info-table th {{ background-color: #f2f2f2; }}
                    .footer {{ margin-top: 20px; font-size: 12px; color: #777; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>⚠️ 火灾报警通知!</h2>
                    </div>
                    <p>系统在视频中检测到火灾，请立即处理!</p>
                    
                    <table class="info-table">
                        <tr>
                            <th>视频名称</th>
                            <td>{alarm_info['video_name']}</td>
                        </tr>
                        <tr>
                            <th>帧编号</th>
                            <td>{alarm_info['frame_number']}</td>
                        </tr>
                        <tr>
                            <th>分类结果</th>
                            <td>{alarm_info['classification']} (置信度: {alarm_info['confidence']:.2f})</td>
                        </tr>
                        <tr>
                            <th>火灾面积占比</th>
                            <td>{alarm_info['fire_area_percentage']:.2f}%</td>
                        </tr>
                        <tr>
                            <th>报警时间</th>
                            <td>{alarm_info['timestamp']}</td>
                        </tr>
                    </table>
                    
                    <p>请查看附件中的火灾图像。</p>
                    
                    <div class="footer">
                        <p>此邮件由无人机火灾检测系统自动发送，请勿直接回复。</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # 添加HTML正文
            message.attach(MIMEText(html_body, "html"))
            
            # 添加图像附件(如果提供)
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as img_file:
                    img_data = img_file.read()
                    img_attachment = MIMEImage(img_data)
                    img_attachment.add_header('Content-Disposition', 'attachment', 
                                            filename=f"fire_detected_{alarm_info['timestamp'].replace(':', '-')}.jpg")
                    message.attach(img_attachment)
            
            # 连接到SMTP服务器并发送邮件
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.use_tls:
                    server.starttls()
            
            # 登录
            server.login(self.sender_email, self.app_password)
            
            # 发送邮件
            server.sendmail(self.sender_email, receiver_email, message.as_string())
            
            # 关闭连接
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"发送报警邮件失败: {str(e)}")
            return False


# 简单的测试函数
def test_fire_alarm_email(use_external=True, receiver_email="2769220120@qq.com"):
    """测试火灾报警邮件发送功能"""
    alarm_system = FireAlarmSystem(use_external=use_external)
    test_info = {
        "video_name": "test_video.mp4",
        "frame_number": 123,
        "classification": "Fire",
        "confidence": 0.95,
        "fire_area_percentage": 15.7,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 创建一个简单的测试图像
    test_image = np.zeros((300, 400, 3), dtype=np.uint8)
    test_image[100:200, 150:250] = (0, 0, 255)  # 红色矩形表示火灾
    cv2.putText(test_image, "TEST FIRE", (130, 280), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.imwrite("test_fire_image.jpg", test_image)
    
    success = alarm_system.send_alarm_email(receiver_email, test_info, "test_fire_image.jpg")
    if success:
        print("测试报警邮件发送成功!")
    else:
        print("测试报警邮件发送失败!")
    
    # 清理测试图像
    if os.path.exists("test_fire_image.jpg"):
        os.remove("test_fire_image.jpg")


if __name__ == "__main__":
    # 直接运行此文件将执行测试功能
    import argparse
    
    parser = argparse.ArgumentParser(description="火灾报警系统测试")
    parser.add_argument("--test", action="store_true", help="测试报警邮件发送功能")
    parser.add_argument("--external", action="store_true", help="使用外网邮箱(Gmail)发送")
    parser.add_argument("--email", type=str, default="2769220120@qq.com", help="接收报警邮件的地址")
    
    args = parser.parse_args()
    
    if args.test:
        test_fire_alarm_email(use_external=args.external, receiver_email=args.email)
    else:
        print("请使用 --test 参数测试报警邮件发送功能")
        print("例如: python fire_alarm.py --test --external --email example@qq.com")
