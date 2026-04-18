import { createRouter, createWebHistory } from 'vue-router'

// 使用动态导入
const HomeView = () =>
    import ('../views/HomeView.vue')
const RoutePlanningView = () =>
    import ('../views/RoutePlanningView.vue')
const ImageRecognitionView = () =>
    import ('../views/ImageRecognitionView.vue')
const VideoTrackingView = () =>
    import ('../views/VideoTrackingView.vue')
const RouteRecordsView = () =>
    import ('../views/RouteRecordsView.vue')
const KnowledgeBaseChatView = () =>
    import ('../views/KnowledgeBaseChat.vue')
const NightDetectionView = () =>
    import ('../views/NightDetectionView.vue')
const RGBTDetectionView = () =>
    import ('../views/RGBTDetectionView.vue')
const TestFusionView = () =>
    import ('../views/TestFusionView.vue')
const PlateRecognitionView = () =>
    import ('../views/PlateRecognitionView.vue')
const FireDetectionView = () =>
    import ('../views/FireDetectionView.vue')
const DesignCompetitionView = () =>
    import ('../views/DesignCompetitionView.vue')
const NightGuardianView = () =>
    import ('../views/NightGuardianView.vue')

const router = createRouter({
    history: createWebHistory(
        import.meta.env.BASE_URL),
    routes: [{
            path: '/',
            name: 'home',
            component: HomeView
        },
        {
            path: '/route-planning',
            name: 'route-planning',
            component: RoutePlanningView
        },
        {
            path: '/route-records',
            name: 'route-records',
            component: RouteRecordsView
        },
        {
            path: '/image-recognition',
            name: 'image-recognition',
            component: ImageRecognitionView
        },
        {
            path: '/video-tracking',
            name: 'video-tracking',
            component: VideoTrackingView
        },
        {
            path: '/knowledge-base-chat',
            name: 'knowledge-base-chat',
            component: KnowledgeBaseChatView
        },
        {
            path: '/night-detection',
            name: 'night-detection',
            component: NightDetectionView
        },
        {
            path: '/rgbt-detection',
            name: 'rgbt-detection',
            component: RGBTDetectionView
        },
        {
            path: '/test-fusion',
            name: 'test-fusion',
            component: TestFusionView
        },
        {
            path: '/plate-recognition',
            name: 'plate-recognition',
            component: PlateRecognitionView
        },
        {
            path: '/fire-detection',
            name: 'fire-detection',
            component: FireDetectionView
        },
        {
            path: '/design-competition',
            name: 'design-competition',
            component: DesignCompetitionView
        },
        {
            path: '/night-guardian',
            name: 'night-guardian',
            component: NightGuardianView
        },
        {
            path: '/:pathMatch(.*)*',
            redirect: '/'
        }
    ]
})

// 添加路由守卫
router.beforeEach((to, from, next) => {
    if (!to.matched.length) {
        next({ name: 'home' })
        return
    }
    next()
})

export default router