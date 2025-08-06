"""
搜索结果缓存系统
"""
from typing import List, Optional, Dict
import time
import json
import hashlib
from pathlib import Path
from ...models.schemas import SearchResult

class SearchCache:
    def __init__(
        self,
        cache_dir: str = "./data/search_cache",
        ttl: int = 3600  # 默认缓存1小时
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_key(self, query: str, engines: Optional[List[str]] = None) -> str:
        """生成缓存键"""
        # 将查询和引擎列表组合成唯一标识
        cache_data = {
            "query": query.lower().strip(),
            "engines": sorted(engines) if engines else "all"
        }
        
        # 生成MD5哈希作为缓存键
        cache_key = hashlib.md5(
            json.dumps(cache_data, sort_keys=True).encode()
        ).hexdigest()
        
        return cache_key
        
    def _get_cache_file(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"
        
    def get(
        self,
        query: str,
        engines: Optional[List[str]] = None
    ) -> Optional[List[SearchResult]]:
        """获取缓存的搜索结果"""
        cache_key = self._get_cache_key(query, engines)
        cache_file = self._get_cache_file(cache_key)
        
        if not cache_file.exists():
            return None
            
        try:
            cache_data = json.loads(cache_file.read_text())
            
            # 检查缓存是否过期
            if time.time() - cache_data["timestamp"] > self.ttl:
                cache_file.unlink()  # 删除过期缓存
                return None
                
            # 将缓存数据转换回SearchResult对象
            return [
                SearchResult(**result)
                for result in cache_data["results"]
            ]
            
        except Exception as e:
            # 如果缓存文件损坏，删除它
            cache_file.unlink()
            return None
            
    def set(
        self,
        query: str,
        results: List[SearchResult],
        engines: Optional[List[str]] = None
    ) -> None:
        """缓存搜索结果"""
        cache_key = self._get_cache_key(query, engines)
        cache_file = self._get_cache_file(cache_key)
        
        # 准备缓存数据
        cache_data = {
            "timestamp": time.time(),
            "results": [
                result.dict()
                for result in results
            ]
        }
        
        # 写入缓存文件
        cache_file.write_text(json.dumps(cache_data, indent=2))
        
    def clear_expired(self) -> int:
        """清理过期缓存"""
        cleared_count = 0
        current_time = time.time()
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_data = json.loads(cache_file.read_text())
                if current_time - cache_data["timestamp"] > self.ttl:
                    cache_file.unlink()
                    cleared_count += 1
            except Exception:
                # 如果文件损坏，直接删除
                cache_file.unlink()
                cleared_count += 1
                
        return cleared_count
        
    def clear_all(self) -> int:
        """清理所有缓存"""
        cleared_count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            cleared_count += 1
        return cleared_count

# 创建全局缓存实例
search_cache = SearchCache() 