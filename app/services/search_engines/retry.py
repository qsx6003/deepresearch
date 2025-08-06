"""
重试机制装饰器
"""
import asyncio
from functools import wraps
from typing import TypeVar, Callable, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar("T")

def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0
):
    """
    异步重试装饰器
    
    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间(秒)
        max_delay: 最大延迟时间(秒)
        backoff_factor: 退避因子
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"Failed after {max_retries} retries: {str(e)}"
                        )
                        raise
                        
                    # 计算下一次重试的延迟时间
                    delay = min(delay * backoff_factor, max_delay)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )
                    
                    # 添加一些随机抖动来避免多个请求同时重试
                    jitter = delay * 0.1 * (asyncio.Random().random() * 2 - 1)
                    await asyncio.sleep(delay + jitter)
                    
            return None
            
        return wrapper
    return decorator 