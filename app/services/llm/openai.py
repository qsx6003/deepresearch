"""
OpenAI LLM服务实现
"""
from typing import List, AsyncGenerator
from openai import AsyncOpenAI
import json

from ...config import settings
from ...utils.logger import llm_logger
from .base import BaseLLMService

class OpenAIService(BaseLLMService):
    def __init__(self):
        """初始化OpenAI服务"""
        llm_logger.info("初始化OpenAI API...")
        self.client = AsyncOpenAI(
            api_key=settings.llm.openai_api_key,
            base_url=settings.llm.openai_api_base
        )
        
    def _build_summary_messages(self, query: str, contexts: List[str]) -> List[dict]:
        """构建OpenAI消息"""
        context_text = "\n\n".join(contexts)
        return [
            {"role": "system", "content": "你是一个专业的搜索助手，负责基于检索到的内容回答问题。"},
            {"role": "user", "content": f"""基于以下内容回答问题:

问题: {query}

相关内容:
{context_text}

请提供一个全面、准确的回答。回答应该:
1. 直接回答问题
2. 基于提供的内容
3. 保持客观
4. 如果内容不足以回答问题，请说明"""}
        ]
        
    async def generate_summary(
        self,
        query: str,
        contexts: List[str]
    ) -> str:
        """生成摘要"""
        llm_logger.info(f"开始生成摘要: query={query}")
        try:
            # 构建消息
            messages = self._build_summary_messages(query, contexts)
            
            # 调用API
            llm_logger.info("调用OpenAI API...")
            response = await self.client.chat.completions.create(
                model=settings.llm.openai_chat_model,
                messages=messages,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            llm_logger.error(f"生成摘要时出错: {str(e)}", exc_info=True)
            raise
            
    async def generate_summary_stream(
        self,
        query: str,
        contexts: List[str]
    ) -> AsyncGenerator[str, None]:
        """流式生成摘要"""
        llm_logger.info(f"开始流式生成摘要: query={query}")
        try:
            # 构建消息
            messages = self._build_summary_messages(query, contexts)
            
            # 调用API
            llm_logger.info("调用OpenAI流式API...")
            response = await self.client.chat.completions.create(
                model=settings.llm.openai_chat_model,
                messages=messages,
                temperature=0.7,
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            llm_logger.error(f"流式生成摘要时出错: {str(e)}", exc_info=True)
            yield json.dumps({"error": str(e)})

    async def extract_content(self, query: str, contexts: List[str], mode: str = "default") -> str:
        """
        从上下文中提取相关内容并生成摘要
        """
        llm_logger.info(f"开始提取内容: query={query}, mode={mode}")
        try:
            # 构建提示
            prompt = self._build_summary_prompt(query, contexts)

            # 构建消息
            messages = [
                {"role": "system", "content": "你是一个专业的内容提取和总结助手。"},
                {"role": "user", "content": prompt}
            ]

            # 调用API
            llm_logger.info("调用OpenAI API进行内容提取...")
            response = await self.client.chat.completions.create(
                model=settings.llm.openai_chat_model,
                messages=messages,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            llm_logger.error(f"提取内容时出错: {str(e)}", exc_info=True)
            raise

    async def extract_content_stream(
        self,
        query: str,
        contexts: List[str],
        mode: str = "default"
    ) -> AsyncGenerator[str, None]:
        """
        流式从上下文中提取相关内容并生成摘要
        """
        llm_logger.info(f"开始流式提取内容: query={query}, mode={mode}")
        try:
            # 构建提示
            prompt = self._build_summary_prompt(query, contexts)

            # 构建消息
            messages = [
                {"role": "system", "content": "你是一个专业的内容提取和总结助手。"},
                {"role": "user", "content": prompt}
            ]

            # 调用API
            llm_logger.info("调用OpenAI流式API进行内容提取...")
            response = await self.client.chat.completions.create(
                model=settings.llm.openai_chat_model,
                messages=messages,
                temperature=0.7,
                stream=True
            )

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            llm_logger.error(f"流式提取内容时出错: {str(e)}", exc_info=True)
            yield json.dumps({"error": str(e)})