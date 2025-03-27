"""
網站爬蟲監控模組 - 監控網站爬蟲服務
"""

import time
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from ..utils.http import async_get, HttpError
from ..utils.logging import get_logger
from .base_monitor import BaseMonitor, Alert, AlertLevel, ServiceStatus

logger = get_logger(__name__)

class WebCrawlerMonitor(BaseMonitor):
    """
    網站爬蟲監控器，負責監控網站爬蟲相關服務
    """
    
    def __init__(self, name: str, service_url: str, check_interval: int = 60, api_key: Optional[str] = None):
        """
        初始化網站爬蟲監控器
        
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
        檢查網站爬蟲服務狀態，僅驗證服務是否在線
        
        Returns:
            (狀態, 狀態訊息, 警報列表)
        """
        alerts = []
        
        try:
            # 獲取網站爬蟲服務狀態，僅檢查主URL是否可訪問
            response = await async_get(self.service_url, headers=self.headers)
            
            # 檢查回應是否成功
            if response.get("success", False):
                # 獲取回應內容
                response_text = response.get("text", "").strip()
                
                # 檢查是否返回了成功狀態
                if response.get("content_type", "").startswith("application/json"):
                    try:
                        # 嘗試解析JSON回應中的狀態
                        import json
                        json_data = json.loads(response_text)
                        if json_data.get("status") == "success":
                            status = ServiceStatus.ONLINE
                            message = "網站爬蟲服務正常運行"
                        else:
                            status = ServiceStatus.DEGRADED
                            message = f"網站爬蟲服務返回異常狀態: {json_data.get('status')}"
                            alerts.append(Alert(
                                monitor_name=self.name,
                                title="網站爬蟲服務異常",
                                message=message,
                                level=AlertLevel.MEDIUM
                            ))
                    except (json.JSONDecodeError, KeyError):
                        # JSON解析失敗，但服務仍然可達
                        status = ServiceStatus.ONLINE
                        message = f"網站爬蟲服務可連接，但返回非標準JSON"
                else:
                    # 非JSON回應，但服務仍在線
                    status = ServiceStatus.ONLINE
                    message = f"網站爬蟲服務可連接，回應: {response_text[:100]}..."
                
                self.logger.info(f"服務 {self.name} 狀態: {status}, 訊息: {message}")
            else:
                # 服務回應但不成功
                status = ServiceStatus.DEGRADED
                message = f"網站爬蟲服務回應異常"
                alerts.append(Alert(
                    monitor_name=self.name,
                    title="網站爬蟲服務回應異常",
                    message=f"服務回應格式異常",
                    level=AlertLevel.MEDIUM
                ))
        
        except HttpError as e:
            # API響應錯誤
            status = ServiceStatus.DEGRADED
            message = f"服務 API 回應錯誤: {e.status_code} - {e.message[:100]}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="網站爬蟲服務 API 錯誤",
                message=f"爬蟲服務回應錯誤: {e.status_code}",
                level=AlertLevel.HIGH,
                details={"status_code": e.status_code}
            ))
        except Exception as e:
            # 其他錯誤
            status = ServiceStatus.DEGRADED
            message = f"檢查網站爬蟲服務時發生未預期錯誤: {str(e)}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="網站爬蟲服務檢查錯誤",
                message=f"檢查爬蟲服務時發生錯誤: {str(e)}",
                level=AlertLevel.HIGH,
                details={"error": str(e)}
            ))
        
        return status, message, alerts 