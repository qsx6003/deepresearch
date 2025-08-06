"""
搜索结果处理器
"""
from typing import List
from ...models.schemas import SearchResult
from difflib import SequenceMatcher

class SearchResultProcessor:
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        
    def process_results(
        self,
        results: List[SearchResult],
        remove_duplicates: bool = True,
        rerank: bool = True
    ) -> List[SearchResult]:
        """
        处理搜索结果
        
        Args:
            results: 原始搜索结果
            remove_duplicates: 是否去重
            rerank: 是否重新排序
            
        Returns:
            List[SearchResult]: 处理后的结果
        """
        if remove_duplicates:
            results = self._remove_duplicates(results)
            
        if rerank:
            results = self._rerank_results(results)
            
        return results
        
    def _remove_duplicates(self, results: List[SearchResult]) -> List[SearchResult]:
        """去除重复结果"""
        unique_results = []
        seen_urls = set()
        
        for result in results:
            # 检查URL是否重复
            if result.url in seen_urls:
                continue
                
            # 检查内容相似度
            is_duplicate = False
            for existing in unique_results:
                if self._is_similar(result, existing):
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                unique_results.append(result)
                seen_urls.add(result.url)
                
        return unique_results
        
    def _is_similar(self, result1: SearchResult, result2: SearchResult) -> bool:
        """检查两个结果是否相似"""
        # 检查标题相似度
        title_ratio = SequenceMatcher(
            None,
            result1.title.lower(),
            result2.title.lower()
        ).ratio()
        
        # 检查摘要相似度
        snippet_ratio = SequenceMatcher(
            None,
            result1.snippet.lower(),
            result2.snippet.lower()
        ).ratio()
        
        return (title_ratio > self.similarity_threshold or 
                snippet_ratio > self.similarity_threshold)
                
    def _rerank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """重新排序结果"""
        # 计算每个结果的分数
        scored_results = []
        for result in results:
            score = self._calculate_result_score(result)
            scored_results.append((score, result))
            
        # 按分数排序
        scored_results.sort(reverse=True)
        return [result for _, result in scored_results]
        
    def _calculate_result_score(self, result: SearchResult) -> float:
        """计算结果分数"""
        score = 0.0
        
        # 根据来源加权
        source_weights = {
            "google": 1.0,
            "bing": 0.9,
            "duckduckgo": 0.8
        }
        score += source_weights.get(result.source, 0.5)
        
        # 根据标题和摘要长度加权
        title_length = len(result.title.split())
        if 3 <= title_length <= 10:
            score += 0.2
            
        snippet_length = len(result.snippet.split())
        if 10 <= snippet_length <= 50:
            score += 0.3
            
        # 根据URL特征加权
        if any(domain in result.url.lower() for domain in [
            ".edu", ".gov", ".org", "wikipedia.org"
        ]):
            score += 0.5
            
        return score

# 创建全局结果处理器实例
result_processor = SearchResultProcessor() 