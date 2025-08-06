"""
ReAct 工具集 - 将 DeepSearch 功能包装为 ReAct 工具
"""
from smolagents import Tool
from typing import Dict, Any, Optional
import json
import asyncio
from ..utils.logger import brain_logger


class DeepSearchTool(Tool):
    """深度搜索工具 - 包装现有的搜索功能"""
    
    name = "deep_search"
    description = """
    执行深度搜索，支持快速和专业两种模式。
    - default模式: 快速搜索，适合简单查询，响应速度快
    - pro模式: 深度搜索，包含完整网页内容抓取，适合复杂分析
    """
    inputs = {
        "query": {
            "type": "string",
            "description": "搜索查询内容，应该是具体明确的问题或关键词"
        },
        "mode": {
            "type": "string",
            "description": "搜索模式，可选值: 'default' (快速) 或 'pro' (深度)",
            "nullable": True  # 添加 nullable 标志
        }
    }
    output_type = "string"
    
    def __init__(self):
        super().__init__()
    
    def forward(self, query: str, mode: str = "default") -> str:
        """执行搜索并返回结果"""
        try:
            brain_logger.info(f"ReAct工具调用: deep_search(query='{query}', mode='{mode}')")

            # 简化版本：使用同步的搜索方法
            import requests
            from ..config import settings

            # 直接调用 Google Custom Search API
            api_key = settings.search.google_api_key
            cx = settings.search.google_cx

            if not api_key or not cx:
                return "Google Search API 未配置，请检查 API Key 和 Custom Search Engine ID"

            # 执行搜索
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': api_key,
                'cx': cx,
                'q': query,
                'num': 5
            }

            response = requests.get(url, params=params)
            if response.status_code != 200:
                return f"搜索请求失败: {response.status_code}"

            data = response.json()
            search_results = data.get('items', [])

            if not search_results:
                return f"搜索 '{query}' 未找到相关结果"

            # 构建简单的摘要
            summary_parts = []
            sources = []

            for i, result in enumerate(search_results[:3], 1):
                title = result.get('title', '无标题')
                snippet = result.get('snippet', '无摘要')
                url = result.get('link', '')  # Google API 返回的是 'link' 不是 'url'

                summary_parts.append(f"{i}. {title}\n   {snippet}")
                if url:
                    sources.append(url)

            summary = f"搜索 '{query}' 的结果:\n\n" + "\n\n".join(summary_parts)

            if sources:
                summary += f"\n\n主要来源:\n" + "\n".join([f"- {source}" for source in sources])

            return summary

        except Exception as e:
            brain_logger.error(f"DeepSearchTool执行失败: {str(e)}")
            return f"搜索工具执行失败: {str(e)}"


class QualityAnalyzerTool(Tool):
    """质量分析工具 - 分析搜索结果的质量和相关性"""
    
    name = "analyze_quality"
    description = "分析搜索结果或内容的质量，包括完整性、相关性和可信度评估"
    inputs = {
        "content": {
            "type": "string", 
            "description": "要分析的内容文本"
        }
    }
    output_type = "string"
    
    def __init__(self):
        super().__init__()
        
    
    def forward(self, content: str) -> str:
        """分析内容质量"""
        try:
            brain_logger.info(f"ReAct工具调用: analyze_quality")

            # 基础质量指标
            quality_indicators = {
                "length_score": min(len(content) / 500, 1.0),  # 长度评分
                "has_sources": any(indicator in content.lower()
                                 for indicator in ["http", "来源", "source", "参考"]),
                "completeness": len(content.split()) > 30,  # 完整性
                "structure": content.count('\n') > 2,  # 结构化程度
                "chinese_friendly": any(char in content for char in "的了是在有")  # 中文内容
            }

            # 计算综合得分
            score = (
                quality_indicators["length_score"] * 0.3 +
                (0.25 if quality_indicators["has_sources"] else 0) +
                (0.2 if quality_indicators["completeness"] else 0) +
                (0.15 if quality_indicators["structure"] else 0) +
                (0.1 if quality_indicators["chinese_friendly"] else 0)
            )

            # 生成分析报告
            analysis = {
                "overall_score": round(score, 2),
                "length": len(content),
                "word_count": len(content.split()),
                "has_sources": quality_indicators["has_sources"],
                "assessment": "优秀" if score >= 0.8 else "良好" if score >= 0.6 else "一般" if score >= 0.4 else "需要改进"
            }

            return f"""质量分析报告:
总体评分: {analysis['overall_score']}/1.0 ({analysis['assessment']})
内容长度: {analysis['length']} 字符
词汇数量: {analysis['word_count']} 词
包含来源: {'是' if analysis['has_sources'] else '否'}

建议: {'内容质量良好，可以直接使用' if score >= 0.7 else '建议进一步搜索或使用pro模式获取更详细信息'}"""

        except Exception as e:
            brain_logger.error(f"QualityAnalyzerTool执行失败: {str(e)}")
            return f"质量分析失败: {str(e)}"


class SearchStrategyTool(Tool):
    """搜索策略建议工具 - 根据查询类型建议最佳搜索策略"""
    
    name = "suggest_strategy"
    description = "分析用户查询的特点，建议最适合的搜索策略和模式"
    inputs = {
        "query": {
            "type": "string", 
            "description": "用户的原始查询"
        }
    }
    output_type = "string"
    
    def forward(self, query: str) -> str:
        """分析查询并建议策略"""
        try:
            brain_logger.info(f"ReAct工具调用: suggest_strategy(query='{query}')")

            query_lower = query.lower()

            # 查询类型分析
            query_patterns = {
                "comparison": ["对比", "比较", "vs", "差异", "区别", "哪个好"],
                "latest": ["最新", "2024", "2025", "现在", "目前", "近期"],
                "explanation": ["原理", "如何", "为什么", "机制", "方法", "步骤"],
                "factual": ["是什么", "什么是", "定义", "介绍"],
                "analysis": ["分析", "评估", "研究", "调查", "报告"],
                "trend": ["趋势", "发展", "前景", "未来", "预测"]
            }

            detected_types = []
            for pattern_type, keywords in query_patterns.items():
                if any(keyword in query_lower for keyword in keywords):
                    detected_types.append(pattern_type)

            # 复杂度评估
            complexity_factors = {
                "length": len(query) > 20,
                "multiple_entities": len(query.split()) > 5,
                "questions": query.count("?") + query.count("？") > 0,
                "multiple_types": len(detected_types) > 1
            }

            complexity_score = sum(complexity_factors.values()) / len(complexity_factors)

            # 生成建议
            if "comparison" in detected_types:
                strategy = "对比分析策略: 建议使用pro模式，分别搜索各个对比对象，然后进行综合分析"
                recommended_mode = "pro"
            elif "latest" in detected_types:
                strategy = "时效性策略: 建议使用default模式快速获取最新信息"
                recommended_mode = "default"
            elif "explanation" in detected_types or "analysis" in detected_types:
                strategy = "深度解释策略: 建议使用pro模式进行深度搜索，获取详细解释和分析"
                recommended_mode = "pro"
            elif complexity_score > 0.5:
                strategy = "复杂查询策略: 查询较为复杂，建议使用pro模式确保信息完整性"
                recommended_mode = "pro"
            else:
                strategy = "标准搜索策略: 查询相对简单，使用default模式即可满足需求"
                recommended_mode = "default"

            return f"""搜索策略分析:

查询类型: {', '.join(detected_types) if detected_types else '通用查询'}
复杂度评分: {complexity_score:.2f}/1.0
推荐模式: {recommended_mode}

策略建议: {strategy}

执行建议:
1. 首先使用推荐模式进行搜索
2. 如果结果不够详细，可以尝试pro模式
3. 如果需要对比信息，建议分步骤搜索各个方面"""

        except Exception as e:
            brain_logger.error(f"SearchStrategyTool执行失败: {str(e)}")
            return f"策略分析失败: {str(e)}"
