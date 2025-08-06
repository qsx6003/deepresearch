"""
Wolfram Alpha 工具实现
"""
from typing import Optional
import wolframalpha
from ...config import settings

class WolframAlphaTool:
    """Wolfram Alpha 查询工具"""
    
    def __init__(self, app_id: Optional[str] = None):
        self.app_id = app_id or settings.wolfram_alpha_app_id
        if not self.app_id:
            raise ValueError("Wolfram Alpha APP ID is required")
        self.client = wolframalpha.Client(self.app_id)
        
    async def query(self, question: str) -> dict:
        """
        执行 Wolfram Alpha 查询
        
        适用场景:
        - 数学计算: "solve x^2 + 2x + 1 = 0"
        - 单位转换: "convert 100 kilometers to miles"
        - 科学数据: "mass of earth"
        - 统计数据: "population of China"
        - 地理信息: "distance between Paris and London"
        
        Args:
            question: 查询问题
            
        Returns:
            dict: 查询结果，包含:
                - success: 是否成功
                - answer: 答案文本
                - pods: 详细数据单元
                - error: 错误信息(如果有)
        """
        try:
            # 执行查询
            res = self.client.query(question)
            
            # 检查是否有结果
            if not hasattr(res, 'pods'):
                return {
                    "success": False,
                    "error": "No results found"
                }
                
            # 提取所有数据单元
            pods = []
            for pod in res.pods:
                if pod.text:
                    pods.append({
                        "title": pod.title,
                        "text": pod.text
                    })
                    
            # 获取主要答案
            answer = next(res.results).text if hasattr(res, 'results') else None
            
            return {
                "success": True,
                "answer": answer,
                "pods": pods
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    def is_configured(self) -> bool:
        """检查是否配置正确"""
        return bool(self.app_id)
        
# 创建全局实例
wolfram_tool = WolframAlphaTool() 