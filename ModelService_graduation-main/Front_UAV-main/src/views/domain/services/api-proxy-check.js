/**
 * API代理检查工具
 * 用于测试前端项目与后端API的连接是否正常
 */

import { ElMessage } from 'element-plus';
import { getApiUrl } from '../src/port_config';

/**
 * 检查API连接状态
 * @returns {Promise<boolean>} 连接是否正常
 */
export async function checkApiConnection() {
    try {
        ElMessage.info('正在检查API连接...');

        // 构建测试API URL
        const testUrl = getApiUrl('fire_detection_direct/health');
        console.log(`[API检查] 测试URL: ${testUrl}`);

        // 添加随机参数避免缓存
        const url = `${testUrl}?t=${Date.now()}`;

        // 发送测试请求
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (response.ok) {
            console.log('[API检查] 连接成功 ?');
            ElMessage.success('API连接正常');
            return true;
        } else {
            console.warn(`[API检查] 连接失败: ${response.status} ${response.statusText}`);
            ElMessage.warning(`API连接异常: ${response.status} ${response.statusText}`);

            // 尝试访问备用健康检查端点
            await fallbackHealthCheck();
            return false;
        }
    } catch (error) {
        console.error('[API检查] 连接错误:', error);
        ElMessage.error(`API连接失败: ${error.message}`);

        // 提供解决建议
        console.log('[API检查] 解决建议:');
        console.log('1. 确认后端服务已启动并监听端口8081');
        console.log('2. 检查vite.config.js中的代理配置是否正确');
        console.log('3. 检查浏览器控制台是否有CORS相关错误');
        console.log('4. 重启前端开发服务器');

        return false;
    }
}

/**
 * 尝试备用端点检查
 */
async function fallbackHealthCheck() {
    try {
        // 尝试访问可能存在的其他端点
        const endpoints = [
            'api/health',
            'api/ping',
            'api/status',
            'api/fire_detection_direct/status'
        ];

        console.log('[API检查] 尝试备用端点检查...');

        for (const endpoint of endpoints) {
            try {
                const url = `/${endpoint}?t=${Date.now()}`;
                console.log(`[API检查] 尝试: ${url}`);

                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    // 设置短超时避免长时间等待
                    signal: AbortSignal.timeout(2000)
                });

                if (response.ok) {
                    console.log(`[API检查] 备用端点 ${endpoint} 可访问 ?`);
                    return true;
                }
            } catch (error) {
                // 记录错误但继续检查其他端点
                console.log(`[API检查] 备用端点 ${endpoint} 不可用: ${error.name}`);
            }
        }

        console.log('[API检查] 所有备用端点检查失败');
        return false;
    } catch (error) {
        console.error('[API检查] 备用检查失败:', error);
        return false;
    }
}

export default {
    checkApiConnection
};