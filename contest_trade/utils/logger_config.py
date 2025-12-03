"""
Loguru 日志配置模块
用于加载和应用日志配置
"""

import os
import sys
import yaml
from pathlib import Path
from loguru import logger


def setup_logger(config_path=None):
    """
    设置loguru日志配置
    
    Args:
        config_path (str, optional): 配置文件路径，默认为项目根目录下的log_config.yaml
            也可以通过环境变量 LOG_CONFIG_FILE 指定
    """
    # 确定配置文件路径
    if config_path is None:
        config_path = os.environ.get('LOG_CONFIG_FILE', 'log_config.yaml')
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent
    config_file = project_root / config_path
    
    # 如果配置文件不存在，使用默认配置
    if not config_file.exists():
        print(f"警告: 日志配置文件 {config_file} 不存在，使用默认配置")
        logger.add(
            "logs/app_{time:YYYY-MM-DD_HH-mm-ss}.log",
            level="INFO",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8"
        )
        return logger
    
    # 加载配置
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            log_config = yaml.safe_load(f)
    except Exception as e:
        print(f"加载日志配置文件失败: {e}，使用默认配置")
        logger.add(
            "logs/app_{time:YYYY-MM-DD_HH-mm-ss}.log",
            level="INFO",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8"
        )
        return logger
    
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台处理器
    if log_config.get('console', {}).get('enabled', True):
        logger.add(
            sys.stderr,
            level=log_config['console'].get('level', 'INFO'),
            colorize=log_config['console'].get('colorize', True),
            format=log_config.get('format',
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
        )
    
    # 添加文件处理器
    if log_config.get('file', {}).get('enabled', True):
        # 确保日志目录存在
        file_path = log_config['file']['path']
        log_dir = Path(file_path).parent
        log_dir.mkdir(exist_ok=True, parents=True)
        
        logger.add(
            file_path,
            level=log_config['file'].get('level', 'DEBUG'),
            format=log_config.get('format', 
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"),
            rotation=log_config['file'].get('rotation', '10 MB'),
            retention=log_config['file'].get('retention', '7 days'),
            compression=log_config['file'].get('compression', 'zip'),
            encoding=log_config['file'].get('encoding', 'utf-8')
        )
    
    # 添加错误文件处理器
    if log_config.get('error_file', {}).get('enabled', True):
        # 确保日志目录存在
        error_file_path = log_config['error_file']['path']
        error_log_dir = Path(error_file_path).parent
        error_log_dir.mkdir(exist_ok=True, parents=True)
        
        logger.add(
            error_file_path,
            level=log_config['error_file'].get('level', 'ERROR'),
            format=log_config.get('format', 
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"),
            rotation=log_config['error_file'].get('rotation', '5 MB'),
            retention=log_config['error_file'].get('retention', '30 days'),
            compression=log_config['error_file'].get('compression', 'zip'),
            encoding=log_config['error_file'].get('encoding', 'utf-8')
        )
    
    # 设置异常捕获
    if log_config.get('catch_exceptions', True):
        logger.configure(
            extra={"diagnose": log_config.get('diagnose', True)}
        )
    
    return logger


# 全局logger实例
_logger = None

def get_logger():
    """获取配置好的logger实例"""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger


if __name__ == "__main__":
    # 测试日志配置
    test_logger = get_logger()
    test_logger.debug("这是一条调试信息")
    test_logger.info("这是一条信息")
    test_logger.warning("这是一条警告")
    test_logger.error("这是一条错误")
    test_logger.critical("这是一条严重错误")
    
    print("日志配置测试完成，请检查logs目录下的日志文件")