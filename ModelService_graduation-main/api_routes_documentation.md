# API路由文档

## 系统概述

本文档描述了智能路径规划与目标追踪系统的所有API路由，包含FastAPI和Django部分。系统端口配置如下：
- Vue前端：8082端口
- FastAPI后端：10000端口 (之前使用8001端口)

## FastAPI 路由

### 核心服务路由

| 前端路径 | API路由前缀 | 描述 | 主要功能 |
|---------|------------|------|---------|
| `/` | `/api` | 首页 | 系统信息和健康检查 |
| `/route-planning` | `/api/route` | 路径规划 | 智能路径规划和优化 |
| `/route-records` | `/api/route` | 路径记录 | 历史路径数据查询和展示 |
| `/image-recognition` | `/api/image-recognition` | 图像识别 | 处理图像并进行目标检测 |
| `/video-tracking` | `/api/video-tracking` | 视频追踪 | 视频中的目标追踪与分析 |
| `/knowledge-base-chat` | `/api/knowledge-chat` | 知识库聊天 | 基于知识库的智能对话 |
| `/night-detection` | `/api/night-detection` | 夜间检测 | 低光图像增强与目标检测 |
| `/rgbt-detection` | `/api/rgbt-detection` | RGBT检测 | 可见光-热微小物体检测 |
| `/plate-recognition` | `/api/plate-recognition` | 车牌识别 | 车牌识别与分析 |
| `/test-fusion` | `/api/test` | 测试融合 | 测试各模块功能融合 |

### 详细API端点

#### 1. 车牌识别服务 (`/api/plate-recognition`)

| 方法 | 路径 | 功能描述 | 参数 |
|-----|------|---------|------|
| GET | `/status` | 检查车牌识别服务状态 | 无 |
| POST | `/upload-image` | 上传图片进行车牌识别 | `file`: 图片文件 |
| POST | `/upload-video` | 上传视频进行车牌识别 | `file`: 视频文件 |
| GET | `/uploaded_file/{filename}` | 获取上传的原始文件 | `filename`: 文件名 |
| GET | `/processed_file/{filename}` | 获取处理后的文件 | `filename`: 文件名 |
| GET | `/video_process_status/{process_id}` | 获取视频处理状态 | `process_id`: 处理ID |
| GET | `/video_results/{process_id}` | 获取视频处理结果 | `process_id`: 处理ID |

#### 2. 路径规划服务 (`/api/route`)

| 方法 | 路径 | 功能描述 | 参数 |
|-----|------|---------|------|
| POST | `/plan` | 规划最优路径 | `start`: 起点, `end`: 终点, `params`: 规划参数 |
| GET | `/history` | 获取历史路径 | `limit`: 数量限制 |
| GET | `/history/{record_id}` | 获取特定历史路径 | `record_id`: 记录ID |
| POST | `/save` | 保存路径记录 | `route`: 路径数据, `metadata`: 元数据 |

#### 3. 图像识别服务 (`/api/image-recognition`)

| 方法 | 路径 | 功能描述 | 参数 |
|-----|------|---------|------|
| POST | `/analyze` | 分析图像 | `file`: 图片文件, `mode`: 分析模式 |
| GET | `/models` | 获取可用模型列表 | 无 |

#### 4. 视频追踪服务 (`/api/video-tracking`)

| 方法 | 路径 | 功能描述 | 参数 |
|-----|------|---------|------|
| POST | `/upload` | 上传视频进行追踪 | `file`: 视频文件, `params`: 追踪参数 |
| GET | `/status/{job_id}` | 获取追踪任务状态 | `job_id`: 任务ID |
| GET | `/result/{job_id}` | 获取追踪结果 | `job_id`: 任务ID |

#### 5. 知识库聊天服务 (`/api/knowledge-chat`)

| 方法 | 路径 | 功能描述 | 参数 |
|-----|------|---------|------|
| POST | `/query` | 提交聊天查询 | `query`: 问题, `history`: 历史对话 |
| GET | `/knowledge-sources` | 获取知识来源列表 | 无 |

#### 6. 夜间检测服务 (`/api/night-detection`)

| 方法 | 路径 | 功能描述 | 参数 |
|-----|------|---------|------|
| POST | `/enhance` | 增强夜间图像 | `file`: 图片文件 |
| POST | `/detect` | 夜间图像目标检测 | `file`: 图片文件, `mode`: 检测模式 |

#### 7. RGBT检测服务 (`/api/rgbt-detection`)

| 方法 | 路径 | 功能描述 | 参数 |
|-----|------|---------|------|
| POST | `/detect` | RGBT微小物体检测 | `visible`: 可见光图像, `thermal`: 热成像图像 |
| POST | `/fuse` | 融合可见光与热成像 | `visible`: 可见光图像, `thermal`: 热成像图像 |

#### 8. 系统服务 (`/api`)

| 方法 | 路径 | 功能描述 | 参数 |
|-----|------|---------|------|
| GET | `/` | 获取系统基本信息 | 无 |
| GET | `/health` | 系统健康检查 | 无 |

## Django 路由

在迁移或集成Django后端时，应保持相同的API路径结构，以确保前端无需大幅修改。建议的Django URL配置模式如下：

```python
# Django项目中的urls.py
from django.urls import path, include

urlpatterns = [
    # 核心API路由
    path('api/plate-recognition/', include('plate_recognition.urls')),
    path('api/route/', include('route_planning.urls')),
    path('api/image-recognition/', include('image_recognition.urls')),
    path('api/video-tracking/', include('video_tracking.urls')),
    path('api/knowledge-chat/', include('knowledge_chat.urls')),
    path('api/night-detection/', include('night_detection.urls')),
    path('api/rgbt-detection/', include('rgbt_detection.urls')),
    path('api/test/', include('test_fusion.urls')),
    
    # 系统API
    path('api/', include('system_api.urls')),
]
```

### 示例: 车牌识别Django应用的urls.py

```python
# plate_recognition/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.status, name='plate_recognition_status'),
    path('upload-image/', views.upload_image, name='plate_recognition_upload_image'),
    path('upload-video/', views.upload_video, name='plate_recognition_upload_video'),
    path('uploaded_file/<str:filename>/', views.get_uploaded_file, name='plate_recognition_uploaded_file'),
    path('processed_file/<str:filename>/', views.get_processed_file, name='plate_recognition_processed_file'),
    path('video_process_status/<str:process_id>/', views.video_process_status, name='plate_recognition_video_process_status'),
    path('video_results/<str:process_id>/', views.video_results, name='plate_recognition_video_results'),
]
```

## 端口和CORS配置

### FastAPI CORS配置
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8082", "http://127.0.0.1:8082", "http://localhost:8081", "http://127.0.0.1:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Django CORS配置
```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8082",
    "http://127.0.0.1:8082",
    "http://localhost:8081", 
    "http://127.0.0.1:8081",
]
CORS_ALLOW_CREDENTIALS = True
```
