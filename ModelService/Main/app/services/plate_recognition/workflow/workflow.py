"""
车牌识别工作流处理模块
负责处理车牌识别的完整业务流程，包括图片识别、视频处理、匹配分析等
"""
import os
import uuid
import time
import cv2
import datetime
import numpy as np
import json
import asyncio
import logging
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 导入检测和识别模块
from ..detector.detector import detect_Recognition_plate, draw_result

logger = logging.getLogger(__name__)

class PlateWorkflow:
    """车牌识别工作流类，处理车牌识别相关的业务流程"""
    
    def __init__(self, base_dir):
        """
        初始化车牌识别工作流
        
        参数:
            base_dir: 项目根目录路径
        """
        self.base_dir = base_dir
        
        # 设置目录路径
        self.upload_folder = os.path.join(base_dir, 'uploads')
        self.image_upload_folder = os.path.join(self.upload_folder, 'images')
        self.video_upload_folder = os.path.join(self.upload_folder, 'videos')
        self.output_folder = os.path.join(base_dir, 'static', 'plate_recognition')
        self.image_output_folder = os.path.join(self.output_folder, 'images', 'processed')
        self.video_output_folder = os.path.join(self.output_folder, 'videos', 'processed')
        
        # 确保目录存在
        os.makedirs(self.image_upload_folder, exist_ok=True)
        os.makedirs(self.video_upload_folder, exist_ok=True)
        os.makedirs(self.image_output_folder, exist_ok=True)
        os.makedirs(self.video_output_folder, exist_ok=True)
        
        # 视频处理状态存储
        self.video_processing_status = {}
        
        # 车牌目标存储
        self.target_plate_info = {
            'plate_no': None,
            'source': None,
            'image_path': None,
            'confidence': 0.0,
            'color': None,
            'set_time': None
        }
        
        # 摄像头匹配结果，用于前端轮询
        self.camera_match_results = {
            'matches': [],
            'last_updated': None,
            'target_plate': None
        }
        
        # 邮件配置
        self.email_config = {
            'enabled': False,
            'sender_email': '',
            'app_password': '',
            'receiver_email': '',
            'subject_template': '车牌识别报警: {plate_no}',
            'body_template': '检测到目标车牌 {plate_no}，时间: {timestamp}，类型: {detection_type}'
        }
        
        logger.info("车牌识别工作流初始化完成")
    
    def create_video_from_matches(self, matches, output_path, fps=5):
        """
        从匹配的帧创建视频
        
        参数:
            matches: 包含frame_path键的字典列表
            output_path: 输出视频路径
            fps: 帧率
        
        返回:
            str/bool: 成功返回视频路径，失败返回False
        """
        try:
            if not matches or len(matches) == 0:
                logger.warning("没有匹配的帧可以创建视频")
                return False
                
            # 读取第一帧来获取尺寸信息
            first_frame_path = matches[0].get('frame_path')
            if not first_frame_path or not os.path.exists(first_frame_path):
                logger.error(f"第一帧不存在: {first_frame_path}")
                return False
                
            first_frame = cv2.imread(first_frame_path)
            if first_frame is None:
                logger.error(f"无法读取第一帧: {first_frame_path}")
                return False
                
            height, width, _ = first_frame.shape
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 尝试多种编码器，确保视频可以创建成功且浏览器兼容
            codec_options = [
                ('avc1', '.mp4'),  # H.264 编码，浏览器兼容性最好
                ('h264', '.mp4'),  # 另一种H.264编码表示
                ('mp4v', '.mp4'),  # MPEG-4 编码
                ('DIVX', '.avi')   # DIVX 编码
            ]
            
            for codec, ext in codec_options:
                actual_output = output_path
                if not actual_output.endswith(ext):
                    actual_output = os.path.splitext(output_path)[0] + ext
                
                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    out = cv2.VideoWriter(actual_output, fourcc, fps, (width, height))
                    
                    # 添加所有匹配帧到视频
                    for match in matches:
                        frame_path = match.get('frame_path')
                        if frame_path and os.path.exists(frame_path):
                            frame = cv2.imread(frame_path)
                            if frame is not None:
                                out.write(frame)
                    
                    out.release()
                    
                    # 检查文件是否创建成功且不为空
                    if os.path.exists(actual_output) and os.path.getsize(actual_output) > 0:
                        logger.info(f"成功创建视频: {actual_output} 使用编码器: {codec}")
                        return actual_output
                    else:
                        logger.warning(f"使用编码器 {codec} 创建的视频为空或不存在")
                        continue
                        
                except Exception as e:
                    logger.error(f"使用编码器 {codec} 创建视频失败: {str(e)}")
                    continue
            
            logger.error("所有编码器尝试失败，无法创建视频")
            return False
        
        except Exception as e:
            logger.error(f"创建视频时发生错误: {str(e)}")
            return False
    
    async def send_alert_email(self, plate_no, detection_type, timestamp, image_path=None, video_name=None):
        """
        发送报警邮件
        
        参数:
            plate_no: 检测到的车牌号
            detection_type: 检测类型（camera/video/image）
            timestamp: 检测时间
            image_path: 图片路径（可选）
            video_name: 视频文件名（可选）
            
        返回:
            bool: 发送成功或失败
        """
        if not self.email_config['enabled']:
            logger.info("邮件报警功能未启用")
            return False
            
        try:
            # 创建邮件对象
            message = MIMEMultipart()
            message["From"] = self.email_config['sender_email']
            message["To"] = self.email_config['receiver_email']
            message["Subject"] = self.email_config['subject_template'].format(plate_no=plate_no)
            
            # 构建邮件正文
            body = self.email_config['body_template'].format(
                plate_no=plate_no,
                timestamp=timestamp,
                detection_type=detection_type
            )
            
            # 添加图片或视频链接信息
            if image_path:
                body += f"\n\n检测图片: {image_path}"
            if video_name:
                body += f"\n\n检测视频: {video_name}"
                
            message.attach(MIMEText(body, "plain"))
            
            # 发送邮件
            server = smtplib.SMTP_SSL("smtp.qq.com", 465)
            try:
                server.login(self.email_config['sender_email'], self.email_config['app_password'])
                server.sendmail(
                    self.email_config['sender_email'], 
                    self.email_config['receiver_email'], 
                    message.as_string()
                )
                logger.info(f"报警邮件发送成功，目标车牌: {plate_no}")
                return True
            except Exception as e:
                logger.error(f"邮件发送失败: {str(e)}")
                return False
            finally:
                server.quit()
                
        except Exception as e:
            logger.error(f"准备邮件过程中发生错误: {str(e)}")
            return False
    
    def set_target_plate(self, plate_no, source="manual", image_path=None, confidence=1.0, color=None):
        """
        设置目标车牌
        
        参数:
            plate_no: 车牌号码
            source: 来源（manual/image/video）
            image_path: 图片路径（可选）
            confidence: 置信度（可选）
            color: 车牌颜色（可选）
            
        返回:
            dict: 目标车牌信息
        """
        self.target_plate_info = {
            'plate_no': plate_no,
            'source': source,
            'image_path': image_path,
            'confidence': confidence,
            'color': color,
            'set_time': datetime.datetime.now().isoformat()
        }
        
        # 更新摄像头匹配结果中的目标车牌
        self.camera_match_results['target_plate'] = plate_no
        
        logger.info(f"已设置目标车牌: {plate_no}")
        return self.target_plate_info
    
    def clear_target_plate(self):
        """
        清除目标车牌
        
        返回:
            dict: 清空后的目标车牌信息
        """
        self.target_plate_info = {
            'plate_no': None,
            'source': None,
            'image_path': None,
            'confidence': 0.0,
            'color': None,
            'set_time': None
        }
        
        # 更新摄像头匹配结果中的目标车牌
        self.camera_match_results['target_plate'] = None
        
        logger.info("已清除目标车牌")
        return self.target_plate_info
    
    def get_target_plate(self):
        """
        获取当前目标车牌信息
        
        返回:
            dict: 目标车牌信息
        """
        return self.target_plate_info
    
    async def match_image(self, image_path, detect_model, rec_model, car_rec_model, device, img_size):
        """
        匹配图片中的车牌
        
        参数:
            image_path: 图片路径
            detect_model: 检测模型
            rec_model: 识别模型
            car_rec_model: 车辆识别模型
            device: 设备类型
            img_size: 图像尺寸
            
        返回:
            dict: 匹配结果
        """
        # 检查是否已设置目标车牌
        if not self.target_plate_info['plate_no']:
            return {'success': False, 'message': '未设置目标车牌', 'matches': []}
        
        target_plate_no = self.target_plate_info['plate_no']
        logger.info(f"开始匹配图片中的车牌，目标车牌: {target_plate_no}")
        
        try:
            # 读取图片
            img = cv2.imread(image_path)
            if img is None:
                return {'success': False, 'message': '无法读取图片', 'matches': []}
            
            # 执行车牌识别
            recognition_results = detect_Recognition_plate(
                detect_model, img, device, rec_model, img_size, car_rec_model
            )
            
            if not recognition_results:
                return {'success': True, 'message': '未检测到车牌', 'matches': []}
            
            # 查找匹配的车牌
            matches = []
            for result in recognition_results:
                if result.get('plate_no') == target_plate_no:
                    # 生成唯一文件名
                    unique_id = str(uuid.uuid4())
                    timestamp = datetime.datetime.now().isoformat()
                    
                    # 绘制匹配结果
                    result_img = draw_result(img, [result], highlight_plate=target_plate_no)
                    
                    # 保存处理后的图片
                    result_filename = f"match_{unique_id}.jpg"
                    result_path = os.path.join(self.image_output_folder, result_filename)
                    cv2.imwrite(result_path, result_img)
                    
                    # 构建匹配信息
                    match_info = {
                        'id': unique_id,
                        'plate_no': result.get('plate_no'),
                        'plate_type': result.get('plate_type', '未知类型'),
                        'plate_color': result.get('plate_color', '未知颜色'),
                        'car_color': result.get('car_color', '未知颜色'),
                        'confidence': float(result.get('score', 0)),
                        'image_path': result_path,
                        'timestamp': timestamp,
                        'detection_type': 'image'
                    }
                    
                    matches.append(match_info)
                    
                    # 发送报警邮件
                    await self.send_alert_email(
                        plate_no=target_plate_no,
                        detection_type='image',
                        timestamp=timestamp,
                        image_path=result_path
                    )
            
            return {
                'success': True, 
                'message': f"找到 {len(matches)} 个匹配车牌" if matches else "未找到匹配车牌",
                'matches': matches
            }
            
        except Exception as e:
            logger.error(f"匹配图片时发生错误: {str(e)}")
            return {'success': False, 'message': f'处理过程中发生错误: {str(e)}', 'matches': []}
    
    async def process_video(self, video_id, video_path, target_plate_no, detect_model, rec_model, car_rec_model, device, img_size):
        """
        处理视频中的车牌
        
        参数:
            video_id: 视频处理ID
            video_path: 视频文件路径
            target_plate_no: 目标车牌号
            detect_model: 检测模型
            rec_model: 识别模型
            car_rec_model: 车辆识别模型
            device: 设备类型
            img_size: 图像尺寸
        """
        logger.info(f"开始处理视频 {video_id}，目标车牌: {target_plate_no}")
        
        # 更新处理状态
        self.video_processing_status[video_id] = {
            'status': 'processing',
            'progress': 0,
            'matches': [],
            'output_video': None,
            'start_time': time.time(),
            'message': '正在处理视频...'
        }
        
        try:
            # 读取视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.video_processing_status[video_id] = {
                    'status': 'error',
                    'message': '无法打开视频文件',
                    'end_time': time.time()
                }
                return
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            # 设置进度更新间隔
            progress_update_interval = max(1, int(total_frames / 100))  # 每1%更新一次
            output_frame_interval = max(1, int(fps))  # 每秒保存一帧
            
            frame_matches = []
            current_frame = 0
            
            # 处理视频帧
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 每隔一定帧数处理一次，减轻计算负担
                if current_frame % output_frame_interval == 0:
                    # 执行车牌识别
                    recognition_results = detect_Recognition_plate(
                        detect_model, frame, device, rec_model, img_size, car_rec_model
                    )
                    
                    # 查找匹配的车牌
                    for result in recognition_results:
                        if result.get('plate_no') == target_plate_no:
                            # 获取当前时间点
                            current_time = current_frame / fps if fps > 0 else 0
                            timestamp = datetime.datetime.now().isoformat()
                            
                            # 生成唯一ID
                            match_id = str(uuid.uuid4())
                            
                            # 绘制匹配结果
                            result_frame = draw_result(frame, [result], highlight_plate=target_plate_no)
                            
                            # 保存匹配帧
                            frame_filename = f"frame_{video_id}_{match_id}.jpg"
                            frame_path = os.path.join(self.image_output_folder, frame_filename)
                            cv2.imwrite(frame_path, result_frame)
                            
                            # 构建匹配信息
                            match_info = {
                                'id': match_id,
                                'plate_no': result.get('plate_no'),
                                'plate_type': result.get('plate_type', '未知类型'),
                                'plate_color': result.get('plate_color', '未知颜色'),
                                'car_color': result.get('car_color', '未知颜色'),
                                'confidence': float(result.get('score', 0)),
                                'frame_path': frame_path,
                                'timestamp': timestamp,
                                'video_time': current_time,
                                'video_time_formatted': self._format_time(current_time)
                            }
                            
                            frame_matches.append(match_info)
                            
                            # 更新处理状态
                            self.video_processing_status[video_id]['matches'] = frame_matches
                            
                            # 如果匹配数量超过限制，停止处理
                            if len(frame_matches) >= 100:  # 限制最多100个匹配
                                logger.warning(f"视频 {video_id} 匹配数量达到上限100，停止进一步处理")
                                break
                
                # 更新进度
                if current_frame % progress_update_interval == 0:
                    progress = min(99, int((current_frame / total_frames) * 100)) if total_frames > 0 else 0
                    self.video_processing_status[video_id]['progress'] = progress
                    self.video_processing_status[video_id]['message'] = f'处理中...{progress}%'
                
                current_frame += 1
                
                # 如果匹配数量超过限制，停止处理
                if len(frame_matches) >= 100:
                    break
            
            # 释放视频资源
            cap.release()
            
            # 如果有匹配结果，创建摘要视频
            if frame_matches:
                output_video_path = os.path.join(
                    self.video_output_folder, 
                    f"summary_{video_id}.mp4"
                )
                
                video_path = self.create_video_from_matches(frame_matches, output_video_path)
                if video_path:
                    self.video_processing_status[video_id]['output_video'] = video_path
                
                # 发送报警邮件
                await self.send_alert_email(
                    plate_no=target_plate_no,
                    detection_type='video',
                    timestamp=datetime.datetime.now().isoformat(),
                    video_name=os.path.basename(video_path) if video_path else None
                )
            
            # 完成处理
            self.video_processing_status[video_id] = {
                'status': 'completed',
                'progress': 100,
                'matches': frame_matches,
                'output_video': self.video_processing_status[video_id].get('output_video'),
                'match_count': len(frame_matches),
                'duration': duration,
                'duration_formatted': self._format_time(duration),
                'end_time': time.time(),
                'message': '处理完成',
                'summary': self._generate_video_summary(frame_matches)
            }
            
            logger.info(f"视频 {video_id} 处理完成，找到 {len(frame_matches)} 个匹配")
            
        except Exception as e:
            logger.error(f"处理视频 {video_id} 时发生错误: {str(e)}")
            self.video_processing_status[video_id] = {
                'status': 'error',
                'message': f'处理过程中发生错误: {str(e)}',
                'end_time': time.time()
            }
    
    def get_video_processing_status(self, video_id):
        """
        获取视频处理状态
        
        参数:
            video_id: 视频处理ID
            
        返回:
            dict: 处理状态信息
        """
        if video_id not in self.video_processing_status:
            return {'status': 'not_found', 'message': '未找到处理任务'}
        
        return self.video_processing_status[video_id]
    
    def get_all_video_status(self):
        """
        获取所有视频处理状态
        
        返回:
            dict: 所有视频处理状态
        """
        return self.video_processing_status
    
    def add_camera_match_result(self, result, frame):
        """
        添加摄像头匹配结果
        
        参数:
            result: 识别结果
            frame: 视频帧
            
        返回:
            dict: 匹配信息
        """
        # 检查是否已设置目标车牌
        if not self.target_plate_info['plate_no']:
            return None
            
        target_plate_no = self.target_plate_info['plate_no']
        
        # 检查是否匹配目标车牌
        if result.get('plate_no') != target_plate_no:
            return None
        
        # 生成唯一ID和时间戳
        match_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # 绘制匹配结果
        result_frame = draw_result(frame, [result], highlight_plate=target_plate_no)
        
        # 保存匹配帧
        frame_filename = f"camera_{match_id}.jpg"
        frame_path = os.path.join(self.image_output_folder, frame_filename)
        cv2.imwrite(frame_path, result_frame)
        
        # 构建匹配信息
        match_info = {
            'id': match_id,
            'plate_no': result.get('plate_no'),
            'plate_type': result.get('plate_type', '未知类型'),
            'plate_color': result.get('plate_color', '未知颜色'),
            'car_color': result.get('car_color', '未知颜色'),
            'confidence': float(result.get('score', 0)),
            'image_path': frame_path,
            'timestamp': timestamp,
            'detection_type': 'camera'
        }
        
        # 添加到匹配结果列表
        self.camera_match_results['matches'].insert(0, match_info)
        self.camera_match_results['last_updated'] = timestamp
        
        # 限制列表长度，最多保留20个结果
        if len(self.camera_match_results['matches']) > 20:
            self.camera_match_results['matches'] = self.camera_match_results['matches'][:20]
        
        # 异步发送报警邮件
        asyncio.create_task(self.send_alert_email(
            plate_no=target_plate_no,
            detection_type='camera',
            timestamp=timestamp,
            image_path=frame_path
        ))
        
        return match_info
    
    def get_camera_match_results(self):
        """
        获取摄像头匹配结果
        
        返回:
            dict: 匹配结果列表
        """
        return self.camera_match_results
    
    def generate_report(self, video_id=None):
        """
        生成摘要报告
        
        参数:
            video_id: 视频处理ID（可选）
            
        返回:
            dict: 报告内容
        """
        # 获取当前目标车牌信息
        target_plate = self.get_target_plate()
        
        # 基础报告信息
        report = {
            'generated_time': datetime.datetime.now().isoformat(),
            'target_plate': target_plate,
            'camera_matches': self.get_camera_match_results(),
            'video_processes': {}
        }
        
        # 添加视频处理信息
        if video_id and video_id in self.video_processing_status:
            report['video_processes'][video_id] = self.video_processing_status[video_id]
        else:
            report['video_processes'] = self.video_processing_status
        
        return report
    
    def _format_time(self, seconds):
        """格式化时间（秒）为 HH:MM:SS 格式"""
        if seconds is None:
            return "00:00:00"
        
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    
    def _generate_video_summary(self, matches):
        """生成视频处理摘要"""
        if not matches:
            return "未找到匹配车牌"
            
        first_match = matches[0] if matches else {}
        plate_no = first_match.get('plate_no', '未知车牌')
        plate_color = first_match.get('plate_color', '未知颜色')
        car_color = first_match.get('car_color', '未知颜色')
        
        return f"检测到车牌 {plate_no}，车牌颜色: {plate_color}，车身颜色: {car_color}，共出现 {len(matches)} 次"
        
    def configure_email(self, enabled, sender_email=None, app_password=None, receiver_email=None):
        """配置邮件报警功能"""
        self.email_config['enabled'] = enabled
        
        if sender_email:
            self.email_config['sender_email'] = sender_email
        if app_password:
            self.email_config['app_password'] = app_password
        if receiver_email:
            self.email_config['receiver_email'] = receiver_email
            
        return self.email_config
