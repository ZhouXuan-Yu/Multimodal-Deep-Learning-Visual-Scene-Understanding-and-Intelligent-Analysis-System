"""
火灾检测邮件报警模块
"""
import os
import time
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

class FireAlarmManager:
    """
    火灾报警管理器 - 负责发送邮件报警
    """
    def __init__(self, 
                use_qq_mail=True, 
                sender_email=None, 
                app_password=None, 
                receiver_email=None,
                alarm_interval=60,   # 报警间隔，单位秒
                alarm_threshold=0.5, # 火灾报警阈值
                ):
        """
        初始化报警管理器
        
        Args:
            use_qq_mail: 是否使用QQ邮箱(内网)，False则使用Gmail(外网)
            sender_email: 发送者邮箱，None则使用默认值
            app_password: 邮箱授权码，None则使用默认值
            receiver_email: 接收者邮箱，None则使用默认值
            alarm_interval: 报警间隔时间(秒)
            alarm_threshold: 火灾报警阈值
        """
        # 是否使用QQ邮箱
        self.use_qq_mail = use_qq_mail
        
        # 发送邮件必要信息
        if self.use_qq_mail:
            # QQ邮箱(内网) - 请替换为您自己的邮箱信息
            self.sender_email = sender_email or "example@qq.com"
            self.app_password = app_password or "授权码" # 建议从环境变量获取，不要硬编码
            self.receiver_email = receiver_email or "receiver@example.com"
            self.smtp_server = "smtp.qq.com"
            self.smtp_port = 465
            self.use_ssl = True
        else:
            # Gmail(外网) - 请替换为您自己的邮箱信息
            self.sender_email = sender_email or "example@gmail.com"
            self.app_password = app_password or "授权码" # 建议从环境变量获取，不要硬编码
            self.receiver_email = receiver_email or "receiver@example.com"
            self.smtp_server = "smtp.gmail.com"
            self.smtp_port = 587
            self.use_ssl = False
        
        # 报警控制参数
        self.alarm_interval = alarm_interval  # 报警间隔(秒)
        self.alarm_threshold = alarm_threshold  # 火灾报警阈值
        self.last_alarm_time = 0  # 上次报警时间
        self.alarm_count = 0  # 报警次数
        
        logger.info(f"火灾报警管理器初始化完成，接收邮箱: {self.receiver_email}, 报警阈值: {self.alarm_threshold}")
    
    def should_send_alarm(self, fire_confidence, fire_percentage):
        """
        判断是否应该发送报警
        
        Args:
            fire_confidence: 火灾置信度
            fire_percentage: 火灾区域百分比
            
        Returns:
            bool: 是否应该发送报警
        """
        # 当前时间
        current_time = time.time()
        
        # 调试信息
        logger.info(f"检查是否应该发送报警:\n"
              f"- 火灾置信度: {fire_confidence:.2f} (阈值: {self.alarm_threshold})\n"
              f"- 火灾面积比例: {fire_percentage:.1f}% (阈值: {self.alarm_threshold*100}%)\n"
              f"- 距上次报警时间: {current_time - self.last_alarm_time:.1f}秒 (最小间隔: {self.alarm_interval}秒)")
        
        # 如果火灾置信度或火灾区域百分比超过阈值
        if fire_confidence > self.alarm_threshold or fire_percentage/100 > self.alarm_threshold:
            # 检查是否超过报警间隔时间
            if current_time - self.last_alarm_time > self.alarm_interval:
                self.last_alarm_time = current_time
                logger.info("条件满足，将发送报警邮件！")
                return True
            else:
                logger.info(f"条件满足，但距离上次报警未超过{self.alarm_interval}秒，暂不发送")
        else:
            logger.info("火灾置信度和面积未超过报警阈值，不发送报警")
        
        return False
    
    def send_alarm_email(self, frame, fire_confidence, fire_percentage, location="未知位置"):
        """
        发送火灾报警邮件
        
        Args:
            frame: 火灾图像帧
            fire_confidence: 火灾置信度
            fire_percentage: 火灾区域百分比
            location: 位置信息
            
        Returns:
            bool: 是否发送成功
        """
        try:
            self.alarm_count += 1
            
            # 创建包含图像的邮件
            msg = MIMEMultipart()
            msg['Subject'] = f'火灾报警! - 火灾置信度 {fire_confidence*100:.2f}% - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            
            # 邮件正文
            body = f"""
            <html>
            <body>
                <h2 style="color: red;">检测到火灾!</h2>
                <p><b>时间:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><b>位置:</b> {location}</p>
                <p><b>火灾置信度:</b> {fire_confidence*100:.2f}%</p>
                <p><b>火灾面积比例:</b> {fire_percentage:.2f}%</p>
                <p><b>这是第 {self.alarm_count} 次报警</b></p>
                <p>请立即查看监控画面并采取必要的安全措施!</p>
                <p>附件中包含检测到火灾的图像</p>
            </body>
            </html>
            """
            msg_body = MIMEText(body, 'html')
            msg.attach(msg_body)
            
            # 将检测到火灾的图像作为附件
            # 确保帧是彩色图像
            if frame is not None:
                # 保存临时图像文件
                temp_image_path = "fire_alarm_temp.jpg"
                import cv2
                cv2.imwrite(temp_image_path, frame)
                
                # 添加图像附件
                with open(temp_image_path, 'rb') as f:
                    img_data = f.read()
                    image = MIMEImage(img_data, name=f'fire_detected_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')
                    msg.attach(image)
                
                # 尝试删除临时文件
                try:
                    os.remove(temp_image_path)
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {str(e)}")
            
            # 发送邮件
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            
            server.login(self.sender_email, self.app_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"火灾报警邮件已发送至 {self.receiver_email}")
            return True
            
        except Exception as e:
            logger.error(f"发送报警邮件失败: {str(e)}")
            return False
