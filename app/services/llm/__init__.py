"""
LLM服务包
"""
from .base import BaseLLMService
from .gemini import GeminiService
from .openai import OpenAIService

# 根据配置创建合适的服务实例
from ...config import settings
from ...utils.logger import llm_logger

# 全局服务实例
_llm_service = None

def get_llm_service() -> BaseLLMService:
    """获取LLM服务实例（单例模式）"""
    global _llm_service
    
    if _llm_service is None:
        if settings.llm.provider == "gemini":
            _llm_service = GeminiService()
        elif settings.llm.provider == "openai":
            _llm_service = OpenAIService()
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm.provider}")
            
    return _llm_service

# 导出服务实例
llm_service = get_llm_service()
__all__ = ["llm_service"] 