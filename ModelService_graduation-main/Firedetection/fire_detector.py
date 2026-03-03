"""
Fire Detection Comprehensive Tool - Support for Image and Video Analysis
Supporting both Classification and Segmentation modes
"""
import os
import cv2
import numpy as np

# Add NumPy compatibility patch to resolve compatibility issues between newer NumPy versions and TensorFlow 2.3.0
# NumPy 1.20+ removed these aliases, adding them back to maintain compatibility with TensorFlow 2.3.0
print("Adding NumPy compatibility patches...")

# Create list of aliases to add
# key is the deprecated NumPy alias, value is the corresponding Python built-in type or NumPy type
aliases = {
    'object': object,
    'bool': bool,
    'float': float,
    'complex': complex,
    'str': str,
    'int': int,
    'long': int,
    'unicode': str
}

# Iterate through alias list and add missing aliases
for old_alias, new_type in aliases.items():
    if not hasattr(np, old_alias):
        setattr(np, old_alias, new_type)
        print(f"  - Added np.{old_alias} -> {new_type}")

# Ensure np.bool points to the correct type
if hasattr(np, 'bool_') and not hasattr(np, 'bool'):
    np.bool = np.bool_
    print("  - Added np.bool -> np.bool_")

# Add typeDict attribute
# typeDict is a dictionary that maps type codes to NumPy types
# https://github.com/numpy/numpy/blob/maintenance/1.16.x/numpy/core/_internal.py#L613
if not hasattr(np, 'typeDict'):
    # Create a basic typeDict
    if hasattr(np, '_typeDict'):
        np.typeDict = np._typeDict
    else:
        np.typeDict = {
            'Float32': np.float32,
            'Float64': np.float64,
            'Int8': np.int8,
            'Int16': np.int16,
            'Int32': np.int32,
            'Int64': np.int64,
            'UInt8': np.uint8,
            'UInt16': np.uint16,
            'UInt32': np.uint32,
            'UInt64': np.uint64,
            'Complex64': np.complex64,
            'Complex128': np.complex128,
            'Bool': np.bool_
        }
    print("  - Added np.typeDict attribute")

# Ensure all h5py related attributes exist
if 'typeDict' in dir(np) and hasattr(np, 'dtype'):
    for dtype_name in dir(np.dtype):
        if dtype_name.startswith('_') or hasattr(np, dtype_name):
            continue
        try:
            attr = getattr(np.dtype, dtype_name)
            setattr(np, dtype_name, attr)
            print(f"  - Added np.{dtype_name} attribute")
        except:
            pass

print("NumPy compatibility patches completed")

# Import TensorFlow after applying patches
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# 在应用补丁后导入TensorFlow
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(f"GPU setting error: {e}")

# 分类模型架构定义
def make_classification_model(input_shape, num_classes=2):
    """
    Same as original training code classification model architecture
    """
    inputs = keras.Input(shape=input_shape)
    x = inputs  # 不使用数据增强
    
    x = tf.keras.layers.Lambda(lambda x: x / 255.0)(x)
    x = layers.Conv2D(8, 3, strides=2, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)
    
    previous_block_activation = x
    
    # 只有一个大小为8的块
    for size in [8]:
        x = layers.Activation("relu")(x)
        x = layers.SeparableConv2D(size, 3, padding="same")(x)
        x = layers.BatchNormalization()(x)
        
        x = layers.Activation("relu")(x)
        x = layers.SeparableConv2D(size, 3, padding="same")(x)
        x = layers.BatchNormalization()(x)
        
        x = layers.MaxPooling2D(3, strides=2, padding="same")(x)
        
        residual = layers.Conv2D(size, 1, strides=2, padding="same")(previous_block_activation)
        
        x = layers.add([x, residual])
        previous_block_activation = x
        
    x = layers.SeparableConv2D(8, 3, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)
    
    x = layers.GlobalAveragePooling2D()(x)
    if num_classes == 2:
        activation = "sigmoid"
        units = 1
    else:
        activation = "softmax"
        units = num_classes
    
    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(units, activation=activation)(x)
    return keras.Model(inputs, outputs, name="model_fire")

# 分割模型架构定义
def make_segmentation_model(img_height, img_width, img_channel=3, num_classes=1):
    """
    Same as original training code segmentation model architecture (small U-Net)
    """
    inputs = keras.Input((img_height, img_width, img_channel))
    s = keras.layers.Lambda(lambda x: x / 255)(inputs)
    
    # 编码器部分 - 比原始模型使用更少的通道数
    c1 = layers.Conv2D(8, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(s)
    c1 = layers.Dropout(0.1)(c1)
    c1 = layers.Conv2D(8, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c1)
    p1 = layers.MaxPooling2D((2, 2))(c1)
    
    c2 = layers.Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p1)
    c2 = layers.Dropout(0.1)(c2)
    c2 = layers.Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c2)
    p2 = layers.MaxPooling2D((2, 2))(c2)
    
    c3 = layers.Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p2)
    c3 = layers.Dropout(0.2)(c3)
    c3 = layers.Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c3)
    p3 = layers.MaxPooling2D((2, 2))(c3)
    
    # 桥接层 - 编码器和解码器之间的连接
    c4 = layers.Conv2D(64, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(p3)
    c4 = layers.Dropout(0.2)(c4)
    c4 = layers.Conv2D(64, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c4)
    
    # 解码器部分 - 上采样和跨连接
    u5 = layers.Conv2DTranspose(32, (2, 2), strides=(2, 2), padding='same')(c4)
    u5 = layers.concatenate([u5, c3])
    c5 = layers.Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u5)
    c5 = layers.Dropout(0.2)(c5)
    c5 = layers.Conv2D(32, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c5)
    
    u6 = layers.Conv2DTranspose(16, (2, 2), strides=(2, 2), padding='same')(c5)
    u6 = layers.concatenate([u6, c2])
    c6 = layers.Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u6)
    c6 = layers.Dropout(0.1)(c6)
    c6 = layers.Conv2D(16, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c6)
    
    u7 = layers.Conv2DTranspose(8, (2, 2), strides=(2, 2), padding='same')(c6)
    u7 = layers.concatenate([u7, c1])
    c7 = layers.Conv2D(8, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(u7)
    c7 = layers.Dropout(0.1)(c7)
    c7 = layers.Conv2D(8, (3, 3), activation='elu', kernel_initializer='he_normal', padding='same')(c7)
    
    # 输出层
    outputs = layers.Conv2D(1, (1, 1), activation='sigmoid')(c7)
    
    model = keras.Model(inputs=[inputs], outputs=[outputs])
    return model

def load_models(mode="both", classification_model_path=None, segmentation_model_path=None):
    """
    Load classification and/or segmentation model, supporting TensorFlow/Keras and YOLOv8 model
    """
    classification_model = None
    segmentation_model = None
    
    # 获取模型路径
    if not classification_model_path:
        classification_model_path = "Output/Checkpoints/classification_1745411231/final_model.h5"
    
    if not segmentation_model_path:
        segmentation_model_path = "Output/Checkpoints/segmentation_1745411231/final_model.h5"
        # 如果没有这个文件，尝试使用最新的segmentation检查点目录
        if not os.path.exists(segmentation_model_path):
            segmentation_dirs = [d for d in os.listdir('Output/Checkpoints') 
                               if d.startswith('segmentation_') and 
                               os.path.isdir(os.path.join('Output/Checkpoints', d))]
            if segmentation_dirs:
                latest_dir = os.path.join('Output/Checkpoints', max(segmentation_dirs))
                seg_files = [f for f in os.listdir(latest_dir) if f.endswith('.h5')]
                if seg_files:
                    if 'final_model.h5' in seg_files:
                        segmentation_model_path = os.path.join(latest_dir, 'final_model.h5')
                    else:
                        # 找最后一个epoch文件
                        epoch_files = sorted([f for f in seg_files if f.startswith('epoch_')])
                        if epoch_files:
                            segmentation_model_path = os.path.join(latest_dir, epoch_files[-1])
    
    # 加载模型 - 检查是否为YOLO模型
    if mode in ["classification", "both"]:
        if os.path.exists(classification_model_path):
            print(f"\nLoading classification model: {classification_model_path}")
            
            # 检查是否是YOLO模型
            is_yolo_model = classification_model_path.lower().endswith('.pt') or 'yolo' in classification_model_path.lower()
            
            if is_yolo_model and YOLO_AVAILABLE:
                try:
                    # 使用YOLO适配器加载模型
                    classification_model = make_yolo_classification_model(classification_model_path)
                    print("YOLOv8 classification model loaded successfully!")
                except Exception as e:
                    print(f"YOLOv8 classification model loading failed: {e}")
                    classification_model = None
            else:
                # 使用传统的TensorFlow/Keras加载方式
                input_shape = (new_size['width'], new_size['height'], 3)
                classification_model = make_classification_model(input_shape=input_shape, num_classes=2)
                try:
                    classification_model.load_weights(classification_model_path)
                    print("Classification model loaded successfully!")
                except Exception as e:
                    print(f"Classification model loading failed: {e}")
                    classification_model = None
        else:
            print(f"Classification model path does not exist: {classification_model_path}")
    
    if mode in ["segmentation", "both"]:
        if os.path.exists(segmentation_model_path):
            print(f"\nLoading segmentation model: {segmentation_model_path}")
            
            # 检查是否是YOLO模型
            is_yolo_model = segmentation_model_path.lower().endswith('.pt') or 'yolo' in segmentation_model_path.lower()
            
            if is_yolo_model and YOLO_AVAILABLE:
                try:
                    # 使用YOLO适配器加载模型
                    segmentation_model = make_yolo_segmentation_model(segmentation_model_path)
                    print("YOLOv8 segmentation model loaded successfully!")
                except Exception as e:
                    print(f"YOLOv8 segmentation model loading failed: {e}")
                    segmentation_model = None
            else:
                # 使用传统的TensorFlow/Keras加载方式
                img_height = segmentation_new_size.get("height")
                img_width = segmentation_new_size.get("width")
                segmentation_model = make_segmentation_model(img_height, img_width, 3, 1)
                try:
                    segmentation_model.load_weights(segmentation_model_path)
                    print("Segmentation model loaded successfully!")
                except Exception as e:
                    print(f"Segmentation model loading failed: {e}")
                    segmentation_model = None
        else:
            print(f"Segmentation model path does not exist: {segmentation_model_path}")
    
    return classification_model, segmentation_model

def process_image(img, classification_model=None, segmentation_model=None, mode="both", 
                 display=True, save_path=None, confidence_threshold=0.5, args=None):
    """
    Process a single image
    
    Args:
        img: Input image
        classification_model: Classification model
        segmentation_model: Segmentation model
        mode: Processing mode ("classification", "segmentation", or "both")
        display: Whether to display results
        save_path: Path to save results
        confidence_threshold: Confidence threshold
        
    Returns:
        Dictionary of processing results
    """
    # Save original image for visualization
    original_img = img.copy()
    
    # Ensure RGB format
    if len(img.shape) == 2:  # Grayscale image
        img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    else:  # Color image
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Classification result
    classification_result = None
    classification_confidence = 0.0
    if classification_model is not None and mode in ["classification", "both"]:
        # Resize for classification
        img_resized = cv2.resize(img_rgb, (new_size.get("width"), new_size.get("height")))
        img_array = np.expand_dims(img_resized / 255.0, axis=0)  # Normalize
        
        # Predict
        predictions = classification_model.predict(img_array, verbose=0)
        confidence = float(predictions[0][0])  # Ensure scalar value
        
        # Translate result - Note: For Binary classification, prediction value is the probability of fire
        if confidence >= confidence_threshold:
            classification_result = "Fire"  # Fire
            class_idx = 1
        else:
            classification_result = "No Fire"
            class_idx = 0
        
        classification_confidence = confidence
    
    # Initialize result image as original image
    result_img = original_img.copy()
    # Initialize segmentation mask and fire percentage
    segmentation_mask = None
    fire_percentage = 0
    
    # Process segmentation (if needed)
    if segmentation_model is not None and mode in ["segmentation", "both"]:
        # Resize for segmentation
        seg_height = segmentation_new_size.get("height")
        seg_width = segmentation_new_size.get("width")
        img_seg_resized = cv2.resize(img_rgb, (seg_width, seg_height))
        img_seg_array = np.expand_dims(img_seg_resized / 255.0, axis=0)  # Normalize
        
        # Predict
        mask_pred = segmentation_model.predict(img_seg_array, verbose=0)
        
        # Process mask - Get probability mask
        prob_mask = mask_pred[0][:,:,0]
        
        # Calculate fire area percentage (using binary mask) - Use configurable segmentation threshold
        # If different segmentation thresholds are provided, use segmentation specific threshold
        segmentation_threshold = args.segmentation_threshold if hasattr(args, 'segmentation_threshold') else confidence_threshold
        binary_mask = (prob_mask > segmentation_threshold).astype(np.uint8)
        fire_percentage = np.mean(binary_mask) * 100
        
        # Improve fire detection logic - Process all images regardless of fire area percentage
        # Apply morphological operations to smooth edges
        kernel = np.ones((5,5), np.uint8)
        smoothed_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)
        smoothed_mask = cv2.morphologyEx(smoothed_mask, cv2.MORPH_CLOSE, kernel)
        
        # Resize back to original size for display
        segmentation_mask = cv2.resize(smoothed_mask, (img.shape[1], img.shape[0]))
        
        # Create multi-layer fire marker effect
        # 1. First create semi-transparent red mask
        fire_mask_colored = np.zeros_like(original_img)
        fire_mask_colored[:,:,2] = segmentation_mask * 255  # Red channel
        
        # 2. Create second layer - More color variation
        heat_mask = cv2.applyColorMap((segmentation_mask * 255).astype(np.uint8), cv2.COLORMAP_JET)
        
        # 3. Mix original image, red mask, and heat map
        alpha1 = 0.5  # Red mask transparency
        alpha2 = 0.3  # Heat map transparency
        
        # First mix original image and red mask
        result_img = cv2.addWeighted(original_img, 1, fire_mask_colored, alpha1, 0)
        
        # Add heat map effect, only in mask area
        for i in range(3):
            heat_mask[:,:,i] = heat_mask[:,:,i] * segmentation_mask
        
        # Mix heat map effect into result image
        result_img = cv2.addWeighted(result_img, 1, heat_mask, alpha2, 0)
        
        # When segmentation detects fire through the logic below, force classification result to fire
        if fire_percentage > 5.0:  # If fire area percentage exceeds threshold
            classification_result = "Fire"  # Fire
            classification_confidence = max(classification_confidence, 0.8)  # Ensure high confidence
            
            # Optimize segmentation mask, apply more morphological operations and filtering
            refined_mask = segmentation_mask.copy()
            
            # Advanced mask refinement option - Can be enabled via command line argument
            use_advanced_refine = args.refine_mask if hasattr(args, 'refine_mask') else False
            
            # Ensure mask values are within 0-255 range
            refined_mask = (refined_mask * 255).astype(np.uint8)
            
            if use_advanced_refine:
                # Enhanced morphological processing
                # 1. First use small core to remove noise points
                small_kernel = np.ones((3, 3), np.uint8)
                refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_OPEN, small_kernel)
                
                # 2. Apply adaptive threshold to get more accurate segmentation
                refined_mask = cv2.adaptiveThreshold(
                    refined_mask, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, -2
                )
                
                # 3. Use medium core for opening operation, remove small noise points
                medium_kernel = np.ones((5, 5), np.uint8)
                refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_OPEN, medium_kernel)
                
                # 4. Use large core for closing operation, fill small holes
                large_kernel = np.ones((9, 9), np.uint8)
                refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_CLOSE, large_kernel)
                
                # 5. Edge buffering and smoothing
                refined_mask = cv2.GaussianBlur(refined_mask, (9, 9), 0)
                _, refined_mask = cv2.threshold(refined_mask, 127, 255, cv2.THRESH_BINARY)
            else:
                # Standard morphological processing
                # Use large core for opening operation, remove small noise points
                kernel_open = np.ones((7, 7), np.uint8)
                refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_OPEN, kernel_open)
                
                # Use closing operation to fill small holes in fire area
                kernel_close = np.ones((15, 15), np.uint8)
                refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_CLOSE, kernel_close)
            
            # Only keep foreground determined area
            _, strong_mask = cv2.threshold(refined_mask, 100, 255, cv2.THRESH_BINARY)
            
            # Find fire area boundary box (using refined mask)
            contours, _ = cv2.findContours(strong_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Draw contour itself on image - Use more precise contour effect
            # Draw contour lines - Use different line colors and widths
            # First draw a white contour with a wider line as base color
            cv2.drawContours(result_img, contours, -1, (255, 255, 255), 3)
            # Then draw a tight red contour
            cv2.drawContours(result_img, contours, -1, (0, 0, 255), 2)
            
            # Set boundary box minimum area and ratio threshold, filter out unreasonable areas
            # Use configurable minimum area
            min_contour_area = args.min_area if hasattr(args, 'min_area') else 500
            min_height = 20  # Minimum height
            max_aspect_ratio = 10.0  # Maximum aspect ratio
            
            # Store valid boundary boxes
            valid_boxes = []
            
            # Draw boundary box
            for contour in contours:
                area = cv2.contourArea(contour)
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / max(h, 1)  # Avoid division by zero
                
                # Filter out unreasonable boxes (too small, too flat, touching image edge)
                if (area > min_contour_area and 
                    h > min_height and 
                    aspect_ratio < max_aspect_ratio and
                    y > 0 and y+h < img.shape[0]-5):  # Not touching image top and bottom
                    
                    # Save valid boundary box
                    valid_boxes.append((x, y, w, h, area))
            
            # Draw validated boundary box on image - Use more professional visual effect
            for x, y, w, h, area in valid_boxes:
                # First draw a boundary box with double border - Yellow outer, Red inner
                # Outer border - Yellow thick border, Solid
                cv2.rectangle(result_img, (x-1, y-1), (x+w+1, y+h+1), (0, 255, 255), 3)
                # Inner border - Red thin border
                cv2.rectangle(result_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
                
                # Add semi-transparent background rectangle, make text easier to read
                # If it's a large fire area, add special mark
                if area > 5000:
                    # Add yellow background rectangle
                    label_bg = np.zeros((25, 180, 3), dtype=np.uint8)
                    label_bg[:,:] = (0, 200, 255)  # Yellow background
                    label_bg_resized = cv2.resize(label_bg, (max(w, 180), 25))
                    
                    # Calculate text label position
                    label_y = max(0, y-30)
                    label_x = x
                    
                    # Avoid exceeding image boundary
                    if label_y + 25 > result_img.shape[0]:
                        label_y = result_img.shape[0] - 25
                    if label_x + label_bg_resized.shape[1] > result_img.shape[1]:
                        label_x = result_img.shape[1] - label_bg_resized.shape[1]
                    
                    # Add semi-transparent background
                    roi = result_img[label_y:label_y+25, label_x:label_x+label_bg_resized.shape[1]]
                    result_img[label_y:label_y+25, label_x:label_x+label_bg_resized.shape[1]] = \
                        cv2.addWeighted(roi, 0.3, label_bg_resized, 0.7, 0)
                    
                    # Add text - Large fire area
                    area_text = f"Large Fire Area: {area:.0f}px"
                    cv2.putText(result_img, area_text, (label_x+5, label_y+18),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
                else:
                    # Simple annotation for small area
                    area_text = f"Fire: {area:.0f}px"
                    # Add text outline, make text easier to read
                    cv2.putText(result_img, area_text, (x+2, y-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)  # Black outline
                    cv2.putText(result_img, area_text, (x+2, y-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)  # Yellow text
                            
                # When boundary box is detected, ensure classification is fire
                classification_result = "Fire"  # Force set to fire
                classification_confidence = max(classification_confidence, 0.9)  # Ensure high confidence
                
            # Regardless of segmentation model result, try direct fire detection based on color
            # Use more relaxed detection conditions, perform color detection for all images
            # Try color-based detection (Red/Orange/Yellow area)
            img_rgb = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
            hsv = cv2.cvtColor(original_img, cv2.COLOR_BGR2HSV)
            
            # Expand HSV range to cover more fire colors
            # Red-Orange range
            lower_red1 = np.array([0, 50, 50])   # Lower saturation and brightness threshold
            upper_red1 = np.array([20, 255, 255])
            # Yellow range
            lower_yellow = np.array([20, 50, 50])
            upper_yellow = np.array([40, 255, 255])
            # Red other end (Covering loop characteristics of HSV color space)
            lower_red2 = np.array([160, 50, 50])
            upper_red2 = np.array([180, 255, 255])
            
            # Create different color range masks
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)    # Red-Orange
            mask2 = cv2.inRange(hsv, lower_yellow, upper_yellow) # Yellow
            mask3 = cv2.inRange(hsv, lower_red2, upper_red2)    # Red (other side)
            
            # Combine all color masks
            fire_color_mask = cv2.bitwise_or(cv2.bitwise_or(mask1, mask2), mask3)
            
            # Apply morphological operations to optimize mask
            # First use opening operation to remove noise points
            kernel_open = np.ones((7, 7), np.uint8)
            fire_color_mask = cv2.morphologyEx(fire_color_mask, cv2.MORPH_OPEN, kernel_open)
            
            # Then use closing operation to connect adjacent areas
            kernel_close = np.ones((15, 15), np.uint8)
            fire_color_mask = cv2.morphologyEx(fire_color_mask, cv2.MORPH_CLOSE, kernel_close)
            
            # If color-based fire detection finds fire area, simply mark it on image
            if np.sum(fire_color_mask) > 0:
                # Find all contours
                contours, _ = cv2.findContours(fire_color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Process larger contours
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > 100:  # Only mark large areas
                        # Draw contour - Use red to increase visibility
                        cv2.drawContours(result_img, [contour], -1, (0, 0, 255), 2)
                        
                        # If large fire area is detected, ensure classification result is fire
                        if area > 1000:
                            classification_result = "Fire"  # Force set to fire
                            classification_confidence = max(classification_confidence, 0.85)
            
            # Find color-based contours
            color_contours, _ = cv2.findContours(fire_color_mask, 
                                             cv2.RETR_EXTERNAL, 
                                             cv2.CHAIN_APPROX_SIMPLE)
            
            # Set lower area threshold, adapt to wildfire scenario
            min_fire_area = 200  # Lower threshold, easier to detect fire
            
            # Draw all qualified boundary boxes
            for contour in color_contours:
                area = cv2.contourArea(contour)
                if area > min_fire_area:  # Lower area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Filter or merge small boundary boxes
                    if w < 20 or h < 20:
                        continue
                        
                    # Filter horizontal strip at bottom of image (possibly false detection)
                    if h < 30 and y > img.shape[0] * 0.8:
                        continue
                    
                    # Draw red boundary box representing fire area
                    cv2.rectangle(result_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    cv2.putText(result_img, f"Fire: {area:.0f}px", (x, y-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                    
            # Additional feature: Try to detect large fire area
            # For wildfire scale that's relatively large, we try to identify larger area
            if len(color_contours) > 0:
                # Find largest contour
                max_contour = max(color_contours, key=cv2.contourArea)
                max_area = cv2.contourArea(max_contour)
                
                # If largest contour is large enough, mark entire area as fire area
                if max_area > 1000:  # Set higher threshold
                    # Get geometric center of all areas in image
                    M = cv2.moments(max_contour)
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])
                        
                        # Add "Large Fire Area" label at center position
                        cv2.putText(result_img, f"Large Fire Area: {max_area:.0f}px", 
                                    (cX-100, cY), cv2.FONT_HERSHEY_SIMPLEX, 
                                    1.0, (0, 165, 255), 2, cv2.LINE_AA)
                    
    # Add classification result text    # Add classification and fire area information to image - Use more professional design
    if classification_result is not None:
        # Classification result - Add transparent background bar
        label_en = "Fire" if classification_result == "Fire" else "No Fire"
        # Create semi-transparent background bar
        bg_height = 40
        bg_width = 350
        overlay = result_img[0:bg_height, 0:bg_width].copy()
        # Choose color based on classification result
        if classification_result == "Fire":
            bg_color = (0, 0, 180)  # Red background bar
            text_color = (255, 255, 255)  # White text
        else:
            bg_color = (0, 180, 0)  # Green background bar
            text_color = (255, 255, 255)  # White text
            
        # Fill background bar
        cv2.rectangle(result_img, (0, 0), (bg_width, bg_height), bg_color, -1)
        # Add semi-transparent effect
        alpha = 0.7
        cv2.addWeighted(overlay, 1-alpha, result_img[0:bg_height, 0:bg_width], alpha, 0, result_img[0:bg_height, 0:bg_width])
        
        # Add text information - Use larger and clearer font
        text = f"Class: {label_en} (conf: {classification_confidence:.2f})"
        cv2.putText(result_img, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                    1.0, text_color, 2, cv2.LINE_AA)
        
        # Add fire area percentage information (if fire detected) - Use more professional display effect
        if fire_percentage > 0:
            # Add semi-transparent background for fire area percentage
            bg_height = 35
            bg_width = 220
            bg_top = 45
            overlay = result_img[bg_top:bg_top+bg_height, 0:bg_width].copy()
            # Add background bar
            cv2.rectangle(result_img, (0, bg_top), (bg_width, bg_top+bg_height), (0, 0, 180), -1)
            # Semi-transparent effect
            alpha = 0.7
            cv2.addWeighted(overlay, 1-alpha, result_img[bg_top:bg_top+bg_height, 0:bg_width], alpha, 0, 
                           result_img[bg_top:bg_top+bg_height, 0:bg_width])
            
            # Add text - Copy font effect to enhance readability
            fire_area_text = f"Fire area: {fire_percentage:.1f}%"
            # First draw black outline
            cv2.putText(result_img, fire_area_text, (12, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 3, cv2.LINE_AA)
            # Then draw main color
            cv2.putText(result_img, fire_area_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
                    
    
    # Display result
    if display:
        cv2.imshow("Fire Detection Result", result_img)
        cv2.waitKey(1)  # Brief display
    
    # Save result (if path provided)
    if save_path:
        cv2.imwrite(save_path, result_img)
        print(f"\nSaved processed result to: {save_path}")
        
    # Return dictionary containing results
    return {
        "classification": classification_result,
        "confidence": classification_confidence,
        "mask": segmentation_mask,
        "fire_percentage": fire_percentage,
        "processed_image": result_img  # Ensure returned processed image, containing all marks and boxes
    }

# Create a video display window class, simple and reliable, supporting real-time video display
class VideoDisplay:
    def __init__(self, window_name="Fire Detection Video", display_interval=1):
        """Initialize video display window
        
        Args:
            window_name (string): Window title
            display_interval (integer): Display every how many frames (default 1, can increase for performance)
        """
        self.window_name = window_name
        self.display_interval = display_interval
        self.frame_count = 0
        self.window_created = False
        self.last_time = time.time()
        self.fps_counter = 0
        self.fps = 0
        
        # Check OpenCV GUI support
        try:
            # Initialize window
            test_img = np.zeros((50, 200, 3), dtype=np.uint8)
            # Write "Loading..." text (Using English to avoid font issue)
            cv2.putText(test_img, "Loading...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.imshow(self.window_name, test_img)
            cv2.waitKey(1)
            self.window_created = True
        except Exception as e:
            print(f"\nWarning: Unable to create display window ({str(e)})")
            print("Video will still process, but unable to display real-time preview")
            # Platform compatibility hint
            if sys.platform == 'win32': 
                print("Hint: On Windows you may need to install 'opencv-python-headless' package then reinstall 'opencv-python'")
            else:
                print("Hint: On Linux you may need to install GTK or QT support library")
    
    def update(self, frame, info=None):
        """Update and display video frame
        
        Args:
            frame (numpy.ndarray): Video frame to display
            info (string): Optional information text, will be displayed on frame
        
        Returns:
            bool: Whether to terminate playback (if user presses q key)
        """
        if not self.window_created:
            return False
        
        self.frame_count += 1
        
        # Calculate FPS
        self.fps_counter += 1
        current_time = time.time()
        time_diff = current_time - self.last_time
        
        # Update FPS every second
        if time_diff >= 1.0:
            self.fps = self.fps_counter / time_diff
            self.fps_counter = 0
            self.last_time = current_time
        
        # Only display specified interval frames, can improve performance
        if self.frame_count % self.display_interval == 0:
            # Create copy of display frame
            display_frame = frame.copy()
            
            # Display frame number and FPS
            cv2.putText(display_frame, f"Frame: {self.frame_count} | FPS: {self.fps:.1f}", 
                      (10, display_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                      0.5, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Display extra information (if any)
            if info:
                cv2.putText(display_frame, info, 
                          (10, display_frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 
                          0.5, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Display frame
            cv2.imshow(self.window_name, display_frame)
            
            # 捕获键盘输入 (按q退出)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                return True  # 告诉调用者退出
        
        return False
    
    def close(self):
        """关闭显示窗口"""
        if self.window_created:
            try:
                cv2.destroyWindow(self.window_name)
                cv2.waitKey(1)  # 强制刷新以确保窗口关闭
            except Exception:
                pass  # 忽略关闭错误

def process_video(video_path, output_path=None, classification_model=None, segmentation_model=None, 
                 mode="both", display=True, confidence_threshold=0.5, save_interval=1, save_frames=False, frames_dir=None, 
                 display_interval=1, args=None):
    """
    处理视频文件
    """
    # 检查文件是否存在
    if not os.path.exists(video_path):
        print(f"\n错误: 视频文件不存在: {video_path}")
        return
        
    # 创建视频显示窗口（如果需要）
    video_display = None
    if display:
        video_display = VideoDisplay(window_name=f"火灾检测: {os.path.basename(video_path)}",
                                  display_interval=display_interval)
        
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"无法打开视频: {video_path}")
        return
    
    # 获取视频属性
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"\n处理视频: {video_path}")
    print(f"分辨率: {width}x{height}, FPS: {fps}, 总帧数: {total_frames}")
    
    # 准备输出视频
    out = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 或尝试 'XVID'
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 处理进度条
    time_start = time.time()
    frame_count = 0
    
    # 创建保存帧的目录
    if save_frames:
        if frames_dir is None:
            frames_dir = os.path.splitext(output_path)[0] + "_frames"
        os.makedirs(frames_dir, exist_ok=True)
        print(f"\n将保存处理后的帧到: {frames_dir}")
    
    try:
        with tqdm(total=total_frames, desc="处理视频", unit="帧") as pbar:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 每隔save_interval帧处理一次
                if frame_count % save_interval == 0:
                    # 处理当前帧 - 传递命令行参数
                    results = process_image(
                        frame, 
                        classification_model=classification_model,
                        segmentation_model=segmentation_model,
                        mode=mode,
                        display=display,
                        confidence_threshold=args.confidence_threshold if hasattr(args, 'confidence_threshold') else 0.5,
                        args=args  # 传递所有参数给处理函数
                    )
                    
                    # 使用process_image函数返回的处理后图像作为输出帧
                    # 这个图像已经包含了所有的检测框、标记和火灾区域
                    output_frame = results["processed_image"]
                    
                    # 显示处理后的帧
                    if display:
                        # 显示处理后的帧（如果需要）
                        if display and video_display:
                            # 生成信息文本用于视频显示
                            info_text = ""
                            if results["classification"] is not None:
                                label = "Fire" if results["classification"] == "火灾" else "No Fire"
                                info_text += f"Class: {label} ({results['confidence']:.2f}) | "
                            if results["fire_percentage"] > 0:
                                info_text += f"Fire area: {results['fire_percentage']:.1f}%"
                            
                            # 更新视频显示窗口，如果用户按了q则退出
                            if video_display.update(output_frame, info_text):
                                print("\n用户按键退出视频播放")
                                break
                            
                            # 每20帧显示当前进度
                            if frame_count % 20 == 0:
                                progress_pct = (frame_count / total_frames) * 100
                                print(f"\r处理进度: {progress_pct:.1f}% ({frame_count}/{total_frames})", end="")
                    
                    # 写入输出视频
                    if out:
                        out.write(output_frame)
                    
                    # 保存当前帧图像
                    if save_frames:
                        frame_filename = os.path.join(frames_dir, f"frame_{frame_count:06d}.jpg")
                        cv2.imwrite(frame_filename, output_frame)
                        
                        # 每10帧或每秒打印一次处理信息
                        if frame_count % 10 == 0:
                            classification_info = ""
                            if results["classification"] is not None:
                                # 报告中使用中文输出
                                label_en = "Fire" if results["classification"] == "火灾" else "No Fire"
                                classification_info = f"分类: {label_en}, 置信度: {results['confidence']:.2f}"
                            
                            segmentation_info = ""
                            if results["mask"] is not None:
                                segmentation_info = f"火灾区域: {results['fire_percentage']:.1f}%"
                                
                            print(f"帧 #{frame_count}: {classification_info} {segmentation_info}")
                
                frame_count += 1
                pbar.update(1)
                
                # 每100帧更新一次进度信息
                if frame_count % 100 == 0:
                    elapsed_time = time.time() - time_start
                    frames_remaining = total_frames - frame_count
                    if frame_count > 0:
                        time_per_frame = elapsed_time / frame_count
                        est_time_remaining = frames_remaining * time_per_frame
                        pbar.set_postfix({
                            "处理速度": f"{1/time_per_frame:.1f} fps",
                            "剩余时间": f"{est_time_remaining/60:.1f} 分钟"
                        })
    
    finally:
        # 清理资源
        cap.release()
        if out:
            out.release()  # 正确关闭视频写入器
        
        # 关闭视频显示窗口
        if display and video_display:
            video_display.close()
    
    print(f"\n视频处理完成，总计 {frame_count} 帧")
    if output_path:
        print(f"已保存处理后的视频到: {output_path}")

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='火灾检测工具 - 支持图像和视频分析')
    parser.add_argument('--input', type=str, help='输入图像或视频路径')
    parser.add_argument('--output', type=str, help='输出文件路径（可选）')
    parser.add_argument('--mode', type=str, default='both', 
                     choices=['classification', 'segmentation', 'both'],
                     help='检测模式: classification, segmentation, 或 both (默认)')
    parser.add_argument('--display', action='store_true', help='显示处理结果')
    parser.add_argument('--save_interval', type=int, default=1, help='视频处理保存间隔')
    parser.add_argument('--save_frames', action='store_true', help='是否保存视频帧图像')
    
    # 新增参数：用于模型路径和阈值控制
    parser.add_argument('--classification_model', type=str, help='分类模型路径（可选）')
    parser.add_argument('--segmentation_model', type=str, help='分割模型路径（可选）')
    parser.add_argument('--confidence_threshold', type=float, default=0.5, 
                      help='置信度阈值（默认0.5），控制检测的灵敏度')
    parser.add_argument('--segmentation_threshold', type=float, default=0.5,
                      help='分割模型阈值（默认0.5），控制分割效果的精确度')
    parser.add_argument('--min_area', type=int, default=500,
                      help='最小火灾区域面积（像素），过滤小噪点（默认500）')
    parser.add_argument('--refine_mask', action='store_true', 
                      help='开启增强版掩码精化，可提高检测准确度')
    parser.add_argument('--use_yolo', action='store_true',
                      help='优先使用YOLOv8模型，如果存在')
    args = parser.parse_args()
    
    # 检查输入是图像还是视频
    input_path = args.input
    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在: {input_path}")
        return
    
    # 加载模型
    print("加载模型...")
    classification_model, segmentation_model = load_models(
        mode=args.mode,
        classification_model_path=args.classification_model,
        segmentation_model_path=args.segmentation_model
    )
    
    # 确定输入类型并处理
    is_video = input_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv'))
    
    if is_video:
        # 处理视频
        output_path = args.output if args.output else os.path.splitext(input_path)[0] + "_processed.mp4"
        process_video(
            input_path,
            output_path=args.output,
            classification_model=classification_model,
            segmentation_model=segmentation_model,
            mode=args.mode,
            display=getattr(args, 'display', True),
            confidence_threshold=getattr(args, 'confidence_threshold', 0.5),
            save_interval=getattr(args, 'save_interval', 1),
            save_frames=getattr(args, 'save_frames', False),
            frames_dir=getattr(args, 'frames_dir', None),
            display_interval=getattr(args, 'display_interval', 1),
            args=args
        )
    else:
        # 处理图像
        img = cv2.imread(input_path)
        if img is None:
            print(f"错误: 无法读取图像: {input_path}")
            return
            
        process_image(
            img, 
            classification_model=classification_model,
            segmentation_model=segmentation_model,
            mode=args.mode,
            display=not getattr(args, 'no_display', False),
            save_path=args.output,
            confidence_threshold=getattr(args, 'confidence_threshold', 0.5),
            args=args
        )
        
        # 视频处理完成后显示
        print("\n处理完成!")
        
        if output_path:
            print(f"结果已保存到: {output_path}")

if __name__ == "__main__":
    main()
