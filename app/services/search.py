"""
搜索服务实现
"""
from typing import List, Dict, Any, Optional
import aiohttp
from ..config import settings
from ..utils.logger import llm_logger

class SearchService:
    def __init__(self):
        # API Keys
        self.serper_api_key = settings.search.serper_api_key
        self.serpapi_api_key = settings.search.serpapi_api_key
        self.google_cx = settings.search.google_cx
        self.bing_api_key = settings.search.bing_api_key
        
        # 配置
        self.max_results = settings.service.max_search_results
        self.timeout = settings.service.http_timeout
        
    async def search(self, query: str, num_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            num_results: 结果数量
            
        Returns:
            List[Dict[str, Any]]: 搜索结果列表
        """
        results = []
        max_results = num_results or self.max_results
        
        try:

            # 尝试使用可用的搜索API (优先使用非Google API)
            if self.serper_api_key:
                llm_logger.info("Using Serper API for search")
                results = await self._search_with_serper(query, max_results)
            elif self.serpapi_api_key:
                llm_logger.info("Using SerpAPI API for search")
                results = await self._search_with_serpapi(query, max_results)
            elif self.bing_api_key and self.bing_api_key.startswith("Ocp-"):
                llm_logger.info("Using Bing API for search")
                results = await self._search_with_bing(query, max_results)
            elif self.google_cx and settings.llm.google_api_key:
                llm_logger.info("Using Google API for search")
                results = await self._search_with_google(query, max_results)
            else:
                raise ValueError("No valid search API configured. Please configure Serper, SerpAPI, Bing (with valid key), or Google Custom Search API.")
                
            return results[:max_results]
            
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")
            
    async def _search_with_serper(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """使用Serper API搜索"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.serper_api_key},
                json={"q": query, "num": num_results},
                timeout=self.timeout
            ) as response:
                data = await response.json()
                
                if "organic" not in data:
                    raise ValueError("Invalid response from Serper API")
                    
                return [
                    {
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", "")
                    }
                    for result in data["organic"]
                ]
                
    async def _search_with_google(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """使用Google Custom Search API搜索"""
        if not settings.search.google_api_key:
            raise ValueError("Google API key not configured")
            
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": settings.search.google_api_key,
                    "cx": self.google_cx,
                    "q": query,
                    "num": min(num_results, 10)  # Google API限制
                },
                timeout=self.timeout
            ) as response:
                data = await response.json()
                
                if "items" not in data:
                    raise ValueError("Invalid response from Google API")
                    
                return [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    }
                    for item in data["items"]
                ]
                
    async def _search_with_bing(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """使用Bing Web Search API搜索"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers={"Ocp-Apim-Subscription-Key": self.bing_api_key},
                params={"q": query, "count": num_results},
                timeout=self.timeout
            ) as response:
                data = await response.json()
                
                if "webPages" not in data or "value" not in data["webPages"]:
                    raise ValueError("Invalid response from Bing API")
                    
                return [
                    {
                        "title": result.get("name", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", "")
                    }
                    for result in data["webPages"]["value"]
                ]
                
    async def _search_with_serpapi(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """使用SerpAPI搜索"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://serpapi.com/search",
                params={
                    "api_key": self.serpapi_api_key,
                    "q": query,
                    "num": num_results,
                    "engine": "google"
                },
                timeout=self.timeout
            ) as response:
                data = await response.json()
                
                if "organic_results" not in data:
                    raise ValueError("Invalid response from SerpAPI")
                    
                return [
                    {
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", "")
                    }
                    for result in data["organic_results"]
                ]

# 创建全局搜索服务实例
search_service = SearchService() 