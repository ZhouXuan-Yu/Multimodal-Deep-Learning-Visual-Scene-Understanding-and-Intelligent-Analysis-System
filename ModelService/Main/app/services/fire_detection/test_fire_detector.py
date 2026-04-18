"""
火灾检测模块测试脚本
用于验证火灾检测器的各项功能和改进
"""
import os
import sys
import cv2
import numpy as np
import time
import logging
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fire_detector_test.log')
    ]
)

logger = logging.getLogger("fire_detector_test")

# 导入火灾检测器
from fire_detector import FireDetector, FireDetectionColorAnalysis, create_fire_detector

def test_color_analysis(image_path=None):
    """测试基于颜色的火灾和烟雾检测"""
    logger.info("=== 测试颜色分析火灾检测 ===")
    
    # 创建颜色分析器
    color_analyzer = FireDetectionColorAnalysis()
    
    # 加载测试图像或创建测试图像
    if image_path and os.path.exists(image_path):
        image = cv2.imread(image_path)
        logger.info(f"已加载测试图像: {image_path}")
    else:
        # 创建模拟火灾图像
        image = np.zeros((400, 600, 3), dtype=np.uint8)
        # 添加模拟火焰区域 (红色-橙色渐变)
        for i in range(100, 300):
            for j in range(200, 400):
                # 创建橙红色渐变
                r = min(255, int(255 * (1.0 - (i-100)/200.0 * 0.3)))
                g = min(255, int(200 * (1.0 - (i-100)/200.0 * 0.7)))
                b = min(255, int(50 * (1.0 - (i-100)/200.0 * 0.9)))
                image[i, j] = [b, g, r]
                
        # 添加模拟烟雾区域 (灰白色)
        for i in range(50, 150):
            for j in range(300, 500):
                # 创建灰白色渐变
                val = min(255, int(220 + (i-50)/100.0 * 35))
                image[i, j] = [val, val, val]
                
        logger.info("已创建模拟火灾和烟雾图像")
    
    # 进行颜色分析检测
    start_time = time.time()
    result = color_analyzer.detect_fire(image)
    elapsed = time.time() - start_time
    
    # 输出检测结果
    logger.info(f"检测结果: 火灾={result['fire_detected']}, 置信度={result['confidence']:.2f}")
    logger.info(f"火灾区域百分比: {result.get('fire_area_percentage', 0)*100:.2f}%")
    logger.info(f"烟雾区域百分比: {result.get('smoke_area_percentage', 0)*100:.2f}%")
    logger.info(f"检测时间: {elapsed*1000:.1f}ms")
    logger.info(f"环境亮度: {result.get('env_brightness', 'N/A')}")
    
    # 获取区域信息
    fire_regions = result.get('fire_regions', [])
    logger.info(f"检测到的区域数量: {len(fire_regions)}")
    for i, region in enumerate(fire_regions):
        region_type = region.get('type', 'unknown')
        bbox = region.get('bbox', (0,0,0,0))
        conf = region.get('confidence', 0)
        logger.info(f"区域 {i+1}: 类型={region_type}, 置信度={conf:.2f}, 边界框={bbox}")
    
    # 显示结果
    highlighted = result.get('highlighted_image', None)
    if highlighted is not None:
        cv2.imwrite("test_color_analysis_result.jpg", highlighted)
        logger.info("结果已保存至 test_color_analysis_result.jpg")
        
        # 显示结果
        cv2.imshow("Color Analysis Result", highlighted)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return result

def test_yolo_integration(image_path=None):
    """测试YOLO模型集成"""
    logger.info("=== 测试YOLO模型集成 ===")
    
    # 创建火灾检测器
    detector = create_fire_detector()
    
    # 检查模型是否可用
    has_classification = hasattr(detector, 'classification_model') and detector.classification_model is not None
    has_segmentation = hasattr(detector, 'segmentation_model') and detector.segmentation_model is not None
    
    logger.info(f"分类模型可用: {has_classification}")
    logger.info(f"分割模型可用: {has_segmentation}")
    
    # 如果没有指定图像，使用上一步创建的测试图像
    if not image_path or not os.path.exists(image_path):
        # 尝试读取上一步的结果图像
        if os.path.exists("test_color_analysis_result.jpg"):
            image_path = "test_color_analysis_result.jpg"
            logger.info(f"使用上一步生成的图像: {image_path}")
        else:
            logger.error("未指定有效的图像路径且无法找到测试图像")
            return None
    
    # 加载图像
    image = cv2.imread(image_path)
    logger.info(f"已加载测试图像: {image_path}, 尺寸: {image.shape}")
    
    # 进行火灾检测
    start_time = time.time()
    result = detector.process_image(image, mode="both")
    elapsed = time.time() - start_time
    
    # 输出检测结果
    logger.info(f"检测结果: 火灾={result['fire_detected']}, 置信度={result['confidence']:.2f}")
    logger.info(f"火灾区域百分比: {result.get('fire_area_percentage', 0)*100:.2f}%")
    logger.info(f"检测方法: {result.get('method', 'unknown')}")
    logger.info(f"检测时间: {elapsed*1000:.1f}ms")
    
    # 保存结果
    output_image = result.get('output_image', None)
    if output_image is not None:
        cv2.imwrite("test_yolo_integration_result.jpg", output_image)
        logger.info("结果已保存至 test_yolo_integration_result.jpg")
        
        # 显示结果
        cv2.imshow("YOLO Integration Result", output_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return result

def test_video_processing(video_path=None):
    """测试视频处理功能"""
    logger.info("=== 测试视频处理 ===")
    
    # 如果未指定视频，使用示例视频或创建模拟视频
    if not video_path or not os.path.exists(video_path):
        logger.warning(f"未找到指定的视频文件: {video_path}")
        logger.info("创建模拟火灾视频用于测试...")
        
        # 创建模拟视频
        video_path = "test_fire_video.mp4"
        create_test_video(video_path)
        
        if not os.path.exists(video_path):
            logger.error("创建测试视频失败")
            return None
    
    # 创建火灾检测器
    detector = create_fire_detector()
    
    # 设置输出路径
    output_path = "test_processed_video.mp4"
    
    # 创建帧保存目录
    frames_dir = "test_fire_frames"
    os.makedirs(frames_dir, exist_ok=True)
    
    # 处理视频
    start_time = time.time()
    result = detector.process_video(
        video_path=video_path,
        output_path=output_path,
        mode="both",
        display=True,
        threshold=0.4,  # 降低阈值增加敏感度
        save_frames=True,
        frames_dir=frames_dir,
        enable_alarm=False  # 测试过程中不发送报警
    )
    elapsed = time.time() - start_time
    
    # 输出处理结果
    logger.info(f"视频处理完成: {result['success']}")
    logger.info(f"总帧数: {result.get('frames_processed', 0)}")
    logger.info(f"火灾帧数: {result.get('fire_frames', 0)}")
    logger.info(f"火灾比例: {result.get('fire_ratio', 0)*100:.2f}%")
    logger.info(f"处理时间: {elapsed:.2f}秒")
    logger.info(f"平均FPS: {result.get('frames_per_second', 0):.1f}")
    logger.info(f"输出视频: {output_path}")
    
    return result

def create_test_video(output_path, duration=5, fps=24):
    """创建测试火灾视频"""
    # 视频参数
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 检查视频写入器是否成功创建
    if not out.isOpened():
        logger.error("创建视频写入器失败")
        return False
    
    # 创建帧
    total_frames = duration * fps
    for i in range(total_frames):
        # 创建基础帧
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 背景 - 渐变天空
        for y in range(height):
            blue = int(200 - y / height * 150)
            green = int(180 - y / height * 100)
            red = int(100 - y / height * 50)
            frame[y, :] = [blue, green, red]
        
        # 地面
        cv2.rectangle(frame, (0, int(height*0.7)), (width, height), (50, 100, 50), -1)
        
        # 添加火灾
        # 根据帧数变化火灾大小和位置，使其看起来有动态
        fire_size = int(50 + 20 * np.sin(i * 0.2))
        fire_x = int(width * 0.3 + 10 * np.sin(i * 0.1))
        fire_y = int(height * 0.5 + 5 * np.cos(i * 0.3))
        
        # 创建火焰形状
        for j in range(fire_size):
            for k in range(fire_size):
                # 计算到火焰中心的距离
                dx = j - fire_size//2
                dy = k - fire_size//2
                dist = np.sqrt(dx*dx + dy*dy)
                
                if dist < fire_size//2:
                    # 火焰颜色 - 由中心向外变化
                    r = min(255, int(255 - dist * 2))
                    g = min(255, int(100 + dist))
                    b = min(255, int(0 + dist * 0.5))
                    
                    # 添加一些随机性使火焰看起来更自然
                    r = min(255, max(0, r + np.random.randint(-20, 20)))
                    g = min(255, max(0, g + np.random.randint(-20, 20)))
                    
                    # 在适当位置绘制火焰像素
                    y_pos = fire_y + k - fire_size//2
                    x_pos = fire_x + j - fire_size//2
                    
                    if 0 <= y_pos < height and 0 <= x_pos < width:
                        frame[y_pos, x_pos] = [b, g, r]
        
        # 添加烟雾
        smoke_size = int(80 + 30 * np.sin(i * 0.1))
        smoke_x = int(fire_x - 20 + 5 * np.sin(i * 0.2))
        smoke_y = int(fire_y - smoke_size + 10 * np.sin(i * 0.15))
        
        # 创建烟雾形状
        for j in range(smoke_size):
            for k in range(smoke_size):
                # 计算到烟雾中心的距离
                dx = j - smoke_size//2
                dy = k - smoke_size//2
                dist = np.sqrt(dx*dx + dy*dy)
                
                if dist < smoke_size//2:
                    # 烟雾的透明度随距离增加而减小
                    alpha = max(0, 1.0 - dist / (smoke_size//2))
                    # 烟雾颜色 - 灰白色
                    smoke_val = min(255, int(200 + np.random.randint(-30, 30) * alpha))
                    
                    # 在适当位置绘制烟雾像素
                    y_pos = smoke_y + k - smoke_size//2
                    x_pos = smoke_x + j - smoke_size//2
                    
                    if 0 <= y_pos < height and 0 <= x_pos < width:
                        # 混合烟雾和背景
                        b, g, r = frame[y_pos, x_pos]
                        b = int(b * (1-alpha) + smoke_val * alpha)
                        g = int(g * (1-alpha) + smoke_val * alpha)
                        r = int(r * (1-alpha) + smoke_val * alpha)
                        frame[y_pos, x_pos] = [b, g, r]
        
        # 添加帧编号和时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"Frame: {i+1}/{total_frames}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, timestamp, (width-230, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 写入帧
        out.write(frame)
    
    # 释放资源
    out.release()
    logger.info(f"已创建测试视频: {output_path}, {total_frames}帧, {fps}FPS, 时长{duration}秒")
    return True

def main():
    """主测试函数"""
    logger.info("开始火灾检测器测试")
    
    # 测试颜色分析
    test_color_analysis()
    
    # 测试YOLO集成
    test_yolo_integration()
    
    # 测试视频处理
    test_video_processing()
    
    logger.info("测试完成!")

if __name__ == "__main__":
    main() 