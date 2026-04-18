// 夜间保卫者系统API调用
import axios from 'axios';

// 定义API路径变量 - 双重格式保证兼容性
const API_PATHS = {
  // 下划线格式(snake_case)
  snake: '/api/night_guardian',
  // 短横线格式(kebab-case)
  kebab: '/api/night-guardian'
};

// 创建API基础路径 - 使用下划线格式作为默认值
const baseURL = API_PATHS.snake; // 主要使用下划线格式

/**
 * 最简单的GET测试 - 不需要任何参数
 * @returns {Promise} 测试结果
 */
export async function testSimpleGet() {
  console.log('执行最简单的GET测试请求');
  try {
    // 先尝试下划线格式路径
    try {
      console.log(`尝试下划线格式路径: ${API_PATHS.snake}/simple_test`);
      const response = await axios.get(`${API_PATHS.snake}/simple_test`);
      console.log('GET测试成功(下划线格式):', response.data);
      return response.data;
    } catch (snakeError) {
      console.warn('下划线格式请求失败，尝试连字符格式:', snakeError);
      
      // 如果下划线格式失败，尝试连字符格式
      console.log(`尝试连字符格式路径: ${API_PATHS.kebab}/simple-test`);
      const kebabResponse = await axios.get(`${API_PATHS.kebab}/simple-test`);
      console.log('GET测试成功(连字符格式):', kebabResponse.data);
      return kebabResponse.data;
    }
  } catch (error) {
    console.error('GET测试失败(所有格式):', error);
    throw error;
  }
}

/**
 * 尝试直接请求后端（不经过代理）
 * @returns {Promise} 测试结果
 */
export async function testDirectBackend() {
  console.log('尝试直接请求后端');
  try {
    // 先尝试下划线格式路径
    try {
      const snakeUrl = `http://localhost:8081/api/night_guardian/simple_test`;
      console.log(`尝试直接请求下划线格式路径: ${snakeUrl}`);
      const response = await axios.get(snakeUrl);
      console.log('直接请求后端成功(下划线格式):', response.data);
      return response.data;
    } catch (snakeError) {
      console.warn('直接请求下划线格式失败，尝试连字符格式:', snakeError);
      
      // 如果下划线格式失败，尝试连字符格式
      const kebabUrl = `http://localhost:8081/api/night-guardian/simple-test`;
      console.log(`尝试直接请求连字符格式路径: ${kebabUrl}`);
      const kebabResponse = await axios.get(kebabUrl);
      console.log('直接请求后端成功(连字符格式):', kebabResponse.data);
      return kebabResponse.data;
    }
  } catch (error) {
    console.error('直接请求后端失败(所有格式):', error);
    throw error;
  }
}

/**
 * 测试上传视频到测试端点
 * @param {File} file - 视频文件
 * @returns {Promise} 处理结果
 */
export async function testUploadVideo(file) {
  console.log('测试上传视频到测试端点');
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    // 先尝试下划线格式路径
    try {
      const endpoint = `${API_PATHS.snake}/test_video`;
      console.log(`尝试下划线格式路径: ${endpoint}`);
      const response = await axios.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      console.log('测试上传成功(下划线格式):', response.data);
      return response.data;
    } catch (snakeError) {
      console.warn('下划线格式上传失败，尝试连字符格式:', snakeError);
      
      // 如果下划线格式失败，尝试连字符格式
      const kebabEndpoint = `${API_PATHS.kebab}/test-video`;
      console.log(`尝试连字符格式路径: ${kebabEndpoint}`);
      const kebabResponse = await axios.post(kebabEndpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      console.log('测试上传成功(连字符格式):', kebabResponse.data);
      return kebabResponse.data;
    }
  } catch (error) {
    console.error('测试上传失败(所有格式):', error);
    throw error;
  }
}

/**
 * 上传视频进行处理
 * @param {File} file - 视频文件
 * @param {Object} options - 处理选项
 * @returns {Promise} 处理结果
 */
export async function uploadVideo(file, options = {}) {
  console.log('开始上传视频进行处理');
  const formData = new FormData();
  formData.append('file', file);
  
  // 添加精简化后的参数
  if (options.modelType) {
    formData.append('model_type', options.modelType);
  }
  
  // 使用默认阈值，不再从前端发送
  // 不再发送clip_len参数，使用后端默认值
  
  if (options.saveFrames !== undefined) {
    formData.append('save_frames', options.saveFrames);
  }
  
  try {
    // 先尝试下划线格式路径
    try {
      const endpoint = `${API_PATHS.snake}/process_video`;
      console.log(`尝试下划线格式路径上传视频: ${endpoint}`);
      const response = await axios.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      console.log('上传视频成功(下划线格式):', response.data);
      return response.data;
    } catch (snakeError) {
      console.warn('下划线格式上传失败，尝试连字符格式:', snakeError);
      
      // 如果下划线格式失败，尝试连字符格式
      const kebabEndpoint = `${API_PATHS.kebab}/process-video`;
      console.log(`尝试连字符格式路径上传视频: ${kebabEndpoint}`);
      const kebabResponse = await axios.post(kebabEndpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      console.log('上传视频成功(连字符格式):', kebabResponse.data);
      return kebabResponse.data;
    }
  } catch (error) {
    console.error('上传视频出错(所有格式):', error);
    throw error;
  }
}

/**
 * 获取任务状态
 * @param {string} taskId - 任务ID
 * @returns {Promise} 任务状态
 */
export async function getTaskStatus(taskId) {
  try {
    // 统一使用连字符格式路径
    console.log(`尝试获取任务状态: ${API_PATHS.kebab}/task/${taskId}`);
    const response = await axios.get(`${API_PATHS.kebab}/task/${taskId}`);
    console.log('获取任务状态成功:', response.data);
    return response.data;
  } catch (error) {
    console.error('获取任务状态出错:', error);
    throw error;
  }
}

/**
 * 获取处理结果
 * @param {string} taskId - 任务ID
 * @returns {Promise} 处理结果
 */
export async function getResults(taskId) {
  try {
    // 统一使用连字符格式路径
    console.log(`尝试获取结果: ${API_PATHS.kebab}/results/${taskId}`);
    const response = await axios.get(`${API_PATHS.kebab}/results/${taskId}`);
    console.log('获取结果成功:', response.data);
    return response.data;
  } catch (error) {
    console.error('获取结果出错:', error);
    throw error;
  }
}

/**
 * 获取处理后的视频URL
 * @param {string} taskId - 任务ID
 * @returns {string} 视频URL
 */
export function getProcessedVideoUrl(taskId) {
  // 统一使用连字符格式路径
  return `${API_PATHS.kebab}/video/${taskId}`;
}

/**
 * 获取视频帧URL
 * @param {string} taskId - 任务ID
 * @param {number} frameId - 帧ID
 * @returns {string} 帧图像URL
 */
export function getFrameUrl(taskId, frameId) {
  // 统一使用连字符格式路径
  return `${API_PATHS.kebab}/frame/${taskId}/${frameId}`;
}

/**
 * 检查服务健康状态
 * @returns {Promise} 健康状态
 */
export async function checkHealth() {
  try {
    // 统一使用连字符格式路径
    console.log(`尝试检查健康状态: ${API_PATHS.kebab}/health`);
    const response = await axios.get(`${API_PATHS.kebab}/health`);
    console.log('健康检查成功:', response.data);
    return response.data;
  } catch (error) {
    console.error('健康检查失败:', error);
    throw error;
  }
}
