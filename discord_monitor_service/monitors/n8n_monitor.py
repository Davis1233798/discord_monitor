"""
n8n監控模組 - 監控n8n自動化工作流服務
"""

import time
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta

from ..utils.http import async_get, HttpError
from ..utils.logging import get_logger
from .base_monitor import BaseMonitor, Alert, AlertLevel, ServiceStatus

logger = get_logger(__name__)

class N8nMonitor(BaseMonitor):
    """
    n8n監控器，負責監控n8n自動化工作流服務
    """
    
    def __init__(self, name: str, service_url: str, check_interval: int = 60, api_key: Optional[str] = None):
        """
        初始化n8n監控器
        
        Args:
            name: 監控器名稱
            service_url: 服務URL
            check_interval: 檢查間隔（秒）
            api_key: API金鑰（如果需要）
        """
        super().__init__(name, service_url, check_interval)
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.last_check_data = {}
        self.failed_workflows = set()
    
    async def check_service(self) -> Tuple[str, str, List[Alert]]:
        """
        檢查n8n服務狀態
        
        Returns:
            (狀態, 狀態訊息, 警報列表)
        """
        alerts = []
        
        try:
            # 嘗試訪問n8n首頁
            response = await async_get(self.service_url, headers=self.headers)
            
            # n8n服務基本運行檢查
            # 由於n8n可能沒有專門的API端點來檢查狀態，我們假設能夠訪問首頁就表示服務在運行
            status_text = response.get("text", "")
            
            if "n8n" in status_text.lower() or response.get("success") == True:
                status = ServiceStatus.ONLINE
                message = "n8n服務正常運行"
                
                # 如果n8n提供了API端點用於檢查工作流狀態，可以使用以下代碼
                try:
                    # 獲取工作流執行狀態
                    # 注意：這需要適當配置n8n以公開此API，或使用適當的認證
                    workflows_response = await async_get(f"{self.service_url}/rest/workflows", headers=self.headers)
                    
                    workflows = workflows_response.get("data", [])
                    active_workflows = 0
                    inactive_workflows = 0
                    failed_executions = 0
                    
                    for workflow in workflows:
                        if workflow.get("active", False):
                            active_workflows += 1
                        else:
                            inactive_workflows += 1
                    
                    # 檢查最近的工作流執行情況
                    executions_response = await async_get(f"{self.service_url}/rest/executions?limit=50", headers=self.headers)
                    executions = executions_response.get("data", [])
                    
                    current_failed_workflows = set()
                    for execution in executions:
                        status = execution.get("status")
                        workflow_id = execution.get("workflowId")
                        workflow_name = execution.get("workflowName", f"工作流 {workflow_id}")
                        
                        if status == "failed":
                            failed_executions += 1
                            current_failed_workflows.add(workflow_id)
                            
                            # 檢查這是否是新失敗的工作流
                            if workflow_id not in self.failed_workflows:
                                self.failed_workflows.add(workflow_id)
                                alerts.append(Alert(
                                    monitor_name=self.name,
                                    title=f"工作流執行失敗: {workflow_name}",
                                    message=f"n8n工作流 '{workflow_name}' 執行失敗",
                                    level=AlertLevel.HIGH,
                                    details={
                                        "workflow_id": workflow_id,
                                        "workflow_name": workflow_name,
                                        "execution_id": execution.get("id"),
                                        "timestamp": execution.get("startedAt")
                                    }
                                ))
                    
                    # 清除已恢復的工作流
                    recovered_workflows = self.failed_workflows - current_failed_workflows
                    for workflow_id in recovered_workflows:
                        self.failed_workflows.remove(workflow_id)
                    
                    # 更新服務狀態訊息
                    if active_workflows > 0:
                        message = f"n8n服務正常運行，{active_workflows} 個活躍工作流"
                        if failed_executions > 0:
                            status = ServiceStatus.DEGRADED
                            message += f"，{failed_executions} 個執行失敗"
                    else:
                        status = ServiceStatus.DEGRADED
                        message = "n8n服務運行但無活躍工作流"
                        alerts.append(Alert(
                            monitor_name=self.name,
                            title="無活躍工作流",
                            message="n8n服務中沒有活躍的工作流",
                            level=AlertLevel.MEDIUM
                        ))
                
                except (HttpError, KeyError, Exception) as e:
                    # 無法獲取工作流狀態，但基本服務仍在運行
                    self.logger.warning(f"未能獲取n8n工作流狀態: {str(e)}")
                    message = "n8n服務運行中，但無法檢查工作流狀態"
            else:
                # 服務響應但內容不符合預期
                status = ServiceStatus.DEGRADED
                message = "n8n服務回應異常內容"
                alerts.append(Alert(
                    monitor_name=self.name,
                    title="n8n服務回應異常",
                    message="n8n服務回應但內容不符合預期",
                    level=AlertLevel.HIGH,
                    details={"response": status_text[:200] if isinstance(status_text, str) else str(response)[:200]}
                ))
        
        except HttpError as e:
            # API響應錯誤
            status = ServiceStatus.DEGRADED
            message = f"n8n服務 API 回應錯誤: {e.status_code} - {e.message}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="n8n服務 API 錯誤",
                message=f"n8n服務回應錯誤: {e.status_code} - {e.message}",
                level=AlertLevel.HIGH,
                details={"status_code": e.status_code, "error": e.message}
            ))
        except Exception as e:
            # 其他錯誤
            status = ServiceStatus.DEGRADED
            message = f"檢查n8n服務時發生未預期錯誤: {str(e)}"
            alerts.append(Alert(
                monitor_name=self.name,
                title="n8n服務檢查錯誤",
                message=f"檢查n8n服務時發生錯誤: {str(e)}",
                level=AlertLevel.HIGH,
                details={"error": str(e)}
            ))
        
        return status, message, alerts 