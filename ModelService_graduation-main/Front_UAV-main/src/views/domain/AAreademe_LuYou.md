# 领域功能模块路由与组件分析

## 1. 整体架构

Front_UAV项目domain目录采用组件化设计，包含两种类型的页面组件：
- **功能介绍页面(Page)**: 用于展示功能概述和特性，如`PathPlanningPage.vue`
- **功能应用页面(App)**: 实现具体功能的交互界面，如`PathPlanningApp.vue`

所有Page组件基于`BaseFunctionPage.vue`构建，提供统一的UI结构，而所有App组件基于`templates/BasePage.vue`构建，提供应用级布局。

## 2. 路由组织结构

### 2.1 路由模式

项目采用嵌套路由结构，所有domain功能模块都在`/domain`路径下：
- 功能介绍页面: `/domain/{function-name}`
- 功能应用页面: `/domain/{function-name}/app`

### 2.2 功能模块路由表

| 模块名称 | 功能介绍路由 | 功能应用路由 | 组件 | 功能描述 |
|---------|------------|------------|------|---------|
| 智程导航 | /domain/path-planning | /domain/path-planning/app | PathPlanningPage.vue<br>PathPlanningApp.vue | 基于LLM的智能路径规划系统，集成高德地图，支持自然语言交互 |
| 智眸千析 | /domain/person-recognition | /domain/person-recognition/app | PersonRecognitionPage.vue<br>PersonRecognitionApp.vue | 人员识别分析系统，支持人脸识别、姿态估计等功能 |
| 智慧知库 | /domain/knowledge-graph | /domain/knowledge-graph/app | KnowledgeGraphPage.vue<br>KnowledgeGraphApp.vue | 知识图谱构建与查询系统，支持知识可视化 |
| 灾害预警 | /domain/disaster-detection | /domain/disaster-detection/app | DisasterDetectionPage.vue<br>DisasterDetectionApp.vue | 灾害检测与预警系统，支持多种类型灾害检测 |
| 车辆监控 | /domain/vehicle-monitoring | /domain/vehicle-monitoring/app | VehicleMonitoringPage.vue<br>VehicleMonitoringApp.vue | 车辆检测与监控系统，支持车牌识别与报警 |
| 夜间增强识别 | /domain/night-enhanced-recognition | /domain/night-enhanced-recognition/app | NightEnhancedRecognitionPage.vue<br>NightEnhancedRecognitionApp.vue | 夜间低光图像增强与目标检测系统 |
| 超远距离识别 | /domain/long-range-identification | /domain/long-range-identification/app | LongRangeIdentificationPage.vue<br>LongRangeIdentificationApp.vue | 远距离目标识别系统，支持远距离物体检测与分类 |
| 夜间守护者 | /domain/night-guardian | /domain/night-guardian/app | NightGuardianPage.vue<br>NightGuardianApp.vue | 夜间安防监控系统，提供夜间安全保障 |
| 数据融合 | - | - | DataFusionApp.vue | 多源数据融合与处理系统，支持多模态数据分析 |

## 3. 功能模块详细说明

### 3.1 智程导航 (Path Planning)

**介绍页面**: `/domain/path-planning`  
**应用页面**: `/domain/path-planning/app`

**核心功能**:
- 多策略路线规划（最快、最经济）
- 实时路况可视化（拥堵监控）
- 自然语言交互查询
- 路线历史记录管理

**技术特点**:
- 集成高德地图API
- 基于大模型的自然语言处理
- 实时路况数据分析

### 3.2 智眸千析 (Person Recognition)

**介绍页面**: `/domain/person-recognition`  
**应用页面**: `/domain/person-recognition/app`

**核心功能**:
- 人脸检测与识别
- 人体姿态估计
- 行为分析与识别
- 属性识别（性别、年龄等）

**技术特点**:
- 深度学习目标检测
- 人体关键点检测
- 特征提取与匹配算法

### 3.3 智慧知库 (Knowledge Graph)

**介绍页面**: `/domain/knowledge-graph`  
**应用页面**: `/domain/knowledge-graph/app`

**核心功能**:
- 知识图谱构建与存储
- 知识可视化交互
- 智能问答与检索
- 知识关联分析

**技术特点**:
- 图数据存储与查询
- 自然语言处理
- 关系抽取与实体链接

### 3.4 灾害预警 (Disaster Detection)

**介绍页面**: `/domain/disaster-detection`  
**应用页面**: `/domain/disaster-detection/app`

**核心功能**:
- 火灾检测与预警
- 洪水检测与分析
- 多源数据集成监控
- 预警信息发布与推送

**技术特点**:
- 计算机视觉目标检测
- 图像分割与场景理解
- 多传感器数据融合

### 3.5 车辆监控 (Vehicle Monitoring)

**介绍页面**: `/domain/vehicle-monitoring`  
**应用页面**: `/domain/vehicle-monitoring/app`

**核心功能**:
- 车辆检测与跟踪
- 车牌识别与记录
- 异常行为监测
- 车辆监控报警系统

**技术特点**:
- 实时视频处理
- OCR车牌识别
- 运动轨迹分析

### 3.6 夜间增强识别 (Night Enhanced Recognition)

**介绍页面**: `/domain/night-enhanced-recognition`  
**应用页面**: `/domain/night-enhanced-recognition/app`

**核心功能**:
- 低光图像增强
- 夜间目标检测
- 场景分析与理解
- 增强图像实时预览

**技术特点**:
- 图像增强算法
- 低光环境适应性
- 红外与可见光融合

### 3.7 超远距离识别 (Long Range Identification)

**介绍页面**: `/domain/long-range-identification`  
**应用页面**: `/domain/long-range-identification/app`

**核心功能**:
- 远距离目标检测
- 远距离身份识别
- 目标放大与增强
- 多镜头融合识别

**技术特点**:
- 超分辨率重建
- 远距离特征提取
- 大场景目标定位

### 3.8 夜间守护者 (Night Guardian)

**介绍页面**: `/domain/night-guardian`  
**应用页面**: `/domain/night-guardian/app`

**核心功能**:
- 夜间安全监控
- 异常行为检测
- 入侵报警系统
- 夜间监控管理

**技术特点**:
- 夜视图像处理
- 行为分析算法
- 智能报警机制

## 4. 组件设计模式

项目采用以下设计模式:

### 4.1 基础组件

- **BaseFunctionPage.vue**: 所有功能介绍页面的基础组件，提供统一的布局结构与UI样式
  - 包含标题、副标题、描述、特性列表和行动按钮
  - 集成了`FeatureHero`、`FeatureContent`和`CtaSection`组件

- **templates/BasePage.vue**: 所有功能应用页面的基础模板
  - 提供顶部导航栏、内容区和页脚
  - 集成了返回按钮和页面标题

### 4.2 组件通信

- Props 向下传递数据
- Events 向上传递事件
- 使用 ref 获取子组件实例
- 部分组件使用服务（services）进行数据处理

### 4.3 代码组织

- **components/**: 按功能模块组织的组件
- **services/**: 功能相关的服务逻辑
- **templates/**: 页面模板组件
- **api/**: API调用函数库，与Vue前端项目API保持兼容

## 5. API兼容性设计

为实现与ModelService/Vue前端项目的API兼容，domain项目进行了以下设计:

### 5.1 前端API适配层

在`Front_UAV-main/src/views/domain/api/`目录下，创建了与Vue项目相同功能的API模块:

| API模块 | 文件路径 | 功能描述 |
|--------|---------|----------|
| 基础请求 | api/request.js | 统一的axios请求封装，处理请求和响应 |
| 路径规划 | api/routePlanning.js | 智能路径规划相关API调用 |
| 图像识别 | api/imageRecognition.js | 图像目标检测与分析API调用 |
| 知识库聊天 | api/knowledgeChat.js | 知识图谱与智能对话API调用 |
| 夜间检测 | api/nightDetection.js | 夜间低光图像增强与检测API调用 |
| 可见光-热红外 | api/rgbtDetection.js | 可见光-热红外检测API调用 |
| 车牌识别 | api/plateRecognition.js | 车牌识别与分析API调用 |

### 5.2 后端路由别名

在后端通过路由别名机制，支持同时接收两套前端项目的API请求:

1. **路由配置**: 在`route_config.py`中添加了别名路由定义
2. **中间件处理**: 添加了`RouteAliasMiddleware`中间件，自动将domain前端的请求重定向到对应的后端处理器

### 5.3 页面与API对应关系

| domain页面路径 | 使用的API模块 | 对应的后端路由 |
|--------------|--------------|-------------|
| /domain/path-planning | routePlanning.js | /api/route |
| /domain/person-recognition | imageRecognition.js | /api/image-recognition |
| /domain/knowledge-graph | knowledgeChat.js | /api/knowledge-chat |
| /domain/vehicle-monitoring | plateRecognition.js | /api/plate-recognition |
| /domain/night-enhanced-recognition | nightDetection.js | /api/night-detection |
| /domain/long-range-identification | rgbtDetection.js | /api/rgbt-detection |
| /domain/disaster-detection | imageAnalysis.js | /api/image-analysis |

## 6. 后续开发建议

1. 统一组件间的通信模式，优先使用props和events
2. 为每个功能模块添加统一的错误处理机制
3. 考虑添加权限管理，控制功能的访问权限
4. 优化移动端适配，提升响应式布局体验
5. 实现国际化支持，满足多语言需求
6. 完善API兼容层，确保所有Vue前端功能可正常移植

## 7. API调用与后端对应关系

| 前端路由 | API调用文件 | 后端API路径 |
|---------|-----------|------------|
| /domain/path-planning | api/routePlanning.js | /api/route |
| /domain/person-recognition | api/imageRecognition.js | /api/image-recognition |
| /domain/knowledge-graph | api/knowledgeChat.js | /api/knowledge-chat |
| /domain/vehicle-monitoring | api/plateRecognition.js | /api/plate-recognition |
| /domain/night-enhanced-recognition | api/nightDetection.js | /api/night-detection |
| /domain/long-range-identification | api/rgbtDetection.js | /api/rgbt-detection |
| /domain/disaster-detection | api/imageAnalysis.js | /api/image-analysis |

# 路径规划模块集成说明

## 问题修复记录

### HTTP 500 错误修复

在将路径规划模块集成到Front_UAV-main项目时，出现了HTTP 500内部服务器错误，主要原因是API路径配置和请求处理方式不匹配。

具体错误：
```
GET http://localhost:5174/api/chat/completions/history?type=general 500 (Internal Server Error)
```

解决方案：

1. 修改了`utils/request.js`和`api/request.js`文件中的baseURL配置，使用完整的API URL：
   ```js
   baseURL: `http://localhost:${backendPort}/api`,
   ```

2. 修改了`stores/index.js`文件中的`loadChatHistory`方法，避免直接调用后端API，改为从本地存储获取聊天历史：
   ```js
   async loadChatHistory(type) {
       this.loading = true
       try {
           // 改为从本地存储获取聊天历史，避免调用不必要的后端API
           const storedHistoryKey = `chatHistory_${type || 'general'}`;
           let chatHistory = [];
           
           const storedHistory = localStorage.getItem(storedHistoryKey);
           if (storedHistory) {
               try {
                   chatHistory = JSON.parse(storedHistory) || [];
               } catch (e) {
                   console.error('解析本地存储的聊天历史失败:', e);
               }
           }
           
           this.chatHistory = chatHistory;
           this.currentChatType = type;
       } catch (error) {
           console.error('加载聊天历史失败:', error)
           this.error = error.message
           this.chatHistory = []
       } finally {
           this.loading = false
       }
   }
   ```

3. 修改了`stores/index.js`文件中的`sendChatMessage`方法，使用正确的API路径，并增加了本地存储聊天历史的逻辑：
   ```js
   if (type === 'route') {
       // 路径规划请求使用routePlanningApi服务
       // ...
       
       // 保存聊天历史到本地存储
       localStorage.setItem(`chatHistory_${type}`, JSON.stringify(this.chatHistory));
   } else {
       // 普通聊天请求 - 直接添加到聊天历史，不调用后端
       // ...
       
       // 保存聊天历史到本地存储
       localStorage.setItem(`chatHistory_${type || 'general'}`, JSON.stringify(this.chatHistory));
   }
   ```

4. 修复了`api/routePlanning.js`文件中的语法错误，确保各方法之间使用正确的逗号分隔。

这些修改使路径规划功能在Front_UAV-main项目中能够正常运行，避开了不必要的后端API调用造成的错误。

## API请求配置统一

为确保路径规划功能正确连接到后端，我们按照原前端项目1的API配置进行了同步更新，主要包括：

### 1. 统一request模块配置

我们更新了`src/api/request.js`文件，使用了与原前端项目1相似的拦截器和错误处理逻辑：

```js
// 请求拦截器
request.interceptors.request.use(
    config => {
        // 打印请求信息
        console.log('============================')
        console.log('【前端请求】发送请求给后端:')
        console.log(`URL: ${config.baseURL}/${config.url}`)
        // ...
    }
)

// 响应拦截器
request.interceptors.response.use(
    response => {
        // 处理返回的数据
        const res = response.data
        
        // 如果响应是直接的内容或API直接返回的数据
        if (!res || typeof res !== 'object' || res.content !== undefined) {
            return res
        }
        // ...
    }
)
```

### 2. 统一API调用方法

更新了`src/api/routePlanning.js`文件，保持与原前端项目1相同的API方法命名和调用方式：

```js
export const routePlanningApi = {
    /**
     * 创建路线规划
     * @param {Object} params - 路线规划参数
     * @returns {Promise<Object>} - 路线规划结果
     */
    getRoutePlan: (params) => {
        console.log('[routePlanningApi] 调用路线规划API，参数:', params);

        // 准备请求参数，确保与后端API格式一致
        const requestParams = {
            text: params.text || '',
            model: params.model || 'gemma2:2b'
        };
        // ...
    }
    // ...其他方法
}
```

### 3. 移除模拟数据，使用实际API

在`stores/index.js`中更新了`sendChatMessage`方法，去除了之前的模拟数据处理，改为实际API调用：

```js
// 普通聊天请求
try {
    // 向API发送实际请求
    const chatEndpoint = type === 'knowledge' ? '/knowledge-chat/completions' : '/chat/completions';
    const apiResponse = await fetch(`http://localhost:${BACKEND_PORT}/api${chatEndpoint}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            messages: [{
                role: 'user',
                content: content
            }],
            model: 'gemma2:2b',
            type: type
        })
    });
    // 处理响应...
}
```

### 4. 访问端口和URL配置

统一使用`port_config.js`中配置的后端端口进行API访问，确保与前端项目1连接相同的后端：

```js
import { BACKEND_PORT } from '../port_config.js'

// 创建axios实例
const request = axios.create({
    baseURL: `http://localhost:${backendPort}/api`,
    // ...
})
```

通过这些配置的统一，确保了路径规划功能在Front_UAV-main项目中能够正确连接到与前端项目1相同的后端服务，保持一致的API调用方式和错误处理逻辑。
