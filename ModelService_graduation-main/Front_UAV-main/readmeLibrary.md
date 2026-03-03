# 前端UAV项目依赖配置指南

## 环境准备
确保已安装Node.js环境（推荐版本16+）

## 项目依赖安装与构建指令

```bash
# 1. 进入正确的项目目录
cd Front_UAV-main/Front_UAV-main

# 2. 使用npm安装依赖
npm install

# 或者使用pnpm安装依赖（推荐，速度更快）
pnpm install

# 3. 项目开发
npm run dev
# 或
pnpm run dev

# 4. 项目构建
npm run build
# 或
pnpm run build

# 5. 预览构建后的项目
npm run preview
# 或
pnpm run preview
```

## 常见问题解决

如果遇到依赖安装失败，可尝试：

```bash
# 清除npm缓存
npm cache clean --force

# 使用淘宝镜像
npm config set registry https://registry.npmmirror.com
npm install

# 如遇到兼容性问题，可尝试
npm install --legacy-peer-deps
```
