<script setup>
import { useRouter } from 'vue-router';

const router = useRouter();

const year = new Date().getFullYear();

const navigationLinks = [
  { title: '功能', items: [
    { label: '路线规划', route: '/route-planning' },
    { label: '图像识别', route: '/image-recognition' },
    { label: '视频追踪', route: '/video-tracking' },
    { label: '人员识别', route: '/person-recognition' },
  ]},
  { title: '支持', items: [
    { label: '知识库', route: '/knowledge-graph' },
    { label: '开发文档', route: '/docs' },
    { label: '联系我们', route: '/contact' },
  ]},
  { title: '关于', items: [
    { label: '研究团队', route: '/team' },
    { label: '技术架构', route: '/technology' },
  ]},
];

// 导航到指定路由
const navigateTo = (route) => {
  router.push(route);
  window.scrollTo(0, 0);
};
</script>

<template>
  <footer class="footer">
    <div class="container mx-auto px-4 py-12">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        <!-- 品牌栏目 -->
        <div class="col-span-1">
          <div class="mb-4">
            <h2 class="text-2xl font-bold text-white mb-2">智能路径规划系统</h2>
            <p class="text-gray-300 text-sm">
              基于AI技术的智能化路径规划与目标追踪系统，为智慧城市和交通提供解决方案。
            </p>
          </div>
          <div class="mt-4">
            <p class="text-gray-400 text-sm">
              ? {{ year }} 智能路径规划与目标追踪系统
            </p>
          </div>
        </div>
        
        <!-- 导航链接 -->
        <div 
          v-for="(column, index) in navigationLinks" 
          :key="index" 
          class="col-span-1"
        >
          <h3 class="text-lg font-semibold text-white mb-4">{{ column.title }}</h3>
          <ul class="space-y-2">
            <li v-for="link in column.items" :key="link.label">
              <a 
                href="#" 
                class="text-gray-300 hover:text-white transition-colors duration-200"
                @click.prevent="navigateTo(link.route)"
              >
                {{ link.label }}
              </a>
            </li>
          </ul>
        </div>
        
        <!-- 联系方式 -->
        <div class="col-span-1">
          <h3 class="text-lg font-semibold text-white mb-4">联系我们</h3>
          <div class="space-y-3 text-gray-300">
            <p class="flex items-start">
              <span class="mr-2">?</span>
              <span>郑州市高新区河南工程技术学院</span>
            </p>
            <p class="flex items-start">
              <span class="mr-2">?</span>
              <span>info@smartpath.com</span>
            </p>
            <p class="flex items-start">
              <span class="mr-2">?</span>
              <span>+86 123-4567-8910</span>
            </p>
          </div>
        </div>
      </div>
      
      <div class="border-t border-gray-700 mt-10 pt-6 text-center">
        <p class="text-gray-400 text-sm">
          智能规划系统 | 版权所有 ? {{ year }}
        </p>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  background-color: #1f2937;
  color: white;
}
</style>