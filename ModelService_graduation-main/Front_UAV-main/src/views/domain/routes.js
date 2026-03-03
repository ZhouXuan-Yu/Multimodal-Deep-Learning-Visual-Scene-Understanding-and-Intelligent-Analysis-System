// 导入新的灾害检测页面和应用
import DisasterDetectionPage from './DisasterDetectionPage.vue';
import DisasterDetectionApp from './DisasterDetectionApp.vue';

// 确保现有路由配置正确包含灾害检测功能
export const domainRoutes = [{
        path: '/domain/disaster-detection',
        name: 'disaster-detection',
        component: DisasterDetectionPage,
        meta: {
            title: '灾害检测',
            icon: 'warning'
        }
    },
    {
        path: '/domain/disaster-detection/app',
        name: 'disaster-detection-app',
        component: DisasterDetectionApp,
        meta: {
            title: '灾害检测应用',
            showInNav: false
        }
    }
    // 其他已有路由可在此处保留...
];

export default domainRoutes;