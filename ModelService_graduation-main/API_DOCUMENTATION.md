# ModelService API 文档

## 概述

本文档提供了ModelService统一平台的API接口说明。所有API都通过同一个FastAPI后端服务提供，基本URL为 `http://localhost:8000`。

## 目录

1. [通用约定](#通用约定)
2. [夜间车辆检测](#夜间车辆检测)
3. [RGBT图像融合](#rgbt图像融合)
4. [火灾检测](#火灾检测)
5. [车牌识别](#车牌识别)
6. [视频追踪](#视频追踪)

## 通用约定

- 所有API路径前缀均为`/api`
- 图像上传API均接受`multipart/form-data`格式的请求
- 响应格式为JSON，包含统一的成功/失败状态字段
- 图像结果通过专门的端点提供访问

## 夜间车辆检测

### 增强夜间低光图像

**端点**: `POST /api/night-detection/enhance`

**描述**: 对夜间低光环境下的图像进行增强处理，提高可见性

**请求参数**:
- `file`: 要增强的图像文件 (必需)
- `method`: 增强方法，可选值为"clahe", "denoise", "gamma", "contrast", "night_vision", "combined" (可选，默认为"combined")

**响应**:
```json
{
  "success": true,
  "enhanced_image_url": "/api/night-detection/result/enhanced_20250430_123456.jpg",
  "processing_time": 0.45
}
```

### 检测夜间车辆

**端点**: `POST /api/night-detection/detect`

**描述**: 检测夜间图像中的车辆

**请求参数**:
- `file`: 要检测的图像文件 (必需)
- `enhance`: 是否先进行图像增强，可选值为"true"或"false" (可选，默认为"true")
- `confidence`: 检测置信度阈值，0.0-1.0之间 (可选，默认为0.25)

**响应**:
```json
{
  "success": true,
  "detections": [
    {
      "class": "car",
      "confidence": 0.89,
      "bbox": [120, 150, 320, 280]
    },
    {
      "class": "truck",
      "confidence": 0.76,
      "bbox": [450, 200, 600, 350]
    }
  ],
  "detection_image_url": "/api/night-detection/result/detection_20250430_123456.jpg",
  "processing_time": 0.67
}
```

## RGBT图像融合

### 融合可见光与热成像图像

**端点**: `POST /api/rgbt-detection/fusion`

**描述**: 融合可见光图像和热成像图像

**请求参数**:
- `rgb_file`: 可见光图像文件 (必需)
- `thermal_file`: 热成像图像文件 (必需)
- `method`: 融合方法，可选值为"average", "wavelet", "guided", "mask" (可选，默认为"guided")

**响应**:
```json
{
  "success": true,
  "fusion_image_url": "/api/rgbt-detection/result/fusion_20250430_123456.jpg",
  "processing_time": 0.56
}
```

## 火灾检测

### 检测火灾

**端点**: `POST /api/fire-detection/detect`

**描述**: 检测图像中的火灾

**请求参数**:
- `file`: 要检测的图像文件 (必需)
- `mode`: 检测模式，可选值为"classification", "segmentation", "both" (可选，默认为"both")
- `threshold`: 检测置信度阈值，0.0-1.0之间 (可选，默认为0.5)

**响应**:
```json
{
  "fire_detected": true,
  "confidence": 0.92,
  "processing_time": 0.78,
  "result_image_path": "fire_detection_uuid4.jpg",
  "mask_image_path": "fire_detection_uuid4_mask.jpg"
}
```

### 获取结果图像

**端点**: `GET /api/fire-detection/result/{image_name}`

**描述**: 获取火灾检测的结果图像

**请求参数**:
- `image_name`: 图像文件名，由检测API返回

**响应**: 图像文件

## 车牌识别

### 识别车牌

**端点**: `POST /api/plate-recognition/recognize`

**描述**: 识别图像中的车牌

**请求参数**:
- `file`: 要识别的图像文件 (必需)
- `return_image`: 是否返回带标注的图像，可选值为"true"或"false" (可选，默认为"true")

**响应**:
```json
{
  "success": true,
  "plate_text": "京A12345",
  "plate_color": "蓝色",
  "confidence": 0.95,
  "plate_coords": [100, 200, 300, 250],
  "result_image_url": "/api/plate-recognition/result/plate_20250430_123456.jpg",
  "processing_time": 0.34
}
```

## 视频追踪

### 创建追踪会话

**端点**: `POST /api/video-tracking/create-session`

**描述**: 创建新的视频追踪会话

**请求参数**:
- `tracker_type`: 追踪器类型，可选值为"KCF", "CSRT", "MOSSE", "MIL", "MedianFlow" (可选，默认为"KCF")

**响应**:
```json
{
  "success": true,
  "session_id": "d8e8fca2-dc0f-4cf8-ae10-7850f8eb1500",
  "status": "initialized"
}
```

### 上传视频

**端点**: `POST /api/video-tracking/upload-video/{session_id}`

**描述**: 上传视频到指定会话

**请求参数**:
- `session_id`: 会话ID (路径参数)
- `file`: 视频文件 (必需)

**响应**:
```json
{
  "success": true,
  "video_info": {
    "width": 1280,
    "height": 720,
    "fps": 30,
    "frame_count": 450
  }
}
```

### 添加追踪目标

**端点**: `POST /api/video-tracking/add-target/{session_id}`

**描述**: 添加追踪目标

**请求参数**:
- `session_id`: 会话ID (路径参数)
- `frame_id`: 帧ID (必需)
- `bbox`: 目标边界框，格式为"x,y,w,h" (必需)
- `class`: 目标类别 (可选)

**响应**:
```json
{
  "success": true,
  "track_id": 1,
  "target_class": "person"
}
```

### 开始追踪

**端点**: `POST /api/video-tracking/start/{session_id}`

**描述**: 开始追踪

**请求参数**:
- `session_id`: 会话ID (路径参数)

**响应**:
```json
{
  "success": true,
  "status": "tracking",
  "message": "追踪已开始"
}
```

### 获取追踪结果

**端点**: `GET /api/video-tracking/results/{session_id}`

**描述**: 获取追踪结果

**请求参数**:
- `session_id`: 会话ID (路径参数)

**响应**:
```json
{
  "success": true,
  "status": "completed",
  "targets": [
    {
      "track_id": 1,
      "class": "person",
      "frames": 450,
      "confidence": 0.92
    }
  ],
  "result_video_url": "/api/video-tracking/result/tracking_20250430_123456.mp4"
}
```

## 启动指南

### 启动统一服务

1. 克隆项目仓库:
```bash
git clone https://github.com/your-username/ModelService_graduation.git
cd ModelService_graduation
```

2. 安装依赖:
```bash
pip install -r comprehensive_requirements.txt
```

3. 启动服务:
```bash
python start_service.py
```

对于开发环境，可以启用热重载:
```bash
python start_service.py --reload
```

默认情况下，服务将在 `http://localhost:8000` 启动。可以通过以下方式更改主机和端口:
```bash
python start_service.py --host 127.0.0.1 --port 8080
```

4. 访问API文档:
```
http://localhost:8000/api/docs
```

## 前端使用说明

前端应用会自动连接到后端API服务。访问前端需要:

1. 进入前端目录:
```bash
cd ModelService/Vue
```

2. 安装依赖:
```bash
npm install
```

3. 启动开发服务器:
```bash
npm run dev
```

4. 在浏览器中访问:
```
http://localhost:5173
```
