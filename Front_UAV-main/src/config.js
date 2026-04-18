/**
 * ��Ŀȫ������
 */

// Ĭ��API����URL
const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || 'http://localhost:8082/api';

// �ߵµ�ͼ����
const AMAP_CONFIG = {
    key: '5c98219ee72ff8b122e46b8167333eb9',
    securityCode: '608d0c6db5d6c5eaf7cec37e55f59b50',
    version: '2.0',
    plugins: 'AMap.Scale,AMap.ToolBar,AMap.Driving,AMap.TileLayer.Traffic,AMap.TileLayer.Satellite,AMap.Buildings,AMap.Geocoder'
};

export default {
    // API����
    apiBaseUrl: API_BASE_URL,
    apiTimeout: 600000, // 10����

    // �ߵµ�ͼ����
    amap: AMAP_CONFIG,

    // ·�߹滮�������
    routePlanning: {
        defaultCenter: [116.397428, 39.90923], // ����
        defaultZoom: 12,
        maxRetries: 3,
        retryDelay: 2000, // 2��
    },

    // ����Ĭ������
    defaults: {
        chatMaxMessages: 50,
        mapControls: {
            showScale: true,
            showToolbar: true,
            showTraffic: false,
            showSatellite: false,
            showBuildings: true,
        }
    }
};