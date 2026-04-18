# 使用外网发送邮件--测试代码


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
 
# 设置发件人邮箱地址和密码
sender_email = "zhouxuan4516@gmail.com"
# 我的个人隐私密码，不要随便泄露
app_password = "qmtg enxt jlli fhng"
 
# 设置收件人邮箱地址
receiver_email = "2769220120@qq.com"
 
# 创建邮件内容
message = MIMEMultipart()
message["From"] = sender_email
message["To"] = receiver_email
message["Subject"] = "Python SMTP Test1"
 
 
# 邮件正文内容
body = "This is a test email sent from Python using SMTP."
message.attach(MIMEText(body, "plain"))
 
# 连接到Gmail的SMTP服务器
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(sender_email, app_password)
 
# 发送邮件
server.sendmail(sender_email, receiver_email, message.as_string())
 
# 关闭连接
server.quit()
 
print("Email sent successfully!")