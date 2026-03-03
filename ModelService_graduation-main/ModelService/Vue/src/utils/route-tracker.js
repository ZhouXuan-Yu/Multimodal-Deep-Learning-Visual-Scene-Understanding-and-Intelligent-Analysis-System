/**
 * 路由追踪器
 * 用于记录和监控前端路由变化和API请求
 */

import { useRouter } from 'vue-router'
import axios from 'axios'

// 保存原始的axios方法
const originalRequest = axios.request;
const originalGet = axios.get;
const originalPost = axios.post;
const originalPut = axios.put;
const originalDelete = axios.delete;

/**
 * 安装路由追踪器
 */
export function setupRouteTracker() {
  // 包装axios请求方法，添加日志
  axios.request = function(config) {
    console.group('🌐 API请求');
    console.log(`📤 请求: ${config.method?.toUpperCase() || 'GET'} ${config.url}`);
    console.log('请求数据:', config.data);
    console.log('请求头:', config.headers);
    console.groupEnd();
    
    return originalRequest.apply(this, arguments)
      .then(response => {
        console.group('🌐 API响应');
        console.log(`📥 响应: ${config.method?.toUpperCase() || 'GET'} ${config.url}`);
        console.log('状态:', response.status);
        console.log('响应数据:', response.data);
        console.groupEnd();
        return response;
      })
      .catch(error => {
        console.group('🚨 API错误');
        console.log(`❌ 错误: ${config.method?.toUpperCase() || 'GET'} ${config.url}`);
        console.log('状态:', error.response?.status);
        console.log('错误信息:', error.message);
        console.log('响应数据:', error.response?.data);
        console.groupEnd();
        throw error;
      });
  };

  // 包装各个HTTP方法
  axios.get = function(url, config) {
    console.log(`📤 GET请求: ${url}`);
    return originalGet.apply(this, arguments)
      .then(response => {
        console.log(`📥 GET响应: ${url}, 状态: ${response.status}`);
        return response;
      });
  };

  axios.post = function(url, data, config) {
    console.log(`📤 POST请求: ${url}`);
    return originalPost.apply(this, arguments)
      .then(response => {
        console.log(`📥 POST响应: ${url}, 状态: ${response.status}`);
        return response;
      });
  };

  axios.put = function(url, data, config) {
    console.log(`📤 PUT请求: ${url}`);
    return originalPut.apply(this, arguments)
      .then(response => {
        console.log(`📥 PUT响应: ${url}, 状态: ${response.status}`);
        return response;
      });
  };

  axios.delete = function(url, config) {
    console.log(`📤 DELETE请求: ${url}`);
    return originalDelete.apply(this, arguments)
      .then(response => {
        console.log(`📥 DELETE响应: ${url}, 状态: ${response.status}`);
        return response;
      });
  };
}

/**
 * Vue组合式API，用于监控路由变化
 */
export function useRouteTracker() {
  const router = useRouter();
  
  // 添加全局路由钩子
  router.beforeEach((to, from) => {
    console.group('🚦 路由变化');
    console.log(`📍 从: ${from.path} (${from.name || 'unnamed'}) → 到: ${to.path} (${to.name || 'unnamed'})`);
    console.log('查询参数:', to.query);
    console.log('路由参数:', to.params);
    console.groupEnd();
    return true;
  });
  
  router.afterEach((to, from) => {
    console.log(`✅ 路由完成: ${to.path}`);
  });
  
  router.onError((error) => {
    console.error(`🚨 路由错误: ${error}`);
  });
  
  return {
    logRouteEvent(event, data) {
      console.log(`📌 路由事件 [${event}]:`, data);
    }
  };
}

export default {
  setupRouteTracker,
  useRouteTracker
};
