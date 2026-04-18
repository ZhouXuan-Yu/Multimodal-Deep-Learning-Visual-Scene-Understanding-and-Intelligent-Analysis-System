"""
嵌入服务 - 负责将文本转换为向量表示
使用sentence-transformers生成文本嵌入
"""

from sentence_transformers import SentenceTransformer
import os
import numpy as np
import logging

# 配置日志
logger = logging.getLogger(__name__)

class EmbeddingService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            # 初始化嵌入模型
            try:
                # 使用轻量级模型
                cls._instance.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                cls._instance.dimension = cls._instance.model.get_sentence_embedding_dimension()
                logger.info(f"✅ 嵌入模型加载成功，向量维度: {cls._instance.dimension}")
            except Exception as e:
                logger.error(f"❌ 嵌入模型加载失败: {str(e)}")
                raise
        return cls._instance
    
    def encode(self, texts):
        """将文本编码为向量"""
        if not isinstance(texts, list):
            texts = [texts]
        
        # 生成嵌入
        embeddings = self.model.encode(texts, show_progress_bar=len(texts) > 100)
        return embeddings.astype(np.float32)
    
    def similarity(self, text1, text2):
        """计算两个文本的相似度"""
        vec1 = self.encode(text1)
        vec2 = self.encode(text2)
        # 计算余弦相似度
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# 创建单例实例
try:
    embedding_service = EmbeddingService()
    logger.info("嵌入服务初始化成功")
except Exception as e:
    logger.error(f"嵌入服务初始化失败: {str(e)}")
    embedding_service = None
