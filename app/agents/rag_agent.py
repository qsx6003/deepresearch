"""
RAG代理 - 负责处理检索增强生成
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
import json

from ..config import settings
from ..models.schemas import SearchResult, Summary
from ..services.llm import llm_service
from ..services.vectorstore import vector_store_service
from ..utils.logger import rag_logger

class RAGAgent:
    async def process(
        self,
        query: str,
        search_results: List[SearchResult],
        mode: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        处理RAG请求，生成摘要
        
        Args:
            query: 查询文本
            search_results: 搜索结果列表
            mode: 处理模式 (default/pro)
            
        Returns:
            Optional[Dict[str, Any]]: 包含摘要和相关信息的字典，如果失败则返回None
        """
        rag_logger.info(f"开始RAG处理: query={query}, mode={mode}")
        
        try:
            if not search_results:
                rag_logger.warning("没有搜索结果可处理")
                return None
                
            # 准备文本和元数据
            texts = []
            metadatas = []
            
            for result in search_results:
                # 合并标题和片段
                text = f"标题: {result.title}\n\n{result.snippet}"
                texts.append(text)
                
                # 准备元数据
                metadata = {
                    "url": result.url,
                    "title": result.title,
                    "source": "search"
                }
                metadatas.append(metadata)
            
            # 向量存储处理
            rag_logger.info("添加搜索结果到向量存储...")
            await vector_store_service.add_texts(texts, metadatas)

            # 直接使用当前搜索结果，而不是进行相似度搜索
            # 这样可以确保我们使用的是与当前查询最相关的内容
            rag_logger.info("使用当前搜索结果进行RAG处理...")
            similar_results = {
                "documents": [texts],
                "metadatas": [metadatas],
                "distances": [[0.0] * len(texts)]  # 假设距离为0，表示完全匹配
            }
            
            if not similar_results or not similar_results.get("documents"):
                rag_logger.warning("没有找到相关文档")
                return None
                
            # 准备上下文
            contexts = []
            chunks = []
            for i, doc in enumerate(similar_results["documents"][0]):
                metadata = similar_results["metadatas"][0][i]
                distance = similar_results["distances"][0][i]
                similarity_score = 1 - distance
                
                context = f"""
来源: {metadata.get('title', '未知标题')}
URL: {metadata.get('url', '未知来源')}
相关度: {similarity_score:.2f}

内容:
{doc}
"""
                contexts.append(context)
                
                # 保存chunk信息
                chunks.append({
                    "title": metadata.get('title', '未知标题'),
                    "url": metadata.get('url', '未知来源'),
                    "content": doc,
                    "score": similarity_score
                })
            
            # 生成摘要
            rag_logger.info("生成文档摘要...")
            extract = await llm_service.extract_content(
                query=query,
                contexts=contexts,
                mode=mode
            )
            
            if not extract:
                rag_logger.error("无法生成文档摘要")
                return None
                
            # 提取来源信息
            sources = [meta.get("url", "") for meta in similar_results["metadatas"][0]]
            # 过滤掉空的URL
            sources = [url for url in sources if url and url.strip()]

            rag_logger.info(f"提取到 {len(sources)} 个来源: {sources[:3]}...")  # 只显示前3个

            # 返回RAG处理结果
            result = {
                "extract": extract,  # 文档摘要
                "chunks": chunks,    # 相关文本块
                "sources": sources   # 来源
            }

            rag_logger.info("RAG处理完成")
            return result
            
        except Exception as e:
            rag_logger.error(f"RAG处理出错: {str(e)}", exc_info=True)
            return None

    async def process_stream(
        self,
        query: str,
        search_results: List[SearchResult],
        mode: str = "default"
    ) -> AsyncGenerator[str, None]:
        """
        流式处理RAG请求
        """
        rag_logger.info(f"开始流式RAG处理: query={query}, mode={mode}")
        try:
            # 向量存储处理
            rag_logger.info("添加搜索结果到向量存储...")
            await vector_store_service.add_texts(
                [result.snippet for result in search_results],
                [{"title": result.title, "url": result.url} for result in search_results]
            )
            
            # 相似度搜索
            rag_logger.info("执行相似度搜索...")
            similar_results = await vector_store_service.similarity_search(
                query,
                k=settings.rag.pro_chunk_size if mode == "pro" else settings.rag.default_chunk_size
            )
            
            if not similar_results or not similar_results.get("documents"):
                rag_logger.warning("没有找到相关文档")
                yield json.dumps({"error": "No relevant documents found"})
                return
                
            # 流式生成摘要
            rag_logger.info("开始流式生成摘要...")
            async for chunk in llm_service.extract_content_stream(
                query=query,
                contexts=similar_results["documents"][0],
                mode=mode
            ):
                yield chunk
                
            rag_logger.info("流式摘要生成完成")
            
        except Exception as e:
            rag_logger.error(f"流式RAG处理出错: {str(e)}", exc_info=True)
            yield json.dumps({"error": str(e)})

# 创建全局RAG代理实例
rag_agent = RAGAgent() 