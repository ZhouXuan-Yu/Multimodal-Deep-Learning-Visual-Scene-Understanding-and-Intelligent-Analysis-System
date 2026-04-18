"""
文本处理服务 - 负责文档分割和处理
将文档处理成适合存储和检索的文本块
"""

import re
import os
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional

# 配置日志
logger = logging.getLogger(__name__)

class TextProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """将文本分割成多个块"""
        # 如果文本长度小于chunk_size，直接返回
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            # 确定当前块的结束位置
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在句子边界处分割
            if end < len(text):
                # 向后找到最近的句子结束标记
                punctuations = ['.', '!', '?', '。', '！', '？', '\n\n']
                found_boundary = False
                
                # 在chunk_size范围内找到句子结束
                for i in range(end, max(start, end - 100), -1):
                    if i < len(text) and text[i] in punctuations:
                        end = i + 1  # 包含标点符号
                        found_boundary = True
                        break
                
                # 如果没找到句子边界，就直接在单词边界分割
                if not found_boundary:
                    end = end  # 在原来位置分割
            
            # 添加当前文本块
            chunks.append(text[start:end])
            
            # 更新起始位置，考虑重叠
            start = end - self.chunk_overlap
            
            # 确保起始位置有效
            if start < 0:
                start = 0
        
        return chunks
    
    def process_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """处理文档文本，返回处理后的文档块和元数据"""
        # 分割文本
        chunks = self.split_text(content)
        
        # 为每个块生成ID和添加元数据
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            # 生成唯一ID
            chunk_id = hashlib.md5(f"{chunk}_{i}".encode()).hexdigest()
            
            # 创建文档块对象
            doc_chunk = {
                "id": chunk_id,
                "text": chunk,
                "metadata": {
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            }
            
            # 添加额外元数据
            if metadata:
                doc_chunk["metadata"].update(metadata)
            
            processed_chunks.append(doc_chunk)
        
        return processed_chunks
    
    def read_and_process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """读取文件并处理内容"""
        # 提取文件元数据
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        metadata = {
            "source": file_path,
            "file_name": file_name,
            "file_type": file_ext[1:] if file_ext else "txt"
        }
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 处理文档
            chunks = self.process_document(content, metadata)
            logger.info(f"成功处理文件 {file_name}，生成了 {len(chunks)} 个文本块")
            return chunks
        except UnicodeDecodeError:
            # 尝试使用其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                chunks = self.process_document(content, metadata)
                logger.info(f"成功处理GBK编码文件 {file_name}，生成了 {len(chunks)} 个文本块")
                return chunks
            except Exception as e:
                logger.error(f"处理文件时发生错误 {file_name}: {str(e)}")
                return []
        except Exception as e:
            logger.error(f"处理文件时发生错误 {file_name}: {str(e)}")
            return []
    
    def save_processed_chunks(self, chunks: List[Dict[str, Any]], output_dir: str):
        """保存处理后的文档块"""
        os.makedirs(output_dir, exist_ok=True)
        
        saved_ids = []
        for chunk in chunks:
            chunk_id = chunk["id"]
            file_path = os.path.join(output_dir, f"{chunk_id}.json")
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(chunk, f, ensure_ascii=False, indent=2)
                saved_ids.append(chunk_id)
            except Exception as e:
                logger.error(f"保存文档块失败 {chunk_id}: {str(e)}")
        
        logger.info(f"成功保存 {len(saved_ids)}/{len(chunks)} 个文档块")
        return saved_ids

# 创建实例
text_processor = TextProcessor()
logger.info("文本处理服务初始化成功")
