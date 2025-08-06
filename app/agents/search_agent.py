"""
搜索Agent实现
"""
from typing import List
from ..models.schemas import AgentState, SearchResult
from ..services.search import search_service
from ..utils.logger import llm_logger

class SearchAgent:
    async def process(self, state: AgentState) -> AgentState:
        """
        执行搜索并更新状态
        
        Args:
            state: 当前Agent状态
            
        Returns:
            AgentState: 更新后的状态
        """
        try:
            # 执行搜索
            results = await search_service.search(
                query=state.refined_query if state.refined_query else state.query,
                num_results=5  # 可以从配置或state.metadata中获取
            )
            
            # 更新状态
            state.search_results = results
            state.search_results = self._filter_results(results)
            llm_logger.info(f"搜索结果: {state.search_results}")
            return state
            
        except Exception as e:
            state.error = f"Search failed: {str(e)}"
            return state
            
    def _filter_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        过滤和排序搜索结果
        
        Args:
            results: 原始搜索结果列表
            
        Returns:
            List[SearchResult]: 过滤后的结果列表
        """
        # 这里可以添加结果过滤逻辑
        # 例如：根据URL域名过滤、根据标题关键词过滤等
        return results

# 创建全局搜索Agent实例
search_agent = SearchAgent() 