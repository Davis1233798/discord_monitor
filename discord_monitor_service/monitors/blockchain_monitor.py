"""
區塊鏈監控模組 - 監控區塊鏈服務
"""

import time
from typing import Dict, Any, List, Tuple, Optional

from ..utils.http import async_get, HttpError
from ..utils.logging import get_logger
from .base_monitor import BaseMonitor, Alert, AlertLevel, ServiceStatus

logger = get_logger(__name__)

class BlockchainMonitor(BaseMonitor):
    """
    區塊鏈監控器，負責監控區塊鏈相關服務
    """
    
    def __init__(self, name: str, service_url: str, check_interval: int = 60, api_key: Optional[str] = None):
        """
        初始化區塊鏈監控器
        
        Args:
            name: 監控器名稱
            service_url: 服務URL
            check_interval: 檢查間隔（秒）
            api_key: API金鑰（如果需要）
        """
        super().__init__(name, service_url, check_interval)
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    
    async def check_service(self) -> Tuple[str, str, List[Alert]]:
        """
        檢查區塊鏈服務狀態，僅驗證服務是否在線
        
        Returns:
            (狀態, 狀態訊息, 警報列表)
        """
        alerts = []
        
        try:
            # 獲取區塊鏈服務狀態，僅檢查能否連接到主URL
            response = await async_get(self.service_url, headers=self.headers)
            
            # 檢查回應是否正常
            if response.get("success", False):
                status = ServiceStatus.ONLINE
                response_text = response.get("text", "").strip()
                
                # 分析回應內容
                if "Monitor is running" in response_text:
                    message = "區塊鏈監控服務正常運行"
                else:
                    message = f"區塊鏈監控服務可連接，回應: {response_text[:100]}..."
                
                self.logger.info(f"服務 {self.name} 狀態: {status}, 訊息: {message}")
            else:
                # 服務回應但不成功
                status = ServiceStatus.DEGRADED
                message = f"區塊鏈監控服務回應異常"
                alerts.append(Alert(
                    monitor_name=self.name,
                    title="區塊鏈服務回應異常",
                    message=f"服務回應格式異常",
                    level=AlertLevel.MEDIUM
                ))
        
        except HttpError as e:
            # 服務響應錯誤
            status = ServiceStatus.DEGRADED
            message = f"服務 API 回應錯誤: {e.status_code} - {e.message[:100]}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="區塊鏈服務 API 錯誤",
                message=f"區塊鏈監控服務回應錯誤: {e.status_code}",
                level=AlertLevel.HIGH,
                details={"status_code": e.status_code}
            ))
        except Exception as e:
            # 其他錯誤
            status = ServiceStatus.DEGRADED
            message = f"檢查區塊鏈服務時發生未預期錯誤: {str(e)}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="區塊鏈服務檢查錯誤",
                message=f"檢查區塊鏈監控服務時發生錯誤: {str(e)}",
                level=AlertLevel.HIGH,
                details={"error": str(e)}
            ))
        
        return status, message, alerts 