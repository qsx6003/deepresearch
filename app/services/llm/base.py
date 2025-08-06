"""
LLM服务基类
"""
from typing import List, AsyncGenerator
from abc import ABC, abstractmethod

class BaseLLMService(ABC):
    @abstractmethod
    async def generate_summary(
        self,
        query: str,
        contexts: List[str]
    ) -> str:
        """生成摘要"""
        pass
        
    @abstractmethod
    async def generate_summary_stream(
        self,
        query: str,
        contexts: List[str]
    ) -> AsyncGenerator[str, None]:
        """流式生成摘要"""
        pass
        
    @abstractmethod
    async def extract_content(self, query: str, contexts: List[str], mode: str = "default") -> str:
        """
        从上下文中提取相关内容并生成摘要
        
        Args:
            query: 查询文本
            contexts: 上下文列表
            mode: 处理模式 (default/pro)
            
        Returns:
            str: 生成的摘要文本
        """
        pass
        
    @abstractmethod
    async def extract_content_stream(
        self,
        query: str,
        contexts: List[str],
        mode: str = "default"
    ) -> AsyncGenerator[str, None]:
        """
        流式从上下文中提取相关内容并生成摘要
        
        Args:
            query: 查询文本
            contexts: 上下文列表
            mode: 处理模式 (default/pro)
            
        Yields:
            str: 生成的摘要文本片段
        """
        pass
    
    def _build_query_prompt(self, query: str, contexts: List[str]) -> str:
        """构建提示"""
        context_text = "\n\n".join(contexts)
        return f"""

你是一个专业的搜索查询翻译器。你的任务是将用户的自然语言搜索词转化为高效、优化的搜索引擎查询。

请考虑以下几点：
* **关键词识别：** 从用户输入中提取最核心的关键词。
* **具体性：** 如果用户的请求比较模糊，请推断出搜索引擎能更好理解的更具体术语。
* **同义词/相关词：** 考虑可能带来更好搜索结果的同义词或紧密相关的词汇。
* **用户意图：** 理解用户搜索的根本目的。他们是在查找信息、产品、服务、定义、操作指南等等？

**用户搜索词：** [{context_text}]

**请将此词组翻译成一个优化的搜索引擎查询。只输出优化后的查询，不包含任何额外文字或解释。**"""
    

    def _build_summary_prompt(self, query: str, contexts: List[str]) -> str:
            """构建提示"""
            context_text = "\n\n".join(contexts)
            return f"""

    你是一位专业的知识整合者。请阅读以下提供的多条搜索结果或文章内容。你的任务是综合这些信息，生成一份清晰、连贯且准确的总结。
    用户的搜索是：{query}

    **总结要求：**
    - **全面性：** 覆盖所有搜索结果中提到的关键事实、观点和发现。
    - **简洁性：** 去除重复信息，避免冗余，聚焦核心内容。
    - **结构化：** 将相关信息归类，使总结逻辑清晰，易于理解。
    - **客观性：** 仅陈述信息，不添加个人观点或评论。

    **搜索结果/文章内容：**
    [{context_text}]

    **请根据以上内容，生成一份综合总结。**
    """