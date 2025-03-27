"""
Telegram監控模組 - 監控Telegram通知服務
"""

import time
from typing import Dict, Any, List, Tuple, Optional
import requests

from ..utils.http import async_get, HttpError
from ..utils.logging import get_logger
from .base_monitor import BaseMonitor, Alert, AlertLevel, ServiceStatus

logger = get_logger(__name__)

class TelegramMonitor(BaseMonitor):
    """
    Telegram監控器，負責監控Telegram通知服務的狀態
    """
    
    def __init__(self, name: str, bot_token: str, check_interval: int = 60):
        """
        初始化Telegram監控器
        
        Args:
            name: 監控器名稱
            bot_token: Telegram機器人令牌
            check_interval: 檢查間隔（秒）
        """
        super().__init__(name, "https://api.telegram.org", check_interval)
        self.bot_token = bot_token
        self.service_url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    async def check_service(self) -> Tuple[str, str, List[Alert]]:
        """
        檢查Telegram服務狀態，驗證機器人令牌是否有效，API是否可用
        
        Returns:
            (狀態, 狀態訊息, 警報列表)
        """
        alerts = []
        
        try:
            # 使用getMe方法檢查機器人是否有效
            response = await async_get(self.service_url, expect_json=True)
            
            # 檢查回應是否包含ok字段且為true
            if response.get("ok", False):
                status = ServiceStatus.ONLINE
                bot_info = response.get("result", {})
                bot_name = bot_info.get("first_name", "Unknown")
                bot_username = bot_info.get("username", "Unknown")
                
                message = f"Telegram機器人服務正常運行 (Bot: {bot_name} @{bot_username})"
                self.logger.info(f"服務 {self.name} 狀態: {status}, 訊息: {message}")
            else:
                # API響應但不包含有效機器人信息
                status = ServiceStatus.DEGRADED
                error_description = response.get("description", "未知錯誤")
                message = f"Telegram機器人配置錯誤: {error_description}"
                alerts.append(Alert(
                    monitor_name=self.name,
                    title="Telegram機器人配置錯誤",
                    message=message,
                    level=AlertLevel.HIGH
                ))
        
        except HttpError as e:
            # API回應錯誤
            status = ServiceStatus.DEGRADED
            message = f"Telegram API錯誤: {e.status_code} - {e.message[:100]}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="Telegram API錯誤",
                message=f"無法連接到Telegram API: {e.status_code}",
                level=AlertLevel.HIGH,
                details={"status_code": e.status_code, "error": e.message}
            ))
        except Exception as e:
            # 其他錯誤
            status = ServiceStatus.DEGRADED
            message = f"檢查Telegram服務時發生未預期錯誤: {str(e)}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="Telegram服務檢查錯誤",
                message=f"檢查Telegram服務時發生錯誤: {str(e)}",
                level=AlertLevel.HIGH,
                details={"error": str(e)}
            ))
        
        return status, message, alerts
    
    async def test_send_message(self, chat_id: str, message: str = "測試訊息") -> Tuple[bool, str]:
        """
        測試向指定聊天發送訊息
        
        Args:
            chat_id: 目標聊天ID
            message: 要發送的訊息
        
        Returns:
            (是否成功, 訊息)
        """
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        
        try:
            # 使用異步HTTP客戶端發送POST請求
            async with self.http_client.session() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        if response_json.get("ok", False):
                            return True, "訊息發送成功"
                        else:
                            return False, f"API回應錯誤: {response_json.get('description', '未知錯誤')}"
                    else:
                        return False, f"HTTP錯誤: {response.status} - {await response.text()}"
        except Exception as e:
            return False, f"發送訊息時出錯: {str(e)}" 