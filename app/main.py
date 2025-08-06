"""
主应用入口
"""
import asyncio
import signal
import sys
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# 配置日志级别
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_TRACE"] = "none"
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("uvicorn.error").setLevel(logging.ERROR)

from fastapi import FastAPI, HTTPException, Query, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json

from .config import settings
from .models.schemas import SearchQuery, Summary, ReactSearchRequest, SearchMode, ReasoningMode, ProcessingStage
from .brain import brain
from .services.websocket import manager
import uuid
from .utils.logger import llm_logger

# 全局变量用于控制服务状态
should_exit = False
server_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    服务生命周期管理
    """
    # 启动时的操作
    print("Starting up...")
    yield
    # 关闭时的操作
    print("Shutting down...")
    if manager:
        await manager.close_all()

def signal_handler(signum, frame):
    """
    信号处理函数
    """
    global should_exit
    print(f"\nReceived signal {signum}")
    should_exit = True
    # 确保服务实例存在
    if server_instance:
        server_instance.should_exit = True

app = FastAPI(
    title="DeepSearch API",
    description="基于多Agent和RAG的搜索结果汇总系统",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket连接处理
    """
    try:
        # 等待连接
        await websocket.accept()
        client_id = str(id(websocket))
        await manager.connect(client_id, websocket)
        llm_logger.info(f"WebSocket客户端连接: {client_id}")
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "search":
                    # 处理搜索请求
                    query = SearchQuery(**message.get("data", {}))
                    llm_logger.info(f"收到WebSocket搜索请求: {query.query}")
                    
                    # 流式处理
                    async for chunk in brain.process_query_stream(
                        query,
                        client_id=client_id
                    ):
                        await websocket.send_text(chunk)
                        
        except Exception as e:
            llm_logger.error(f"处理WebSocket消息时出错: {str(e)}", exc_info=True)
            await websocket.send_text(json.dumps({"error": str(e)}))
            
    except Exception as e:
        llm_logger.error(f"WebSocket连接出错: {str(e)}", exc_info=True)
    finally:
        # 清理连接
        await manager.disconnect(client_id)
        llm_logger.info(f"WebSocket客户端断开连接: {client_id}")

@app.post("/api/search", response_model=Summary)
async def search(
    query: SearchQuery,
    mode: SearchMode = Query(
        default=SearchMode.PRO,
        description="搜索模式: default(快速) | pro(深度)"
    ),
    reasoning_mode: ReasoningMode = Query(
        default=ReasoningMode.AUTO,
        description="推理模式: standard(标准) | react(智能推理) | auto(自动选择)"
    ),
    client_id: str = Query(default=None, description="客户端ID，用于进度推送")
):
    """
    🔍 智能搜索与总结 API
    
    ## 搜索模式
    - **default**: 快速模式，基于搜索摘要，适合简单查询 (10-20秒)
    - **pro**: 深度模式，抓取完整网页内容，适合复杂分析 (30-60秒)
    
    ## 推理模式  
    - **standard**: 使用传统的多Agent流程，稳定可靠
    - **react**: 使用ReAct推理模式，AI自主决定处理步骤，适合复杂查询
    - **auto**: 根据查询复杂度自动选择最适合的模式
    
    ## 处理流程
    1. 查询理解与优化
    2. 多引擎搜索执行
    3. 内容处理 (PRO模式)
    4. RAG知识增强
    5. 质量评估与优化
    """
    try:
        llm_logger.info(f"🔍 收到搜索请求: {query.query} | 模式: {mode.value} | 推理: {reasoning_mode.value}")
        return await brain.process_query(
            query,
            mode=mode.value,
            client_id=client_id,
            reasoning_mode=reasoning_mode.value
        )
    except Exception as e:
        llm_logger.error(f"❌ 处理搜索请求失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索处理失败: {str(e)}")

@app.post("/api/react-search", response_model=Summary)
async def react_search(
    query: SearchQuery,
    mode: SearchMode = Query(
        default=SearchMode.PRO,
        description="搜索模式: default(快速) | pro(深度)"
    ),
    client_id: str = Query(default=None, description="客户端ID，用于进度推送")
):
    """
    🧠 ReAct 智能推理搜索 API
    
    使用 ReAct (Reasoning + Acting) 模式进行智能推理和搜索。
    AI 会自主分析查询、选择工具、评估结果，提供透明的推理过程。
    
    ## 特点
    - 🤖 AI自主决策处理步骤
    - 🔍 智能工具选择和使用
    - 📊 透明的推理过程
    - 🎯 适应性强，能处理复杂查询
    
    ## 适用场景
    - 复杂的对比分析问题
    - 需要多步推理的查询
    - 需要策略规划的问题
    - 不确定最佳处理方式的查询
    """
    try:
        llm_logger.info(f"🧠 收到ReAct搜索请求: {query.query} | 模式: {mode.value}")
        return await brain.process_query(
            query,
            mode=mode.value,
            client_id=client_id,
            reasoning_mode=ReasoningMode.REACT.value
        )
    except Exception as e:
        llm_logger.error(f"❌ 处理ReAct搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ReAct搜索处理失败: {str(e)}")

@app.post("/api/search/stream")
async def search_stream(
    query: SearchQuery,
    mode: SearchMode = Query(
        default=SearchMode.PRO,
        description="搜索模式: default(快速) | pro(深度)"
    )
):
    """
    📡 流式搜索 API
    
    返回 Server-Sent Events 格式的流式响应，实时显示处理进度。
    
    ## 响应格式
    ```
    data: {"stage": "searching", "progress": 0.4, "details": {...}}
    data: {"stage": "rag_processing", "progress": 0.8, "details": {...}}  
    data: {"summary": "最终结果...", "sources": [...]}
    ```
    
    ## 处理阶段
    - starting → query_understanding → searching → rag_processing → completed
    - PRO模式额外包含: content_processing
    """
    client_id = str(uuid.uuid4())
    return StreamingResponse(
        brain.process_query_stream(query, mode.value, client_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/api/history")
async def get_history():
    """
    📊 获取搜索历史
    
    返回最近的搜索迭代历史，包含质量评分和处理时长等信息。
    """
    try:
        return brain.get_iteration_history()
    except Exception as e:
        llm_logger.error(f"❌ 获取历史记录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")

@app.get("/api/health")
async def health_check():
    """
    🏥 系统健康检查
    
    检查各个组件的状态，包括AI模型、搜索引擎、向量数据库等。
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "components": {
            "brain": "ready",
            "websocket": "active",
            "react_agent": "available" if brain.react_agent else "unavailable"
        },
        "supported_modes": {
            "search_modes": [mode.value for mode in SearchMode],
            "reasoning_modes": [mode.value for mode in ReasoningMode]
        }
    }

@app.get("/api/status")
async def get_status():
    """
    📈 系统状态信息
    
    获取当前系统运行状态和统计信息。
    """
    return {
        "active_connections": len(manager.active_connections) if manager else 0,
        "total_iterations": len(brain.iterations),
        "brain_config": {
            "max_iterations": brain.max_iterations,
            "min_quality_score": brain.min_quality_score,
            "default_mode": brain.default_mode
        }
    }

def run_server():
    """
    启动服务器的函数
    """
    global server_instance
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 运行服务器
    uvicorn.run(
        "app.main:app",
        host=settings.service.host,
        port=settings.service.port,
        reload=settings.service.debug
    )

if __name__ == "__main__":
    run_server() 