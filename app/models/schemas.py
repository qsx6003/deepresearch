"""
数据模型定义
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ProcessingStage(str, Enum):
    """处理阶段枚举"""
    STARTING = "starting"
    QUERY_UNDERSTANDING = "query_understanding"  
    SEARCHING = "searching"
    CONTENT_PROCESSING = "content_processing"
    RAG_PROCESSING = "rag_processing"
    QUALITY_EVALUATION = "quality_evaluation"
    SUMMARY_OPTIMIZATION = "summary_optimization"
    REACT_REASONING = "react_reasoning"
    COMPLETED = "completed"
    ERROR = "error"

class ReasoningMode(str, Enum):
    """推理模式枚举"""
    STANDARD = "standard"
    REACT = "react"
    AUTO = "auto"

class SearchMode(str, Enum):
    """搜索模式枚举"""
    DEFAULT = "default"
    PRO = "pro"

class SearchQuery(BaseModel):
    """搜索查询"""
    query: str
    max_results: Optional[int] = 10

class ReactSearchRequest(BaseModel):
    """ReAct搜索请求"""
    query: str = Field(..., description="搜索查询内容")
    mode: str = Field(default="pro", description="搜索模式 (default/pro)")
    client_id: Optional[str] = Field(default=None, description="客户端ID")

class SearchResult(BaseModel):
    """单个搜索结果模型"""
    title: str = Field(..., description="结果标题")
    url: str = Field(..., description="结果URL")
    snippet: str = Field(..., description="结果摘要")
    
class ProcessedContent(BaseModel):
    """处理后的内容模型"""
    text: str = Field(..., description="处理后的文本内容")
    metadata: Dict = Field(default_factory=dict, description="元数据")
    
class RAGChunk(BaseModel):
    """RAG文本块"""
    text: str
    metadata: Dict[str, Any] = {}
    score: Optional[float] = None
    
class Summary(BaseModel):
    """搜索总结"""
    summary: str
    sources: List[str]
    metadata: Dict[str, Any] = {}
    
class AgentState(BaseModel):
    """Agent状态"""
    query: str
    refined_query: Optional[str] = None
    search_results: List[Dict[str, Any]] = []
    processed_content: List[Dict[str, Any]] = []
    rag_chunks: List[RAGChunk] = []
    summary: Optional[Summary] = None
    error: Optional[str] = None
    current_stage: ProcessingStage = ProcessingStage.STARTING
    processing_mode: Optional[SearchMode] = None
    reasoning_mode: Optional[ReasoningMode] = None
    metadata: Dict[str, Any] = {}

class SearchIteration(BaseModel):
    """搜索迭代"""
    iteration: int
    state: AgentState
    is_successful: bool
    error: Optional[str] = None
    mode: SearchMode
    reasoning_mode: ReasoningMode
    quality_score: Optional[float] = None
    processing_time: Optional[float] = None
    stages_completed: List[ProcessingStage] = []
    metadata: Dict[str, Any] = {}