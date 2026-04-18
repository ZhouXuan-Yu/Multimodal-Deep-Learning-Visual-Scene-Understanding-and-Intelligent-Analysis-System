import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, 'src')
        }
    },
    server: {
        port: 8082,
        strictPort: true,
        cors: true,
        proxy: {
            // 简化的代理配置
            '/api': {
                target: 'http://127.0.0.1:8081',
                changeOrigin: true,
                secure: false,
                rewrite: path => path,
                configure: (proxy, options) => {
                    console.log('测试配置: 配置简化代理');
                    proxy.on('error', (err, req, res) => {
                        console.error('代理错误:', err);
                    });
                }
            }
        }
    }
})