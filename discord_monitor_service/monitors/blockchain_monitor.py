"""
區塊鏈監控模組 - 監控區塊鏈服務
"""

import time
from typing import Dict, Any, List, Tuple, Optional
import json

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
        self.last_block_height = None
        self.last_block_time = None
    
    async def check_service(self) -> Tuple[str, str, List[Alert]]:
        """
        檢查區塊鏈服務狀態
        
        Returns:
            (狀態, 狀態訊息, 警報列表)
        """
        alerts = []
        
        try:
            # 獲取區塊鏈服務狀態
            # 嘗試獲取服務響應
            response = await async_get(f"{self.service_url}", headers=self.headers)
            
            # 檢查響應內容來判斷服務狀態
            status_text = response.get("text", "")
            
            # 如果響應包含"Monitor is running"，表示服務正常
            if "Monitor is running" in status_text:
                status = ServiceStatus.ONLINE
                message = "區塊鏈監控服務正常運行"
            else:
                # 嘗試獲取更詳細的服務資訊（如果有）
                try:
                    stats_response = await async_get(f"{self.service_url}/stats", headers=self.headers)
                    # 檢查是否有最新區塊信息
                    current_block = stats_response.get("latest_block", {})
                    current_height = current_block.get("height")
                    current_time = current_block.get("time")
                    
                    if current_height:
                        # 檢查區塊是否更新
                        if self.last_block_height and current_height <= self.last_block_height:
                            # 區塊沒有更新，可能有延遲
                            time_diff = time.time() - self.last_block_time if self.last_block_time else 0
                            if time_diff > 600:  # 10分鐘沒有新區塊
                                status = ServiceStatus.DEGRADED
                                message = f"區塊高度 {current_height} 超過10分鐘沒有更新"
                                alerts.append(Alert(
                                    monitor_name=self.name,
                                    title="區塊鏈同步延遲",
                                    message=f"區塊高度 {current_height} 超過10分鐘沒有更新",
                                    level=AlertLevel.MEDIUM,
                                    details={"block_height": current_height, "time_diff": time_diff}
                                ))
                            else:
                                status = ServiceStatus.ONLINE
                                message = f"區塊鏈監控服務正常運行，當前區塊高度: {current_height}"
                        else:
                            # 區塊已更新
                            status = ServiceStatus.ONLINE
                            message = f"區塊鏈監控服務正常運行，當前區塊高度: {current_height}"
                            
                            # 更新最後區塊高度和時間
                            self.last_block_height = current_height
                            self.last_block_time = time.time()
                    else:
                        status = ServiceStatus.DEGRADED
                        message = "無法獲取最新區塊高度"
                        alerts.append(Alert(
                            monitor_name=self.name,
                            title="無法獲取區塊高度",
                            message="區塊鏈監控服務未提供最新區塊高度",
                            level=AlertLevel.MEDIUM
                        ))
                except (HttpError, KeyError, Exception) as e:
                    # 無法獲取詳細統計信息，但基本服務可能仍在運行
                    status = ServiceStatus.ONLINE
                    message = f"區塊鏈監控服務正常運行，但未提供詳細統計: {str(e)}"
                    self.logger.warning(f"未能獲取詳細區塊鏈統計: {str(e)}")
            
            # 檢查交易警報（如果有報告）
            try:
                alerts_response = await async_get(f"{self.service_url}/alerts", headers=self.headers)
                transaction_alerts = alerts_response.get("alerts", [])
                
                for tx_alert in transaction_alerts:
                    # 將服務提供的警報轉換為我們的警報格式
                    level = AlertLevel.HIGH if tx_alert.get("amount_usd", 0) > 1000000 else AlertLevel.MEDIUM
                    alerts.append(Alert(
                        monitor_name=self.name,
                        title=tx_alert.get("title", "大額交易"),
                        message=tx_alert.get("description", "檢測到大額交易"),
                        level=level,
                        details=tx_alert
                    ))
                    
                    if level == AlertLevel.HIGH:
                        self.logger.warning(f"檢測到高價值交易: {tx_alert.get('description')}")
            except (HttpError, KeyError, Exception) as e:
                # 無法獲取警報資訊，但不影響基本服務狀態
                self.logger.warning(f"未能獲取區塊鏈警報: {str(e)}")
            
        except HttpError as e:
            # 服務響應錯誤
            status = ServiceStatus.DEGRADED
            message = f"服務 API 回應錯誤: {e.status_code} - {e.message}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="區塊鏈服務 API 錯誤",
                message=f"區塊鏈監控服務回應錯誤: {e.status_code} - {e.message}",
                level=AlertLevel.HIGH,
                details={"status_code": e.status_code, "error": e.message}
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