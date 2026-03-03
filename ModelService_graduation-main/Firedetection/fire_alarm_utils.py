"""
火灾报警工具模块
支持内网(QQ邮箱)和外网(Gmail)发送邮件报警
"""
import os
import time
import smtplib
import numpy as np
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import cv2

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
            # QQ邮箱(内网)
            self.sender_email = sender_email or "1241515924@qq.com"
            self.app_password = app_password or "lszowfvdnwwxjged"
            self.receiver_email = receiver_email or "2769220120@qq.com"  # 修改为与cc.py相同的接收者
            self.smtp_server = "smtp.qq.com"
            self.smtp_port = 465
            self.use_ssl = True
        else:
            # Gmail(外网)
            self.sender_email = sender_email or "zhouxuan4516@gmail.com"
            self.app_password = app_password or "qmtg enxt jlli fhng"
            self.receiver_email = receiver_email or "2769220120@qq.com"  # 保持一致的接收者
            self.smtp_server = "smtp.gmail.com"
            self.smtp_port = 587
            self.use_ssl = False
        
        # 报警控制参数
        self.alarm_interval = alarm_interval  # 报警间隔(秒)
        self.alarm_threshold = alarm_threshold  # 火灾报警阈值
        self.last_alarm_time = 0  # 上次报警时间
        self.alarm_count = 0  # 报警次数
    
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
        print(f"\n检查是否应该发送报警:\n"
              f"- 火灾置信度: {fire_confidence:.2f} (阈值: {self.alarm_threshold})\n"
              f"- 火灾面积比例: {fire_percentage:.1f}% (阈值: {self.alarm_threshold*100}%)\n"
              f"- 距上次报警时间: {current_time - self.last_alarm_time:.1f}秒 (最小间隔: {self.alarm_interval}秒)")
        
        # 如果火灾置信度或火灾区域百分比超过阈值
        if fire_confidence > self.alarm_threshold or fire_percentage/100 > self.alarm_threshold:
            # 检查是否超过报警间隔时间
            if current_time - self.last_alarm_time > self.alarm_interval:
                self.last_alarm_time = current_time
                print("条件满足，将发送报警邮件！")
                return True
            else:
                print(f"条件满足，但距离上次报警未超过{self.alarm_interval}秒，暂不发送")
        else:
            print("火灾置信度和面积未超过报警阈值，不发送报警")
        
        return False
    
    def send_alarm_email(self, frame, fire_confidence, fire_percentage, location="未知位置"):
        """
        发送火灾报警邮件
        
        Args:
            frame: 检测到火灾的帧
            fire_confidence: 火灾置信度
            fire_percentage: 火灾区域百分比
            location: 火灾位置信息
        
        Returns:
            bool: 发送是否成功
        """
        try:
            print(f"\n正在准备发送火灾警报邮件...\n"
                  f"- 使用{'QQ邮箱(内网)' if self.use_qq_mail else 'Gmail(外网)'}\n"
                  f"- 发送者: {self.sender_email}\n"
                  f"- 接收者: {self.receiver_email}\n"
                  f"- 火灾置信度: {fire_confidence:.2f}\n"
                  f"- 火灾区域: {fire_percentage:.1f}%")
            
            # 创建邮件内容
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = self.receiver_email
            
            # 标题附加报警编号，以区分不同报警
            self.alarm_count += 1
            message["Subject"] = f"[紧急] 火灾报警 #{self.alarm_count} - 置信度: {fire_confidence:.2f}, 区域: {fire_percentage:.1f}%"
            
            # 邮件正文内容
            body = f"""
            <html>
            <body>
                <h2 style="color: red;">火灾警报!</h2>
                <p><b>时间:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><b>位置:</b> {location}</p>
                <p><b>火灾置信度:</b> {fire_confidence:.2f}</p>
                <p><b>火灾覆盖区域:</b> {fire_percentage:.1f}%</p>
                <p><b>警报等级:</b> {'严重' if fire_percentage > 30 else '中等'}</p>
                <p style="color: red;">请立即采取行动!</p>
                <p>下方附有火灾场景图片。</p>
            </body>
            </html>
            """
            message.attach(MIMEText(body, "html"))
            
            # 保存图像并附加到邮件
            alarm_img_path = "temp_alarm_image.jpg"
            cv2.imwrite(alarm_img_path, frame)
            
            with open(alarm_img_path, 'rb') as f:
                img_data = f.read()
                image = MIMEImage(img_data, name=os.path.basename(alarm_img_path))
                message.attach(image)
            
            # 连接到SMTP服务器并发送邮件
            if self.use_ssl:
                print(f"使用SSL连接到SMTP服务器: {self.smtp_server}:{self.smtp_port}")
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                print(f"连接到SMTP服务器: {self.smtp_server}:{self.smtp_port}")
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                print("启用TLS加密...")
                server.starttls()  # 启用TLS加密
            
            # 登录邮箱
            print(f"尝试登录邮箱: {self.sender_email}")
            server.login(self.sender_email, self.app_password)
            
            # 发送邮件
            print(f"发送邮件: {self.sender_email} -> {self.receiver_email}")
            server.sendmail(self.sender_email, self.receiver_email, message.as_string())
            
            # 关闭连接
            print("关闭SMTP连接")
            server.quit()
            
            # 删除临时图像
            if os.path.exists(alarm_img_path):
                os.remove(alarm_img_path)
            
            print(f"火灾警报邮件成功发送! 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            return True
            
        except Exception as e:
            print(f"发送警报邮件失败: {e}")
            return False

# 如果直接运行此文件，则进行测试
if __name__ == "__main__":
    # 创建报警管理器
    # 测试QQ邮箱发送(内网)
    alarm_manager_qq = FireAlarmManager(use_qq_mail=True)
    
    # 创建测试图像
    test_img = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.rectangle(test_img, (100, 100), (300, 200), (0, 0, 255), -1)  # 红色矩形表示火灾
    cv2.putText(test_img, "FIRE TEST", (120, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # 发送测试报警
    alarm_manager_qq.send_alarm_email(test_img, 0.85, 30.5, "测试位置")
    
    # 测试等待5秒
    print("等待5秒后测试Gmail发送...")
    time.sleep(5)
    
    # 测试Gmail发送(外网)
    alarm_manager_gmail = FireAlarmManager(use_qq_mail=False)
    alarm_manager_gmail.send_alarm_email(test_img, 0.92, 45.8, "测试位置2")
    
    print("测试完成!")
