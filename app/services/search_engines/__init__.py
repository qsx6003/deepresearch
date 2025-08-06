"""
搜索引擎适配器接口
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ...models.schemas import SearchResult

class SearchEngine(ABC):
    """搜索引擎基类"""
    
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数量
            
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        pass
        
    @abstractmethod
    def is_configured(self) -> bool:
        """
        检查搜索引擎是否配置正确
        
        Returns:
            bool: 是否配置正确
        """
        pass 