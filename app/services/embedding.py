"""
嵌入服务 - 负责生成文本的向量表示
"""
from typing import List
import google.generativeai as genai

from ..config import settings
from ..utils.logger import vectorstore_logger
from .llm import llm_service

class EmbeddingService:
    def __init__(self):
        """初始化嵌入服务"""
        vectorstore_logger.info("初始化嵌入服务...")
        genai.configure(api_key=settings.llm.google_api_key)
        self.model = settings.llm.gemini_embedding_model
        
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        获取文本的向量表示
        
        Args:
            texts: 文本列表
            
        Returns:
            List[List[float]]: 向量表示列表
        """
        try:
            vectorstore_logger.info(f"开始生成嵌入向量: {len(texts)} 条文本")
            embeddings = []
            
            for text in texts:
                result = await genai.embed_content_async(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
                
            vectorstore_logger.info("嵌入向量生成完成")
            return embeddings
            
        except Exception as e:
            vectorstore_logger.error(f"生成嵌入向量时出错: {str(e)}", exc_info=True)
            raise

# 创建全局嵌入服务实例
embedding_service = EmbeddingService() 