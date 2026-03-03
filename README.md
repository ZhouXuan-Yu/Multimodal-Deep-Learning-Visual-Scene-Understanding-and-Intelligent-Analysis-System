## 项目总览：ModelService 毕设综合 AI 模型服务平台

本仓库是你的毕业设计综合工程代码库，主要包含一个 **前后端分离的 AI 模型服务系统**，以及多个配套的子项目与实验代码。核心目标是：通过统一的后端服务和现代化前端界面，将多种视觉识别/检测模型（火灾检测、夜间检测、车牌识别、超远距离识别等）集成到一个可供演示与扩展的平台中。

- **后端主服务**：FastAPI + 多模型服务整合（目录：`ModelService_graduation-main/ModelService`）
- **前端主站点**：Vue 3 + Vite + TypeScript + Element Plus + ECharts（目录：`ModelService_graduation-main/Front_UAV-main`）
- **专项模块与实验代码**：火灾检测、夜间检测、车牌识别、超远距离识别等（如 `Firedetection`、`Night`、`License_plate_recognition_tracking`、`Long-range identification`、`Ultra_long_distance_recognition` 等目录）
- **数据集与工具**：UNISV 数据集相关脚本、端口管理脚本、权重检查脚本等

> 说明：仓库根目录下还包含论文相关 Markdown 文件（如 `论文/`），用于撰写与维护毕设论文，不参与运行环境。

---

## 目录结构概览

根目录重点目录说明（只列出与运行/演示密切相关的部分）：

- **`ModelService_graduation-main/`**：实际项目代码主目录
  - `ModelService/`：FastAPI 后端主工程，负责统一对接各类模型服务与路由管理
  - `Front_UAV-main/`：Vue 3 前端单页应用，提供统一的 Web 可视化与交互界面
  - `Firedetection/`：火灾/烟雾检测相关子项目与脚本
  - `License_plate_recognition_tracking/`：车牌识别与目标跟踪服务
  - `Long-range identification/`：超远距离识别相关代码
  - `Night/`、`night recognition/`：夜间检测/夜视识别相关代码
  - `Ultra_long_distance_recognition/`：超远距离识别另一套实现与工具脚本
  - `UNISV-Dataset-main/`：与 UNISV 数据集相关的数据加载、训练与推理脚本
  - `static/`、`app/static/`：静态资源（示例视频、图片、前端静态文件）
  - `start_service.py`：统一后端服务启动脚本
  - `port_config.json` / `flask_port.txt` / `ports_configuration.txt`：端口配置与同步相关文件
  - 其他辅助脚本：`check_weights.py`、`create_minimal_model.py`、`print_routes.py`、`service_manager_backup.py` 等
- **`论文/`**：毕设论文各章节 Markdown 草稿与大纲
- **根目录其他文件**：
  - `detect.py`：顶层测试/演示脚本（具体功能视代码内容而定）
  - `.gitattributes` / `.gitignore`：Git 配置与忽略规则
  - `zhou.mdc`：针对本项目的 AI 助手使用说明与工作流设定

如需查看前端组件、后端接口等详细说明，可参考子目录内的多个 `README.md` 与 `API_DOCUMENTATION.md`/`api_routes_documentation.md`。

---

## 环境要求

完整运行 **前后端主系统（ModelService + Front_UAV-main）** 推荐环境如下：

- **操作系统**：Windows 10/11（当前开发环境为 Windows 10）
- **Python**：3.8 及以上版本
- **Node.js**：16 及以上版本
- **CUDA**：建议 12.4 及以上（如需启用 GPU 推理）
- **包管理工具**：
  - 后端：`conda`（推荐）或 `venv`
  - 前端：`npm` / `pnpm`
- **建议的 Conda 环境名称**：`modelapp`

> 说明：各子模块（如 `UNISV-Dataset-main`、`Ultra_long_distance_recognition`）可能有各自的 `requirements.txt` 或依赖要求，按需分别创建虚拟环境或在同一环境中安装。

---

## 快速启动（推荐流程）

完整启动流程可以参考 `ModelService_graduation-main/app/启动.md`，这里给出简化版步骤，方便快速上手。

### 1. 克隆与目录说明

```bash
# 从 GitHub 克隆仓库
git clone https://github.com/ZhouXuan-Yu/BiShe.git

# 进入仓库根目录
cd BiShe

# 实际项目代码在子目录 ModelService_graduation-main 中
cd ModelService_graduation-main
```

### 2. 后端主服务启动（FastAPI）

#### 2.1 创建并激活 Python 环境（示例使用 conda）

```bash
conda create -n modelapp python=3.10
conda activate modelapp

# 根据项目需要安装依赖（示例）
cd ModelService_graduation-main
pip install -r Ultra_long_distance_recognition/requirements.txt
# 以及其他 ModelService 主工程所需依赖（如 FastAPI、Uvicorn、Pydantic 等）
```

> 实际依赖请根据各子模块的 `requirements.txt`、`setup` 注释或代码中的 `import` 情况补充安装。

#### 2.2 使用统一脚本启动后端（推荐）

```bash
cd D:\ModelService_graduation-main\ModelService_graduation-main
conda activate modelapp

# 启动后端主服务
python start_service.py --host 0.0.0.0 --port 8082
```

- 默认会整合主服务以及内部集成的车牌识别等子服务
- 如 `8081` 被占用，推荐使用 `8082` 甚至 `8083` 等其他可用端口

#### 2.3 直接使用 Uvicorn 启动 FastAPI（备选方案）

```bash
cd D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main
conda activate modelapp

python -m uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
```

启动完成后，可通过浏览器访问：

- **后端 Swagger 文档**：`http://localhost:8081/docs` 或 `http://localhost:8082/docs`
- **ReDoc 文档**：`http://localhost:8081/redoc` 或 `http://localhost:8082/redoc`

---

### 3. 前端主站点启动（Vue 3 + Vite）

#### 3.1 安装前端依赖

```bash
cd D:\ModelService_graduation-main\ModelService_graduation-main\Front_UAV-main

# 使用 npm 安装依赖
npm install
```

> 如需使用 `pnpm`，请先全局安装 pnpm，然后根据 `pnpm-lock.yaml` 安装依赖。

#### 3.2 启动前端开发服务器

```bash
npm run dev
```

Vite 默认会在 `5173~5179` 之间选一个可用端口，常见如 `5174` 或 `5176`。终端会显示实际访问地址，例如：

- `http://localhost:5174/` 或  
- `http://localhost:5176/`

请使用浏览器打开对应地址，即可访问前端界面。

---

## 前后端联调与端口说明

- **前端开发服务器端口**：通常为 `5174` 或 `5176`（由 Vite 自动选择）
- **后端主服务端口**：
  - 常规：`8081`
  - 推荐/备选：`8082`、`8083` 等
- **车牌识别等子服务端口**：例如 `5001`（可通过环境变量或配置文件指定）

前端通过 Vite 的代理功能将 `/api` 请求转发到后端，例如（示意）：

```js
// Front_UAV-main/vite.config.js 中可能存在类似配置
proxy: {
  '/api': {
    target: 'http://localhost:8081',
    changeOrigin: true
  }
}
```

如果你修改了后端端口（例如改到 `8082`），记得同步更新前端的代理配置，确保接口正常访问。

---

## 核心功能模块概述

此仓库中包含多个子模块，每个模块对应一种或多种视觉任务，统一由 `ModelService` 后端进行调度与暴露接口，再由前端进行可视化与交互。

- **火灾/烟雾检测（Firedetection / ModelService 内部模块）**
  - 对摄像头或视频流中的火灾/烟雾目标进行检测和标注
  - 可用于早期火情告警演示
- **夜间检测与夜视识别（Night / night recognition / static/night_detection）**
  - 针对夜间低照度场景的目标检测、行人/车辆识别
  - 对比不同算法在夜间场景下的检测效果
- **车牌识别与跟踪（License_plate_recognition_tracking）**
  - 实现车牌检测、字符识别
  - 结合跟踪模块，输出车辆轨迹与识别结果
- **超远距离识别（Long-range identification / Ultra_long_distance_recognition）**
  - 面向远距离监控场景的目标检测与识别
  - 包含数据预处理、序列转视频、检测与可视化等脚本
- **数据集与训练脚本（UNISV-Dataset-main）**
  - 与 UNISV 数据集相关的数据加载器、模型定义与训练脚本
  - 为上述业务模块提供训练、验证与推理基础
- **前端可视化与交互（Front_UAV-main）**
  - 采用 Vue 3 + TypeScript + Element Plus + ECharts
  - 提供多模型结果展示、曲线图/热力图、地图可视化等界面
  - 集成 DeepSeek API，用于对地理/检测结果进行智能分析（详见 `Front_UAV-main/README.md`）

---

## 常见问题与排查建议

- **Q1：端口被占用，后端启动失败？**
  - 检查是否已有其他服务占用了 `8081`/`8082`，可在命令行中使用 `netstat -ano` 查找
  - 使用 `python start_service.py --port 8083` 等方式切换到其他端口
  - 修改前端代理配置，使其指向新的后端端口

- **Q2：前端访问时报错：无法连接后端 / CORS 问题？**
  - 检查后端是否已成功启动、端口是否正确
  - 确认前端 `vite.config.js` 中的代理地址与后端实际端口一致
  - 如跨域配置有问题，适当调整 FastAPI 中的 CORS 中间件设置

- **Q3：某些模型推理报错：找不到权重或 CUDA 错误？**
  - 确认权重文件是否已正确放置（部分大文件可能被 `.gitignore` 忽略，需要本地手动添加）
  - 检查 CUDA 版本与 PyTorch/TensorRT 等依赖是否匹配
  - 若当前环境无 GPU，可尝试切换到 CPU 模式（需在相应脚本或配置中修改）

- **Q4：UNISV 或其他训练脚本运行失败？**
  - 检查 `UNISV-Dataset-main` 下的依赖是否完整安装
  - 确认数据集路径配置正确
  - 根据错误日志逐项排查缺失模块或路径问题

---

## 开发与扩展建议

- **后端扩展**
  - 在 `ModelService` 中新增路由，将新的模型推理函数封装为统一的 API
  - 注意统一使用 Pydantic 模型进行请求/响应数据结构管理
  - 搭配 `api_routes_documentation.md` / `API_DOCUMENTATION.md` 保持接口文档同步更新

- **前端扩展**
  - 在 `Front_UAV-main/src/views` 中新增页面，或在现有页面中增加模块
  - 复用已有的图表组件（ECharts）、布局组件（Element Plus）与地图组件
  - 若新增 AI 分析功能，可参考 `DeepSeekService.ts` 的封装方式

- **论文撰写关联**
  - 根目录 `论文/` 下已按章节拆分 Markdown，建议在实现/优化功能后同步补充对应章节内容
  - 可在 README 中记录与论文章节对应的功能模块与实验脚本，便于答辩时快速说明代码与论文的对应关系

---

## 致谢与说明

本仓库为毕业设计项目配套工程，包含大量实验性代码与多种模型集成方案。  
后续若继续维护或对外开源，建议进一步整理：

- 将大型权重文件与数据集移出 Git，只保留下载脚本或说明文档
- 为每个主要子模块补充独立的 `README.md` 与示例
- 编写自动化测试与 CI 配置，提升工程稳定性与可移植性

如需协助进一步重构、优化或添加新模块，可以在此基础上继续迭代。

