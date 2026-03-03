import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-CN.mjs'
import './styles/variables.css'
// 导入路由追踪器
import { setupRouteTracker } from './utils/route-tracker'
import { ElMessage } from 'element-plus'

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// 设置路由追踪
setupRouteTracker()
console.log('🚦 路由追踪已启用')

// 添加高德地图API加载检查和处理
const checkAndLoadAMapApi = () => {
    return new Promise((resolve, reject) => {
        // 如果已加载，直接返回
        if (window.AMap && typeof window.AMap.Geocoder === 'function') {
            console.log('高德地图API和Geocoder插件已加载');
            resolve();
            return;
        }

        console.log('等待高德地图API加载...');

        // 监听自定义加载完成事件
        window.addEventListener('amap:loaded', () => {
            console.log('检测到高德地图API加载完成事件');
            resolve();
        }, { once: true });

        // 如果5秒后还未加载完成，则手动加载
        setTimeout(() => {
            if (!window.AMap) {
                console.warn('高德地图API加载超时，尝试手动加载');
                const script = document.createElement('script');
                script.type = 'text/javascript';
                script.src = 'https://webapi.amap.com/maps?v=2.0&key=5c98219ee72ff8b122e46b8167333eb9&plugin=AMap.Scale,AMap.ToolBar,AMap.Driving,AMap.Geocoder,AMap.TileLayer.Traffic,AMap.TileLayer.Satellite,AMap.Buildings';

                script.onload = () => {
                    console.log('手动加载高德地图API成功');
                    // 加载插件
                    if (window.AMap && typeof window.AMap.plugin === 'function') {
                        window.AMap.plugin(['AMap.Geocoder', 'AMap.Driving'], function() {
                            console.log('高德地图插件加载完成');
                            resolve();
                        });
                    } else {
                        console.error('高德地图API加载成功但plugin方法缺失');
                        reject(new Error('高德地图API加载异常'));
                    }
                };

                script.onerror = (e) => {
                    console.error('手动加载高德地图API失败', e);
                    reject(new Error('高德地图API加载失败'));
                };

                document.head.appendChild(script);
            }
        }, 5000);
    });
};

// 在应用启动前加载高德地图API
checkAndLoadAMapApi()
    .then(() => {
        console.log('高德地图API加载成功，启动应用');
        app.mount('#app');
    })
    .catch(error => {
        console.error('高德地图API加载失败:', error);
        // 仍然启动应用，但显示错误提示
        ElMessage.error('地图组件加载失败，部分功能可能不可用');
        app.mount('#app');
    });

// 添加全局错误处理，捕获Geocoder相关错误
app.config.errorHandler = (err, vm, info) => {
    console.error('Vue Error:', err);
    console.error('Error Info:', info);

    if (err.message && err.message.includes('AMap.Geocoder is not a constructor')) {
        console.error('检测到地理编码器错误，尝试重新加载插件');
        // 尝试重新加载Geocoder插件
        if (window.AMap && typeof window.AMap.plugin === 'function') {
            window.AMap.plugin(['AMap.Geocoder'], function() {
                console.log('重新加载Geocoder插件成功');
                ElMessage.warning('地图组件已修复，请重试上一操作');
            });
        }
    } else if (err.message && err.message.includes('AMap')) {
        ElMessage.error('地图加载失败，请检查网络连接并刷新页面');
    }
};