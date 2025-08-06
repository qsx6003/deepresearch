"""
配置模块，用于加载和管理应用配置
"""
import os
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent

class LLMConfig(BaseSettings):
    """LLM相关配置"""
    provider: Literal["openai", "gemini"] = "gemini"

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_api_base: str = "https://api.openai.com/v1"
    openai_chat_model: str = "gpt-3.5-turbo"
    openai_embedding_model: str = "text-embedding-ada-002"

    # Google
    google_api_key: str = ""
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "models/embedding-001"

    # ReAct 相关配置
    react_enabled: bool = True
    react_model: str = "gemini/gemini-2.0-flash"  # 使用 Google AI Studio 路径
    react_max_iterations: int = 10
    react_complexity_threshold: float = 0.7

    class Config:
        env_file = ".env"
        env_prefix = ""

class SearchConfig(BaseSettings):
    """搜索相关配置"""
    # Google Search (需要启用 Custom Search API)
    google_cx: Optional[str] = None
    google_api_key: str = ""

    # Bing Search (需要有效的 Bing API key)
    bing_api_key: Optional[str] = None

    # Other Search APIs (推荐使用)
    serper_api_key: Optional[str] = None  # 获取: https://serper.dev/
    serpapi_api_key: Optional[str] = None  # 获取: https://serpapi.com/

class RAGConfig(BaseSettings):
    """RAG相关配置"""
    # Embedding
    embedding_provider: Literal["openai", "gemini"] = "gemini"
    
    # Vector Store
    vector_store_type: Literal["chroma"] = "chroma"
    vector_store_path: Path = ROOT_DIR / "data" / "vector_store"
    collection_name: str = "search_results"
    
    # Chunk Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4

class ServiceConfig(BaseSettings):
    """服务配置"""
    # 服务器设置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # 处理设置
    max_search_results: int = 10
    max_retries: int = 3
    timeout: int = 30
    
    # HTTP客户端设置
    http_timeout: int = 30
    max_connections: int = 100
    
    # 缓存设置
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1小时
    
    # 并发设置
    max_concurrent_requests: int = 10
    max_queue_size: int = 100

class NetworkConfig(BaseSettings):
    """网络配置"""
    proxy: str = ""  # HTTP代理
    timeout: int = 30  # 请求超时时间(秒)

class Settings(BaseSettings):
    """全局配置"""
    llm: LLMConfig = LLMConfig()
    search: SearchConfig = SearchConfig()
    rag: RAGConfig = RAGConfig()
    service: ServiceConfig = ServiceConfig()
    network: NetworkConfig = NetworkConfig()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    def setup(self):
        """初始化设置"""
        # 确保必要的目录存在
        Path(self.rag.vector_store_path).mkdir(parents=True, exist_ok=True)
        
        # 验证关键配置
        if self.llm.provider == "openai" and not self.llm.openai_api_key:
            raise ValueError("OpenAI API key is required when using OpenAI provider")
        if not self.llm.google_api_key:
            raise ValueError("Google API key is required")
            
        # 验证服务配置
        if self.service.max_connections < 1:
            raise ValueError("max_connections must be greater than 0")
        if self.service.http_timeout < 1:
            raise ValueError("http_timeout must be greater than 0")
        if self.service.max_concurrent_requests < 1:
            raise ValueError("max_concurrent_requests must be greater than 0")

# 创建全局设置实例
settings = Settings()
settings.setup() 
