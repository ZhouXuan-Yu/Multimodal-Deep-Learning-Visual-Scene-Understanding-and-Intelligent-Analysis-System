/**
 * 路径规划服务
 */
import { post } from '../src/utils/request.js';

export default {
  /**
   * 获取路线规划
   * @param {Object} data - 包含规划请求的数据
   * @param {string} data.text - 用户输入的路线规划指令文本
   * @param {string} data.model - 使用的模型
   * @param {AbortSignal} [signal] - 用于取消请求的AbortSignal对象
   * @returns {Promise} - 返回路线规划结果
   */
  getRoutePlan(data, signal) {
    // 准备请求数据
    const requestData = {
      text: data.text || '',
      model: data.model || 'qwen3-vl:8b'
    };
    
    console.log('发送路线规划请求:', requestData);
    
    // 使用统一的请求封装，发送到相对路径 /route/plan（最终由 base /api 前缀拼接）
    return post('/route/plan', requestData, { timeout: 400000, signal });
  },

  /**
   * 获取历史记录
   * @returns {Promise} - 返回历史记录列表
   */
  getHistory() {
    return axios.get('/api/uav/route/history')
      .then(response => {
        if (response.data && response.data.success) {
          return response.data.history || [];
        }
        // 如果请求失败或没有数据，返回空数组
        return [];
      })
      .catch(error => {
        console.error('获取历史记录失败:', error);
        // 返回空数组，避免应用崩溃
        return [];
      });
  },

  /**
   * 删除历史记录
   * @param {string} routeId - 要删除的路线ID
   * @returns {Promise}
   */
  deleteHistory(routeId) {
    return axios.delete(`/api/uav/route/history/${routeId}`);
  },

  /**
   * 获取收藏路线
   * @returns {Promise} - 返回收藏路线列表
   */
  getFavorites() {
    return axios.get('/api/uav/route/favorites')
      .then(response => {
        if (response.data && response.data.success) {
          return response.data.favorites || [];
        }
        return [];
      })
      .catch(error => {
        console.error('获取收藏路线失败:', error);
        return [];
      });
  },

  /**
   * 添加收藏路线
   * @param {Object} data - 路线数据
   * @returns {Promise}
   */
  addFavorite(data) {
    return axios.post('/api/uav/route/favorites', data);
  },

  /**
   * 删除收藏路线
   * @param {string} routeId - 要删除的路线ID
   * @returns {Promise}
   */
  removeFavorite(routeId) {
    return axios.delete(`/api/uav/route/favorites/${routeId}`);
  },

  /**
   * 导出路线
   * @param {Object} data - 路线数据
   * @returns {Promise}
   */
  exportRoute(data) {
    return axios.post('/api/uav/route/export', data, {
      responseType: 'blob' // 指定响应类型为blob
    });
  },

  /**
   * 获取路线详情
   * @param {string} routeId - 路线ID
   * @returns {Promise}
   */
  getRouteDetail(routeId) {
    return axios.get(`/api/uav/route/${routeId}`);
  }
}
