"""
Fire Detection Module Improved Test Script
Test the improvements to the fire detection system
"""
import os
import sys
import logging
import cv2
import numpy as np
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('improved_fire_detector_test.log')
    ]
)

logger = logging.getLogger("improved_fire_detector_test")

# Import fire detector
from fire_detector import FireDetector, create_fire_detector

def test_char_encoding():
    """Test whether text rendering works properly without Chinese characters"""
    logger.info("=== Testing character encoding fixes ===")
    
    # Create a test image
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    
    # Create fire detector
    detector = create_fire_detector()
    
    # Process the image
    result = detector.process_image(img)
    
    # Get output image
    output_img = result.get("output_image", None)
    
    if output_img is not None:
        # Save the image to check text rendering
        output_path = "encoding_test_result.jpg"
        cv2.imwrite(output_path, output_img)
        logger.info(f"Saved text rendering test image to {output_path}")
        
        # Display the image
        cv2.imshow("Text Rendering Test", output_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return result

def test_fire_detection_marking():
    """Test fire detection and region marking"""
    logger.info("=== Testing fire region marking ===")
    
    # Create a test image with simulated fire
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    
    # Add a red-orange region to simulate fire
    for i in range(100, 250):
        for j in range(200, 350):
            # Create orange-red gradient for fire
            r = min(255, int(255 * (1.0 - (i-100)/150.0 * 0.3)))
            g = min(255, int(200 * (1.0 - (i-100)/150.0 * 0.7)))
            b = min(255, int(50 * (1.0 - (i-100)/150.0 * 0.9)))
            img[i, j] = [b, g, r]
    
    # Create fire detector
    detector = create_fire_detector()
    
    # Process the image
    result = detector.process_image(img)
    
    # Get output image
    output_img = result.get("output_image", None)
    
    # Check if fire was detected
    logger.info(f"Fire detected: {result.get('fire_detected', False)}")
    logger.info(f"Confidence: {result.get('confidence', 0):.2f}")
    logger.info(f"Fire regions found: {len(result.get('fire_regions', []))}")
    
    if output_img is not None:
        # Save the image to check fire marking
        output_path = "fire_marking_test_result.jpg"
        cv2.imwrite(output_path, output_img)
        logger.info(f"Saved fire marking test image to {output_path}")
        
        # Display the image
        cv2.imshow("Fire Marking Test", output_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return result

def test_frame_skipping():
    """Test frame skipping in video processing"""
    logger.info("=== Testing frame skipping ===")
    
    # Create a test video or use an existing one
    video_path = "test_fire_video.mp4"
    
    if not os.path.exists(video_path):
        logger.info("Creating test video...")
        create_test_video(video_path)
    
    # Create fire detector
    detector = create_fire_detector()
    
    # Process with different frame skipping values
    skip_values = [1, 5, 10]
    results = {}
    
    for skip in skip_values:
        logger.info(f"Testing with frame_skip={skip}")
        
        output_path = f"test_frame_skip_{skip}.mp4"
        
        # Process the video
        start_time = time.time()
        result = detector.process_video(
            video_path=video_path,
            output_path=output_path,
            mode="both",
            display=False,
            threshold=0.4,
            save_frames=False,
            frame_skip=skip
        )
        processing_time = time.time() - start_time
        
        # Log results
        logger.info(f"Frame skip: {skip}")
        logger.info(f"Total frames: {result.get('total_frames', 0)}")
        logger.info(f"Processed frames: {result.get('frames_processed', 0)}")
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        logger.info(f"Frames per second: {result.get('frames_per_second', 0):.1f}")
        
        results[skip] = {
            "total_frames": result.get("total_frames", 0),
            "processed_frames": result.get("frames_processed", 0),
            "processing_time": processing_time,
            "fps": result.get("frames_per_second", 0)
        }
    
    # Compare results
    logger.info("=== Frame Skipping Comparison ===")
    for skip, result in results.items():
        logger.info(f"Skip: {skip}, FPS: {result['fps']:.1f}, Time: {result['processing_time']:.2f}s")
    
    return results

def create_test_video(output_path, duration=5, fps=24):
    """Create a test video with simulated fire"""
    # Video parameters
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Check if video writer was created successfully
    if not out.isOpened():
        logger.error("Failed to create video writer")
        return False
    
    # Create frames
    total_frames = duration * fps
    for i in range(total_frames):
        # Create base frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Background - gradient sky
        for y in range(height):
            blue = int(200 - y / height * 150)
            green = int(180 - y / height * 100)
            red = int(100 - y / height * 50)
            frame[y, :] = [blue, green, red]
        
        # Ground
        cv2.rectangle(frame, (0, int(height*0.7)), (width, height), (50, 100, 50), -1)
        
        # Add fire
        # Vary fire size and position with frame number to make it look dynamic
        fire_size = int(50 + 20 * np.sin(i * 0.2))
        fire_x = int(width * 0.3 + 10 * np.sin(i * 0.1))
        fire_y = int(height * 0.5 + 5 * np.cos(i * 0.3))
        
        # Create fire shape
        for j in range(fire_size):
            for k in range(fire_size):
                # Calculate distance to fire center
                dx = j - fire_size//2
                dy = k - fire_size//2
                dist = np.sqrt(dx*dx + dy*dy)
                
                if dist < fire_size//2:
                    # Fire color - varies from center outward
                    r = min(255, int(255 - dist * 2))
                    g = min(255, int(100 + dist))
                    b = min(255, int(0 + dist * 0.5))
                    
                    # Add some randomness to make fire look more natural
                    r = min(255, max(0, r + np.random.randint(-20, 20)))
                    g = min(255, max(0, g + np.random.randint(-20, 20)))
                    
                    # Draw fire pixel at appropriate position
                    y_pos = fire_y + k - fire_size//2
                    x_pos = fire_x + j - fire_size//2
                    
                    if 0 <= y_pos < height and 0 <= x_pos < width:
                        frame[y_pos, x_pos] = [b, g, r]
        
        # Add frame number and timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"Frame: {i+1}/{total_frames}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, timestamp, (width-230, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Write frame
        out.write(frame)
    
    # Release resources
    out.release()
    logger.info(f"Created test video: {output_path}, {total_frames} frames, {fps}FPS, {duration}s duration")
    return True

def main():
    """Main test function"""
    logger.info("Starting improved fire detector tests")
    
    # Test character encoding fixes
    test_char_encoding()
    
    # Test fire detection marking
    test_fire_detection_marking()
    
    # Test frame skipping
    test_frame_skipping()
    
    logger.info("Tests completed!")

if __name__ == "__main__":
    main() 