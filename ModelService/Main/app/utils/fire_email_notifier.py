#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
火灾检测邮件通知模块
用于在检测到火灾时发送邮件提醒
"""

import os
import smtplib
import logging
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# 获取日志记录器
logger = logging.getLogger(__name__)

class FireEmailNotifier:
    """火灾检测邮件通知类"""
    
    def __init__(self):
        """初始化邮件配置"""
        # QQ邮箱配置
        self.config = {
            "smtp_server": "smtp.qq.com",
            "smtp_port": 465,
            "sender_email": "1241515924@qq.com",   # 发件人邮箱
            "password": "lszowfvdnwwxjged",        # QQ邮箱授权码
            "receiver_email": "2769220120@qq.com", # 默认接收邮箱
            "use_ssl": True
        }
        
        # Gmail备用配置
        self.config["gmail_sender"] = "firedetectionreport@gmail.com"
        self.config["gmail_password"] = "your_gmail_app_password"
        self.config["gmail_server"] = "smtp.gmail.com"
        self.config["gmail_port"] = 587
        
        logger.info("火灾检测邮件通知器已初始化")
    
    def send_fire_alarm(self, detection_details, frame_path=None):
        """
        发送火灾报警邮件
        
        Args:
            detection_details: 火灾检测详情字典，包含以下信息：
                - process_id: 处理ID
                - detection_time: 检测时间
                - video_path: 视频路径
                - fire_score: 火灾分数
                - message: 其他描述信息
            frame_path: 火灾截图路径（可选）
            
        Returns:
            bool: 发送是否成功
        """
        # 打印调试信息
        logger.warning("===== 开始发送火灾报警邮件 =====")
        logger.warning(f"检测详情: {detection_details}")
        logger.warning(f"图像路径: {frame_path}")
        
        try:
            # 创建邮件
            message = MIMEMultipart()
            message["From"] = self.config["sender_email"]
            
            # 设置收件人
            receiver = detection_details.get("alarm_email") or self.config["receiver_email"]
            message["To"] = receiver
            
            # 设置邮件主题
            message["Subject"] = f"🔥 火灾检测警报 - 检测分数: {detection_details.get('fire_score', 'N/A')}"
            
            # 构建邮件HTML内容
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #ff4d4d; color: white; padding: 15px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .info-row {{ margin-bottom: 10px; }}
                    .label {{ font-weight: bold; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
                    .warning {{ color: #e74c3c; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔥 火灾检测警报</h1>
                    </div>
                    <div class="content">
                        <p class="warning">系统在视频分析中检测到火灾风险！</p>
                        
                        <div class="info-row">
                            <span class="label">检测时间:</span> {detection_details.get('detection_time', '未知')}
                        </div>
                        
                        <div class="info-row">
                            <span class="label">火灾分数:</span> {detection_details.get('fire_score', '未知')}
                        </div>
                        
                        <div class="info-row">
                            <span class="label">处理ID:</span> {detection_details.get('process_id', '未知')}
                        </div>
                        
                        <div class="info-row">
                            <span class="label">视频文件:</span> {os.path.basename(detection_details.get('video_path', '未知'))}
                        </div>
                        
                        <div class="info-row">
                            <span class="label">消息:</span> {detection_details.get('message', '无附加信息')}
                        </div>
                        
                        <p>请立即查看视频并采取必要的安全措施。</p>
                    </div>
                    <div class="footer">
                        这是一封自动生成的邮件，请勿直接回复。<br>
                        火灾检测系统 © {datetime.datetime.now().year}
                    </div>
                </div>
            </body>
            </html>
            """
            
            # 添加HTML内容到邮件
            message.attach(MIMEText(html_content, "html"))
            
            # 如果提供了火灾图像，添加为附件
            if frame_path and os.path.exists(frame_path):
                with open(frame_path, "rb") as image_file:
                    image_data = image_file.read()
                    image = MIMEImage(image_data)
                    image_filename = os.path.basename(frame_path)
                    image.add_header("Content-Disposition", f"attachment; filename={image_filename}")
                    image.add_header("Content-ID", f"<{image_filename}>")
                    message.attach(image)
            
            # 发送邮件
            server = smtplib.SMTP_SSL(self.config["smtp_server"], self.config["smtp_port"])
            server.login(self.config["sender_email"], self.config["password"])
            server.sendmail(self.config["sender_email"], receiver, message.as_string())
            server.quit()
            
            logger.info(f"火灾报警邮件已成功发送至 {receiver}")
            return True
            
        except Exception as e:
            logger.error(f"发送火灾报警邮件失败: {str(e)}")
            
            # 尝试使用备用Gmail发送
            try:
                logger.info("尝试使用Gmail备用邮箱发送")
                
                message = MIMEMultipart()
                message["From"] = self.config["gmail_sender"]
                
                # 设置收件人
                receiver = detection_details.get("alarm_email") or self.config["receiver_email"]
                message["To"] = receiver
                
                # 设置邮件主题
                message["Subject"] = f"🔥 火灾检测警报 (Gmail备用) - 检测分数: {detection_details.get('fire_score', 'N/A')}"
                
                # 重用上面的HTML内容
                message.attach(MIMEText(html_content, "html"))
                
                # 如果提供了火灾图像，添加为附件
                if frame_path and os.path.exists(frame_path):
                    with open(frame_path, "rb") as image_file:
                        image_data = image_file.read()
                        image = MIMEImage(image_data)
                        image_filename = os.path.basename(frame_path)
                        image.add_header("Content-Disposition", f"attachment; filename={image_filename}")
                        image.add_header("Content-ID", f"<{image_filename}>")
                        message.attach(image)
                
                # 发送邮件
                server = smtplib.SMTP(self.config["gmail_server"], self.config["gmail_port"])
                server.starttls()
                server.login(self.config["gmail_sender"], self.config["gmail_password"])
                server.sendmail(self.config["gmail_sender"], receiver, message.as_string())
                server.quit()
                
                logger.info(f"备用Gmail火灾报警邮件已成功发送至 {receiver}")
                return True
                
            except Exception as gmail_error:
                logger.error(f"Gmail备用邮箱发送失败: {str(gmail_error)}")
                return False
                
            return False
    
    def send_test_email(self, receiver_email=None):
        """
        发送测试邮件以验证邮件系统是否正常工作
        
        Args:
            receiver_email: 接收邮件的地址，如果为None则使用默认配置
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 创建邮件
            message = MIMEMultipart()
            message["From"] = self.config["sender_email"]
            message["To"] = receiver_email or self.config["receiver_email"]
            message["Subject"] = "火灾检测系统测试邮件"
            
            # 邮件正文
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            body = f"""
<html>
<body>
    <h2>火灾检测系统邮件测试</h2>
    <p>这是一封测试邮件，用于验证火灾检测系统的邮件发送功能是否正常工作。</p>
    <p>如果您收到此邮件，说明系统配置正确。</p>
    <p>发送时间: {current_time}</p>
</body>
</html>
"""
            message.attach(MIMEText(body, "html"))
            
            # 发送邮件
            server = smtplib.SMTP_SSL(self.config["smtp_server"], self.config["smtp_port"])
            server.login(self.config["sender_email"], self.config["password"])
            server.sendmail(self.config["sender_email"], message["To"], message.as_string())
            server.quit()
            
            logger.info(f"火灾检测测试邮件已成功发送至 {message['To']}")
            return True
            
        except Exception as e:
            logger.error(f"发送火灾检测测试邮件失败: {str(e)}")
            
            # 尝试使用备用Gmail
            try:
                return self._send_test_gmail(receiver_email)
            except Exception as gmail_error:
                logger.error(f"Gmail备用发送也失败: {str(gmail_error)}")
                return False
                
    def _send_test_gmail(self, receiver_email=None):
        """Gmail备用发送测试邮件"""
        message = MIMEMultipart()
        message["From"] = self.config["gmail_sender"]
        message["To"] = receiver_email or self.config["receiver_email"]
        message["Subject"] = "火灾检测系统测试邮件 (Gmail备用)"
        
        # 邮件正文
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = f"""
<html>
<body>
    <h2>火灾检测系统邮件测试 (Gmail备用)</h2>
    <p>这是一封通过Gmail备用通道发送的测试邮件，用于验证火灾检测系统的邮件发送功能是否正常工作。</p>
    <p>如果您收到此邮件，说明系统配置正确。</p>
    <p>发送时间: {current_time}</p>
</body>
</html>
"""
        message.attach(MIMEText(body, "html"))
        
        # 发送邮件
        server = smtplib.SMTP(self.config["gmail_server"], self.config["gmail_port"])
        server.starttls()
        server.login(self.config["gmail_sender"], self.config["gmail_password"])
        server.sendmail(self.config["gmail_sender"], message["To"], message.as_string())
        server.quit()
        
        logger.info(f"Gmail备用测试邮件已成功发送至 {message['To']}")
        return True

# 创建默认的邮件通知器实例
fire_email_notifier = FireEmailNotifier()
