"""
YOLOv8 Adapter - Integrate YOLOv8 models into fire detection system
"""
import os
import numpy as np
import cv2
from ultralytics import YOLO

class YOLOModelAdapter:
    """YOLOv8 model adapter, making it compatible with existing system"""
    
    def __init__(self, model_path, model_type="detection", confidence_threshold=0.3):
        """
        Initialize YOLOv8 model adapter
        
        Args:
            model_path: YOLO model file path
            model_type: Model type, can be "detection", "classification" or "segmentation"
            confidence_threshold: Confidence threshold
        """
        self.model_path = model_path
        self.model_type = model_type
        self.confidence_threshold = confidence_threshold
        self.model = None
        
        # Check if model file exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"YOLO model file does not exist: {model_path}")
        
        # Load YOLO model
        try:
            self.model = YOLO(model_path)
            print(f"Successfully loaded YOLO model: {model_path}")
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            raise
    
    def predict(self, img_array, verbose=0):
        """
        Use YOLOv8 model for prediction, output format compatible with original fire detection system
        
        Args:
            img_array: Input image array, shape (1, height, width, 3)
            verbose: Verbosity level
        
        Returns:
            Prediction result, format depends on model type
        """
        if self.model is None:
            raise ValueError("Model not loaded, cannot predict")
        
        # Ensure input format is correct - YOLO expects BGR image, not normalized array
        # If input is normalized, convert back to 0-255 range
        if img_array.max() <= 1.0:
            img_array = (img_array * 255).astype(np.uint8)
        
        # Extract single image from batch array
        if len(img_array.shape) == 4:
            img = img_array[0]  # (height, width, 3)
        else:
            img = img_array  # Already a single image
        
        if self.model_type == "detection":
            # Detection mode
            results = self.model(img, verbose=False, conf=self.confidence_threshold)
            return self._process_detection_results(results)
        
        elif self.model_type == "classification":
            # Classification mode
            results = self.model(img, verbose=False)
            return self._process_classification_results(results)
        
        elif self.model_type == "segmentation":
            # Segmentation mode
            results = self.model(img, verbose=False, conf=self.confidence_threshold)
            return self._process_segmentation_results(results, img.shape[:2])
        
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def _process_detection_results(self, results):
        """
        Process YOLOv8 detection results, convert to format compatible with original system
        
        Args:
            results: YOLOv8 detection results
        
        Returns:
            Detection results in compatible format
        """
        result = results[0]  # Get result for first image
        
        # Extract confidence scores and class IDs
        boxes = result.boxes
        
        # Find fire and smoke related detection results
        fire_confidence = 0.0
        smoke_confidence = 0.0
        fire_detected = False
        smoke_detected = False
        
        # Check all detection boxes
        for box in boxes:
            # Get class ID and confidence
            cls_id = int(box.cls.item())
            conf = float(box.conf.item())
            
            # Get class name
            class_name = result.names[cls_id].lower()
            
            # Find fire related classes (fire, flame, etc.)
            if "fire" in class_name or "flame" in class_name:
                if conf > fire_confidence:
                    fire_confidence = conf
                    fire_detected = True
        
            # Also check for smoke - important for early fire detection
            elif "smoke" in class_name:
                if conf > smoke_confidence:
                    smoke_confidence = conf
                    smoke_detected = True
        
        # Combine fire and smoke detections - if smoke is detected with higher confidence than fire
        # Still mark as fire but with lower confidence (early warning)
        if fire_detected and smoke_detected:
            # Both detected - use higher confidence
            combined_confidence = max(fire_confidence, smoke_confidence * 0.9)
        elif fire_detected:
            # Only fire detected
            combined_confidence = fire_confidence
        elif smoke_detected:
            # Only smoke detected - use reduced confidence as it might be early fire
            combined_confidence = smoke_confidence * 0.8  # Apply slight reduction for smoke-only
        else:
            # Neither detected
            combined_confidence = 0.0
        
        # Create format compatible with classification model output
        if fire_detected or smoke_detected:
            # Return format: [[no_fire_prob, fire_prob]]
            return np.array([[1.0 - combined_confidence, combined_confidence]])
        else:
            # No fire detected
            return np.array([[1.0, 0.0]])
    
    def _process_classification_results(self, results):
        """
        Process YOLOv8 classification results, convert to format compatible with original system
        
        Args:
            results: YOLOv8 classification results
        
        Returns:
            Classification results in compatible format
        """
        result = results[0]  # Get result for first image
        probs = result.probs.data.cpu().numpy()
        
        # Find fire related classes (if any)
        fire_prob = 0.0
        class_names = result.names
        
        for i, name in class_names.items():
            name_lower = name.lower()
            if "fire" in name_lower or "flame" in name_lower:
                fire_prob = max(fire_prob, probs[i])
            # Also consider smoke as potential fire
            elif "smoke" in name_lower:
                fire_prob = max(fire_prob, probs[i] * 0.8)  # Slightly lower confidence for smoke
        
        # Create format compatible with our system
        return np.array([[1.0 - fire_prob, fire_prob]])
    
    def _process_segmentation_results(self, results, original_shape):
        """
        Process YOLOv8 segmentation results, convert to format compatible with original system
        
        Args:
            results: YOLOv8 segmentation results
            original_shape: Original image shape (height, width)
        
        Returns:
            Segmentation mask in compatible format
        """
        result = results[0]  # Get result for first image
        
        # Create empty masks for fire and smoke
        height, width = original_shape
        fire_mask = np.zeros((height, width, 1), dtype=np.float32)
        smoke_mask = np.zeros((height, width, 1), dtype=np.float32)
        
        # If there are segmentation masks
        if hasattr(result, 'masks') and result.masks is not None:
            masks = result.masks
            boxes = result.boxes
            
            for i, (mask, box) in enumerate(zip(masks.data, boxes)):
                # Get class ID and confidence
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                
                # Get class name
                class_name = result.names[cls_id].lower()
                
                # Process fire related classes with lower threshold (0.2)
                if ("fire" in class_name or "flame" in class_name) and conf >= 0.2:
                    # Resize mask to original image size
                    mask_np = mask.cpu().numpy()  # Convert to numpy array
                    mask_np = cv2.resize(mask_np, (width, height))
                    
                    # Add mask to combined fire mask with confidence weighting
                    fire_mask = np.maximum(fire_mask, mask_np[:,:,np.newaxis] * conf)
        
                # Also process smoke masks, also with lower threshold (0.2)
                elif "smoke" in class_name and conf >= 0.2:
                    # Resize mask to original image size
                    mask_np = mask.cpu().numpy()
                    mask_np = cv2.resize(mask_np, (width, height))
                    
                    # Add mask to combined smoke mask with confidence weighting
                    smoke_mask = np.maximum(smoke_mask, mask_np[:,:,np.newaxis] * conf)
        
        # Combine masks - fire has priority over smoke
        combined_mask = np.maximum(fire_mask, smoke_mask * 0.8)  # Reduce smoke importance slightly
        
        # Return format compatible with segmentation model output
        return np.array([combined_mask])  # shape (1, height, width, 1)
    
    def load_weights(self, weights_path):
        """Method provided for compatibility with original system interface"""
        # YOLO model already loaded during initialization, this method is just for API compatibility
        print("YOLO model already loaded, no need to load weights separately")
        return True

def make_yolo_classification_model(model_path, confidence_threshold=0.3):
    """
    Create YOLO model adapter for classification
    
    Args:
        model_path: YOLO model path
        confidence_threshold: Confidence threshold
    
    Returns:
        YOLOModelAdapter instance
    """
    return YOLOModelAdapter(model_path, model_type="classification", confidence_threshold=confidence_threshold)

def make_yolo_segmentation_model(model_path, confidence_threshold=0.3):
    """
    Create YOLO model adapter for segmentation
    
    Args:
        model_path: YOLO model path
        confidence_threshold: Confidence threshold
    
    Returns:
        YOLOModelAdapter instance
    """
    return YOLOModelAdapter(model_path, model_type="segmentation", confidence_threshold=confidence_threshold)

def make_yolo_detection_model(model_path, confidence_threshold=0.3):
    """
    Create YOLO model adapter for detection
    
    Args:
        model_path: YOLO model path
        confidence_threshold: Confidence threshold
    
    Returns:
        YOLOModelAdapter instance
    """
    return YOLOModelAdapter(model_path, model_type="detection", confidence_threshold=confidence_threshold)
