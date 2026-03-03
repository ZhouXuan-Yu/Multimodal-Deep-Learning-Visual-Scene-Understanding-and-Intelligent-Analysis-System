"""
报警模块，用于发送邮件警报
"""

import os
import time
import smtplib
import traceback
import ssl
# threading不再需要，因为我们现在直接在主线程调用邮件发送
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header
from datetime import datetime

# 邮件发送配置 - Gmail
GMAIL_CONFIG = {
    "sender_email": "zhouxuan4516@gmail.com",
    "app_password": "qmtg enxt jlli fhng",  # bb.py中的Gmail授权码
    "receiver_email": "2769220120@qq.com",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "use_tls": True
}

# 原始QQ邮箱配置（授权码可能已过期）
QQ_CONFIG_ORIGINAL = {
    "sender_email": "1241515924@qq.com",
    "app_password": "lszowfvdnwwxjged",  # 旧授权码，已过期
    "receiver_email": "2769220120@qq.com",
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "use_ssl": True
}

# ======================================================================
# QQ邮箱配置 - 使用cc.py中的授权码
# ======================================================================
QQ_CONFIG = {
    "sender_email": "1241515924@qq.com",
    "app_password": "lszowfvdnwwxjged",  # 从cc.py获取的授权码
    "receiver_email": "2769220120@qq.com",  # 修改为当前设置的接收邮箱
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "use_ssl": True
}

# 备用QQ授权码（如果您有备用的授权码，可以在这里填写）
QQ_CONFIG_BACKUP = {
    "sender_email": "1241515924@qq.com",
    "app_password": "备用授权码填写处",
    "receiver_email": "2769220120@qq.com",
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "use_ssl": True
}

# 默认配置，优先使用内网QQ邮箱
DEFAULT_CONFIG = QQ_CONFIG

# 警报冷却时间（秒）
RED_ALERT_COOLDOWN = 1  # 红色警报的冷却时间，降低到1秒基本等于禁用
YELLOW_ALERT_COOLDOWN = 5  # 黄色警报的冷却时间，也降低

# 警报时间记录
last_red_alert_time = 0
last_yellow_alert_time = 0


class EmailSender:
    """邮件发送类，支持Gmail和QQ邮箱"""
    
    def __init__(self, config=None):
        self.config = config if config else DEFAULT_CONFIG
        print(f"\n===== 初始化邮件发送器 =====")
        print(f"SMTP服务器: {self.config['smtp_server']}")
        print(f"发件人邮箱: {self.config['sender_email']}")
        print(f"收件人邮箱: {self.config['receiver_email']}")
        
        # 安全地显示授权码信息的第一个字符和长度
        auth_code = self.config['app_password']
        auth_code_masked = auth_code[:1] + '*' * (len(auth_code) - 1) if auth_code else "未设置"
        print(f"授权码: {auth_code_masked} (长度: {len(auth_code)})")    
        
        # 警告到解占位符授权码
        if "请在此处填入" in auth_code or "备用授权码" in auth_code:
            print("\n\u2757 警告: 检测到授权码可能是占位符，请更新alarm.py中的授权码为真实的QQ邮箱授权码\u2757")
            print("\n请参照以下步骤获取新的授权码:")
            print("1. 登录网页版QQ邮箱 (https://mail.qq.com)")
            print("2. 点击「设置」>「账户」")
            print("3. 找到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务」并开启")
            print("4. 点击「生成授权码」按钮获取新的授权码")
        
    @staticmethod
    def send_email(subject, body, config=DEFAULT_CONFIG, attachment_path=None):
        """
        发送邮件，先尝试使用指定配置，失败后自动尝试备用配置
        
        Args:
            subject: 邮件主题
            body: 邮件正文
            config: 邮件配置
            attachment_path: 附件路径（如截图）
            
        Returns:
            bool: 是否发送成功
        """
        print(f"\n===== 开始发送邮件 =====")
        print(f"主题: {subject}")
        print(f"正文长度: {len(body)} 字符")
        print(f"附件: {attachment_path if attachment_path else '无'}")
        
        # 创建多部分邮件
        msg = MIMEMultipart()
        msg['From'] = config['sender_email']
        msg['To'] = config['receiver_email']
        # 处理主题中的中文字符
        msg['Subject'] = Header(subject, 'utf-8').encode()
        
        # 添加邮件正文，确保中文显示正确
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 添加附件
        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, 'rb') as f:
                    img_data = f.read()
                image = MIMEImage(img_data, name=os.path.basename(attachment_path))
                msg.attach(image)
                print(f"成功添加附件: {attachment_path}")
            except Exception as e:
                print(f"附件添加失败 {attachment_path}: {str(e)}")
        
        # 连接服务器并发送邮件
        try:
            print(f"\n正在连接到 {config['smtp_server']}:{config['smtp_port']}...")
            
            # 检查授权码是否是占位符
            auth_code = config['app_password']
            if "请在此处填入" in auth_code or "备用授权码" in auth_code:
                print("\n❗ 错误: 检测到授权码是占位符，无法发送邮件❗")
                print("请先在alarm.py文件中更新QQ_CONFIG中的app_password为真实的授权码再尝试发送邮件")
                return False
                
            # 根据配置选择SSL或普通连接
            if config.get('use_ssl', False):
                try:
                    server = smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port'])
                    print("成功使用SSL连接到SMTP服务器")
                except Exception as ssl_error:
                    print(f"SSL连接错误: {str(ssl_error)}")
                    print(traceback.format_exc())
                    raise
            else:
                server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
                if config.get('use_tls', False):
                    server.starttls()
                    print("成功使用TLS连接到SMTP服务器")
            
            print(f"正在使用 {config['sender_email']} 登录...")
            server.login(config['sender_email'], config['app_password'])
            print("登录成功！")
            
            print("正在发送邮件...")
            server.send_message(msg)
            server.quit()
            print("邮件发送成功！")
            return True
        
        except Exception as e:
            print(f"邮件发送失败: {str(e)}")
            
            # 如果QQ邮箱失败，尝试使用Gmail
            if config == QQ_CONFIG:
                print("原配置发送失败，尝试使用Gmail发送...")
                try:
                    # 尝试使用Gmail作为备份
                    return EmailSender.send_email(subject, body, GMAIL_CONFIG, attachment_path)
                except Exception as gmail_error:
                    print(f"Gmail发送也失败: {str(gmail_error)}")
                    # 尝试回退到旧的QQ配置
                    try:
                        print("尝试使用旧的QQ邮箱配置...")
                        return EmailSender.send_email(subject, body, QQ_CONFIG_ORIGINAL, attachment_path)
                    except Exception as qq_old_error:
                        print(f"所有邮件发送方式均失败，最后错误: {str(qq_old_error)}")
                        return False
            else:
                print(f"邮件发送失败: {str(e)}")
                return False


def send_red_alert(action_name, confidence, image_path=None):
    """
    发送红色警报邮件
    
    Args:
        action_name: 检测到的行为名称
        confidence: 置信度
        image_path: 截图路径
    """
    global last_red_alert_time
    
    # 检查冷却时间
    current_time = time.time()
    if current_time - last_red_alert_time < RED_ALERT_COOLDOWN:
        print(f"红色警报冷却中，但仍然尝试发送 (经过{current_time - last_red_alert_time:.2f}秒)")
    
    # 更新最后发送时间
    last_red_alert_time = current_time
    
    # 创建邮件内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"危险行为警报: {action_name.upper()} 已检测到!"
    body = f"""
危险行为警报!

检测到的行为: {action_name}
置信度: {confidence:.2f}
时间: {timestamp}

此邮件由红外监控视频行为识别系统自动发送，请立即查看并处理!
"""
    
    # 直接发送邮件，使用简化的方式
    print("开始直接发送红色警报邮件...") 
    
    try:
        # 使用简化的邮件发送方式
        sender = "1241515924@qq.com"
        receiver = "2769220120@qq.com"
        password = "lszowfvdnwwxjged"
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = Header(subject, 'utf-8').encode()
        
        # 添加邮件正文
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 添加图片附件（如果有）
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                image = MIMEImage(img_data, name=os.path.basename(image_path))
                msg.attach(image)
                print(f"成功添加附件: {image_path}")
            except Exception as img_error:
                print(f"附件添加失败: {str(img_error)}")
        
        # 连接服务器并发送邮件
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        print("邮件发送成功!")
        return True
        
    except Exception as e:
        print(f"红色警报邮件发送失败: {str(e)}")
        return False


def send_yellow_alert(action_name, confidence, image_path=None):
    """
    发送黄色警报邮件
    
    Args:
        action_name: 检测到的行为名称
        confidence: 置信度
        image_path: 截图路径
    """
    global last_yellow_alert_time
    
    # 检查冷却时间
    current_time = time.time()
    if current_time - last_yellow_alert_time < YELLOW_ALERT_COOLDOWN:
        print(f"黄色警报冷却中，但仍然尝试发送 (经过{current_time - last_yellow_alert_time:.2f}秒)")
    
    # 更新最后发送时间
    last_yellow_alert_time = current_time
    
    # 创建邮件内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"警告通知: {action_name.capitalize()} 行为已检测到"
    body = f"""
警告通知

检测到的行为: {action_name}
置信度: {confidence:.2f}
时间: {timestamp}

此邮件由红外监控视频行为识别系统自动发送，请注意关注该区域，考虑是否需要加强管理。
"""
    
    # 直接发送邮件，采用与红色警报相同的简化方式
    print("开始直接发送黄色警报邮件...") 
    
    try:
        # 使用简化的邮件发送方式
        sender = "1241515924@qq.com"
        receiver = "2769220120@qq.com"
        password = "lszowfvdnwwxjged"
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = Header(subject, 'utf-8').encode()
        
        # 添加邮件正文
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 添加图片附件（如果有）
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                image = MIMEImage(img_data, name=os.path.basename(image_path))
                msg.attach(image)
                print(f"成功添加附件: {image_path}")
            except Exception as img_error:
                print(f"附件添加失败: {str(img_error)}")
        
        # 连接服务器并发送邮件
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        print("邮件发送成功!")
        return True
        
    except Exception as e:
        print(f"黄色警报邮件发送失败: {str(e)}")
        return False


# 测试函数
if __name__ == "__main__":
    # 测试邮件发送系统
    print("=== 开始测试邮件发送系统... ===")
    print("测试Gmail配置")
    EmailSender.send_email("测试Gmail", "这是一个测试邮件", GMAIL_CONFIG)
    
    print("测试QQ邮箱配置")
    EmailSender.send_email("测试QQ邮箱", "这是一个测试邮件", QQ_CONFIG)
    
    # 测试红色警报
    print("测试红色警报")
    send_red_alert("战斗", 0.95)
    
    # 等待一会儿
    time.sleep(2)
    
    # 测试黄色警报
    print("测试黄色警报")
    send_yellow_alert("握手", 0.85)
    
    print("=== 邮件系统测试完成 ===")
