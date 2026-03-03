<script setup>
import { ref } from 'vue';
import knowledgeGraphService from '../../services/knowledgeGraphService';

const emit = defineEmits(['upload-success', 'upload-error']);

const file = ref(null);
const description = ref('');
const tags = ref('');
const isUploading = ref(false);
const uploadProgress = ref(0);
const dragOver = ref(false);

// 选择文件
const handleFileChange = (event) => {
  file.value = event.target.files[0];
};

// 拖放文件处理
const handleDragOver = (e) => {
  e.preventDefault();
  dragOver.value = true;
};

const handleDragLeave = () => {
  dragOver.value = false;
};

const handleDrop = (e) => {
  e.preventDefault();
  dragOver.value = false;
  
  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    file.value = e.dataTransfer.files[0];
  }
};

// 上传文件
const uploadFile = async () => {
  if (!file.value) {
    emit('upload-error', '请选择要上传的文件');
    return;
  }
  
  isUploading.value = true;
  uploadProgress.value = 0;
  
  try {
    // 模拟上传进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10;
      }
    }, 300);
    
    // 调用上传API
    const response = await knowledgeGraphService.uploadDocument(file.value, {
      description: description.value,
      tags: tags.value
    });
    
    clearInterval(progressInterval);
    uploadProgress.value = 100;
    
    // 发出上传成功事件
    emit('upload-success', response.data);
    
    // 清空表单
    resetForm();
    
  } catch (error) {
    console.error('上传文件失败', error);
    emit('upload-error', error.response?.data?.detail || '上传文件失败，请重试');
  } finally {
    setTimeout(() => {
      isUploading.value = false;
      uploadProgress.value = 0;
    }, 1000);
  }
};

// 重置表单
const resetForm = () => {
  file.value = null;
  description.value = '';
  tags.value = '';
  
  // 重置文件输入
  const fileInput = document.getElementById('file-input');
  if (fileInput) {
    fileInput.value = '';
  }
};
</script>

<template>
  <div class="document-upload">
    <h3 class="text-lg font-semibold mb-4">上传文档到知识库</h3>
    
    <!-- 文件拖放区域 -->
    <div 
      class="file-drop-area"
      :class="{ 'drag-over': dragOver, 'has-file': file }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
    >
      <div class="file-drop-content">
        <svg v-if="!file" xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        
        <div v-if="file" class="selected-file">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          <span class="file-name">{{ file.name }}</span>
        </div>
        <span v-else class="drop-text">拖放文件到此处或</span>
        
        <label v-if="!file" class="browse-button">
          浏览文件
          <input 
            type="file" 
            id="file-input"
            @change="handleFileChange" 
            accept=".pdf,.doc,.docx,.txt,.md,.rtf"
            hidden
          >
        </label>
      </div>
    </div>
    
    <!-- 上传进度条 -->
    <div v-if="isUploading" class="progress-bar">
      <div class="progress" :style="{ width: uploadProgress + '%' }"></div>
    </div>
    
    <!-- 表单字段 -->
    <div class="form-fields">
      <div class="form-group">
        <label for="description">描述 (可选)</label>
        <textarea 
          id="description"
          v-model="description"
          placeholder="添加对文档的描述..."
          rows="2"
        ></textarea>
      </div>
      
      <div class="form-group">
        <label for="tags">标签 (可选)</label>
        <input 
          id="tags"
          v-model="tags"
          placeholder="添加标签，以逗号分隔..."
          type="text"
        >
      </div>
    </div>
    
    <!-- 操作按钮 -->
    <div class="actions">
      <button 
        @click="resetForm" 
        class="cancel-button"
        :disabled="isUploading"
      >
        取消
      </button>
      <button 
        @click="uploadFile" 
        class="upload-button"
        :disabled="!file || isUploading"
      >
        {{ isUploading ? '上传中...' : '上传' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.document-upload {
  background-color: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
}

.file-drop-area {
  border: 2px dashed #e5e7eb;
  border-radius: 0.5rem;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
  margin-bottom: 1.5rem;
}

.file-drop-area.drag-over {
  border-color: #4f46e5;
  background-color: rgba(79, 70, 229, 0.05);
}

.file-drop-area.has-file {
  border-color: #10b981;
  background-color: rgba(16, 185, 129, 0.05);
}

.file-drop-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
}

.drop-text {
  margin-top: 0.5rem;
}

.browse-button {
  background-color: #f3f4f6;
  color: #4b5563;
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.2s;
}

.browse-button:hover {
  background-color: #e5e7eb;
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #10b981;
}

.file-name {
  font-size: 0.875rem;
  font-weight: 500;
}

.progress-bar {
  width: 100%;
  height: 0.5rem;
  background-color: #e5e7eb;
  border-radius: 0.25rem;
  overflow: hidden;
  margin-bottom: 1.5rem;
}

.progress {
  height: 100%;
  background-color: #4f46e5;
  transition: width 0.3s ease;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #4b5563;
}

textarea, input {
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  resize: none;
  outline: none;
}

textarea:focus, input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.1);
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.cancel-button {
  padding: 0.625rem 1.25rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  background-color: white;
  color: #4b5563;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-button:hover:not(:disabled) {
  background-color: #f9fafb;
}

.upload-button {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 0.375rem;
  background-color: #4f46e5;
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-button:hover:not(:disabled) {
  background-color: #4338ca;
}

.upload-button:disabled, .cancel-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
