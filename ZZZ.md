# 启动说明（已固定 — 包含后端与前端常用启动命令与简单测试）

## 后端（ModelService）
1. 进入后端项目目录

   cd ModelService/Main
    cd  ModelService_graduation-main\ModelService\Main
2. 安装依赖（建议在虚拟环境中执行）
   conda modelservice
   python -m pip install -r requirements.txt

3. 启动开发服务器（热重载）

   python -m uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload

4. 快速测试后端是否可用（在另一个终端执行）

   curl http://localhost:8082/docs


## 前端（开发：Front_UAV-main）
1. 进入前端项目目录

   cd Front_UAV-main

2. 安装依赖并启动开发服务器（Vite）

   npm install
   npm run dev

3. 如果需要对外网可访问（已在 package.json 中追加 --host），可在局域网中通过 `http://<你的机器IP>:5173` 访问


## 备用前端（若使用 ModelService/Vue）
1. 进入备用前端目录

   cd ModelService/Vue

2. 安装并启动

   npm install
   npm run dev

3. 访问方式同上（默认端口由 Vite 决定，通常为 5173）


## 备注与建议
- 请在启动前确保 Python 依赖已安装且 Python 版本兼容（建议 3.8+）。
- 若使用 GPU 加速，请按 `requirements.txt` 中注释的 PyTorch 指引安装对应 CUDA 版本的 wheel。
- 若需要将前后端同时运行，可在不同终端分别启动后端（端口 8081）和前端（Vite 默认端口 5173）。
  