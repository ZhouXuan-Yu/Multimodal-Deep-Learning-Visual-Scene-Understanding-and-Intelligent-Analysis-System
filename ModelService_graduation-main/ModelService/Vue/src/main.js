import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import './styles/variables.css'
// 导入路由追踪器
import { setupRouteTracker } from './utils/route-tracker'

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

app.config.errorHandler = (err, vm, info) => {
    console.error('Vue Error:', err)
    console.error('Error Info:', info)
    if (err.message.includes('AMap')) {
        ElMessage.error('地图加载失败，请检查网络连接并刷新页面')
    }
}

app.mount('#app')