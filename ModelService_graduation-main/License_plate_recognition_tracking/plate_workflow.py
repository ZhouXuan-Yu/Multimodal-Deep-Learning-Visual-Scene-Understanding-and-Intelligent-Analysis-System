import os
import uuid
import time
import cv2
import datetime
import numpy as np
import threading
import socket
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, Response
from werkzeug.utils import secure_filename
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 导入检测和识别模块
from scripts.Car_recognition import detect_Recognition_plate, draw_result

# 创建视频合成函数
def create_video_from_matches(matches, output_path, fps=5):
    """从匹配的帧创建视频
    Args:
        matches: 包含frame_path键的字典列表
        output_path: 输出视频路径
        fps: 帧率
    Returns:
        str/bool: 成功返回视频路径，失败返回False
    """
    try:
        if not matches or len(matches) == 0:
            print("没有匹配的帧可以创建视频")
            return False
            
        # 读取第一帧来获取尺寸信息
        first_frame_path = matches[0].get('frame_path')
        if not first_frame_path or not os.path.exists(first_frame_path):
            print(f"第一帧不存在: {first_frame_path}")
            return False
            
        first_frame = cv2.imread(first_frame_path)
        if first_frame is None:
            print(f"无法读取第一帧: {first_frame_path}")
            return False
            
        height, width, _ = first_frame.shape
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 尝试多种编码器，确保视频可以创建成功且浏览器兼容
        codec_options = [
            ('mp4v', '.mp4'),  # 优先使用MP4格式，浏览器兼容性最好
            ('avc1', '.mp4'),  # H.264编码，网页播放兼容性好
            ('H264', '.mp4'),  # 标准H.264
            ('X264', '.mp4'),  # 另一种H.264实现
            ('MJPG', '.avi'),  # Motion JPEG
            ('XVID', '.avi'),  # AVI格式
            ('DIVX', '.avi')   # DIVX编码
        ]
        
        # 确保扩展名匹配
        base_path, ext = os.path.splitext(output_path)
        
        # 按帧号排序匹配结果
        sorted_matches = sorted(matches, key=lambda x: x.get('frame_number', 0))
        
        # 尝试每一种编码器
        for codec, extension in codec_options:
            try:
                # 生成输出视频路径
                video_path = f"{base_path}{extension}"
                
                print(f"尝试使用编码器: {codec} 创建视频: {video_path}")
                # 创建视频写入器
                fourcc = cv2.VideoWriter_fourcc(*codec)
                video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
                
                if not video_writer.isOpened():
                    print(f"无法打开视频写入器: {video_path}")
                    continue
                
                # 写入每一帧
                frame_count = 0
                for match in sorted_matches:
                    frame_path = match.get('frame_path')
                    if not frame_path or not os.path.exists(frame_path):
                        print(f"帧不存在: {frame_path}")
                        continue
                    
                    frame = cv2.imread(frame_path)
                    if frame is None:
                        print(f"无法读取帧: {frame_path}")
                        continue
                    
                    # 在帧上绘制识别结果
                    if 'plate_number' in match:
                        cv2.putText(frame, match['plate_number'], (10, 30), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    if 'frame_number' in match:
                        cv2.putText(frame, f"Frame: {match['frame_number']}", (10, 60), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # 写入帧
                    video_writer.write(frame)
                    frame_count += 1
                    
                    # 增加额外的复制帧使视频时间更长
                    for _ in range(3):  # 每个帧复制几次，使视频播放速度显得更慢
                        video_writer.write(frame)
                
                # 释放视频写入器
                video_writer.release()
                
                # 验证视频已经生成
                if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                    print(f"视频生成成功: {video_path} (大小: {os.path.getsize(video_path)/1024:.2f} KB)")
                    return video_path
                else:
                    print(f"视频文件不存在或大小为零: {video_path}")
            except Exception as e:
                print(f"使用编码器 {codec} 创建视频时出错: {e}")
                continue
        
        # 如果所有编码器都无法成功创建视频，则返回False
        print("所有视频编码器尝试失败，无法创建视频")
        return False
            
    except Exception as e:
        print(f"创建视频时发生错误: {e}")
        return False

# 创建发送邮件函数
def send_alert_email(plate_no, detection_type, timestamp, image_path=None, video_name=None):
    """发送报警邮件
    
    参数:
        plate_no: 检测到的车牌号
        detection_type: 检测类型（camera/video/image）
        timestamp: 检测时间
        image_path: 图片路径（可选）
        video_name: 视频文件名（可选）
    
    返回:
        bool: 发送成功或失败
    """
    # 生成告警消息并显示在控制台，不管邮件是否能发送成功
    detection_mode = {
        "camera": "实时摄像头", 
        "video": "视频分析", 
        "image": "图片上传"
    }.get(detection_type, "未知方式")
    
    alert_message = f"\n{'='*50}\n\n\t[车牌识别系统报警]\n\t"
    alert_message += f"\n\t目标车牌: {plate_no}"
    alert_message += f"\n\t检测时间: {timestamp}"
    alert_message += f"\n\t检测方式: {detection_mode}"
    
    if video_name:
        alert_message += f"\n\t视频文件: {video_name}"
    
    alert_message += f"\n\n{'='*50}"
    print(alert_message)
    
    # 尝试发送邮件，但不阻止主要功能
    try:
        # 邮件配置 - QQ邮箱设置
        email_config = {
            'enabled': True,
            'smtp_server': "smtp.qq.com",
            'port': 465,
            'sender': "1241515924@qq.com", 
            'password': "lszowfvdnwwxjged",  # QQ邮箱授权码
            'receiver': "2769220120@qq.com",
            'use_ssl': True  # 使用SSL连接
        }
        
        # 如果邮件功能未启用，直接返回
        if not email_config.get('enabled', False):
            print("\n[INFO] 邮件功能未启用，跳过发送邮件步骤")
            return False
        
        # 创建邮件消息
        message = MIMEMultipart()
        message["From"] = email_config['sender']
        message["To"] = email_config['receiver']
        message["Subject"] = f"车牌报警 - 检测到车牌: {plate_no}"
        
        # 邮件HTML正文
        video_info = f"<p><strong>视频文件:</strong> {video_name}</p>" if video_name else ""
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #d9534f; border-bottom: 1px solid #eee; padding-bottom: 10px;">车牌识别系统报警通知</h2>
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p><strong style="color: #d9534f;">检测到目标车牌:</strong> {plate_no}</p>
                    <p><strong>检测时间:</strong> {timestamp}</p>
                    <p><strong>检测方式:</strong> {detection_mode}</p>
                    {video_info}
                </div>
                <p style="color: #777; font-size: 12px;">此邮件由系统自动发送，请勿直接回复</p>
            </div>
        </body>
        </html>
        """
        
        message.attach(MIMEText(body, "html"))
        
        # 创建SMTP连接 - 使用SSL和QQ邮箱
        if email_config.get('use_ssl', False):
            server = smtplib.SMTP_SSL(email_config['smtp_server'], email_config['port'], timeout=15)
            print("\n[INFO] 已连接到QQ邮箱SMTP服务器(SSL)")
        else:
            server = smtplib.SMTP(email_config['smtp_server'], email_config['port'], timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
            print("\n[INFO] 已连接到SMTP服务器(TLS)")
        
        # 登录
        server.login(email_config['sender'], email_config['password'])
        print("\n[INFO] 登录成功")
        
        # 发送邮件
        server.send_message(message)
        
        # 关闭连接
        server.quit()
        
        # 提示成功
        print(f"\n[SUCCESS] 报警邮件已发送至: {email_config['receiver']}")
        return True
        
    except socket.timeout:
        print("\n[ERROR] 邮件发送失败: 连接超时，请检查网络或SMTP服务器设置")
        return False
    except Exception as e:
        print(f"\n[ERROR] 邮件发送失败: {str(e)}")
        return False

plate_workflow = Blueprint('plate_workflow', __name__)

@plate_workflow.route('/workflow')
def workflow_page():
    return render_template('plate_recognition_workflow.html')

# 车牌目标存储
target_plate_info = {
    'plate_no': None,
    'source': None,
    'timestamp': None
}

# 确保必要的目录存在
UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/output'
DEBUG_FOLDER = 'static/debug'
VIDEO_FOLDER = 'static/video'

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, DEBUG_FOLDER, VIDEO_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# 添加一个新路由用于上传图片并识别所有车牌，不需要事先设置目标车牌
@plate_workflow.route('/upload_and_recognize', methods=['POST'])
def upload_and_recognize():
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': '没有上传图片'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择图片'}), 400
        
    # 保存上传的图片
    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # 路径转换为操作系统相对路径
    filepath = filepath.replace('/', os.sep)
    
    try:
        # 读取图片
        image = cv2.imread(filepath)
        if image is None:
            return jsonify({'status': 'error', 'message': '无法读取图片，可能格式不支持'}), 400
            
        # 加载模型和执行识别
        from appPro import device, detect_model, rec_model, car_rec_model
        results = detect_Recognition_plate(detect_model, image, device, rec_model, 1024, car_rec_model)
        
        # 保存原始图片和标记了车牌的图片
        marked_image = draw_result(image.copy(), results, highlight_plate=None)
        marked_filename = f"marked_{os.path.basename(filepath)}"
        marked_path = os.path.join(OUTPUT_FOLDER, marked_filename)
        cv2.imwrite(marked_path, marked_image)
        
        # 提取所有识别到的车牌
        plate_results = []
        for index, result in enumerate(results):
            if 'plate_no' in result:
                # 为每个车牌创建缩略图
                plate_crop = None
                if 'plate_bbox' in result:
                    x1, y1, x2, y2 = result['plate_bbox']
                    plate_crop = image[int(y1):int(y2), int(x1):int(x2)]
                    
                    if plate_crop is not None and plate_crop.size > 0:
                        crop_filename = f"plate_{index}_{os.path.basename(filepath)}"
                        crop_path = os.path.join(OUTPUT_FOLDER, crop_filename)
                        cv2.imwrite(crop_path, plate_crop)
                        crop_url = f"/static/output/{crop_filename}"
                    else:
                        crop_url = None
                else:
                    crop_url = None
                
                plate_results.append({
                    'plate_no': result['plate_no'],
                    'confidence': float(result.get('score', 0)),
                    'plate_image': crop_url,
                    'index': index
                })
        
        # 返回结果
        return jsonify({
            'status': 'success',
            'plate_count': len(plate_results),
            'plates': plate_results,
            'original_image': f"/static/uploads/{filename}",
            'marked_image': f"/static/output/{marked_filename}",
            'message': f"成功识别 {len(plate_results)} 个车牌"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'处理图片时出错: {str(e)}'}), 500

# 设置目标车牌
@plate_workflow.route('/set_target_plate', methods=['POST'])
def set_target_plate():
    data = request.json
    target_plate_info['plate_no'] = data.get('plate_no')
    target_plate_info['source'] = data.get('source', 'manual')
    target_plate_info['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'status': 'success',
        'message': f"目标车牌已设置为: {target_plate_info['plate_no']}",
        'target_plate': target_plate_info
    })

# 图片匹配处理
@plate_workflow.route('/match_image', methods=['POST'])
def match_image():
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': '没有上传图片'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择图片'}), 400
        
    if target_plate_info['plate_no'] is None:
        return jsonify({'status': 'error', 'message': '请先设置目标车牌'}), 400
        
    # 保存上传的图片
    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # 路径转换为操作系统相对路径
    filepath = filepath.replace('/', os.sep)
    
    try:
        # 读取图片
        image = cv2.imread(filepath)
        if image is None:
            return jsonify({'status': 'error', 'message': '无法读取图片，可能格式不支持'}), 400
            
        # 加载模型和执行识别
        from appPro import device, detect_model, rec_model, car_rec_model
        results = detect_Recognition_plate(detect_model, image, device, rec_model, 1024, car_rec_model)
        
        # 检查结果是否匹配目标车牌
        matches = []
        for result in results:
            if 'plate_no' in result and result['plate_no'] == target_plate_info['plate_no']:
                matches.append(result)
                
        # 创建结果图像
        result_image = image.copy()
        for match in matches:
            # 高亮显示目标车牌
            result_image = draw_result(result_image, [match], highlight_plate=target_plate_info['plate_no'])
        
        # 保存结果图像
        result_filename = f"match_{os.path.basename(filepath)}"
        result_path = os.path.join(OUTPUT_FOLDER, result_filename)
        cv2.imwrite(result_path, result_image)
        
        # 如果找到匹配，发送邮件警报
        if matches:
            send_alert_email(
                target_plate_info['plate_no'],
                'image',
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                image_path=result_path
            )
        
        # 返回结果    
        return jsonify({
            'status': 'success',
            'matches': len(matches),
            'match_details': matches,
            'result_image': f"/static/output/{result_filename}",
            'message': f"找到 {len(matches)} 个匹配" if matches else "未找到匹配的车牌"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'处理图片时出错: {str(e)}'}), 500

# 视频处理状态存储
video_processing_status = {}

# 视频上传和处理
@plate_workflow.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'status': 'error', 'message': '没有上传视频'}), 400
        
    file = request.files['video']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择视频'}), 400
        
    if target_plate_info['plate_no'] is None:
        return jsonify({'status': 'error', 'message': '请先设置目标车牌'}), 400
        
    # 生成唯一ID用于跟踪处理状态
    video_id = str(uuid.uuid4())
    
    # 保存上传的视频
    filename = secure_filename(f"{video_id}_{file.filename}")
    filepath = os.path.join(VIDEO_FOLDER, filename)
    file.save(filepath)
    
    # 初始化处理状态
    video_processing_status[video_id] = {
        'status': 'processing',
        'progress': 0,
        'total_frames': 0,
        'processed_frames': 0,
        'matches': [],
        'total_matches': 0,
        'message': '视频处理中...',
        'video_path': filepath,
        'completed': False,
        'video_url': None
    }
    
    # 启动处理线程
    thread = threading.Thread(target=process_video, args=(video_id, filepath, target_plate_info['plate_no']))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'success',
        'message': '视频上传成功，正在处理...',
        'video_id': video_id
    })

def process_video(video_id, video_path, target_plate_no):
    try:
        # 获取视频信息
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            video_processing_status[video_id]['status'] = 'error'
            video_processing_status[video_id]['message'] = '无法打开视频文件'
            video_processing_status[video_id]['completed'] = True
            return
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        video_processing_status[video_id]['total_frames'] = total_frames
        
        # 加载模型
        from appPro import device, detect_model, rec_model, car_rec_model
        
        # 处理视频帧
        matches = []
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # 每5帧处理一次
            if frame_count % 5 == 0:
                results = detect_Recognition_plate(detect_model, frame, device, rec_model, 1024, car_rec_model)
                
                # 检查结果是否匹配目标车牌
                for result in results:
                    if 'plate_no' in result and result['plate_no'] == target_plate_no:
                        # 找到匹配，保存帧
                        match_frame_path = os.path.join(OUTPUT_FOLDER, f"match_{video_id}_{frame_count}.jpg")
                        
                        # 高亮显示目标车牌
                        result_frame = draw_result(frame.copy(), [result], highlight_plate=target_plate_no)
                        cv2.imwrite(match_frame_path, result_frame)
                        
                        # 添加到匹配列表
                        matches.append({
                            'frame_number': frame_count,
                            'frame_path': match_frame_path,
                            'timestamp': str(datetime.timedelta(seconds=frame_count/fps)),
                            'plate_no': result['plate_no'],
                            'confidence': float(result.get('score', 0)),
                            'frame_url': f"/static/output/match_{video_id}_{frame_count}.jpg"
                        })
                
                # 更新进度
                video_processing_status[video_id]['processed_frames'] = frame_count
                video_processing_status[video_id]['progress'] = min(99, int((frame_count / total_frames) * 100))
                # 添加判断确保匹配数组被正确更新
                video_processing_status[video_id]['matches'] = matches.copy()  # 使用副本避免引用问题
                video_processing_status[video_id]['total_matches'] = len(matches)
                print(f"视频处理中: 已找到{len(matches)}个匹配框")
                
            frame_count += 1
            
        cap.release()
        
        # 如果有匹配结果，创建匹配视频
        if matches:
            try:
                # 使用通用路径，让create_video_from_matches函数自动选择最佳格式
                base_video_path = os.path.join(OUTPUT_FOLDER, f"matches_{video_id}")
                video_url = create_video_from_matches(matches, base_video_path)
                
                if video_url:
                    # 从实际生成的视频路径提取URL
                    _, ext = os.path.splitext(video_url)
                    video_processing_status[video_id]['video_url'] = f"/static/output/matches_{video_id}{ext}"
                    
                    # 发送邮件警报
                    send_alert_email(
                        target_plate_no,
                        'video',
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        video_name=os.path.basename(video_path)
                    )
            except Exception as e:
                print(f"视频生成失败，但不影响其他功能: {e}")
                
        # 完成处理
        video_processing_status[video_id]['progress'] = 100
        video_processing_status[video_id]['status'] = 'completed'
        video_processing_status[video_id]['message'] = f"处理完成，找到 {len(matches)} 个匹配"
        video_processing_status[video_id]['completed'] = True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        video_processing_status[video_id]['status'] = 'error'
        video_processing_status[video_id]['message'] = f"处理视频时出错: {str(e)}"
        video_processing_status[video_id]['completed'] = True

# 获取视频处理状态
@plate_workflow.route('/video_processing_status', methods=['GET'])
def get_video_processing_status():
    video_id = request.args.get('video_id')
    if not video_id or video_id not in video_processing_status:
        return jsonify({'status': 'error', 'message': '视频ID不存在'}), 404
    
    # 打印发送给前端的状态数据，用于调试
    print(f"发送视频处理状态: {video_processing_status[video_id]}")
    
    # 确保matches数据为可序列化的列表 
    if 'matches' in video_processing_status[video_id]:
        # 检查并修复每个匹配项的数据
        for match in video_processing_status[video_id]['matches']:
            # 确保所有数值都是可序列化的
            if 'confidence' in match and not isinstance(match['confidence'], (int, float)):
                match['confidence'] = float(match['confidence'])
            # 确保所有路径都是有效的相对URL
            if 'frame_url' in match and not match['frame_url'].startswith('/'):
                match['frame_url'] = f"/static/output/{os.path.basename(match['frame_url'])}"
    
    # 检查视频URL是否有效
    if video_processing_status[video_id].get('video_url'):
        video_url = video_processing_status[video_id]['video_url']
        # 确保URL格式正确
        if not video_url.startswith('/'):
            video_processing_status[video_id]['video_url'] = f"/static/output/{os.path.basename(video_url)}"
        # 检查文件是否存在
        file_path = os.path.join(os.getcwd(), 'static', 'output', os.path.basename(video_url))
        if not os.path.exists(file_path):
            print(f"警告: 视频文件不存在于路径 {file_path}")
    
    return jsonify(video_processing_status[video_id])

# 生成摘要报告
@plate_workflow.route('/generate_report', methods=['GET'])
def generate_report():
    video_id = request.args.get('video_id')
    if not video_id or video_id not in video_processing_status:
        return jsonify({'status': 'error', 'message': '视频ID不存在'}), 404
        
    status_data = video_processing_status[video_id]
    if not status_data['completed']:
        return jsonify({'status': 'error', 'message': '视频处理尚未完成'}), 400
        
    if status_data['total_matches'] == 0:
        return jsonify({'status': 'error', 'message': '没有找到匹配的车牌'}), 404
        
    try:
        # 生成HTML报告内容
        matches = status_data['matches']
        report_id = uuid.uuid4()
        report_filename = f"report_{report_id}.html"
        report_path = os.path.join(OUTPUT_FOLDER, report_filename)
        
        # 创建报告HTML
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>车牌识别报告 - {target_plate_info['plate_no']}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
                    .header {{ background-color: #f5f5f5; padding: 20px; margin-bottom: 20px; border-radius: 5px; }}
                    .match-item {{ border: 1px solid #ddd; margin-bottom: 20px; padding: 15px; border-radius: 5px; }}
                    .match-item img {{ max-width: 100%; height: auto; display: block; margin: 10px 0; }}
                    h1, h2, h3 {{ color: #333; }}
                    .info {{ margin-bottom: 10px; }}
                    .timestamp {{ color: #666; font-style: italic; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>车牌识别报告</h1>
                    <div class="info">目标车牌: <strong>{target_plate_info['plate_no']}</strong></div>
                    <div class="info">报告生成时间: <strong>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong></div>
                    <div class="info">匹配总数: <strong>{status_data['total_matches']}</strong></div>
                </div>
                
                <h2>匹配详情</h2>
            """)
            
            for i, match in enumerate(matches):
                f.write(f"""
                <div class="match-item">
                    <h3>匹配 #{i+1}</h3>
                    <div class="info">帧号: <strong>{match['frame_number']}</strong></div>
                    <div class="info">时间点: <strong>{match['timestamp']}</strong></div>
                    <div class="info">置信度: <strong>{match['confidence']:.2f}</strong></div>
                    <img src="{match['frame_url']}" alt="匹配帧">
                </div>
                """)
                
            f.write("""
            </body>
            </html>
            """)
            
        return jsonify({
            'status': 'success',
            'message': '报告生成成功',
            'report_url': f"/static/output/{report_filename}"
        })
                
    except Exception as e:
        print(f"生成报告失败: {e}")
        return jsonify({'status': 'error', 'message': f'生成报告失败: {str(e)}'}), 500

# 摄像头匹配结果，用于前端轮询
camera_match_results = {
    'matches': [],
    'last_updated': None
}

# 获取摄像头匹配结果
@plate_workflow.route('/camera_match_results', methods=['GET'])
def get_camera_match_results():
    return jsonify(camera_match_results)

# 添加摄像头匹配结果（由视频流处理调用）
def add_camera_match_result(result, frame):
    try:
        # 保存当前帧
        filename = f"camera_match_{uuid.uuid4()}.jpg"
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        
        # 高亮显示目标车牌
        result_frame = draw_result(frame.copy(), [result], highlight_plate=target_plate_info['plate_no'])
        cv2.imwrite(filepath, result_frame)
        
        # 添加到匹配列表，最多保留10个
        match_info = {
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'plate_no': result['plate_no'],
            'confidence': float(result.get('score', 0)),
            'frame_url': f"/static/output/{filename}"
        }
        
        camera_match_results['matches'].insert(0, match_info)
        if len(camera_match_results['matches']) > 10:
            camera_match_results['matches'] = camera_match_results['matches'][:10]
            
        camera_match_results['last_updated'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 发送邮件警报
        send_alert_email(
            result['plate_no'],
            'camera',
            match_info['timestamp'],
            image_path=filepath
        )
        
        return match_info
    except Exception as e:
        print(f"添加摄像头匹配结果失败: {e}")
        return None

# 实时视频流
@plate_workflow.route('/live_video_feed')
def live_video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 生成视频帧
def gen_frames():
    # 打开摄像头
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("无法打开摄像头")
        camera_unavailable = '摄像头不可用'.encode('utf-8')
        yield (b'--frame\r\n'
               b'Content-Type: text/plain\r\n\r\n' + 
               camera_unavailable + b'\r\n\r\n')
        return
        
    try:
        # 加载模型
        from appPro import device, detect_model, rec_model, car_rec_model
        
        while True:
            # 读取帧
            ret, frame = cap.read()
            if not ret:
                break
                
            # 执行车牌识别
            if target_plate_info['plate_no'] is not None:
                results = detect_Recognition_plate(detect_model, frame, device, rec_model, 1024, car_rec_model)
                
                # 绘制所有识别结果
                frame = draw_result(frame, results)
                
                # 检查是否有目标车牌匹配
                for result in results:
                    if 'plate_no' in result and result['plate_no'] == target_plate_info['plate_no']:
                        # 找到匹配，高亮显示
                        frame = draw_result(frame, [result], highlight_plate=target_plate_info['plate_no'])
                        
                        # 添加到匹配结果并发送警报
                        add_camera_match_result(result, frame)
                
            # 编码为jpg
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            # 以multipart格式传输
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
    except Exception as e:
        print(f"摄像头处理出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cap.release()