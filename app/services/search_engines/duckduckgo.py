"""
DuckDuckGo搜索引擎适配器
"""
from typing import List
from duckduckgo_search import DDGS
from . import SearchEngine
from ...models.schemas import SearchResult

class DuckDuckGoSearchEngine(SearchEngine):
    def __init__(self):
        self.ddgs = DDGS()
        
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        results = []
        try:
            ddg_results = self.ddgs.text(
                query,
                max_results=max_results
            )
            
            for item in ddg_results:
                results.append(SearchResult(
                    title=item["title"],
                    url=item["link"],
                    snippet=item.get("body", ""),
                    source="duckduckgo"
                ))
                
        except Exception as e:
            raise Exception(f"DuckDuckGo search failed: {str(e)}")
            
        return results
        
    def is_configured(self) -> bool:
        return True  # DuckDuckGo不需要API密钥 