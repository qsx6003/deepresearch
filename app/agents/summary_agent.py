"""
总结Agent实现
"""
from typing import List, AsyncGenerator
from ..config import settings
from ..models.schemas import AgentState, Summary, RAGChunk
from ..services.llm import llm_service

SYSTEM_PROMPT = """你是一个专业的中文内容总结专家。你的任务是：
1. 理解用户的原始查询意图
2. 分析所提供的相关文本块
3. 生成一个全面、准确、连贯的中文总结

注意事项：
- 保持客观性，避免添加未在源文本中出现的信息
- 确保总结涵盖所有重要观点和细节
- 使用清晰、专业的中文表达
- 适当组织和结构化信息
- 保留重要的技术术语和专有名词
- 注明信息来源

总结应该：
- 开始时简要说明主题
- 按逻辑顺序组织内容
- 突出关键信息和见解
- 在适当的地方引用来源
- 结尾处提供简短的总结或结论
"""

class SummaryAgent:
    def __init__(self):
        # 使用统一的 LLM 服务
        pass
        
    async def process(self, state: AgentState) -> AgentState:
        """
        生成总结
        
        Args:
            state: 当前Agent状态
            
        Returns:
            AgentState: 更新后的状态
        """
        try:
            if not state.rag_chunks:
                raise ValueError("No RAG chunks to summarize")
                
            # 检查是否已有 RAG 摘要
            if state.summary and state.summary.summary:
                # 使用 RAG Agent 已生成的摘要作为基础，进行优化和完善
                rag_summary = state.summary.summary
                summary_text = await llm_service.generate_summary(
                    query=state.query,  # 只传递原始查询
                    contexts=[rag_summary]
                )
            else:
                # 如果没有 RAG 摘要，则从 chunks 重新生成
                context = self._prepare_context(state.rag_chunks)
                summary_text = await llm_service.generate_summary(
                    query=state.query,  # 只传递原始查询
                    contexts=[context]
                )
            
            # 获取源URL列表
            sources = list(set(
                chunk.metadata.get("source", "")
                for chunk in state.rag_chunks
                if chunk.metadata.get("source")
            ))
            
            # 创建总结
            summary = Summary(
                summary=summary_text,
                sources=sources
            )
            
            # 更新状态
            state.summary = summary
            
            return state
            
        except Exception as e:
            state.error = f"Summary generation failed: {str(e)}"
            return state
            
    def _prepare_context(self, chunks: List[RAGChunk]) -> str:
        """
        准备用于总结的上下文
        
        Args:
            chunks: RAG文本块列表
            
        Returns:
            str: 格式化的上下文文本
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("source", "未知来源")
            title = chunk.metadata.get("title", "未知标题")
            
            context_parts.append(f"""
来源 {i}:
标题: {title}
URL: {source}
内容:
{chunk.text}
""")
            
        return "\n".join(context_parts)

# 创建全局总结Agent实例
summary_agent = SummaryAgent() 