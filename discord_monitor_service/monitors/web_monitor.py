"""
網站爬蟲監控模組 - 監控網站爬蟲服務
"""

import time
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta

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
        self.last_crawl_time = None
        self.last_successful_crawl = None
    
    async def check_service(self) -> Tuple[str, str, List[Alert]]:
        """
        檢查網站爬蟲服務狀態
        
        Returns:
            (狀態, 狀態訊息, 警報列表)
        """
        alerts = []
        
        try:
            # 獲取網站爬蟲服務狀態
            response = await async_get(self.service_url, headers=self.headers)
            
            # 分析回應來確定服務狀態
            if response.get("status") == "success":
                status = ServiceStatus.ONLINE
                message = "網站爬蟲服務正常運行"
                
                # 檢查最近的爬蟲活動
                try:
                    stats_response = await async_get(f"{self.service_url}/stats", headers=self.headers)
                    
                    # 如果有上次爬蟲時間，檢查爬蟲頻率
                    last_crawl = stats_response.get("last_crawl_time")
                    if last_crawl:
                        self.last_crawl_time = datetime.fromisoformat(last_crawl)
                        time_diff = datetime.now() - self.last_crawl_time
                        
                        # 檢查是否超過預期的爬蟲間隔
                        expected_interval = stats_response.get("expected_interval_minutes", 30)
                        if time_diff > timedelta(minutes=expected_interval*1.5):  # 給予50%的緩衝
                            status = ServiceStatus.DEGRADED
                            message = f"爬蟲服務延遲: 最後爬蟲時間為 {self.last_crawl_time.isoformat()}"
                            alerts.append(Alert(
                                monitor_name=self.name,
                                title="爬蟲服務延遲",
                                message=f"爬蟲服務超過 {time_diff.total_seconds()/60:.1f} 分鐘未執行，預期間隔為 {expected_interval} 分鐘",
                                level=AlertLevel.MEDIUM,
                                details={"last_crawl": last_crawl, "expected_interval": expected_interval}
                            ))
                    
                    # 檢查爬蟲成功率
                    success_rate = stats_response.get("success_rate")
                    if success_rate is not None and success_rate < 0.8:  # 低於80%成功率
                        status = ServiceStatus.DEGRADED
                        message = f"爬蟲成功率低: {success_rate*100:.1f}%"
                        alerts.append(Alert(
                            monitor_name=self.name,
                            title="爬蟲成功率低",
                            message=f"爬蟲服務成功率為 {success_rate*100:.1f}%，低於預期的80%",
                            level=AlertLevel.MEDIUM,
                            details={"success_rate": success_rate}
                        ))
                    
                    # 檢查爬蟲錯誤
                    recent_errors = stats_response.get("recent_errors", [])
                    if recent_errors and len(recent_errors) > 0:
                        for error in recent_errors[:5]:  # 最多報告5個錯誤
                            alerts.append(Alert(
                                monitor_name=self.name,
                                title="爬蟲錯誤",
                                message=f"爬蟲服務報告錯誤: {error.get('message', '未知錯誤')}",
                                level=AlertLevel.MEDIUM,
                                details=error
                            ))
                
                except (HttpError, KeyError, ValueError, Exception) as e:
                    # 無法獲取詳細統計資訊，但基本服務仍在運行
                    self.logger.warning(f"未能獲取爬蟲服務詳細統計: {str(e)}")
                
                # 檢查監測到的網站變更
                try:
                    alerts_response = await async_get(f"{self.service_url}/alerts", headers=self.headers)
                    website_alerts = alerts_response.get("alerts", [])
                    
                    for website_alert in website_alerts:
                        level = website_alert.get("level", "medium").lower()
                        alert_level = (
                            AlertLevel.CRITICAL if level == "critical" else
                            AlertLevel.HIGH if level == "high" else
                            AlertLevel.MEDIUM if level == "medium" else
                            AlertLevel.LOW
                        )
                        
                        alerts.append(Alert(
                            monitor_name=self.name,
                            title=website_alert.get("title", "網站變更"),
                            message=website_alert.get("message", "檢測到網站變更"),
                            level=alert_level,
                            details=website_alert
                        ))
                        
                        if alert_level in [AlertLevel.CRITICAL, AlertLevel.HIGH]:
                            self.logger.warning(f"重要網站變更: {website_alert.get('message')}")
                            
                except (HttpError, KeyError, Exception) as e:
                    # 無法獲取警報資訊，但不影響基本服務狀態
                    self.logger.warning(f"未能獲取網站爬蟲警報: {str(e)}")
                
            else:
                # 服務響應但狀態不是成功
                status = ServiceStatus.DEGRADED
                message = f"網站爬蟲服務回應異常: {response.get('message', '無錯誤訊息')}"
                alerts.append(Alert(
                    monitor_name=self.name,
                    title="網站爬蟲服務異常",
                    message=f"服務回應異常狀態: {response.get('status')}，訊息: {response.get('message', '無錯誤訊息')}",
                    level=AlertLevel.HIGH,
                    details=response
                ))
        
        except HttpError as e:
            # API響應錯誤
            status = ServiceStatus.DEGRADED
            message = f"服務 API 回應錯誤: {e.status_code} - {e.message}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="網站爬蟲服務 API 錯誤",
                message=f"爬蟲服務回應錯誤: {e.status_code} - {e.message}",
                level=AlertLevel.HIGH,
                details={"status_code": e.status_code, "error": e.message}
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