import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'

// 端口配置 - 采用固定端口方案
// 前端：8080端口
// 后端主服务：8081端口
// 车牌识别服务：5001端口

// 使用固定端口，不再使用动态配置，避免端口冲突问题
let backendPort = 8081 // 后端主服务使用8081端口，与启动命令中的端口保持一致

// 首先尝试从port_config.json读取端口（最高优先级）
const jsonConfigPath = path.resolve(__dirname, '../../port_config.json')
if (fs.existsSync(jsonConfigPath)) {
    try {
        // 读取JSON配置文件
        const jsonContent = fs.readFileSync(jsonConfigPath, 'utf8')
        const config = JSON.parse(jsonContent)
        if (config && config.main && !isNaN(parseInt(config.main))) {
            // 只有当配置文件明确指定8081以外的值时才使用
            // 由于我们发现后端实际运行在8081端口，这里添加特殊处理
            if (parseInt(config.main) === 8081) {
                backendPort = 8081
                console.log('使用后端默认端口: 8081')
            } else {
                console.log(`从port_config.json读取到端口: ${config.main}，但后端实际运行在8081端口，使用8081`)
                backendPort = 8081
            }
        }
    } catch (error) {
        console.error(`读取JSON配置文件失败: ${error.message}`)
    }
}

// 无论配置文件中指定什么端口，都强制使用8081端口，
// 因为我们已经确认后端实际运行在8081端口上
backendPort = 8081
console.log(`确认使用后端端口: ${backendPort}`)

// 尝试自动更新port_config.js文件，确保其他地方使用正确的端口
const configPath = path.resolve(__dirname, 'src/port_config.js')
try {
    const configContent = `// 自动生成的端口配置文件 - 请勿手动修改\n// 由vite.config.js于 ${new Date().toISOString()} 生成\n\nexport const BACKEND_PORT = ${backendPort};\nexport default BACKEND_PORT;\n`
    fs.writeFileSync(configPath, configContent, 'utf8')
    console.log(`已自动更新端口配置文件: ${configPath}`)
} catch (writeError) {
    console.error(`更新端口配置文件失败: ${writeError.message}`)
}

export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, 'src')
        }
    },
    server: {
        port: 8080, // 前端运行在8080端口，避免与后端端口冲突
        strictPort: true, // 强制使用指定的端口，如果已被占用则抛出错误而不是尝试下一个端口
        cors: true,
        proxy: {
            // 为静态文件路径添加代理
            '/static': {
                target: `http://127.0.0.1:${backendPort}`,
                changeOrigin: true,
                secure: false,
                ws: true,
                configure: (proxy, options) => {
                    console.log(`配置静态文件代理: /static -> http://127.0.0.1:${backendPort}/static`);
                    proxy.on('proxyReq', (proxyReq, req, res) => {
                        console.log(`静态文件代理请求: ${req.method} ${req.url} -> ${proxyReq.path}`);
                    });
                }
            },
            // 使用一个通用的简单代理配置
            '/api': {
                target: `http://127.0.0.1:${backendPort}`,
                changeOrigin: true,
                secure: false,
                ws: true,
                // 增加调试模式
                logLevel: 'debug',
                // 不移除前缀，直接转发全路径
                configure: (proxy, options) => {
                    // 打印详细日志
                    console.log(`配置代理: /api -> http://127.0.0.1:${backendPort}`);

                    // 监听代理请求事件
                    proxy.on('proxyReq', (proxyReq, req, res) => {
                        console.log(`代理请求: ${req.method} ${req.url} -> ${proxyReq.path}`);
                    });

                    // 监听代理响应事件
                    proxy.on('proxyRes', (proxyRes, req, res) => {
                        console.log(`代理响应: ${req.method} ${req.url} -> ${proxyRes.statusCode}`);
                    });

                    // 监听错误事件
                    proxy.on('error', (err, req, res) => {
                        console.error('代理错误:', err);
                        console.error(`请求URL: ${req.url}`);
                        console.error(`错误代码: ${err.code}`);
                        console.error(`错误消息: ${err.message}`);

                        if (!res.headersSent) {
                            res.writeHead(500, {
                                'Content-Type': 'application/json'
                            });
                            res.end(JSON.stringify({
                                error: '代理错误',
                                message: err.message,
                                url: req.url
                            }));
                        }
                    });
                },
                timeout: 1000000, // 更长的超时时间
                proxyTimeout: 1000000
            },
            // 增加火灾检测直接路由的专门代理配置
            '/api/fire_detection_direct': {
                target: `http://127.0.0.1:${backendPort}`,
                changeOrigin: true,
                secure: false,
                rewrite: (path) => path,
                timeout: 1000000,
                proxyTimeout: 1000000
            },
            // 增加夜间保卫者专门的代理配置
            '/api/night-guardian': {
                target: `http://127.0.0.1:${backendPort}`,
                changeOrigin: true,
                secure: false,
                logLevel: 'debug',
                configure: (proxy, options) => {
                    console.log(`配置夜间保卫者代理: /api/night-guardian -> http://127.0.0.1:${backendPort}/api/night-guardian`);
                    
                    // 监听代理请求事件
                    proxy.on('proxyReq', (proxyReq, req, res) => {
                        console.log(`夜间保卫者代理请求: ${req.method} ${req.url} -> ${proxyReq.protocol}//${proxyReq.host}${proxyReq.path}`);
                        if (req.method === 'POST') {
                            console.log('请求头:', JSON.stringify(req.headers, null, 2));
                        }
                    });
                    
                    // 监听代理响应事件
                    proxy.on('proxyRes', (proxyRes, req, res) => {
                        console.log(`夜间保卫者代理响应: ${req.method} ${req.url} -> ${proxyRes.statusCode}`);
                    });
                    
                    // 监听错误事件
                    proxy.on('error', (err, req, res) => {
                        console.error('夜间保卫者代理错误:', err);
                    });
                },
                timeout: 60000,
                proxyTimeout: 60000
            }
        }
    },
    optimizeDeps: {
        include: ['qrcode']
    }
})