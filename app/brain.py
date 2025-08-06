"""
Brain - 智能搜索系统核心调度器
负责协调和管理整个搜索总结流程
"""
from typing import List, Optional, Dict, AsyncGenerator, Literal, Any
from .models.schemas import (
    AgentState, SearchQuery, Summary, SearchIteration, SearchResult,
    ProcessingStage, ReasoningMode, SearchMode
)
from .agents.query_agent import query_agent
from .agents.search_agent import search_agent
from .agents.process_agent import process_agent
from .agents.rag_agent import rag_agent
from .agents.summary_agent import summary_agent
from .services.websocket import manager
from .utils.logger import brain_logger
import asyncio
import nest_asyncio
import time

# 确保在 Jupyter 等环境中可以正常运行
nest_asyncio.apply()


class Brain:
    """🧠 智能搜索系统核心调度器
    
    负责协调多个Agent的工作流程，支持多种搜索模式和推理模式。
    """

    def __init__(
        self,
        max_iterations: int = 3,
        min_quality_score: float = 0.7,
        default_mode: str = SearchMode.DEFAULT.value
    ):
        self.max_iterations = max_iterations
        self.min_quality_score = min_quality_score
        self.default_mode = default_mode
        self.iterations: List[SearchIteration] = []

        # ReAct 相关组件 (懒加载)
        self._react_agent = None
        self._react_tools = None
        
        brain_logger.info(f"🧠 Brain初始化完成 | 最大迭代: {max_iterations} | 质量阈值: {min_quality_score}")

    @property
    def react_agent(self):
        """懒加载 ReAct Agent"""
        if self._react_agent is None:
            try:
                # 检查依赖是否可用
                try:
                    import smolagents
                    import litellm
                    brain_logger.info(f"smolagents 版本: {smolagents.__version__}")
                except ImportError as import_error:
                    brain_logger.error(f"ReAct 依赖缺失: {import_error}")
                    return None

                from smolagents import ToolCallingAgent, LiteLLMModel
                from .config import settings
                import os

                # 设置环境变量，LiteLLM 会自动读取
                if settings.llm.google_api_key:
                    # 为 Google AI Studio 设置 API Key
                    os.environ["GOOGLE_API_KEY"] = settings.llm.google_api_key
                    os.environ["GEMINI_API_KEY"] = settings.llm.google_api_key  # 备用
                    brain_logger.info("已设置 Google API Key 环境变量")

                # 创建 LiteLLM 模型
                brain_logger.info(f"正在创建 LiteLLM 模型: {settings.llm.react_model}")
                brain_logger.info(f"当前环境变量 GOOGLE_API_KEY: {'已设置' if os.environ.get('GOOGLE_API_KEY') else '未设置'}")

                model = LiteLLMModel(
                    model_id=settings.llm.react_model,
                    max_tokens=4096,
                    temperature=0.1
                )
                brain_logger.info(f"LiteLLM 模型创建成功: {model}")

                brain_logger.info("正在创建 ToolCallingAgent...")
                self._react_agent = ToolCallingAgent(
                    tools=self.react_tools,
                    model=model
                    # 注意：ToolCallingAgent 会使用默认的系统提示词
                )
                brain_logger.info(f"ReAct Agent 初始化成功，使用模型: {settings.llm.react_model}")
            except Exception as e:
                brain_logger.error(f"ReAct Agent 初始化失败: {str(e)}", exc_info=True)
                self._react_agent = None
        return self._react_agent

    @property
    def react_tools(self):
        """懒加载 ReAct 工具"""
        if self._react_tools is None:
            self._react_tools = self._create_react_tools()
        return self._react_tools

    # ==================== 主要接口 ====================
    
    async def process_query(
        self,
        query: SearchQuery,
        mode: Optional[str] = None,
        client_id: Optional[str] = None,
        reasoning_mode: Literal["standard", "react", "auto"] = "auto"
    ) -> Summary:
        """
        🔍 处理搜索查询 - 主要入口点

        Args:
            query: 搜索查询
            mode: 搜索模式 (default/pro)
            client_id: 客户端ID，用于发送进度更新
            reasoning_mode: 推理模式
                - "standard": 使用现有的多Agent流程
                - "react": 使用ReAct推理模式
                - "auto": 自动选择最适合的模式

        Returns:
            Summary: 最终总结结果
        """
        start_time = time.time()
        brain_logger.info(f"🚀 开始处理查询: {query.query}")
        brain_logger.info(f"📋 处理参数: 模式={mode} | 推理={reasoning_mode} | 客户端={client_id}")

        # 选择推理模式
        selected_mode = await self._select_reasoning_mode(query.query, reasoning_mode)
        brain_logger.info(f"🎯 选定推理模式: {selected_mode}")
        
        try:
            # 根据推理模式分发处理
            if selected_mode == "react":
                result = await self._process_with_react(query, mode, client_id)
            else:
                result = await self._process_standard(query, mode, client_id)
                
            processing_time = time.time() - start_time
            brain_logger.info(f"✅ 查询处理完成，耗时: {processing_time:.2f}秒")
            
            # 添加处理时间到元数据
            if not result.metadata:
                result.metadata = {}
            result.metadata.update({
                "processing_time": processing_time,
                "reasoning_mode": selected_mode,
                "search_mode": mode or self.default_mode
            })
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            brain_logger.error(f"❌ 查询处理失败: {str(e)} | 耗时: {processing_time:.2f}秒", exc_info=True)
            raise

    async def _select_reasoning_mode(self, query: str, reasoning_mode: str) -> str:
        """🎯 选择最适合的推理模式"""
        if reasoning_mode == "react":
            return "react"
        elif reasoning_mode == "standard":
            return "standard"
        elif reasoning_mode == "auto":
            # 智能选择处理模式
            complexity = await self._analyze_query_complexity(query)
            if complexity >= 0.7:  # 复杂查询用ReAct
                brain_logger.info(f"🧠 查询复杂度 {complexity:.2f}，选择ReAct模式")
                return "react"
            else:
                brain_logger.info(f"⚡ 查询复杂度 {complexity:.2f}，选择标准模式")
                return "standard"
        else:
            brain_logger.warning(f"⚠️ 未知推理模式: {reasoning_mode}，使用标准模式")
            return "standard"

    async def _process_standard(self, query: SearchQuery, mode: Optional[str], client_id: Optional[str]) -> Summary:
        """标准处理流程 - 保持现有逻辑"""
        best_summary = None
        best_quality_score = 0.0
        search_mode = mode or self.default_mode
        last_error = None

        # 进度回调函数
        async def send_progress(stage: str, progress: float, details: dict = None):
            await self._send_progress_update(client_id, stage, progress, details)

        # 迭代处理
        current_iteration = 0
        while current_iteration < self.max_iterations:
            try:
                # 创建新的迭代状态
                state = AgentState(query=query.query)
                
                # 执行搜索和总结流程
                await send_progress("starting", 0.1, {"iteration": current_iteration})
                state = await self._execute_pipeline(state, search_mode, send_progress)
                
                if state.error:
                    brain_logger.error(f"处理查询时出错: {state.error}")
                    last_error = state.error
                    current_iteration += 1
                    continue
                
                # 评估结果质量
                await send_progress("evaluating", 0.9, {"iteration": current_iteration})
                quality_score = await self._evaluate_quality(state, search_mode)
                
                # 记录本次迭代
                self._record_iteration(current_iteration, state, True, None, search_mode, "standard")
                
                # 更新最佳结果
                if quality_score > best_quality_score:
                    best_quality_score = quality_score
                    best_summary = state.summary
                    
                # 检查是否达到质量要求
                if quality_score >= self.min_quality_score:
                    await send_progress("completed", 1.0, {
                        "quality_score": quality_score,
                        "iteration": current_iteration
                    })
                    break
                    
                # 准备下一次迭代
                await send_progress("preparing_next", 0.95, {"iteration": current_iteration})
                query, next_mode = await self._prepare_next_iteration(
                    state, current_iteration, search_mode
                )
                search_mode = next_mode
                current_iteration += 1
                
            except Exception as e:
                brain_logger.error(f"迭代 {current_iteration} 处理时出错: {str(e)}", exc_info=True)
                last_error = str(e)
                await send_progress("error", 1.0, {"error": str(e)})
                self._record_iteration(current_iteration, AgentState(query=query.query, error=str(e)), 
                                     False, str(e), search_mode, "standard")
                current_iteration += 1

        # 返回最佳结果或抛出异常
        if best_summary:
            brain_logger.info(f"查询处理完成，最佳质量得分: {best_quality_score:.2f}")
            return best_summary
        else:
            error_msg = last_error or "未能生成有效的搜索结果总结"
            brain_logger.error(f"处理查询失败: {error_msg}")
            raise Exception(error_msg)

    async def process_query_stream(
        self,
        query: SearchQuery,
        mode: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式处理搜索查询
        
        Args:
            query: 搜索查询
            mode: 搜索模式
            client_id: 客户端ID
            
        Yields:
            str: 流式响应数据
        """
        brain_logger.info(f"开始流式处理查询: {query.query}, 模式: {mode}")
        
        try:
            # 初始化状态
            state = AgentState(query=query.query)
            search_mode = mode or self.default_mode
            
            # 定义进度更新函数
            async def send_progress(stage: str, progress: float, details: dict = None):
                message = f"data: {{'stage': '{stage}', 'progress': {progress}}}\n\n"
                yield message
                await self._send_progress_update(client_id, stage, progress, details)
            
            # 执行处理流程
            async for progress in send_progress("starting", 0.1):
                yield progress
                
            # 查询理解
            async for progress in send_progress("query_understanding", 0.2):
                yield progress
            state = await query_agent.process(state)
            if state.error:
                raise Exception(state.error)
            
            # 搜索执行
            async for progress in send_progress("searching", 0.4):
                yield progress
            state = await search_agent.process(state)
            if state.error:
                raise Exception(state.error)
            
            # 内容处理 (PRO模式)
            if mode == SearchMode.PRO.value:
                async for progress in send_progress("processing", 0.6):
                    yield progress
                state = await process_agent.process(state)
                if state.error:
                    raise Exception(state.error)
            
            # RAG处理
            async for progress in send_progress("rag_processing", 0.8):
                yield progress

            # 检查搜索结果
            if not state.search_results:
                raise Exception("No search results available for RAG processing")

            # 将搜索结果转换为 SearchResult 对象
            search_results = self._convert_search_results(state.search_results)

            # 使用优化后的查询
            query_text = state.refined_query if state.refined_query else state.query
            brain_logger.info(f"使用查询: {query_text}")

            # 流式生成摘要
            async for chunk in rag_agent.process_stream(
                query=query_text,
                search_results=search_results,
                mode=search_mode
            ):
                yield f"data: {chunk}\n\n"
            
            # 完成
            async for progress in send_progress("completed", 1.0):
                yield progress
            
        except Exception as e:
            brain_logger.error(f"流式处理查询时出错: {str(e)}", exc_info=True)
            error_message = f"data: {{'error': '{str(e)}'}}\n\n"
            yield error_message

    # ==================== 核心处理流程 ====================
    
    async def _execute_pipeline(
        self,
        state: AgentState,
        mode: str,
        send_progress=None
    ) -> AgentState:
        """
        执行完整的处理流程
        
        Args:
            state: 当前状态
            mode: 处理模式 (default/pro)
            send_progress: 进度回调函数
            
        Returns:
            AgentState: 更新后的状态
        """
        try:
            # 1. 查询理解
            state = await self._step_query_understanding(state, send_progress)
            if state.error:
                return state
                
            # 2. 执行搜索
            state = await self._step_search_execution(state, send_progress)
            if state.error:
                return state
                
            # 3. 内容处理 (PRO模式)
            if mode == SearchMode.PRO.value:
                state = await self._step_content_processing(state, send_progress)
                if state.error:
                    return state
                    
            # 4. RAG处理
            state = await self._step_rag_processing(state, mode, send_progress)
            if state.error:
                return state
                
            # 5. 总结优化 (可选)
            if self._should_use_summary_agent(state, mode):
                state = await self._step_summary_optimization(state, send_progress)
                if state.error:
                    return state
            else:
                brain_logger.info("RAG摘要质量良好，跳过额外总结处理")

            brain_logger.info("处理流程完成")
            return state
            
        except Exception as e:
            brain_logger.error(f"执行处理流程时出错: {str(e)}", exc_info=True)
            state.error = f"Pipeline execution failed: {str(e)}"
            return state


    # ==================== 处理步骤 ====================

    async def _step_query_understanding(self, state: AgentState, send_progress=None) -> AgentState:
        """查询理解步骤"""
        if send_progress:
            await send_progress("query_understanding", 0.2)
        brain_logger.info("开始查询理解...")

        state = await query_agent.process(state)
        if state.error:
            brain_logger.error(f"查询理解失败: {state.error}")
        return state

    async def _step_search_execution(self, state: AgentState, send_progress=None) -> AgentState:
        """搜索执行步骤"""
        if send_progress:
            await send_progress("searching", 0.4)
        brain_logger.info("开始执行搜索...")

        state = await search_agent.process(state)
        if state.error:
            brain_logger.error(f"搜索执行失败: {state.error}")
        return state

    async def _step_content_processing(self, state: AgentState, send_progress=None) -> AgentState:
        """内容处理步骤 (PRO模式)"""
        if send_progress:
            await send_progress("processing", 0.6)
        brain_logger.info("开始内容处理(PRO模式)...")

        state = await process_agent.process(state)
        if state.error:
            brain_logger.error(f"内容处理失败: {state.error}")
        return state

    async def _step_rag_processing(self, state: AgentState, mode: str, send_progress=None) -> AgentState:
        """RAG处理步骤"""
        if send_progress:
            await send_progress("rag_processing", 0.8)
        brain_logger.info("开始RAG处理...")

        # 检查搜索结果
        if not state.search_results:
            state.error = "No search results available for RAG processing"
            brain_logger.error(state.error)
            return state

        try:
            # 根据模式选择使用的内容
            if mode == SearchMode.PRO.value and state.processed_content:
                # PRO模式：优先使用处理后的完整内容
                brain_logger.info(f"PRO模式：使用处理后的内容，共 {len(state.processed_content)} 项")
                search_results = self._convert_processed_content_to_search_results(state.processed_content)
            else:
                # 默认模式：使用原始搜索结果
                brain_logger.info(f"默认模式：使用原始搜索结果，共 {len(state.search_results)} 项")
                search_results = self._convert_search_results(state.search_results)

            # 使用优化后的查询
            query = state.refined_query if state.refined_query else state.query
            brain_logger.info(f"使用查询: {query}")

            # 调用 RAG Agent 进行内容提取
            rag_result = await rag_agent.process(
                query=query,
                search_results=search_results,
                mode=mode.lower()
            )

            if not rag_result:
                state.error = "RAG processing failed: Could not extract content"
                brain_logger.error(state.error)
                return state

            # 处理RAG结果
            state = self._process_rag_result(state, rag_result)
            brain_logger.info(f"RAG处理完成，生成摘要: {state.summary.summary[:100]}...")

        except Exception as rag_error:
            state.error = f"RAG processing failed: {str(rag_error)}"
            brain_logger.error(state.error, exc_info=True)

        return state

    async def _step_summary_optimization(self, state: AgentState, send_progress=None) -> AgentState:
        """总结优化步骤"""
        if send_progress:
            await send_progress("summarizing", 0.9)
        brain_logger.info("开始生成最终总结...")

        state = await summary_agent.process(state)
        if state.error:
            brain_logger.error(f"总结生成失败: {state.error}")
        return state

    # ==================== 工具函数 ====================

    def _convert_processed_content_to_search_results(self, processed_content: List[Dict]) -> List[SearchResult]:
        """将处理后的内容转换为SearchResult对象"""
        results = []
        for i, content in enumerate(processed_content):
            # 从处理后的内容中提取信息
            text = content.get('text', '')
            metadata = content.get('metadata', {})

            # 提取元数据信息
            url = metadata.get('url', '')
            title = metadata.get('title', f'处理后的内容 {i+1}')

            brain_logger.debug(f"处理内容 {i+1}: title='{title}', url='{url}', text_length={len(text)}")

            # 创建SearchResult对象，使用处理后的完整内容
            result = SearchResult(
                title=title,
                url=url,
                snippet=text[:500] + '...' if len(text) > 500 else text,  # 使用完整内容作为snippet
                source='processed'
            )
            results.append(result)

        brain_logger.info(f"转换了 {len(results)} 个处理后的内容为SearchResult")
        return results

    def _convert_search_results(self, search_results: List[Dict]) -> List[SearchResult]:
        """将搜索结果字典转换为 SearchResult 对象"""
        converted_results = []
        for result in search_results:
            converted_results.append(SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                snippet=result.get("snippet", "")
            ))
        return converted_results

    def _process_rag_result(self, state: AgentState, rag_result: Dict) -> AgentState:
        """处理RAG结果并更新状态"""
        from .models.schemas import RAGChunk, Summary

        # 创建 RAGChunk 对象
        rag_chunks = []
        for chunk_data in rag_result["chunks"]:
            rag_chunk = RAGChunk(
                text=chunk_data["content"],
                metadata={
                    "title": chunk_data["title"],
                    "url": chunk_data["url"],
                    "source": chunk_data["url"]
                },
                score=chunk_data["score"]
            )
            rag_chunks.append(rag_chunk)

        state.rag_chunks = rag_chunks

        # 创建 Summary 对象
        sources = rag_result.get("sources", [])
        brain_logger.info(f"从RAG结果中获取到 {len(sources)} 个来源")

        summary = Summary(
            summary=rag_result["extract"],
            sources=sources
        )
        state.summary = summary

        return state

    async def _send_progress_update(self, client_id: Optional[str], stage: str,
                                  progress: float, details: dict = None):
        """发送进度更新"""
        if client_id:
            try:
                await manager.send_update(client_id, {
                    "stage": stage,
                    "progress": progress,
                    "details": details or {}
                })
            except Exception as e:
                brain_logger.error(f"发送进度更新时出错: {str(e)}", exc_info=True)

    def _record_iteration(self, iteration: int, state: AgentState, is_successful: bool,
                         error: Optional[str], mode: str, reasoning_mode: str = "standard"):
        """记录迭代结果"""
        self.iterations.append(SearchIteration(
            iteration=iteration,
            state=state,
            is_successful=is_successful,
            error=error,
            mode=SearchMode(mode) if mode in [m.value for m in SearchMode] else SearchMode.DEFAULT,
            reasoning_mode=ReasoningMode(reasoning_mode) if reasoning_mode in [m.value for m in ReasoningMode] else ReasoningMode.STANDARD,
            stages_completed=[]
        ))

    # ==================== 质量评估 ====================

    async def _evaluate_quality(self, state: AgentState, mode: str) -> float:
        """
        评估结果质量

        Args:
            state: 当前状态
            mode: 处理模式

        Returns:
            float: 质量得分 (0.0-1.0)
        """
        try:
            score = 0.0

            if mode == SearchMode.DEFAULT.value:
                score = self._evaluate_default_quality(state)
            else:  # PRO mode
                score = self._evaluate_pro_quality(state)

            brain_logger.info(f"质量评估得分: {score:.2f}")
            return score

        except Exception as e:
            brain_logger.error(f"评估质量时出错: {str(e)}", exc_info=True)
            return 0.0

    def _evaluate_default_quality(self, state: AgentState) -> float:
        """评估DEFAULT模式的质量"""
        score = 0.0

        # 1. 检查是否有足够的源
        if state.summary and state.summary.sources and len(state.summary.sources) >= 2:
            score += 0.3

        # 2. 检查总结长度
        if state.summary and state.summary.summary and len(state.summary.summary) >= 150:
            score += 0.3

        # 3. 检查RAG chunks的相关度
        if state.rag_chunks and len(state.rag_chunks) > 0:
            avg_score = sum(chunk.score or 0 for chunk in state.rag_chunks) / len(state.rag_chunks)
            if avg_score >= 0.7:
                score += 0.4

        return min(score, 1.0)

    def _evaluate_pro_quality(self, state: AgentState) -> float:
        """评估PRO模式的质量"""
        score = 0.0
        max_score = 1.0

        # 1. 来源数量评分 (0-0.25)
        if state.summary and state.summary.sources:
            source_count = len(state.summary.sources)
            if source_count >= 3:
                score += 0.25
            elif source_count >= 2:
                score += 0.15
            elif source_count >= 1:
                score += 0.1

        # 2. 总结质量评分 (0-0.25)
        if state.summary and state.summary.summary:
            summary_length = len(state.summary.summary)
            if summary_length >= 500:
                score += 0.25
            elif summary_length >= 300:
                score += 0.2
            elif summary_length >= 150:
                score += 0.15
            elif summary_length >= 50:
                score += 0.1

        # 3. RAG chunks 数量评分 (0-0.2)
        if state.rag_chunks:
            chunk_count = len(state.rag_chunks)
            if chunk_count >= 4:
                score += 0.2
            elif chunk_count >= 3:
                score += 0.15
            elif chunk_count >= 2:
                score += 0.1
            elif chunk_count >= 1:
                score += 0.05

        # 4. RAG chunks 相关度评分 (0-0.15)
        if state.rag_chunks:
            valid_scores = [chunk.score for chunk in state.rag_chunks if chunk.score is not None]
            if valid_scores:
                avg_score = sum(valid_scores) / len(valid_scores)
                if avg_score >= 0.9:
                    score += 0.15
                elif avg_score >= 0.8:
                    score += 0.12
                elif avg_score >= 0.7:
                    score += 0.08
                elif avg_score >= 0.6:
                    score += 0.05

        # 5. 来源多样性评分 (0-0.15)
        if state.summary and state.summary.sources:
            try:
                unique_domains = set()
                for url in state.summary.sources:
                    if url and url.startswith(('http://', 'https://')):
                        parts = url.split('/')
                        if len(parts) >= 3:
                            domain = parts[2]
                            # 移除 www. 前缀进行更好的去重
                            if domain.startswith('www.'):
                                domain = domain[4:]
                            unique_domains.add(domain)

                domain_count = len(unique_domains)
                if domain_count >= 3:
                    score += 0.15
                elif domain_count >= 2:
                    score += 0.1
                elif domain_count >= 1:
                    score += 0.05
            except Exception as e:
                brain_logger.warning(f"域名多样性评估失败: {str(e)}")

        final_score = min(score, max_score)
        brain_logger.info(f"PRO模式质量评估: {final_score:.2f} (来源: {len(state.summary.sources) if state.summary and state.summary.sources else 0}, "
                         f"总结长度: {len(state.summary.summary) if state.summary and state.summary.summary else 0}, "
                         f"RAG块: {len(state.rag_chunks) if state.rag_chunks else 0})")

        return final_score

    # ==================== 迭代管理 ====================

    async def _prepare_next_iteration(self, state: AgentState, current_iteration: int,
                                    current_mode: str) -> tuple[SearchQuery, str]:
        """
        准备下一次迭代

        Args:
            state: 当前状态
            current_iteration: 当前迭代次数
            current_mode: 当前模式

        Returns:
            tuple: (新查询, 新模式)
        """
        original_query = state.query

        # 如果当前是默认模式且质量不够，切换到PRO模式
        if current_mode == SearchMode.DEFAULT.value and current_iteration == 0:
            return SearchQuery(query=original_query), SearchMode.PRO.value

        # 尝试优化查询
        optimized_query = await self._optimize_query_for_retry(state)
        return SearchQuery(query=optimized_query), current_mode

    async def _optimize_query_for_retry(self, state: AgentState) -> str:
        """为重试优化查询"""
        # 简单的查询优化策略
        original_query = state.query

        # 可以在这里添加更复杂的查询优化逻辑
        # 例如：添加同义词、调整关键词等

        return original_query

    def _should_use_summary_agent(self, state: AgentState, mode: str) -> bool:
        """
        判断是否需要使用 Summary Agent

        Args:
            state: 当前状态
            mode: 处理模式

        Returns:
            bool: 是否需要使用 Summary Agent
        """
        # 如果没有 RAG 摘要，必须使用 Summary Agent
        if not state.summary or not state.summary.summary:
            return True

        # 检查 RAG 摘要的质量
        rag_summary = state.summary.summary

        # 简单的质量检查
        if len(rag_summary) < 100:  # 摘要太短
            return True

        if "错误" in rag_summary or "无法" in rag_summary:  # 包含错误信息
            return True

        # 检查摘要是否与查询相关
        query_keywords = state.query.lower().split()
        summary_lower = rag_summary.lower()

        # 如果摘要中包含查询关键词，认为质量较好
        keyword_matches = sum(1 for keyword in query_keywords if keyword in summary_lower)
        if keyword_matches >= len(query_keywords) * 0.5:  # 至少50%的关键词匹配
            brain_logger.info(f"RAG摘要质量良好 (关键词匹配: {keyword_matches}/{len(query_keywords)})")
            return False  # 不需要额外处理

        return True  # 需要 Summary Agent 进一步处理

    # ==================== ReAct 相关方法 ====================

    async def _process_with_react(self, query: SearchQuery, mode: Optional[str], client_id: Optional[str]) -> Summary:
        """ReAct 推理模式处理"""
        try:
            brain_logger.info("开始ReAct推理模式处理")

            if self.react_agent is None:
                brain_logger.warning("ReAct Agent 不可用，降级到标准模式")
                return await self._process_standard(query, mode, client_id)

            # 设置ReAct上下文
            react_context = {
                "original_query": query.query,
                "search_mode": mode or self.default_mode,
                "client_id": client_id,
                "sources": []
            }

            # 构建ReAct查询
            react_query = f"""
用户查询: {query.query}
搜索模式: {mode or 'default'}

请分析这个查询并使用合适的工具来获取准确的答案。
如果查询复杂或需要详细信息，请使用pro模式进行深度搜索。
确保最终答案准确、完整，并包含可靠的来源。
"""

            # 发送进度更新
            await self._send_progress_update(client_id, "react_reasoning", 0.1, {"stage": "开始ReAct推理"})

            # 执行ReAct推理 (注意：run() 方法是同步的，返回 AgentText)
            result = self.react_agent.run(react_query)

            await self._send_progress_update(client_id, "react_completed", 1.0, {"stage": "ReAct推理完成"})

            # 提取文本内容
            result_text = str(result) if result else "ReAct推理未返回结果"

            # 转换为标准Summary格式
            return Summary(
                summary=result_text,
                sources=react_context.get("sources", []),
                metadata={
                    "reasoning_mode": "react",
                    "context": react_context,
                    "processing_time": 0  # TODO: 添加时间统计
                }
            )

        except Exception as e:
            brain_logger.error(f"ReAct模式处理失败: {str(e)}", exc_info=True)
            brain_logger.info("降级到标准模式")
            return await self._process_standard(query, mode, client_id)

    def _create_react_tools(self):
        """创建ReAct工具集"""
        try:
            from .agents.react_tools import DeepSearchTool, QualityAnalyzerTool, SearchStrategyTool

            tools = [
                DeepSearchTool(),
                QualityAnalyzerTool(),
                SearchStrategyTool()
            ]

            brain_logger.info(f"创建了 {len(tools)} 个ReAct工具")
            return tools

        except Exception as e:
            brain_logger.error(f"创建ReAct工具失败: {str(e)}")
            return []



    async def _analyze_query_complexity(self, query: str) -> float:
        """分析查询复杂度 (0-1)"""
        try:
            complexity_indicators = {
                "length": min(len(query) / 100, 1.0) * 0.2,
                "keywords": len([w for w in ["对比", "分析", "原理", "如何", "为什么", "比较", "评估"]
                               if w in query]) * 0.15,
                "entities": (len(query.split()) > 5) * 0.25,  # 简化的实体检测
                "questions": (query.count("?") + query.count("？") > 0) * 0.2,
                "complexity_words": len([w for w in ["复杂", "详细", "深入", "全面", "系统"]
                                       if w in query]) * 0.2
            }

            score = sum(complexity_indicators.values())
            brain_logger.debug(f"查询复杂度分析: {complexity_indicators}, 总分: {score:.2f}")

            return min(score, 1.0)

        except Exception as e:
            brain_logger.error(f"查询复杂度分析失败: {str(e)}")
            return 0.5  # 默认中等复杂度

    def get_iteration_history(self) -> Dict[str, Any]:
        """📊 获取迭代历史"""
        return {
            "total_iterations": len(self.iterations),
            "recent_iterations": [
                {
                    "iteration": iter.iteration,
                    "query": iter.state.query,
                    "mode": iter.mode.value if hasattr(iter.mode, 'value') else iter.mode,
                    "reasoning_mode": iter.reasoning_mode.value if hasattr(iter.reasoning_mode, 'value') else iter.reasoning_mode,
                    "is_successful": iter.is_successful,
                    "quality_score": iter.quality_score,
                    "processing_time": iter.processing_time,
                    "stages_completed": [stage.value if hasattr(stage, 'value') else stage for stage in iter.stages_completed],
                    "error": iter.error
                }
                for iter in self.iterations[-10:]  # 最近10次
                  
            ]
        }

    def _create_initial_state(self, query: str, mode: str, reasoning_mode: str) -> AgentState:
        """🏗️ 创建初始状态"""
        return AgentState(
            query=query,
            current_stage=ProcessingStage.STARTING,
            processing_mode=SearchMode(mode) if mode else SearchMode(self.default_mode),
            reasoning_mode=ReasoningMode(reasoning_mode)
        )


# 创建全局大脑实例
brain = Brain()
