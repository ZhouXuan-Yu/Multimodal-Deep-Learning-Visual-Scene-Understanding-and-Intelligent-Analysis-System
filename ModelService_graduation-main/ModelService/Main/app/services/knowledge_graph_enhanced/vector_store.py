"""
向量存储服务 - 使用FAISS进行高效向量检索
负责文本向量的存储和相似性搜索
"""

import os
import json
import pickle
import numpy as np
import faiss
import logging
from typing import List, Dict, Any, Optional, Tuple
from .embedding import embedding_service

# 配置日志
logger = logging.getLogger(__name__)

# 默认数据路径
DEFAULT_INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                  "data", "faiss_indexes")

class VectorStore:
    def __init__(self, index_path: str = DEFAULT_INDEX_PATH):
        self.index_path = index_path
        self.dimension = embedding_service.dimension if embedding_service else 384
        self.index = None
        self.document_map = {}  # ID映射到文档内容
        
        # 确保索引目录存在
        os.makedirs(index_path, exist_ok=True)
        
        # 尝试加载现有索引
        self._load_index()
    
    def _load_index(self):
        """加载FAISS索引"""
        index_file = os.path.join(self.index_path, "faiss.index")
        map_file = os.path.join(self.index_path, "document_map.pkl")
        
        if os.path.exists(index_file) and os.path.exists(map_file):
            try:
                self.index = faiss.read_index(index_file)
                with open(map_file, 'rb') as f:
                    self.document_map = pickle.load(f)
                logger.info(f"✅ 成功加载FAISS索引，包含{self.index.ntotal}个向量")
                return True
            except Exception as e:
                logger.error(f"❌ 加载FAISS索引失败: {str(e)}")
        
        # 如果没有加载成功，创建新索引
        self.index = faiss.IndexFlatL2(self.dimension)
        logger.info(f"⚠️ 未找到现有索引，已创建新的FAISS索引(维度:{self.dimension})")
        return False
    
    def _save_index(self):
        """保存FAISS索引"""
        if self.index is None:
            return
        
        index_file = os.path.join(self.index_path, "faiss.index")
        map_file = os.path.join(self.index_path, "document_map.pkl")
        
        try:
            faiss.write_index(self.index, index_file)
            with open(map_file, 'wb') as f:
                pickle.dump(self.document_map, f)
            logger.info(f"✅ 成功保存FAISS索引，包含{self.index.ntotal}个向量")
            return True
        except Exception as e:
            logger.error(f"❌ 保存FAISS索引失败: {str(e)}")
            return False
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """添加文档到向量存储"""
        if not documents:
            return []
        
        if embedding_service is None:
            logger.error("❌ 嵌入服务未初始化，无法添加文档")
            return []
        
        # 提取文本
        texts = [doc["text"] for doc in documents]
        
        # 生成向量
        try:
            vectors = embedding_service.encode(texts)
            
            # 获取当前索引大小作为起始ID
            start_id = self.index.ntotal
            
            # 添加向量到索引
            self.index.add(vectors)
            
            # 更新文档映射
            for i, doc in enumerate(documents):
                vector_id = start_id + i
                self.document_map[vector_id] = doc
            
            # 保存索引
            self._save_index()
            
            logger.info(f"✅ 成功添加{len(documents)}个文档到向量存储")
            # 返回向量ID
            return list(range(start_id, start_id + len(documents)))
        
        except Exception as e:
            logger.error(f"❌ 添加文档到向量存储失败: {str(e)}")
            return []
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """搜索最相似的文档"""
        if self.index is None or self.index.ntotal == 0:
            logger.warning("⚠️ 向量索引为空，无法执行搜索")
            return []
        
        if embedding_service is None:
            logger.error("❌ 嵌入服务未初始化，无法执行搜索")
            return []
        
        # 生成查询向量
        try:
            query_vector = embedding_service.encode(query)
            
            # 搜索
            distances, indices = self.index.search(np.array([query_vector]), k)
            
            # 构建结果
            results = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx in self.document_map:  # 有效的索引
                    doc = self.document_map[idx]
                    # 计算归一化分数 (1 表示完全匹配)
                    score = 1.0 - min(distances[0][i] / 100.0, 0.99)
                    
                    results.append({
                        "id": doc.get("id", str(idx)),
                        "text": doc["text"],
                        "metadata": doc.get("metadata", {}),
                        "score": float(score),
                        "vector_id": int(idx)
                    })
            
            return results
        except Exception as e:
            logger.error(f"❌ 向量搜索失败: {str(e)}")
            return []
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """通过文档ID获取文档"""
        for vector_id, doc in self.document_map.items():
            if doc.get("id") == doc_id:
                return doc
        return None
    
    def get_document_by_vector_id(self, vector_id: int) -> Optional[Dict[str, Any]]:
        """通过向量ID获取文档"""
        return self.document_map.get(vector_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档 (注意：FAISS不支持直接删除，这里只从映射中移除)"""
        # 找到对应的向量ID
        vector_ids_to_remove = []
        for vector_id, doc in self.document_map.items():
            if doc.get("id") == doc_id:
                vector_ids_to_remove.append(vector_id)
        
        if not vector_ids_to_remove:
            return False
        
        # 从映射中移除
        for vector_id in vector_ids_to_remove:
            del self.document_map[vector_id]
        
        # 保存索引
        self._save_index()
        
        # 注意：向量仍然在FAISS索引中，但不会被返回
        logger.warning(f"⚠️ 文档ID: {doc_id} 已从映射中移除，但向量仍在FAISS索引中")
        return True

# 创建单例实例
try:
    vector_store = VectorStore()
    logger.info("向量存储服务初始化成功")
except Exception as e:
    logger.error(f"向量存储服务初始化失败: {str(e)}")
    vector_store = None
