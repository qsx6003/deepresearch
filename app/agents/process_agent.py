"""
内容处理Agent实现
"""
import re
from typing import List
import requests
from bs4 import BeautifulSoup
from ..models.schemas import AgentState, ProcessedContent, SearchResult
from ..utils.logger import brain_logger
class ProcessAgent:
    async def process(self, state: AgentState) -> AgentState:
        """
        处理搜索结果内容
        
        Args:
            state: 当前Agent状态
            
        Returns:
            AgentState: 更新后的状态
        """
        try:
            if not state.search_results:
                raise ValueError("No search results to process")
                
            processed_content = []

            for result in state.search_results:
                # 首先使用snippet
                content = ProcessedContent(
                    text=result.get("snippet", ""),
                    metadata={
                        "url": result.get("url", ""),      # 使用 url 而不是 source
                        "title": result.get("title", ""),
                        "source": "processed"              # 添加处理来源标识
                    }
                )

                # 如果需要，获取完整网页内容
                if self._should_fetch_full_content(result):
                    try:
                        full_content = await self._fetch_and_extract_content(result.get("url", ""))
                        if full_content:
                            content.text = full_content
                    except Exception as e:
                        # 如果获取完整内容失败，继续使用snippet
                        pass

                # 转换为字典格式以匹配 AgentState 的类型定义
                processed_content.append({
                    "text": content.text,
                    "metadata": content.metadata
                })

            state.processed_content = processed_content
            return state
            
        except Exception as e:
            state.error = f"Content processing failed: {str(e)}"
            return state
            
    def _should_fetch_full_content(self, result) -> bool:
        """更智能的判断逻辑"""
        snippet = result.get("snippet", "") if isinstance(result, dict) else result.snippet
        url = result.get("url", "") if isinstance(result, dict) else result.url
        
        # 1. snippet 太短
        if len(snippet) < 200:
            return True
        
        # 2. 特定类型的网站（通常内容更丰富）
        rich_content_domains = ["wikipedia.org", "baike.baidu.com", "zhihu.com"]
        if any(domain in url for domain in rich_content_domains):
            return True
        
        # 3. snippet 包含"更多"、"详细"等关键词
        if any(keyword in snippet for keyword in ["更多", "详细", "完整", "全文"]):
            return True
        
        # 4. 学术或新闻网站
        academic_domains = [".edu", ".gov", "news", "paper"]
        if any(domain in url for domain in academic_domains):
            return True
        
        return False
        
    async def _fetch_and_extract_content(self, url: str) -> str:
        """
        获取并提取网页内容
        """
        try:
            # 发送请求
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除不需要的元素
            for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
                
            # 提取正文
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            
            if main_content:
                # 获取所有段落文本
                paragraphs = main_content.find_all('p')
                text = ' '.join(p.get_text().strip() for p in paragraphs)
                
                # 清理文本
                text = self._clean_text(text)
                #brain_logger.info(f"Fetched and cleaned content {text}")
                
                return text
                
            return ""
            
        except Exception as e:
            raise Exception(f"Failed to fetch content from {url}: {str(e)}")
            
    def _clean_text(self, text: str) -> str:
        """
        清理提取的文本
        """
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,?!，。？！]', '', text)
        
        # 移除空行
        text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
        
        return text.strip()

# 创建全局内容处理Agent实例
process_agent = ProcessAgent() 