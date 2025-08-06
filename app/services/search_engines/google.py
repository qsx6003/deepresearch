"""
Google搜索引擎适配器
"""
from typing import List
import os
from googleapiclient.discovery import build
from . import SearchEngine
from ...models.schemas import SearchResult
from ...config import settings

class GoogleSearchEngine(SearchEngine):
    def __init__(self):
        self.api_key = settings.search.google_api_key
        self.cx = settings.search.google_cx
        
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.is_configured():
            raise ValueError("Google Search API not configured")
            
        service = build(
            "customsearch", "v1",
            developerKey=self.api_key
        )
        
        results = []
        try:
            res = service.cse().list(
                q=query,
                cx=self.cx,
                num=max_results
            ).execute()
            
            if "items" in res:
                for item in res["items"]:
                    results.append(SearchResult(
                        title=item["title"],
                        url=item["link"],
                        snippet=item.get("snippet", ""),
                        source="google"
                    ))
                    
        except Exception as e:
            raise Exception(f"Google search failed: {str(e)}")
            
        return results
        
    def is_configured(self) -> bool:
        return bool(self.api_key and self.cx) 