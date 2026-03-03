from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse
import os
import uuid
import logging
import time
from app.services.fire_detection.fire_detector import create_fire_detector

# Configure logging
logger = logging.getLogger(__name__)

# Initialize fire detector
fire_detector = create_fire_detector()

# Create router
router = APIRouter(
    prefix="/api/fire_detection",
    tags=["fire_detection"],
    responses={404: {"description": "Not Found"}},
)

@router.post("/detect")
async def detect_fire(
    file: UploadFile = File(...),
    save_result: bool = Form(False),
    output_dir: str = Form("output/fire_detection"),
):
    """
    Detect fire in an image
    
    Args:
        file: Image file
        save_result: Whether to save result
        output_dir: Output directory for saving result
    
    Returns:
        Detection result with image URL if saved
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate unique ID for this request
        request_id = str(uuid.uuid4())
        
        # Save uploaded file temporarily
        temp_path = f"temp/fire_detection_{request_id}.jpg"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        # Write file contents
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        
        # Process image
        import cv2
        img = cv2.imread(temp_path)
        if img is None:
            return JSONResponse(
                status_code=400, 
                content={"success": False, "error": "Invalid image file"}
            )
        
        # Detect fire
        result = fire_detector.process_image(img)
        
        # Save result if requested
        result_url = None
        if save_result:
            output_path = f"{output_dir}/fire_detection_{request_id}.jpg"
            output_img = result.get("output_image", None)
            if output_img is not None:
                cv2.imwrite(output_path, output_img)
                result_url = f"/api/fire_detection/result/{request_id}"
        
        # Clean up temporary file
        try:
            os.remove(temp_path)
        except:
            pass
        
        # Return result
        return {
            "success": True,
            "fire_detected": result.get("fire_detected", False),
            "confidence": result.get("confidence", 0),
            "fire_area_percentage": result.get("fire_area_percentage", 0) * 100,
            "method": result.get("method", "unknown"),
            "result_url": result_url
        }
    except Exception as e:
        logger.error(f"Fire detection failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/detect-video")
async def detect_fire_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    save_frames: bool = Form(False),
    enable_alarm: bool = Form(False),
    email: str = Form(None),
    frame_skip: int = Form(5),  # Default skip 5 frames
):
    """
    Detect fire in a video (asynchronous processing)
    
    Args:
        background_tasks: FastAPI background tasks
        file: Video file
        save_frames: Whether to save key frames
        enable_alarm: Whether to enable email alarm
        email: Email address for alarm
        frame_skip: Number of frames to skip (process 1 frame every N frames)
    
    Returns:
        Task ID for getting processing result
    """
    try:
        # Generate unique ID for this task
        task_id = str(uuid.uuid4())
        
        # Create output directory
        output_dir = f"ModelService/output/fire_detection"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save uploaded file temporarily
        temp_path = f"temp/fire_detection_video_{task_id}.mp4"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        # Write file contents
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        
        # Set up output paths
        output_path = f"{output_dir}/processed_fire_detection_{task_id}.mp4"
        frames_dir = f"{output_dir}/frames/{task_id}" if save_frames else None
        
        # Add video processing task to background tasks
        background_tasks.add_task(
            process_video_task,
            task_id=task_id,
            video_path=temp_path,
            output_path=output_path,
            save_frames=save_frames,
            frames_dir=frames_dir,
            enable_alarm=enable_alarm,
            email=email,
            frame_skip=frame_skip  # Pass frame_skip parameter
        )
        
        # Return task ID
        return {
            "success": True,
            "task_id": task_id,
            "message": "Video processing started in background"
        }
    except Exception as e:
        logger.error(f"Fire detection video processing failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# Function for background video processing
def process_video_task(
    task_id: str,
    video_path: str,
    output_path: str,
    save_frames: bool = False,
    frames_dir: str = None,
    enable_alarm: bool = False,
    email: str = None,
    frame_skip: int = 5  # Default skip 5 frames
):
    """
    Process video in background
    
    Args:
        task_id: Task ID
        video_path: Video file path
        output_path: Output video path
        save_frames: Whether to save key frames
        frames_dir: Directory for saving frames
        enable_alarm: Whether to enable alarm
        email: Email address for alarm
        frame_skip: Number of frames to skip
    """
    try:
        logger.info(f"Starting fire detection video processing for task {task_id}")
        logger.info(f"Frame skip: {frame_skip}, Save frames: {save_frames}, Enable alarm: {enable_alarm}")
        
        # Process video
        result = fire_detector.process_video(
            video_path=video_path,
            output_path=output_path,
            mode="both",
            display=False,
            threshold=0.4,  # Lower threshold for better sensitivity
            save_frames=save_frames,
            frames_dir=frames_dir,
            enable_alarm=enable_alarm,
            receiver_email=email,
            frame_skip=frame_skip  # Pass frame_skip parameter
        )
        
        # Log result
        logger.info(f"Fire detection video processing completed for task {task_id}")
        logger.info(f"Total frames: {result.get('total_frames', 0)}, Processed frames: {result.get('frames_processed', 0)}")
        logger.info(f"Fire frames: {result.get('fire_frames', 0)}, Processing time: {result.get('processing_time', 0):.2f}s")
        
        # Clean up temporary file
        try:
            os.remove(video_path)
        except:
            pass
        
        # Save result to file for later retrieval
        result_path = f"ModelService/output/fire_detection/result_{task_id}.json"
        import json
        with open(result_path, "w") as f:
            # Convert any non-serializable values to strings
            serializable_result = {}
            for key, value in result.items():
                if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                    serializable_result[key] = value
                else:
                    serializable_result[key] = str(value)
            json.dump(serializable_result, f)
        
    except Exception as e:
        logger.error(f"Fire detection video processing failed for task {task_id}: {str(e)}")
        
        # Save error to file for later retrieval
        error_path = f"ModelService/output/fire_detection/error_{task_id}.txt"
        with open(error_path, "w") as f:
            f.write(str(e))

@router.get("/result/{task_id}")
async def get_fire_detection_result(task_id: str):
    """
    Get result of fire detection video processing
    
    Args:
        task_id: Task ID
    
    Returns:
        Processing result or status
    """
    # Check if result file exists
    result_path = f"ModelService/output/fire_detection/result_{task_id}.json"
    if os.path.exists(result_path):
        # Read result from file
        import json
        with open(result_path, "r") as f:
            result = json.load(f)
        
        # Add URLs for accessing processed video and frames
        result["video_url"] = f"/api/fire_detection/result-video/{task_id}"
        result["original_video_url"] = f"/api/fire_detection/original-video/{task_id}"
        
        # If frames were saved, add URL pattern for accessing them
        if result.get("frames_dir") or result.get("save_frames", False):
            result["frames_url_pattern"] = f"/api/fire_detection/frame/{task_id}/fire_frame_XXXX.jpg"
        
        return result
    
    # Check if error file exists
    error_path = f"ModelService/output/fire_detection/error_{task_id}.txt"
    if os.path.exists(error_path):
        # Read error from file
        with open(error_path, "r") as f:
            error = f.read()
        
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": error}
        )
    
    # Check if output video exists (processing completed but result file missing)
    output_path = f"ModelService/output/fire_detection/processed_fire_detection_{task_id}.mp4"
    if os.path.exists(output_path):
        return {
            "success": True,
            "status": "completed",
            "message": "Processing completed but detailed result not available",
            "video_url": f"/api/fire_detection/result-video/{task_id}"
        }
    
    # Check if temporary input file exists (processing in progress)
    temp_path = f"temp/fire_detection_video_{task_id}.mp4"
    if os.path.exists(temp_path):
        return {
            "success": True,
            "status": "processing",
            "message": "Video processing in progress"
        }
    
    # No files found, assume invalid task ID
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "Task not found"}
    )

@router.get("/result-video/{task_id}")
async def get_fire_detection_result_video(task_id: str):
    """
    Get processed video with fire detection
    
    Args:
        task_id: Task ID
    
    Returns:
        Processed video file
    """
    output_path = f"ModelService/output/fire_detection/processed_fire_detection_{task_id}.mp4"
    if os.path.exists(output_path):
        logger.info(f"Returning processed video: {output_path}, size: {os.path.getsize(output_path)} bytes")
        return FileResponse(output_path)
    else:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Processed video not found"}
        )

@router.get("/original-video/{task_id}")
async def get_fire_detection_original_video(task_id: str):
    """
    Get original video
    
    Args:
        task_id: Task ID
    
    Returns:
        Original video file
    """
    # First check in temp directory (if processing is not completed)
    temp_path = f"temp/fire_detection_video_{task_id}.mp4"
    if os.path.exists(temp_path):
        logger.info(f"Returning original video from temp: {temp_path}")
        return FileResponse(temp_path)
    
    # If not in temp, check if it was saved elsewhere
    # (You might want to add logic to save original video if needed)
    
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "Original video not found"}
    )

@router.get("/frame/{task_id}/{frame_file}")
async def get_fire_detection_frame(task_id: str, frame_file: str):
    """
    Get saved frame from fire detection
    
    Args:
        task_id: Task ID
        frame_file: Frame file name
    
    Returns:
        Frame image file
    """
    frames_dir = f"ModelService/output/fire_detection/frames/{task_id}"
    frame_path = os.path.join(frames_dir, frame_file)
    
    # Validate file name to prevent directory traversal
    if ".." in frame_file or not frame_file.endswith((".jpg", ".png")):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Invalid frame file name"}
        )
    
    if os.path.exists(frame_path):
        return FileResponse(frame_path)
    else:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Frame not found"}
        ) 