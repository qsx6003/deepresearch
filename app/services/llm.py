"""
LLM服务 - 负责与大语言模型交互
"""
from typing import List, AsyncGenerator
import google.generativeai as genai
from openai import AsyncOpenAI
import json

from ..config import settings
from ..utils.logger import llm_logger

class LLMService:
    def __init__(self):
        self.provider = settings.llm.provider
        
        # 初始化Google API
        if self.provider == "gemini":
            llm_logger.info("初始化Gemini API...")
            genai.configure(api_key=settings.llm.google_api_key)
            self.model = genai.GenerativeModel(settings.llm.gemini_chat_model)
            
        # 初始化OpenAI API
        elif self.provider == "openai":
            llm_logger.info("初始化OpenAI API...")
            self.client = AsyncOpenAI(
                api_key=settings.llm.openai_api_key,
                base_url=settings.llm.openai_api_base
            )
            
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
            
    async def generate_summary(
        self,
        query: str,
        contexts: List[str]
    ) -> str:
        """
        生成摘要
        """
        llm_logger.info(f"开始生成摘要: query={query}")
        try:
            if self.provider == "gemini":
                # 构建提示
                prompt = self._build_summary_prompt(query, contexts)
                
                # 调用API
                llm_logger.info("调用Gemini API...")
                response = await self.model.generate_content_async(prompt)
                
                return response.text
                
            elif self.provider == "openai":
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
        """
        流式生成摘要
        """
        llm_logger.info(f"开始流式生成摘要: query={query}")
        try:
            if self.provider == "gemini":
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
                        
            elif self.provider == "openai":
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
            
    def _build_summary_prompt(self, query: str, contexts: List[str]) -> str:
        """构建Gemini提示"""
        context_text = "\n\n".join(contexts)
        return f"""基于以下内容回答问题:

问题: {query}

相关内容:
{context_text}

请提供一个全面、准确的回答。回答应该:
1. 直接回答问题
2. 基于提供的内容
3. 保持客观
4. 如果内容不足以回答问题，请说明"""

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

# 创建全局LLM服务实例
llm_service = LLMService() 