"""
監控基類 - 定義所有監控器的共用接口
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import time

from ..utils.logging import get_logger
from ..utils.http import is_service_online

logger = get_logger(__name__)

class ServiceStatus:
    """服務狀態類"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

class AlertLevel:
    """警報等級類"""
    CRITICAL = "critical"  # 緊急，需要立即處理
    HIGH = "high"          # 高，需要儘快處理
    MEDIUM = "medium"      # 中等，需要注意
    LOW = "low"            # 低，不需要立即處理
    INFO = "info"          # 信息性質，僅作通知

class Alert:
    """
    警報類，記錄監控警報
    """
    
    def __init__(self, 
                monitor_name: str,
                title: str, 
                message: str, 
                level: str = AlertLevel.INFO,
                details: Optional[Dict[str, Any]] = None,
                timestamp: Optional[float] = None):
        """
        初始化警報
        
        Args:
            monitor_name: 產生警報的監控器名稱
            title: 警報標題
            message: 警報訊息
            level: 警報等級 (使用 AlertLevel 類)
            details: 詳細資訊 (字典)
            timestamp: 時間戳 (如未提供則使用當前時間)
        """
        self.monitor_name = monitor_name
        self.title = title
        self.message = message
        self.level = level
        self.details = details or {}
        self.timestamp = timestamp or time.time()
        self.datetime = datetime.fromtimestamp(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "monitor": self.monitor_name,
            "title": self.title,
            "message": self.message,
            "level": self.level,
            "details": self.details,
            "timestamp": self.timestamp,
            "datetime": self.datetime.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """從字典創建警報"""
        return cls(
            monitor_name=data["monitor"],
            title=data["title"],
            message=data["message"],
            level=data["level"],
            details=data["details"],
            timestamp=data["timestamp"]
        )

class BaseMonitor(ABC):
    """
    監控器基類，所有監控器應繼承此類
    """
    
    def __init__(self, name: str, service_url: str, check_interval: int = 60):
        """
        初始化監控器
        
        Args:
            name: 監控器名稱
            service_url: 服務URL
            check_interval: 檢查間隔（秒）
        """
        self.name = name
        self.service_url = service_url
        self.check_interval = check_interval
        self.logger = get_logger(f"monitor.{name}")
        self.status = ServiceStatus.UNKNOWN
        self.last_check_time = 0
        self.status_message = "監控尚未開始"
        self.alerts = []
        self.running = False
        
        # 將最後一次檢查的結果暫存
        self._last_check_result = None
    
    @abstractmethod
    async def check_service(self) -> Tuple[str, str, List[Alert]]:
        """
        檢查服務狀態
        
        Returns:
            (狀態, 狀態訊息, 警報列表)
        """
        pass
    
    async def monitor_service(self):
        """
        持續監控服務，這是一個長期運行的任務
        """
        self.running = True
        self.logger.info(f"開始監控服務 {self.name} ({self.service_url})")
        
        while self.running:
            try:
                # 檢查基本連通性
                is_online, message = is_service_online(self.service_url)
                
                if not is_online:
                    # 如果服務離線，記錄並發出警報
                    self.status = ServiceStatus.OFFLINE
                    self.status_message = message
                    alert = Alert(
                        monitor_name=self.name,
                        title=f"服務 {self.name} 離線",
                        message=f"服務 {self.name} 已離線: {message}",
                        level=AlertLevel.CRITICAL,
                        details={"url": self.service_url}
                    )
                    self.alerts.append(alert)
                    self.logger.error(f"服務 {self.name} 離線: {message}")
                else:
                    # 服務在線，執行詳細檢查
                    try:
                        status, message, new_alerts = await self.check_service()
                        
                        self.status = status
                        self.status_message = message
                        
                        # 如果有新警報，添加到列表中
                        if new_alerts:
                            self.alerts.extend(new_alerts)
                            for alert in new_alerts:
                                log_method = (
                                    self.logger.critical if alert.level == AlertLevel.CRITICAL else
                                    self.logger.error if alert.level == AlertLevel.HIGH else
                                    self.logger.warning if alert.level == AlertLevel.MEDIUM else
                                    self.logger.info
                                )
                                log_method(f"{alert.title}: {alert.message}")
                        
                        self.logger.debug(f"服務 {self.name} 狀態: {status}, 訊息: {message}")
                    except Exception as e:
                        self.status = ServiceStatus.DEGRADED
                        self.status_message = f"檢查服務時發生錯誤: {str(e)}"
                        
                        # 創建異常警報
                        alert = Alert(
                            monitor_name=self.name,
                            title=f"服務 {self.name} 檢查失敗",
                            message=f"檢查服務 {self.name} 時發生錯誤: {str(e)}",
                            level=AlertLevel.HIGH,
                            details={"url": self.service_url, "error": str(e)}
                        )
                        self.alerts.append(alert)
                        self.logger.error(f"檢查服務 {self.name} 時發生錯誤: {str(e)}")
                
                # 更新最後檢查時間
                self.last_check_time = time.time()
                
            except Exception as e:
                self.logger.exception(f"監控服務 {self.name} 時發生未處理的異常: {str(e)}")
            
            # 等待下一次檢查
            await asyncio.sleep(self.check_interval)
    
    def get_status(self) -> Dict[str, Any]:
        """
        獲取服務狀態
        
        Returns:
            包含狀態信息的字典
        """
        return {
            "name": self.name,
            "url": self.service_url,
            "status": self.status,
            "message": self.status_message,
            "last_check": self.last_check_time,
            "check_interval": self.check_interval,
            "alert_count": len(self.alerts)
        }
    
    def get_recent_alerts(self, count: int = 5) -> List[Alert]:
        """
        獲取最近的警報
        
        Args:
            count: 要獲取的警報數量
            
        Returns:
            警報列表
        """
        return sorted(self.alerts, key=lambda x: x.timestamp, reverse=True)[:count]
    
    def stop(self):
        """停止監控"""
        self.running = False
        self.logger.info(f"停止監控服務 {self.name}")
    
    def create_alert(self, title: str, message: str, level: str = AlertLevel.INFO, 
                    details: Optional[Dict[str, Any]] = None) -> Alert:
        """
        創建新警報
        
        Args:
            title: 警報標題
            message: 警報訊息
            level: 警報等級
            details: 詳細資訊
            
        Returns:
            創建的警報
        """
        alert = Alert(
            monitor_name=self.name,
            title=title,
            message=message,
            level=level,
            details=details or {}
        )
        self.alerts.append(alert)
        return alert 