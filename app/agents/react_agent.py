"""
ReAct (Reasoning and Acting) Agent 实现
"""
from typing import List, Dict, Any
from ..services.tools.wolfram_tool import wolfram_tool
from ..services.search_engines.manager import search_engine_manager
import uuid
import re

class ReActAgent:
    """
    ReAct Agent实现
    
    工作流程:
    1. 思考(Thought): 分析当前情况，制定计划
    2. 行动(Action): 执行具体工具调用
    3. 观察(Observation): 获取行动结果
    4. 反思(Reflection): 评估结果，调整计划
    """
    
    def __init__(self):
        self.tools = {
            "search": search_engine_manager,
            "calculate": wolfram_tool
        }
        self.thought_history = []
        
    async def process(self, query: str) -> Dict[str, Any]:
        """
        处理查询
        
        Args:
            query: 用户查询
            
        Returns:
            Dict: 处理结果
        """
        # 初始化处理状态
        state = {
            "query": query,
            "thoughts": [],
            "actions": [],
            "observations": [],
            "final_answer": None
        }
        
        # 执行 ReAct 循环
        max_steps = 5  # 最大步骤数
        current_step = 0
        
        while current_step < max_steps:
            # 1. 思考
            thought = await self._think(state)
            state["thoughts"].append(thought)
            
            # 如果认为已经可以回答，就停止
            if "FINAL ANSWER:" in thought:
                state["final_answer"] = thought.split("FINAL ANSWER:")[1].strip()
                break
                
            # 2. 行动
            action = await self._act(thought, state)
            state["actions"].append(action)
            
            # 3. 观察
            observation = await self._observe(action, state)
            state["observations"].append(observation)
            
            # 4. 反思
            reflection = await self._reflect(state)
            state["thoughts"].append(f"Reflection: {reflection}")
            
            current_step += 1
            
        return state
        
    async def _think(self, state: Dict) -> str:
        """思考下一步行动"""
        # 分析查询和历史
        query = state["query"]
        history = state["thoughts"]
        
        # 示例思考逻辑
        if not history:
            # 初始思考
            if any(math_keyword in query.lower() for math_keyword in [
                "calculate", "solve", "compute", "convert"
            ]):
                return f"This seems like a mathematical question. I should use the calculate tool to solve it."
            else:
                return f"I should search for information about this query first."
        else:
            # 基于历史的思考
            last_observation = state["observations"][-1] if state["observations"] else None
            if last_observation and last_observation.get("success"):
                return f"FINAL ANSWER: {last_observation.get('answer')}"
            else:
                return f"The last attempt wasn't successful. I should try a different approach."
                
    async def _act(self, thought: str, state: Dict) -> Dict:
        """执行行动"""
        action = {
            "tool": None,
            "input": None
        }
        
        if "calculate" in thought.lower():
            action["tool"] = "calculate"
            action["input"] = state["query"]
        else:
            action["tool"] = "search"
            action["input"] = state["query"]
            
        return action
        
    async def _observe(self, action: Dict, state: Dict) -> Dict:
        """观察行动结果"""
        tool = self.tools.get(action["tool"])
        if not tool:
            return {
                "success": False,
                "error": f"Tool {action['tool']} not found"
            }
            
        if action["tool"] == "calculate":
            return await tool.query(action["input"])
        else:
            results = await tool.search(action["input"])
            return {
                "success": bool(results),
                "answer": results[0].snippet if results else None,
                "results": results
            }
            
    async def _reflect(self, state: Dict) -> str:
        """反思当前进展"""
        last_action = state["actions"][-1]
        last_observation = state["observations"][-1]
        
        if last_observation.get("success"):
            return "The last action was successful. The information seems reliable."
        else:
            return f"The {last_action['tool']} tool didn't provide satisfactory results. Should try a different approach."

# 创建全局 ReAct Agent 实例
react_agent = ReActAgent() 

class VectorStoreService:
    async def get_or_create_collection(self, query_type: str):
        """获取或创建特定类型的持久化集合"""
        collection_name = f"rag_{query_type}"
        try:
            return self.client.get_collection(collection_name)
        except ValueError:
            return self.client.create_collection(
                name=collection_name,
                metadata={"type": query_type}
            ) 

class RAGAgent:
    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        # 1. 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 2. 标准化标点符号
        text = self._normalize_punctuation(text)
        
        # 3. 处理特殊字符
        text = self._handle_special_chars(text)
        
        return text.strip()
        
    def _create_chunks(self, content: ProcessedContent) -> List[RAGChunk]:
        # 先预处理文本
        cleaned_text = self._preprocess_text(content.text)
        # 再进行分块 

    def _split_by_semantic(self, text: str) -> List[str]:
        """语义分块"""
        # 1. 识别段落边界
        paragraphs = text.split('\n\n')
        
        # 2. 分析段落关系
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            # 如果当前块太大，创建新块
            if current_length + para_length > self.chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
                
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        return chunks 

    def _evaluate_chunk_relevance(
        self,
        query: str,
        chunk: RAGChunk
    ) -> float:
        """评估块相关性"""
        score = 0.0
        
        # 1. 关键词匹配
        keywords = self._extract_keywords(query)
        keyword_matches = sum(
            1 for kw in keywords 
            if kw.lower() in chunk.text.lower()
        )
        score += keyword_matches * 0.3
        
        # 2. 语义相似度
        semantic_score = embedding_service.compute_similarity(
            query_embedding,
            chunk.embedding
        )
        score += semantic_score * 0.7
        
        return score 

class RAGContext:
    def __init__(self):
        self.chunks: Dict[str, RAGChunk] = {}
        self.query_history: List[str] = []
        self.relevance_scores: Dict[str, float] = {}
        
    def add_chunk(self, chunk_id: str, chunk: RAGChunk):
        self.chunks[chunk_id] = chunk
        
    def update_relevance(self, chunk_id: str, score: float):
        self.relevance_scores[chunk_id] = score
        
    def get_top_chunks(self, n: int = 5) -> List[RAGChunk]:
        sorted_chunks = sorted(
            self.chunks.items(),
            key=lambda x: self.relevance_scores.get(x[0], 0),
            reverse=True
        )
        return [chunk for _, chunk in sorted_chunks[:n]] 

class EnhancedRAGAgent:
    def __init__(self):
        self.context = RAGContext()
        self.preprocessor = TextPreprocessor()
        self.chunker = SemanticChunker()
        self.evaluator = RelevanceEvaluator()
        
    async def process(self, state: AgentState) -> AgentState:
        try:
            # 1. 获取持久化集合
            collection = await vector_store_service.get_or_create_collection(
                query_type=self._get_query_type(state.query)
            )
            
            # 2. 预处理和分块
            processed_contents = []
            for content in state.processed_contents:
                # 清理文本
                cleaned_text = self.preprocessor.process(content.text)
                # 智能分块
                chunks = self.chunker.split(
                    cleaned_text,
                    strategy=self._get_chunk_strategy(state)
                )
                processed_contents.extend(chunks)
                
            # 3. 向量化和存储
            await vector_store_service.add_texts(
                collection.name,
                processed_contents,
                metadata=self._get_metadata(state)
            )
            
            # 4. 相关性检索
            query_embedding = await embedding_service.get_embedding(
                state.query
            )
            results = await vector_store_service.search(
                collection.name,
                query_embedding,
                n_results=self._get_n_results(state)
            )
            
            # 5. 相关性评估和过滤
            scored_results = []
            for result in results:
                score = self.evaluator.evaluate(
                    query=state.query,
                    chunk=result,
                    context=self.context
                )
                if score > self.min_relevance_score:
                    scored_results.append((score, result))
                    
            # 6. 更新上下文
            self.context.update(
                query=state.query,
                results=scored_results
            )
            
            # 7. 返回最相关的结果
            state.rag_chunks = [
                chunk for _, chunk in sorted(
                    scored_results,
                    key=lambda x: x[0],
                    reverse=True
                )
            ]
            
            return state
            
        except Exception as e:
            state.error = f"Enhanced RAG processing failed: {str(e)}"
            return state 