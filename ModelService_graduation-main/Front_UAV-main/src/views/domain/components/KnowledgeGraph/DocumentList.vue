<script setup>
import { ref, onMounted } from 'vue';
import knowledgeGraphService from '../../services/knowledgeGraphService';

const documents = ref([]);
const isLoading = ref(true);
const error = ref(null);

// 加载文档列表
const loadDocuments = async () => {
  isLoading.value = true;
  error.value = null;
  
  try {
    const response = await knowledgeGraphService.getDocumentsList();
    documents.value = response.data;
  } catch (err) {
    console.error('获取文档列表失败', err);
    error.value = '无法加载文档列表，请稍后重试';
  } finally {
    isLoading.value = false;
  }
};

// 计算文件图标类型
const getFileIcon = (filename) => {
  if (!filename) return 'file';
  
  const extension = filename.split('.').pop().toLowerCase();
  
  switch (extension) {
    case 'pdf':
      return 'file-pdf';
    case 'doc':
    case 'docx':
      return 'file-word';
    case 'xls':
    case 'xlsx':
      return 'file-excel';
    case 'ppt':
    case 'pptx':
      return 'file-powerpoint';
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
      return 'file-image';
    case 'txt':
    case 'md':
      return 'file-text';
    default:
      return 'file';
  }
};

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  
  return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i];
};

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// 触发刷新
const refreshDocuments = () => {
  loadDocuments();
};

onMounted(() => {
  loadDocuments();
});

defineExpose({
  refreshDocuments
});
</script>

<template>
  <div class="document-list">
    <div class="document-list-header">
      <h3 class="text-lg font-semibold">知识库文档</h3>
      <button @click="refreshDocuments" class="refresh-button" title="刷新文档列表">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
        </svg>
      </button>
    </div>
    
    <div v-if="isLoading" class="loading-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="loading-icon">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
      </svg>
      <span>正在加载文档...</span>
    </div>
    
    <div v-else-if="error" class="error-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <span>{{ error }}</span>
      <button @click="refreshDocuments" class="retry-button">重试</button>
    </div>
    
    <div v-else-if="documents.length === 0" class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <path d="M14 2v6h6"></path>
        <path d="M12 18v-6"></path>
        <path d="M9 15h6"></path>
      </svg>
      <span>暂无文档</span>
      <p>请上传文档到知识库</p>
    </div>
    
    <div v-else class="documents-container">
      <div v-for="(doc, index) in documents" :key="index" class="document-item">
        <div class="document-icon">
          <svg v-if="getFileIcon(doc.filename) === 'file-pdf'" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <path d="M14 2v6h6"></path>
            <path d="M16 13H8"></path>
            <path d="M16 17H8"></path>
            <path d="M10 9H8"></path>
          </svg>
          <svg v-else-if="getFileIcon(doc.filename) === 'file-word'" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <path d="M14 2v6h6"></path>
            <path d="M10 12.3c.2-1.2.7-1.8 1.5-1.8s1.3.6 1.5 1.8"></path>
            <path d="M9 18h6"></path>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <path d="M14 2v6h6"></path>
            <path d="M16 13H8"></path>
            <path d="M16 17H8"></path>
            <path d="M10 9H8"></path>
          </svg>
        </div>
        <div class="document-info">
          <div class="document-name">{{ doc.filename || '未命名文档' }}</div>
          <div class="document-meta">
            <span class="document-size">{{ formatFileSize(doc.size) }}</span>
            <span class="document-date">{{ formatDate(doc.upload_date) }}</span>
          </div>
          <div v-if="doc.description" class="document-description">
            {{ doc.description }}
          </div>
          <div v-if="doc.tags && doc.tags.length > 0" class="document-tags">
            <span v-for="(tag, tagIndex) in doc.tags" :key="tagIndex" class="tag">{{ tag }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.document-list {
  background-color: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.document-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.refresh-button {
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.refresh-button:hover {
  color: #4b5563;
  background-color: #f3f4f6;
}

.loading-state, .error-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 0;
  color: #6b7280;
  gap: 0.75rem;
  text-align: center;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

.retry-button {
  margin-top: 0.5rem;
  padding: 0.375rem 0.75rem;
  background-color: #f3f4f6;
  border: none;
  border-radius: 0.25rem;
  color: #4b5563;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-button:hover {
  background-color: #e5e7eb;
}

.documents-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 300px;
  overflow-y: auto;
}

.document-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.375rem;
  transition: background-color 0.2s;
}

.document-item:hover {
  background-color: #f9fafb;
}

.document-icon {
  flex-shrink: 0;
  color: #4f46e5;
}

.document-info {
  flex-grow: 1;
  min-width: 0;
}

.document-name {
  font-weight: 500;
  font-size: 0.9375rem;
  color: #111827;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.document-meta {
  display: flex;
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.document-size {
  margin-right: 0.75rem;
}

.document-description {
  font-size: 0.875rem;
  color: #4b5563;
  margin-bottom: 0.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.document-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.tag {
  background-color: #e0e7ff;
  color: #4f46e5;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
