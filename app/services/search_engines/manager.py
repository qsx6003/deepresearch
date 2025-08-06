"""
搜索引擎管理器
"""
from typing import List, Dict, Type
from . import SearchEngine
from .google import GoogleSearchEngine
from .bing import BingSearchEngine
from .duckduckgo import DuckDuckGoSearchEngine
from .result_processor import result_processor
from .cache import search_cache
from .retry import with_retry
from ...models.schemas import SearchResult
from ...config import settings

class SearchEngineManager:
    """搜索引擎管理器"""
    
    def __init__(self):
        self.engines: Dict[str, SearchEngine] = {}
        self._register_engines()
        
    def _register_engines(self):
        """注册所有配置的搜索引擎"""
        engine_classes = {
            "google": GoogleSearchEngine,
            "bing": BingSearchEngine,
            "duckduckgo": DuckDuckGoSearchEngine
        }
        
        # 根据配置初始化搜索引擎
        for name, engine_class in engine_classes.items():
            engine = engine_class()
            if engine.is_configured():
                self.engines[name] = engine
                
    @with_retry(max_retries=3)
    async def search(
        self,
        query: str,
        engines: List[str] = None,
        max_results_per_engine: int = 5,
        use_cache: bool = True,
        process_results: bool = True
    ) -> List[SearchResult]:
        """
        使用指定的搜索引擎执行搜索
        
        Args:
            query: 搜索查询
            engines: 要使用的搜索引擎列表，如果为None则使用所有可用的引擎
            max_results_per_engine: 每个引擎返回的最大结果数
            use_cache: 是否使用缓存
            process_results: 是否处理结果(去重和排序)
            
        Returns:
            List[SearchResult]: 合并后的搜索结果
        """
        if not engines:
            engines = list(self.engines.keys())
            
        # 检查缓存
        if use_cache:
            cached_results = search_cache.get(query, engines)
            if cached_results:
                return cached_results
                
        results = []
        errors = []
        
        # 并行执行搜索
        import asyncio
        search_tasks = []
        
        for engine_name in engines:
            if engine_name not in self.engines:
                continue
                
            task = asyncio.create_task(self._search_with_engine(
                engine_name,
                query,
                max_results_per_engine
            ))
            search_tasks.append(task)
            
        # 等待所有搜索完成
        completed_tasks = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 处理结果
        for task_result in completed_tasks:
            if isinstance(task_result, Exception):
                errors.append(str(task_result))
            elif isinstance(task_result, list):
                results.extend(task_result)
                
        # 处理结果
        if process_results:
            results = result_processor.process_results(results)
            
        # 缓存结果
        if use_cache and results:
            search_cache.set(query, results, engines)
            
        return results
        
    async def _search_with_engine(
        self,
        engine_name: str,
        query: str,
        max_results: int
    ) -> List[SearchResult]:
        """使用单个引擎执行搜索"""
        try:
            return await self.engines[engine_name].search(query, max_results)
        except Exception as e:
            raise Exception(f"Error with {engine_name}: {str(e)}")
            
    def get_available_engines(self) -> List[str]:
        """获取所有可用的搜索引擎列表"""
        return list(self.engines.keys())
        
# 创建全局搜索引擎管理器实例
search_engine_manager = SearchEngineManager() 