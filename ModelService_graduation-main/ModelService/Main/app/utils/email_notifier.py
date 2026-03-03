"""
邮件通知模块
用于在检测到目标车牌时发送邮件通知
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
import datetime

logger = logging.getLogger(__name__)

class EmailNotifier:
    """邮件通知类，用于发送车牌检测报警邮件"""
    
    def __init__(self, config=None):
        """
        初始化邮件通知器
        
        Args:
            config: 邮件配置，如果为None则使用默认配置
        """
        # 默认配置
        self.config = {
            # QQ邮箱配置
            "sender_email": "1241515924@qq.com",
            "app_password": "lszowfvdnwwxjged",  # QQ邮箱授权码
            "receiver_email": "2769220120@qq.com",
            "smtp_server": "smtp.qq.com",
            "smtp_port": 465,
            "use_ssl": True,
            
            # Gmail配置（备用）
            "gmail_sender": "zhouxuan4516@gmail.com",
            "gmail_password": "qmtg enxt jlli fhng",
            "gmail_server": "smtp.gmail.com",
            "gmail_port": 587,
            "gmail_use_tls": True
        }
        
        # 更新配置
        if config:
            self.config.update(config)
    
    def send_plate_alarm(self, plate_number, frame_path=None, video_id=None, details=None):
        """
        发送车牌报警邮件
        
        Args:
            plate_number: 检测到的车牌号码
            frame_path: 车牌图像路径（可选）
            video_id: 视频ID（可选）
            details: 其他详细信息字典（可选）
            
        Returns:
            bool: 发送是否成功
        """
        # 打印调试信息
        logger.warning("===== 开始发送车牌报警邮件 =====")
        logger.warning(f"目标车牌: {plate_number}")
        logger.warning(f"图像路径: {frame_path}")
        logger.warning(f"视频ID: {video_id}")
        logger.warning(f"详细信息: {details}")
        
        try:
            # 创建邮件
            message = MIMEMultipart()
            message["From"] = self.config["sender_email"]
            message["To"] = self.config["receiver_email"]
            
            # 当前时间
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 邮件主题
            message["Subject"] = f"【车牌监控报警】检测到目标车牌 {plate_number} - {current_time}"
            
            # 邮件正文
            body = f"""
<html>
<body>
    <h2 style="color: red;">⚠️ 车牌监控报警</h2>
    <p>系统在 <b>{current_time}</b> 检测到目标车牌：</p>
    <h3 style="background-color: #ffeeee; padding: 10px; border-left: 4px solid red;">{plate_number}</h3>
"""
            
            # 添加视频信息（如果有）
            if video_id:
                body += f"<p><b>视频ID:</b> {video_id}</p>"
            
            # 添加其他详细信息（如果有）
            if details:
                body += "<h4>详细信息:</h4><ul>"
                for key, value in details.items():
                    body += f"<li><b>{key}:</b> {value}</li>"
                body += "</ul>"
            
            body += """
    <p>请及时查看监控系统了解更多详情。</p>
    <hr>
    <p style="color: gray; font-size: 12px;">此邮件由车牌监控系统自动发送，请勿回复。</p>
</body>
</html>
"""
            message.attach(MIMEText(body, "html"))
            
            # 如果有帧图像，附加到邮件中
            if frame_path and os.path.exists(frame_path):
                try:
                    with open(frame_path, 'rb') as f:
                        img_data = f.read()
                    
                    image = MIMEImage(img_data)
                    image.add_header('Content-Disposition', 'attachment', filename=f"plate_{plate_number}.jpg")
                    message.attach(image)
                except Exception as img_error:
                    logger.error(f"添加图片附件失败: {str(img_error)}")
            
            # 使用QQ邮箱发送
            if self.config["use_ssl"]:
                server = smtplib.SMTP_SSL(self.config["smtp_server"], self.config["smtp_port"])
            else:
                server = smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"])
                if self.config.get("use_tls", False):
                    server.starttls()
            
            server.login(self.config["sender_email"], self.config["app_password"])
            server.sendmail(self.config["sender_email"], self.config["receiver_email"], message.as_string())
            server.quit()
            
            logger.info(f"车牌报警邮件已成功发送至 {self.config['receiver_email']}")
            return True
            
        except Exception as e:
            logger.error(f"发送报警邮件失败: {e}")
            
            # 尝试使用备用Gmail发送
            try:
                logger.info("在send_gmail_alarm中创建了邮件内容")
                
                message = MIMEMultipart()
                message["From"] = self.config["gmail_sender"]
                message["To"] = self.config["receiver_email"]
                message["Subject"] = f"【车牌监控报警】检测到目标车牌 {plate_number} - {current_time}"
                
                # 简化的纯文本邮件
                simple_body = f"""
车牌监控报警

系统在 {current_time} 检测到目标车牌：
{plate_number}

视频ID: {video_id if video_id else '未知'}

此邮件由车牌监控系统自动发送，请勿回复。
"""
                message.attach(MIMEText(simple_body, "plain"))
                
                # 使用Gmail发送
                server = smtplib.SMTP(self.config["gmail_server"], self.config["gmail_port"])
                server.starttls()
                server.login(self.config["gmail_sender"], self.config["gmail_password"])
                server.sendmail(self.config["gmail_sender"], self.config["receiver_email"], message.as_string())
                server.quit()
                
                logger.info(f"车牌报警邮件已通过Gmail备用邮箱成功发送")
                return True
                
            except Exception as gmail_error:
                logger.error(f"Gmail备用邮箱发送失败: {gmail_error}")
                return False
                
            return False
    
    def send_test_email(self):
        """
        发送测试邮件以验证邮件系统是否正常工作
        
        Returns:
            bool: 发送是否成功
        """
        try:
            # 创建邮件
            message = MIMEMultipart()
            message["From"] = self.config["sender_email"]
            message["To"] = self.config["receiver_email"]
            message["Subject"] = "车牌监控系统测试邮件"
            
            # 邮件正文
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            body = f"""
<html>
<body>
    <h2>车牌监控系统邮件测试</h2>
    <p>这是一封测试邮件，用于验证车牌监控系统的邮件发送功能是否正常工作。</p>
    <p>如果您收到此邮件，说明系统配置正确。</p>
    <p>发送时间: {current_time}</p>
</body>
</html>
"""
            message.attach(MIMEText(body, "html"))
            
            # 发送邮件
            server = smtplib.SMTP_SSL(self.config["smtp_server"], self.config["smtp_port"])
            server.login(self.config["sender_email"], self.config["app_password"])
            server.sendmail(self.config["sender_email"], self.config["receiver_email"], message.as_string())
            server.quit()
            
            logger.info(f"测试邮件已成功发送至 {self.config['receiver_email']}")
            return True
            
        except Exception as e:
            logger.error(f"发送测试邮件失败: {e}")
            
            # 尝试使用备用Gmail
            try:
                return self._send_test_gmail()
            except Exception as gmail_error:
                logger.error(f"Gmail备用发送也失败: {gmail_error}")
                return False

# 创建默认的邮件通知器实例
email_notifier = EmailNotifier()
