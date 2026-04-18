/**
 * API模块索引文件
 * 统一导出所有API接口
 */

// 导入各个API模块
import { request, get, post, put, del } from './request';
import { routePlanningApi } from './routePlanning';
import { imageRecognitionApi } from './imageRecognition';
import { knowledgeChatApi } from './knowledgeChat';
import { nightDetectionApi } from './nightDetection';
import { plateRecognitionApi } from './plateRecognition';
import { rgbtDetectionApi } from './rgbtDetection';
import { videoTrackingApi } from './videoTracking';
import { fireDetectionApi } from './fireDetection';

// 导出通用请求方法
export {
    request,
    get,
    post,
    put,
    del
};

// 导出API模块
export {
    routePlanningApi,
    imageRecognitionApi,
    knowledgeChatApi,
    nightDetectionApi,
    plateRecognitionApi,
    rgbtDetectionApi,
    videoTrackingApi,
    fireDetectionApi
};

// 默认导出所有API
export default {
    request,
    get,
    post,
    put,
    del,
    // API模块
    routePlanning: routePlanningApi,
    imageRecognition: imageRecognitionApi,
    knowledgeChat: knowledgeChatApi,
    nightDetection: nightDetectionApi,
    plateRecognition: plateRecognitionApi,
    rgbtDetection: rgbtDetectionApi,
    videoTracking: videoTrackingApi,
    fireDetection: fireDetectionApi
};