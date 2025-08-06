"""
Bing搜索引擎适配器
"""
from typing import List
import aiohttp
from . import SearchEngine
from ...models.schemas import SearchResult
from ...config import settings

class BingSearchEngine(SearchEngine):
    def __init__(self):
        self.api_key = settings.bing_api_key
        self.endpoint = "https://api.bing.microsoft.com/v7.0/search"
        
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.is_configured():
            raise ValueError("Bing Search API not configured")
            
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {
            "q": query,
            "count": max_results,
            "responseFilter": "Webpages"
        }
        
        results = []
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.endpoint, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "webPages" in data and "value" in data["webPages"]:
                            for item in data["webPages"]["value"]:
                                results.append(SearchResult(
                                    title=item["name"],
                                    url=item["url"],
                                    snippet=item.get("snippet", ""),
                                    source="bing"
                                ))
                    else:
                        raise Exception(f"Bing API returned status {response.status}")
                        
            except Exception as e:
                raise Exception(f"Bing search failed: {str(e)}")
                
        return results
        
    def is_configured(self) -> bool:
        return bool(self.api_key) 