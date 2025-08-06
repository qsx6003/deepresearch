"""
Gemini LLM服务实现
"""
from typing import List, AsyncGenerator
import google.generativeai as genai
import json
import warnings

from ...config import settings
from ...utils.logger import llm_logger
from .base import BaseLLMService

class GeminiService(BaseLLMService):
    def __init__(self):
        """初始化Gemini服务"""
        llm_logger.info("初始化Gemini API...")
        
        # 禁用遥测警告
        warnings.filterwarnings('ignore', message='Failed to send telemetry event')
        
        genai.configure(api_key=settings.llm.google_api_key)
        self.model = genai.GenerativeModel(settings.llm.gemini_chat_model)
        
    async def generate_query(
        self,
        query: str,
        contexts: List[str]
    ) -> str:
        """生成摘要"""
        llm_logger.info(f"开始生成摘要: query={query}")
        try:
            # 构建提示
            prompt = self._build_query_prompt(query, contexts)
            
            # 调用API
            llm_logger.info("调用Gemini API...contexts={contexts}")
            response = await self.model.generate_content_async(prompt)
            
            return response.text
            
        except Exception as e:
            llm_logger.error(f"生成摘要时出错: {str(e)}", exc_info=True)
            raise


    async def generate_summary(
            self,
            query: str,
            contexts: List[str]
        ) -> str:
            """生成摘要"""
            # 清理查询中的特殊字符以避免编码错误
            clean_query = query.replace('\xa0', ' ').replace('\u2028', ' ').replace('\u2029', ' ')
            llm_logger.info(f"开始生成摘要: query={clean_query[:200]}...")
            try:
                # 构建提示
                prompt = self._build_summary_prompt(query, contexts)
                
                # 调用API
                llm_logger.info("调用Gemini API...contexts={prompt}")
                response = await self.model.generate_content_async(prompt)
                
                return response.text
                
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
            # 构建提示
            prompt = self._build_summary_prompt(query, contexts)
            
            # 调用API
            llm_logger.info("调用Gemini流式API...")
            response = await self.model.generate_content_async(
                prompt,
                stream=True
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
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

            # 调用API
            llm_logger.info("调用Gemini API进行内容提取...{prompt}")
            response = await self.model.generate_content_async(prompt)

            return response.text

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

            # 调用API
            llm_logger.info("调用Gemini流式API进行内容提取...")
            response = await self.model.generate_content_async(
                prompt,
                stream=True
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            llm_logger.error(f"流式提取内容时出错: {str(e)}", exc_info=True)
            yield json.dumps({"error": str(e)})