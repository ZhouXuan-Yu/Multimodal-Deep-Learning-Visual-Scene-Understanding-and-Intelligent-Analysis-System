# ModelService 前端路由接口总览

## 1. 系统架构概述

ModelService前端基于Vue3框架开发，使用Vite作为构建工具，采用模块化设计。前端统一运行在8080端口，后端服务运行在8081端口。系统主要功能包括：
- 路径规划与优化
- 图像分析与识别
- 视频目标跟踪
- 车牌识别系统
- 知识库聊天功能
- 夜间低光图像增强与检测
- 可见光-热红外融合检测
- 火灾检测与监控

前端通过RESTful API与后端服务通信，所有API请求通过'/api'前缀路由到后端服务。

## 2. 页面路由配置

### 页面路由表

| 路由路径 | 名称 | 组件 | 描述 |
|----------|------|------|------|
| / | home | HomeView | 首页，提供系统概览和功能导航 |
| /route-planning | route-planning | RoutePlanningView | 路径规划功能，提供智能路线规划 |
| /route-records | route-records | RouteRecordsView | 路径记录，查看历史规划路径 |
| /image-recognition | image-recognition | ImageRecognitionView | 图像识别功能，支持多种目标检测 |
| /video-tracking | video-tracking | VideoTrackingView | 视频跟踪功能，实时跟踪视频中的目标 |
| /knowledge-base-chat | knowledge-base-chat | KnowledgeBaseChatView | 知识库聊天功能，智能问答系统 |
| /night-detection | night-detection | NightDetectionView | 夜间低光图像增强与检测功能 |
| /rgbt-detection | rgbt-detection | RGBTDetectionView | 可见光-热红外融合检测功能 |
| /test-fusion | test-fusion | TestFusionView | 融合测试页面，用于测试多模态融合 |
| /plate-recognition | plate-recognition | PlateRecognitionView | 车牌识别功能，识别图像中的车牌 |
| /fire-detection | fire-detection | FireDetectionView | 火灾检测功能，检测火灾场景 |
| /design-competition | design-competition | DesignCompetitionView | 设计竞赛页面，展示竞赛相关功能 |
| /:pathMatch(.*)\* | - | 重定向到首页 | 捕获所有未匹配路由并重定向到首页 |

### 路由守卫配置

```javascript
// 添加路由守卫
router.beforeEach((to, from, next) => {
    if (!to.matched.length) {
        next({ name: 'home' })
        return
    }
    next()
})
```

## 3. API接口配置

### 3.1 图像识别模块 (/api/image-recognition)

| 接口路径 | 方法 | 描述 | 参数 |
|----------|------|------|------|
| /api/image-recognition/analyze | POST | 图像分析，提供目标检测、人体姿态估计等功能 | file: 图像文件<br>mode: 分析模式 |
| /api/image-recognition/health | GET | 健康检查，检查服务状态 | - |
| /api/image-recognition/models | GET | 获取可用的图像识别模型列表 | - |

### 3.2 路径规划模块 (/api/route)

| 接口路径 | 方法 | 描述 | 参数 |
|----------|------|------|------|
| /api/route/plan | POST | 生成路径规划方案 | text: 规划需求文本<br>model: 使用的模型 |
| /api/route/history | GET | 获取历史规划记录 | - |
| /api/route/history/{routeId} | DELETE | 删除特定历史记录 | routeId: 路线ID |
| /api/route/export | POST | 导出路线 | 路线数据对象 |

### 3.3 知识库聊天模块 (/api/knowledge-chat)

| 接口路径 | 方法 | 描述 | 参数 |
|----------|------|------|------|
| /api/knowledge-chat/stream | POST | 发送消息到知识库聊天(流式响应) | message: 用户消息<br>model: 使用的模型<br>temperature: 温度参数<br>web_search: 是否联网搜索 |
| /api/knowledge-chat/graph | GET | 获取知识图谱数据 | - |
| /api/knowledge-chat/graph/add | POST | 添加节点到知识图谱 | node: 节点数据<br>links: 连接数据 |

### 3.4 夜间低光图像增强模块 (/api/night-detection)

| 接口路径 | 方法 | 描述 | 参数 |
|----------|------|------|------|
| /api/night-detection/process | POST | 处理低光图像 | image: 图像文件 |
| /api/night-detection/process-video | POST | 处理低光视频 | video: 视频文件 |
| /api/night-detection/video-progress/{processId} | GET | 获取视频处理进度 | processId: 处理ID |
| /api/night-detection/video-status/{processId} | GET | 获取视频处理状态 | processId: 处理ID |
| /api/night-detection/history | GET | 获取处理历史 | - |

### 3.5 车牌识别模块 (/api/plate-recognition)

| 接口路径 | 方法 | 描述 | 参数 |
|----------|------|------|------|
| /api/plate-recognition/upload-image | POST | 上传图片进行车牌识别 | file: 图像文件 |
| /api/plate-recognition/upload-video | POST | 上传视频进行车牌识别 | file: 视频文件 |
| /api/plate-recognition/video-status/{processId} | GET | 获取视频处理状态 | processId: 处理ID |
| /api/plate-recognition/processed_video/{filename} | GET | 获取处理后的视频 | filename: 文件名 |

### 3.6 车牌监控模块 (/api/plate-monitoring)

| 接口路径 | 方法 | 描述 | 参数 |
|----------|------|------|------|
| /api/plate-monitoring/upload-video | POST | 上传视频进行车牌监控 | file: 视频文件<br>alarm_plates: 报警车牌列表 |
| /api/plate-monitoring/status/{processId} | GET | 获取监控处理状态 | processId: 处理ID |
| /api/plate-monitoring/get-alarm-plates | GET | 获取所有报警车牌 | - |
| /api/plate-monitoring/add-alarm-plate | POST | 添加报警车牌 | plate: 车牌号<br>description: 描述 |

### 3.7 可见光-热红外检测模块 (/api/rgbt-detection)

| 接口路径 | 方法 | 描述 | 参数 |
|----------|------|------|------|
| /api/rgbt-detection/detect | POST | 上传图像进行检测 | visible: 可见光图像<br>thermal: 热红外图像 |
| /api/rgbt-detection/fuse | POST | 融合可见光与热红外图像 | visible: 可见光图像<br>thermal: 热红外图像 |
| /api/rgbt-detection/video | POST | 处理视频序列 | visible_video: 可见光视频<br>thermal_video: 热红外视频 |
| /api/rgbt-detection/status/{processId} | GET | 获取处理状态 | processId: 处理ID |

### 3.8 视频追踪模块 (/api/video-tracking)

| 接口路径 | 方法 | 描述 | 参数 |
|----------|------|------|------|
| /api/video-tracking/upload | POST | 上传视频进行目标追踪 | file: 视频文件<br>track_type: 追踪类型 |
| /api/video-tracking/status/{trackingId} | GET | 获取追踪处理状态 | trackingId: 追踪ID |
| /api/video-tracking/result/{trackingId} | GET | 获取追踪结果 | trackingId: 追踪ID |

### 3.9 火灾检测专用接口 (/api/fire_detection_direct)

| 接口路径 | 方法 | 描述 | 参数 |
|----------|------|------|------|
| /api/fire_detection_direct/upload-video | POST | 上传视频进行火灾检测 | file: 视频文件<br>save_frames: 是否保存帧<br>enable_alarm: 是否启用报警 |
| /api/fire_detection_direct/detect-image | POST | 图像火灾检测 | file: 图像文件<br>threshold: 检测阈值 |
| /api/fire_detection_direct/video-status/{processId} | GET | 获取视频处理状态 | processId: 处理ID |
| /api/fire_detection_direct/result-video/{processId} | GET | 获取处理后的视频 | processId: 处理ID |

## 4. 代理配置

前端Vite开发服务器配置了代理，将API请求转发到后端服务：

```javascript
server: {
    port: 8080, // 前端运行在8080端口
    proxy: {
        // 所有API请求转发到后端
        '/api': {
            target: 'http://127.0.0.1:8081',
            changeOrigin: true,
            secure: false,
            ws: true
        },
        // 静态文件代理
        '/static': {
            target: 'http://127.0.0.1:8081',
            changeOrigin: true,
            secure: false,
            ws: true
        },
        // 火灾检测直接路由代理
        '/api/fire_detection_direct': {
            target: 'http://127.0.0.1:8081',
            changeOrigin: true,
            secure: false,
            rewrite: (path) => path
        }
    }
}
```

## 5. 组件结构

前端组件按照功能模块进行组织，主要分为以下几类：
- 页面组件：位于src/views目录，对应各个路由页面
- 公共组件：位于src/components目录，可复用的UI组件
- API模块：位于src/api目录，封装与后端的通信逻辑

## 6. 开发建议

1. 所有API请求应统一通过src/api目录下的模块进行，避免在组件中直接发起请求
2. 添加新功能时，建议先设计好API接口规范，再同步开发前后端
3. 大文件上传和流式处理应特别注意超时设置和错误处理
4. 所有路由组件应使用异步加载方式，提高首屏加载速度
5. API响应处理应统一添加详细日志，方便调试和排错

---

> 本文档仅包含前端路由和API接口信息，具体业务逻辑和组件实现请参考相应的源代码文件。
