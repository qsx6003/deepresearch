"""
查询代理 - 负责理解和优化用户查询
"""
from typing import List, Dict
from ..models.schemas import AgentState
from ..services.llm import llm_service
from ..utils.logger import llm_logger

class QueryAgent:
    async def process(self, state: AgentState) -> AgentState:
        """
        处理查询
        """
        try:
            # 使用LLM优化查询
            llm_logger.info(f"开始处理查询: {state.query}")
            optimized_query = await llm_service.generate_query(
                query="优化以下搜索查询，使其更准确和全面",
                contexts=[state.query]
            )
            
            # 更新状态
            
            
            llm_logger.info(f"优化后的查询: {optimized_query}")
            state.refined_query = optimized_query
            return state
            
        except Exception as e:
            state.error = f"Query processing failed: {str(e)}"
            return state

# 创建全局查询代理实例
query_agent = QueryAgent() 