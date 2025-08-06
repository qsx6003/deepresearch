"""
向量存储服务 - 负责管理和检索文本向量
使用FAISS作为向量数据库
"""
import numpy as np
from typing import List, Dict, Any
from pathlib import Path
import faiss
import pickle
import json
import asyncio
from datetime import datetime

from ..config import settings
from ..utils.logger import vectorstore_logger
from .embedding import embedding_service

class VectorStoreService:
    def __init__(self):
        """初始化向量存储服务"""
        vectorstore_logger.info("初始化向量存储服务...")
        
        # 确保向量存储目录存在
        self.vector_store_path = Path(settings.rag.vector_store_path)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # FAISS索引文件路径
        self.index_path = self.vector_store_path / "faiss.index"
        # 元数据文件路径
        self.metadata_path = self.vector_store_path / "metadata.pkl"
        # 文档内容文件路径
        self.documents_path = self.vector_store_path / "documents.pkl"
        
        try:
            self._load_or_create_index()
            vectorstore_logger.info("向量存储服务初始化完成")
        except Exception as e:
            vectorstore_logger.error(f"初始化向量存储服务时发生错误: {str(e)}", exc_info=True)
            raise
            
    def _load_or_create_index(self):
        """加载或创建FAISS索引"""
        try:
            if self.index_path.exists() and self.metadata_path.exists() and self.documents_path.exists():
                # 加载现有索引和数据
                self.index = faiss.read_index(str(self.index_path))
                with open(self.metadata_path, 'rb') as f:
                    self.metadatas = pickle.load(f)
                with open(self.documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                vectorstore_logger.info(f"加载了现有索引，包含 {self.index.ntotal} 个向量")
            else:
                # 创建新索引
                self.index = faiss.IndexFlatIP(768)  # 使用内积(IP)相似度，维度为768
                self.metadatas = []
                self.documents = []
                vectorstore_logger.info("创建了新的FAISS索引")
                
        except Exception as e:
            vectorstore_logger.error(f"加载或创建索引时出错: {str(e)}", exc_info=True)
            raise
            
    def _save_index(self):
        """保存索引和相关数据"""
        try:
            faiss.write_index(self.index, str(self.index_path))
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadatas, f)
            with open(self.documents_path, 'wb') as f:
                pickle.dump(self.documents, f)
            vectorstore_logger.info("索引和数据保存成功")
        except Exception as e:
            vectorstore_logger.error(f"保存索引时出错: {str(e)}", exc_info=True)
            raise
            
    async def add_texts(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]] = None
    ) -> None:
        """
        添加文本到向量存储
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
        """
        try:
            if not texts:
                vectorstore_logger.warning("没有文本需要添加到向量存储")
                return
                
            vectorstore_logger.info(f"开始添加 {len(texts)} 条文本到向量存储")
            
            # 生成嵌入向量
            vectorstore_logger.info(f"开始生成嵌入向量，共 {len(texts)} 条文本")
            embeddings = await embedding_service.get_embeddings(texts)
            vectorstore_logger.info(f"嵌入向量生成完成，维度: {len(embeddings[0])}")
            
            # 准备元数据
            if not metadatas:
                metadatas = [{"source": "default", "timestamp": datetime.now().isoformat()} for _ in texts]
                
            # 添加到FAISS
            embeddings_array = np.array(embeddings).astype('float32')
            self.index.add(embeddings_array)
            
            # 保存文档和元数据
            self.documents.extend(texts)
            self.metadatas.extend(metadatas)
            
            # 保存到磁盘
            self._save_index()
            
            vectorstore_logger.info("文本添加完成")
            
        except Exception as e:
            vectorstore_logger.error(f"添加文本时出错: {str(e)}", exc_info=True)
            raise
            
    async def similarity_search(
        self,
        query: str,
        k: int = 4
    ) -> Dict[str, List]:
        """
        执行相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            
        Returns:
            Dict[str, List]: 搜索结果，包含文档和相似度分数
        """
        try:
            if not query:
                vectorstore_logger.warning("查询文本为空")
                return self._empty_results()
                
            vectorstore_logger.info(f"执行相似度搜索: query='{query[:50]}...', k={k}")
            
            # 生成查询向量
            query_embedding = (await embedding_service.get_embeddings([query]))[0]
            query_embedding = np.array([query_embedding]).astype('float32')
            
            # 执行搜索
            if self.index.ntotal == 0:
                vectorstore_logger.warning("索引为空，无法搜索")
                return self._empty_results()
                
            # FAISS搜索
            distances, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
            
            # 准备返回结果
            results = {
                "documents": [[self.documents[i] for i in indices[0]]],
                "distances": [[(1 - d) for d in distances[0]]],  # 转换为相似度分数
                "metadatas": [[self.metadatas[i] for i in indices[0]]]
            }
            
            vectorstore_logger.info(f"找到 {len(results['documents'][0])} 个相关文档")
            return results
            
        except Exception as e:
            vectorstore_logger.error(f"相似度搜索时出错: {str(e)}", exc_info=True)
            raise
            
    def _empty_results(self) -> Dict[str, List]:
        """返回空结果"""
        return {
            "documents": [[]],
            "distances": [[]],
            "metadatas": [[]]
        }
            
    async def clear(self):
        """清空向量存储"""
        try:
            vectorstore_logger.info("开始清空向量存储...")
            # 创建新的空索引
            self.index = faiss.IndexFlatIP(768)
            self.metadatas = []
            self.documents = []
            # 保存空索引
            self._save_index()
            vectorstore_logger.info("向量存储清空完成")
        except Exception as e:
            vectorstore_logger.error(f"清空向量存储时出错: {str(e)}", exc_info=True)
            raise

# 创建全局向量存储服务实例
vector_store_service = VectorStoreService()