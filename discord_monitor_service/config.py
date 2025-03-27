"""
配置管理模組 - 處理應用程式配置和環境變數
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

class ConfigurationError(Exception):
    """配置錯誤異常"""
    pass

class Config:
    """配置管理類"""
    
    _instance = None
    
    def __new__(cls):
        """單例模式確保只有一個配置實例"""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if self._initialized:
            return
        
        # 載入環境變數
        load_dotenv()
        
        # 載入默認配置
        self._config_dir = Path(os.getenv('CONFIG_DIR', '.'))
        self._config = self._load_yaml_config()
        
        # 合併環境變數與配置文件
        self._merge_env_variables()
        
        # 驗證必要配置
        self._validate_config()
        
        self._initialized = True
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """載入YAML配置文件"""
        config_path = self._config_dir / 'config.yaml'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file) or {}
            except Exception as e:
                print(f"警告: 無法載入配置文件 {config_path}: {e}")
                return {}
        else:
            print(f"警告: 配置文件不存在: {config_path}")
            return {}
    
    def _merge_env_variables(self):
        """合併環境變數到配置中"""
        # Discord 設定
        self._config['discord'] = {
            'bot_token': os.getenv('DISCORD_BOT_TOKEN'),
            'guild_id': os.getenv('DISCORD_GUILD_ID'),
            'channels': {
                'general': os.getenv('DISCORD_GENERAL_CHANNEL_ID'),
                'blockchain': os.getenv('DISCORD_BLOCKCHAIN_CHANNEL_ID'),
                'webcrawler': os.getenv('DISCORD_WEBCRAWLER_CHANNEL_ID'),
                'n8n': os.getenv('DISCORD_N8N_CHANNEL_ID'),
                'alerts': os.getenv('DISCORD_ALERTS_CHANNEL_ID')
            }
        }
        
        # 服務端點
        self._config['services'] = {
            'telegram': {
                'bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
                'chat_id': os.getenv('TELEGRAM_CHAT_ID')
            },
            'blockchain': {
                'url': os.getenv('BLOCKCHAIN_SERVICE_URL', 'https://onchain-monitor.onrender.com/'),
                'api_key': os.getenv('BLOCKCHAIN_API_KEY')
            },
            'webcrawler': {
                'url': os.getenv('WEBCRAWLER_SERVICE_URL', 'https://monitor-flask-flame.vercel.app/'),
                'api_key': os.getenv('WEBCRAWLER_API_KEY')
            },
            'n8n': {
                'url': os.getenv('N8N_SERVICE_URL', 'https://n8n-latest-wz1v.onrender.com')
            }
        }
        
        # 監控設定
        self._config['monitoring'] = {
            'polling_interval': int(os.getenv('POLLING_INTERVAL', '60')),
            'alert_cooldown': int(os.getenv('ALERT_COOLDOWN', '300')),
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }
        
        # 資料庫設定
        self._config['database'] = {
            'connection_string': os.getenv('DB_CONNECTION_STRING', 'sqlite:///data/monitoring.db')
        }
        
        # 通知設定
        self._config['notifications'] = {
            'email': {
                'enabled': bool(os.getenv('SMTP_SERVER')),
                'smtp_server': os.getenv('SMTP_SERVER'),
                'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                'username': os.getenv('SMTP_USERNAME'),
                'password': os.getenv('SMTP_PASSWORD'),
                'from_address': os.getenv('NOTIFICATION_EMAIL')
            }
        }
    
    def _validate_config(self):
        """驗證配置是否完整和有效"""
        required_configs = [
            ('discord.bot_token', '未設定 DISCORD_BOT_TOKEN'),
            ('discord.guild_id', '未設定 DISCORD_GUILD_ID'),
            ('discord.channels.general', '未設定 DISCORD_GENERAL_CHANNEL_ID'),
            ('services.blockchain.url', '未設定 BLOCKCHAIN_SERVICE_URL'),
            ('services.webcrawler.url', '未設定 WEBCRAWLER_SERVICE_URL'),
            ('services.n8n.url', '未設定 N8N_SERVICE_URL')
        ]
        
        for path, error_msg in required_configs:
            if not self.get(path):
                raise ConfigurationError(error_msg)
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        從配置中獲取值，使用點標記(.)的路徑訪問嵌套鍵
        
        Args:
            path: 使用點標記的配置路徑，例如 'discord.bot_token'
            default: 如果路徑不存在時的默認值
        
        Returns:
            配置值或默認值
        """
        parts = path.split('.')
        value = self._config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """返回完整配置的副本"""
        return self._config.copy()


# 全局配置實例
config = Config() 