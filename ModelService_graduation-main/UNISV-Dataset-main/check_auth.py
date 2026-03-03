#!/usr/bin/env python
# -*- coding: utf-8 -*-

from alarm import QQ_CONFIG, DEFAULT_CONFIG

def check_auth_code():
    """检查并输出邮箱授权码信息"""
    print("\n===== 邮箱授权码检查 =====")
    
    # 检查QQ邮箱授权码
    auth_code = QQ_CONFIG.get('app_password', '')
    print(f"QQ邮箱授权码: '{auth_code}'")
    print(f"授权码长度: {len(auth_code)}")
    
    # 判断是否是占位符
    if "请在此处填入" in auth_code:
        print("\n⚠️ 警告: QQ邮箱授权码是占位符，邮件无法发送!")
        print("请在alarm.py文件中更新QQ_CONFIG['app_password']为真实的授权码")
        print("\n获取授权码步骤:")
        print("1. 登录网页版QQ邮箱 (https://mail.qq.com)")
        print("2. 点击「设置」>「账户」")
        print("3. 找到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务」并开启")
        print("4. 点击「生成授权码」按钮获取新的授权码")
        print("5. 将获取的授权码复制到alarm.py文件中的QQ_CONFIG字典的'app_password'值中")
    else:
        print("授权码格式正确，但仍需确认其有效性")
        
    # 检查当前默认配置
    print(f"\n当前使用的默认配置: {'QQ邮箱' if DEFAULT_CONFIG == QQ_CONFIG else 'Gmail'}")
    
if __name__ == "__main__":
    check_auth_code()
