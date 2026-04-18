// @ts-check
// -*- coding: utf-8 -*-

/**
 * API�����ļ�
 * ����API����URL������ȫ������
 */

// API����URL������Ϊ��ȷ��API����URL·��
export const API_BASE_URL = 'http://localhost:8082/api';

// ��̬��Դ����URL
export const STATIC_BASE_URL = 'http://localhost:8082/static';

// API��ʱ���ã����룩
export const API_TIMEOUT = 120000; // 120�� - ���ӳ�ʱʱ����ƥ���˴���ʱ��

// �ϴ��ļ���С���ƣ��ֽڣ�
export const MAX_UPLOAD_SIZE = 100 * 1024 * 1024; // 100MB

// ��������
export const RETRY_CONFIG = {
    maxRetries: 3, // ������Դ���
    retryDelay: 1000, // ���Լ�������룩
};

// API�汾
export const API_VERSION = 'v1';

// ����Ĭ������
export default {
    API_BASE_URL,
    STATIC_BASE_URL,
    API_TIMEOUT,
    MAX_UPLOAD_SIZE,
    RETRY_CONFIG,
    API_VERSION,
    amap: {
        key: '5c98219ee72ff8b122e46b8167333eb9', // ʹ����ModelService��ͬ��key
        securityCode: '608d0c6db5d6c5eaf7cec37e55f59b50',
        plugins: 'AMap.Scale,AMap.ToolBar,AMap.Driving,AMap.Geocoder,AMap.TileLayer.Traffic,AMap.TileLayer.Satellite,AMap.Buildings'
    }
};