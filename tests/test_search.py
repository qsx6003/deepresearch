"""
搜索功能测试
"""
import pytest
from httpx import AsyncClient
from app.main import app
from app.models.schemas import SearchQuery, Summary

@pytest.mark.asyncio
async def test_search():
    """测试搜索API"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 准备测试数据
        query = SearchQuery(
            query="Python异步编程最佳实践",
            max_results=3
        )
        
        # 发送请求
        response = await client.post("/api/search", json=query.model_dump())
        
        # 验证响应
        assert response.status_code == 200
        
        # 解析响应
        summary = Summary.model_validate(response.json())
        
        # 验证结果
        assert summary.summary
        assert len(summary.sources) > 0

@pytest.mark.asyncio
async def test_search_error_handling():
    """测试搜索API错误处理"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 发送无效请求
        response = await client.post("/api/search", json={})
        
        # 验证错误响应
        assert response.status_code == 422  # Validation error 