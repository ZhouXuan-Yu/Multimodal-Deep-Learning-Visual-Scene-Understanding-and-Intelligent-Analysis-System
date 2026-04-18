/**
 * ͼ������������
 * �ṩ���˴�ģ��API��ͨ�Ź���
 */
import { BACKEND_PORT } from '../src/port_config.js';

// ��ȡ���API�Ļ���URL
const getBaseUrl = () => {
    // ����Ƿ���localStorage�б���Ķ˿�����
    const savedPort = localStorage.getItem('backendPort');
    let port = BACKEND_PORT;

    if (savedPort && !isNaN(parseInt(savedPort))) {
        port = parseInt(savedPort);
        console.log(`��localStorage��ȡ��˶˿�: ${port}`);
    }

    // ���˿��Ƿ�����Ч��Χ��
    if (port <= 0 || port > 65535) {
        console.warn(`�˿ڷ�Χ��Ч: ${port}, ʹ��Ĭ�϶˿�8081`);
        port = 8081;
    }

    // ����������API URL
    return `http://localhost:${port}/api`;
};

/**
 * ������Ϣ�����ش�ģ��
 * @param {string} message - �û���Ϣ
 * @param {Object} analysisData - ��ǰ�������
 * @param {boolean} stream - �Ƿ�ʹ����ʽ���
 * @returns {Promise}
 */
async function sendMessage(message, analysisData = null, stream = false) {
    console.log('=== ��ʼ������������ ===');
    console.log('�û���Ϣ:', message);
    console.log('��������:', analysisData);
    console.log('��ʽ���:', stream);

    if (!analysisData) {
        console.error('����: ȱ�ٷ�������');
        return Promise.reject(new Error('ȱ��ͼ���������'));
    }

    // ȷ�� analysisData �ĸ�ʽ��ȷ
    const persons = Array.isArray(analysisData.persons) ? analysisData.persons : [];
    const detected = parseInt(analysisData.detected || 0);

    console.log('�����������:', detected);
    console.log('�������������Ϣ���鳤��:', persons.length);

    const formattedAnalysisData = {
        currentAnalysis: {
            persons: persons.map((person, index) => ({
                id: index + 1,
                age: parseFloat(person.age || 0),
                age_confidence: parseFloat(person.age_confidence || 1.0),
                gender: person.gender || "unknown",
                gender_confidence: parseFloat(person.gender_confidence || 0),
                upper_color: person.upper_color || "unknown",
                upper_color_confidence: parseFloat(person.upper_color_confidence || 0),
                lower_color: person.lower_color || "unknown",
                lower_color_confidence: parseFloat(person.lower_color_confidence || 0),
                bbox: Array.isArray(person.bbox) ? person.bbox.map(Number) : [0, 0, 0, 0]
            })),
            detected: detected
        },
        analysisHistory: []
    };

    console.log('��ʽ�������������:', formattedAnalysisData);
    console.log('������Ϣ:', JSON.stringify(formattedAnalysisData.currentAnalysis.persons, null, 2));

    const requestData = {
        messages: [{
            role: "user",
            content: message.toString()
        }],
        model: "qwen3.5:4b",
        temperature: 0.7,
        stream: stream,
        context: formattedAnalysisData
    };

    console.log('���͵���˵���������:', JSON.stringify(requestData, null, 2));

    // ʹ����ȷ�ĺ�˻���URL
    const baseUrl = getBaseUrl();
    const url = `${baseUrl}/image-analysis-chat/stream`;

    try {
        if (stream) {
            // ������ʽ���������fetch����
            return fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });
        } else {
            // ����ʽ���ʹ�ñ�׼������ʽ
            const response = await fetch(`${baseUrl}/image-analysis-chat/completions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`API����: ${response.status}`);
            }

            return response.json();
        }
    } catch (error) {
        console.error('��ģ������ʧ��:', error);
        throw error;
    }
}

// ��������
export default {
    sendMessage
};