"""
日志工具模块
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_console_handler():
    """获取控制台日志处理器"""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler

def get_file_handler(filename):
    """获取文件日志处理器"""
    file_handler = RotatingFileHandler(
        LOG_DIR / filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(FORMATTER)
    return file_handler

def get_logger(logger_name, log_file=None):
    """
    获取logger实例
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)  # 可通过环境变量配置
    
    # 添加控制台处理器
    logger.addHandler(get_console_handler())
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        logger.addHandler(get_file_handler(log_file))
    
    # 防止日志重复
    logger.propagate = False
    
    return logger

# 创建各个模块的logger
search_logger = get_logger('search', 'search.log')
brain_logger = get_logger('brain', 'brain.log')
rag_logger = get_logger('rag', 'rag.log')
llm_logger = get_logger('llm', 'llm.log')
vectorstore_logger = get_logger('vectorstore', 'vectorstore.log') 