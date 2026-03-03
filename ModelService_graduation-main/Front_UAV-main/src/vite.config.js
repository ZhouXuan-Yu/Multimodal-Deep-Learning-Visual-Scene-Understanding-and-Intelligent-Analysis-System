import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(
    import.meta.url));

// 后端端口配置 - 固定使用8081端口与前端项目2保持一致
const backendPort = '8081';
const backendUrl = `http://localhost:${backendPort}`;
console.log(`使用后端地址: ${backendUrl}`);

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        }
    },
    server: {
        port: 5174, // 指定开发服务器端口
        proxy: {
            // 代理所有API请求到后端服务器
            '/api': {
                target: backendUrl,
                changeOrigin: true,
                secure: false,
                ws: true,
                // 添加调试日志
                onProxyReq: (proxyReq, req) => {
                    console.log(`[代理] 请求转发到 ${backendUrl}${req.url}`);
                }
            },
            // 代理静态资源请求
            '/static': {
                target: backendUrl,
                changeOrigin: true,
                secure: false,
                // 添加调试日志
                onProxyReq: (proxyReq, req) => {
                    console.log(`[代理] 静态资源请求转发到 ${backendUrl}${req.url}`);
                }
            },
            // 代理输出目录请求
            '/output': {
                target: backendUrl,
                changeOrigin: true,
                secure: false,
                // 添加调试日志
                onProxyReq: (proxyReq, req) => {
                    console.log(`[代理] 输出资源请求转发到 ${backendUrl}${req.url}`);
                }
            }
        },
        cors: true
    },
    build: {
        rollupOptions: {
            // 处理无法解析的静态资源路径
            onwarn(warning, warn) {
                // 忽略特定的警告
                if (warning.code === 'UNRESOLVED_IMPORT' && warning.message.includes('drone-icon.png')) {
                    return;
                }
                warn(warning);
            }
        }
    }
});