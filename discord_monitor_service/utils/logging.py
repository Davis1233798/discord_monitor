"""
日誌工具 - 提供應用程式日誌功能
"""

import os
import logging
import colorlog
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

from ..config import config

# 日誌等級映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# 顏色映射
COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red'
}

class Logger:
    """日誌管理類"""
    
    _instance = None
    
    def __new__(cls):
        """單例模式確保只有一個日誌實例"""
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化日誌記錄器"""
        if self._initialized:
            return
        
        # 建立日誌目錄
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # 設定日誌檔案路徑
        today = datetime.now().strftime('%Y-%m-%d')
        log_filename = log_dir / f'discord_monitor_{today}.log'
        
        # 獲取日誌等級
        log_level_name = config.get('monitoring.log_level', 'INFO')
        log_level = LOG_LEVELS.get(log_level_name, logging.INFO)
        
        # 根日誌記錄器
        self.logger = logging.getLogger('discord_monitor')
        self.logger.setLevel(log_level)
        self.logger.propagate = False
        
        # 清除任何現有的處理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 使用彩色格式化工具
        color_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors=COLORS
        )
        console_handler.setFormatter(color_formatter)
        
        # 檔案處理器
        file_handler = RotatingFileHandler(
            log_filename,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # 檔案格式化工具
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # 添加處理器到日誌記錄器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        self._initialized = True
    
    def get_logger(self, name='discord_monitor'):
        """
        獲取命名的日誌記錄器
        
        Args:
            name: 日誌記錄器名稱
            
        Returns:
            命名的日誌記錄器實例
        """
        logger = logging.getLogger(name)
        logger.parent = self.logger
        return logger


# 全局日誌實例
logger_manager = Logger()

def get_logger(name):
    """
    獲取指定名稱的日誌記錄器
    
    Args:
        name: 日誌記錄器名稱
    
    Returns:
        日誌記錄器實例
    """
    return logger_manager.get_logger(name) 