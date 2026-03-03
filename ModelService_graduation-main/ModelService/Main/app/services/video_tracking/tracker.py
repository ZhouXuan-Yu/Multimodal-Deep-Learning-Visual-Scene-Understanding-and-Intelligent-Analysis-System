"""
视频目标追踪服务模块
集成多种追踪算法的视频目标追踪功能
"""
import os
import cv2
import numpy as np
import logging
import time
from pathlib import Path
import threading
import uuid
from collections import defaultdict

# 配置日志
logger = logging.getLogger(__name__)

# 模型路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))))
MODEL_DIR = os.path.join(BASE_DIR, "ModelService", "Main", "models", "video_tracking")
os.makedirs(MODEL_DIR, exist_ok=True)

# 输出路径
OUTPUT_DIR = os.path.join(BASE_DIR, "ModelService", "Main", "output", "video_tracking")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 追踪器类型
AVAILABLE_TRACKERS = {
    'KCF': cv2.legacy.TrackerKCF_create,
    'CSRT': cv2.legacy.TrackerCSRT_create,
    'MOSSE': cv2.legacy.TrackerMOSSE_create,
    'MIL': cv2.legacy.TrackerMIL_create,
    'MedianFlow': cv2.legacy.TrackerMedianFlow_create,
}

class MultiObjectTracker:
    """多目标追踪器类"""
    
    def __init__(self, tracker_type='KCF'):
        """
        初始化多目标追踪器
        
        Args:
            tracker_type: 追踪器类型，可选值为 'KCF', 'CSRT', 'MOSSE', 'MIL', 'MedianFlow'
        """
        self.logger = logging.getLogger(__name__ + ".MultiObjectTracker")
        self.trackers = {}  # 每个目标的追踪器
        self.bboxes = {}    # 每个目标的边界框
        self.tracker_type = tracker_type
        self.tracking = False
        self.tracking_thread = None
        self.video_capture = None
        self.frame_width = 0
        self.frame_height = 0
        self.fps = 0
        self.current_frame = None
        self.processed_frames = []
        self.tracking_results = {}
        self.target_classes = {}  # 每个目标的类别
        self.track_id_counter = 0
        self.stop_flag = False
        
        # 检查选择的追踪器是否可用
        if tracker_type not in AVAILABLE_TRACKERS:
            self.logger.warning(f"追踪器类型 {tracker_type} 不可用，将使用默认的KCF追踪器")
            self.tracker_type = 'KCF'
        
        self.logger.info(f"初始化多目标追踪器，类型: {self.tracker_type}")
    
    def _create_tracker(self):
        """创建新的追踪器实例"""
        return AVAILABLE_TRACKERS[self.tracker_type]()
    
    def add_target(self, frame, bbox, target_class=None):
        """
        添加新的追踪目标
        
        Args:
            frame: 当前帧
            bbox: 边界框 (x, y, w, h)
            target_class: 可选，目标类别名称
            
        Returns:
            新的追踪ID
        """
        # 生成新的追踪ID
        track_id = self.track_id_counter
        self.track_id_counter += 1
        
        # 创建新的追踪器并初始化
        tracker = self._create_tracker()
        success = tracker.init(frame, bbox)
        
        if success:
            self.trackers[track_id] = tracker
            self.bboxes[track_id] = bbox
            self.tracking_results[track_id] = []
            
            # 保存目标类别信息
            if target_class:
                self.target_classes[track_id] = target_class
            else:
                self.target_classes[track_id] = f"目标-{track_id}"
                
            self.logger.info(f"成功添加目标: ID={track_id}, 类别={self.target_classes[track_id]}, 位置={bbox}")
            return track_id
        else:
            self.logger.warning(f"无法初始化目标追踪器")
            return None
    
    def remove_target(self, track_id):
        """
        移除追踪目标
        
        Args:
            track_id: 追踪ID
            
        Returns:
            是否成功移除
        """
        if track_id in self.trackers:
            del self.trackers[track_id]
            del self.bboxes[track_id]
            del self.target_classes[track_id]
            self.logger.info(f"已移除目标: ID={track_id}")
            return True
        else:
            self.logger.warning(f"未找到目标: ID={track_id}")
            return False
    
    def update(self, frame):
        """
        使用当前帧更新所有追踪器
        
        Args:
            frame: 当前帧
            
        Returns:
            每个目标的追踪结果
        """
        # 保存当前帧
        self.current_frame = frame.copy()
        
        # 追踪结果
        results = {}
        failed_trackers = []
        
        # 遍历所有追踪器并更新
        for track_id, tracker in self.trackers.items():
            # 更新追踪器
            success, bbox = tracker.update(frame)
            
            if success:
                # 保存新的边界框
                self.bboxes[track_id] = bbox
                
                # 记录追踪结果
                x, y, w, h = [int(v) for v in bbox]
                results[track_id] = {
                    'bbox': (x, y, w, h),
                    'center': (x + w // 2, y + h // 2),
                    'class': self.target_classes[track_id]
                }
                
                # 将结果添加到历史记录
                self.tracking_results[track_id].append((x, y, w, h))
            else:
                self.logger.warning(f"目标 {track_id} 追踪失败")
                failed_trackers.append(track_id)
        
        # 移除失败的追踪器
        for track_id in failed_trackers:
            self.remove_target(track_id)
            
        return results
    
    def draw_tracks(self, frame, results=None, draw_history=False, history_length=20):
        """
        在帧上绘制追踪结果
        
        Args:
            frame: 输入帧
            results: 追踪结果，如果为None则使用最新的结果
            draw_history: 是否绘制历史轨迹
            history_length: 历史轨迹长度
            
        Returns:
            带有追踪结果的帧
        """
        # 创建输出帧
        output_frame = frame.copy()
        
        # 如果结果为None，则使用当前的边界框
        if results is None:
            results = {}
            for track_id, bbox in self.bboxes.items():
                x, y, w, h = [int(v) for v in bbox]
                results[track_id] = {
                    'bbox': (x, y, w, h),
                    'center': (x + w // 2, y + h // 2),
                    'class': self.target_classes[track_id]
                }
        
        # 为每个ID分配固定颜色
        colors = {}
        
        # 绘制每个追踪目标
        for track_id, result in results.items():
            # 获取或生成颜色
            if track_id not in colors:
                # 随机生成BGR颜色
                colors[track_id] = tuple(map(int, np.random.randint(0, 255, 3)))
            
            color = colors[track_id]
            bbox = result['bbox']
            class_name = result['class']
            
            # 绘制边界框
            x, y, w, h = bbox
            cv2.rectangle(output_frame, (x, y), (x + w, y + h), color, 2)
            
            # 绘制ID和类别
            label = f"ID:{track_id} {class_name}"
            cv2.putText(output_frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # 绘制历史轨迹
            if draw_history and track_id in self.tracking_results:
                history = self.tracking_results[track_id]
                
                # 限制历史长度
                if len(history) > 1:
                    if history_length > 0 and len(history) > history_length:
                        history = history[-history_length:]
                    
                    # 绘制历史轨迹
                    for i in range(1, len(history)):
                        x1, y1 = history[i-1][0] + history[i-1][2] // 2, history[i-1][1] + history[i-1][3] // 2
                        x2, y2 = history[i][0] + history[i][2] // 2, history[i][1] + history[i][3] // 2
                        cv2.line(output_frame, (x1, y1), (x2, y2), color, 2)
        
        return output_frame
    
    def open_video(self, video_path):
        """
        打开视频文件或摄像头
        
        Args:
            video_path: 视频文件路径或摄像头索引
            
        Returns:
            是否成功打开
        """
        try:
            # 关闭之前的视频捕获
            if self.video_capture is not None and self.video_capture.isOpened():
                self.video_capture.release()
            
            # 打开新的视频捕获
            if isinstance(video_path, int) or (isinstance(video_path, str) and video_path.isdigit()):
                # 如果是数字，则视为摄像头索引
                video_path = int(video_path)
                self.logger.info(f"正在打开摄像头: {video_path}")
            else:
                self.logger.info(f"正在打开视频文件: {video_path}")
                
            self.video_capture = cv2.VideoCapture(video_path)
            
            if not self.video_capture.isOpened():
                self.logger.error(f"无法打开视频源: {video_path}")
                return False
                
            # 获取视频属性
            self.frame_width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            
            if self.fps <= 0:
                self.fps = 30  # 默认30fps
                
            self.logger.info(f"视频已打开: {self.frame_width}x{self.frame_height}, {self.fps}fps")
            return True
        except Exception as e:
            self.logger.error(f"打开视频时发生错误: {str(e)}")
            return False
    
    def start_tracking(self):
        """
        在新线程中开始追踪
        
        Returns:
            是否成功启动
        """
        if self.tracking:
            self.logger.warning("追踪已经在运行")
            return False
            
        if self.video_capture is None or not self.video_capture.isOpened():
            self.logger.error("没有打开的视频源")
            return False
            
        # 清空之前的处理结果
        self.processed_frames = []
        self.stop_flag = False
        
        # 启动追踪线程
        self.tracking = True
        self.tracking_thread = threading.Thread(target=self._tracking_worker)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        self.logger.info("追踪已启动")
        return True
    
    def stop_tracking(self):
        """
        停止追踪
        
        Returns:
            是否成功停止
        """
        if not self.tracking:
            self.logger.warning("追踪未在运行")
            return False
            
        # 设置停止标志
        self.stop_flag = True
        
        # 等待线程结束
        if self.tracking_thread is not None and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=3.0)
            
        # 标记追踪已停止
        self.tracking = False
        
        self.logger.info("追踪已停止")
        return True
    
    def _tracking_worker(self):
        """追踪工作线程"""
        self.logger.info("追踪线程已启动")
        
        frame_count = 0
        
        while not self.stop_flag:
            # 读取下一帧
            ret, frame = self.video_capture.read()
            
            if not ret:
                self.logger.info("视频结束或读取错误")
                break
                
            # 更新追踪器
            results = self.update(frame)
            
            # 绘制追踪结果
            processed_frame = self.draw_tracks(frame, results, draw_history=True)
            
            # 保存处理后的帧
            self.processed_frames.append(processed_frame)
            
            # 限制保存的帧数量
            max_frames = 100  # 保存最近100帧
            if len(self.processed_frames) > max_frames:
                self.processed_frames = self.processed_frames[-max_frames:]
                
            frame_count += 1
            
        # 结束追踪
        self.tracking = False
        self.logger.info(f"追踪线程已结束，处理了 {frame_count} 帧")
    
    def save_tracking_results(self, output_path=None):
        """
        保存追踪结果视频
        
        Args:
            output_path: 输出视频路径，如果为None则自动生成
            
        Returns:
            输出视频路径或None（失败时）
        """
        if not self.processed_frames:
            self.logger.warning("没有处理后的帧可保存")
            return None
            
        # 生成输出路径
        if output_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_filename = f"tracking_result_{timestamp}.mp4"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
        try:
            # 获取第一帧尺寸
            height, width = self.processed_frames[0].shape[:2]
            
            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))
            
            # 写入所有帧
            for frame in self.processed_frames:
                out.write(frame)
                
            # 释放资源
            out.release()
            
            self.logger.info(f"追踪结果已保存: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"保存视频时发生错误: {str(e)}")
            return None
    
    def get_tracking_status(self):
        """
        获取追踪状态信息
        
        Returns:
            包含追踪状态的字典
        """
        status = {
            'tracking': self.tracking,
            'tracker_type': self.tracker_type,
            'video_open': self.video_capture is not None and self.video_capture.isOpened(),
            'frame_size': (self.frame_width, self.frame_height) if self.frame_width > 0 else None,
            'fps': self.fps,
            'target_count': len(self.trackers),
            'targets': {},
            'processed_frames_count': len(self.processed_frames)
        }
        
        # 添加每个目标的信息
        for track_id, bbox in self.bboxes.items():
            status['targets'][track_id] = {
                'bbox': bbox,
                'class': self.target_classes.get(track_id, 'unknown')
            }
            
        return status
    
    def get_latest_frame(self):
        """
        获取最新的处理帧
        
        Returns:
            最新的处理后的帧，或None
        """
        if self.processed_frames:
            return self.processed_frames[-1]
        return None
    
    def release(self):
        """释放资源"""
        # 停止追踪
        if self.tracking:
            self.stop_tracking()
            
        # 释放视频捕获
        if self.video_capture is not None and self.video_capture.isOpened():
            self.video_capture.release()
            self.video_capture = None
            
        self.logger.info("已释放所有资源")

# 视频追踪管理器类
class VideoTrackingManager:
    """视频追踪服务管理器"""
    
    def __init__(self):
        """初始化视频追踪管理器"""
        self.logger = logging.getLogger(__name__ + ".VideoTrackingManager")
        self.logger.info("初始化视频追踪管理器")
        
        # 存储所有活动的追踪会话
        self.tracking_sessions = {}
    
    def create_session(self, tracker_type='KCF'):
        """
        创建新的追踪会话
        
        Args:
            tracker_type: 追踪器类型
            
        Returns:
            会话ID
        """
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 创建追踪器实例
        tracker = MultiObjectTracker(tracker_type)
        
        # 保存会话
        self.tracking_sessions[session_id] = {
            'tracker': tracker,
            'created_at': time.time(),
            'last_activity': time.time(),
            'status': 'initialized'
        }
        
        self.logger.info(f"创建了新的追踪会话: {session_id}, 追踪器类型: {tracker_type}")
        
        return session_id
    
    def get_session(self, session_id):
        """
        获取追踪会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息或None
        """
        if session_id not in self.tracking_sessions:
            self.logger.warning(f"未找到会话: {session_id}")
            return None
            
        # 更新最后活动时间
        self.tracking_sessions[session_id]['last_activity'] = time.time()
        
        return self.tracking_sessions[session_id]
    
    def get_tracker(self, session_id):
        """
        获取会话中的追踪器
        
        Args:
            session_id: 会话ID
            
        Returns:
            追踪器实例或None
        """
        session = self.get_session(session_id)
        if session is None:
            return None
            
        return session['tracker']
    
    def close_session(self, session_id):
        """
        关闭追踪会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功关闭
        """
        if session_id not in self.tracking_sessions:
            self.logger.warning(f"未找到会话: {session_id}")
            return False
            
        # 获取追踪器并释放资源
        tracker = self.tracking_sessions[session_id]['tracker']
        tracker.release()
        
        # 移除会话
        del self.tracking_sessions[session_id]
        
        self.logger.info(f"已关闭会话: {session_id}")
        
        return True
    
    def cleanup_inactive_sessions(self, max_inactive_time=3600):
        """
        清理不活跃的会话
        
        Args:
            max_inactive_time: 最大不活跃时间(秒)
            
        Returns:
            清理的会话数量
        """
        now = time.time()
        inactive_sessions = []
        
        # 查找不活跃的会话
        for session_id, session in self.tracking_sessions.items():
            inactive_time = now - session['last_activity']
            if inactive_time > max_inactive_time:
                inactive_sessions.append(session_id)
                
        # 关闭不活跃的会话
        for session_id in inactive_sessions:
            self.close_session(session_id)
            
        if inactive_sessions:
            self.logger.info(f"已清理 {len(inactive_sessions)} 个不活跃会话")
            
        return len(inactive_sessions)
    
    def get_all_sessions(self):
        """
        获取所有会话信息
        
        Returns:
            会话信息字典
        """
        sessions_info = {}
        
        for session_id, session in self.tracking_sessions.items():
            tracker = session['tracker']
            status = tracker.get_tracking_status()
            
            sessions_info[session_id] = {
                'created_at': session['created_at'],
                'last_activity': session['last_activity'],
                'status': session['status'],
                'tracking': status['tracking'],
                'target_count': status['target_count']
            }
            
        return sessions_info

# 创建视频追踪管理器的实例
_tracking_manager = None

def get_tracking_manager():
    """获取视频追踪管理器单例"""
    global _tracking_manager
    if _tracking_manager is None:
        _tracking_manager = VideoTrackingManager()
    return _tracking_manager
