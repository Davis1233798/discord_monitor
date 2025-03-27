"""
HTTP工具 - 提供HTTP請求的工具函數
"""

import aiohttp
import asyncio
import requests
from typing import Dict, Any, Optional, Union, Tuple
import json
from ..utils.logging import get_logger

logger = get_logger(__name__)

class HttpError(Exception):
    """HTTP請求錯誤"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP錯誤 {status_code}: {message}")

async def async_get(url: str, headers: Optional[Dict[str, str]] = None, 
                   timeout: int = 10, retries: int = 3,
                   retry_delay: int = 1,
                   expect_json: bool = False) -> Dict[str, Any]:
    """
    執行異步GET請求
    
    Args:
        url: 目標URL
        headers: 請求標頭
        timeout: 請求超時（秒）
        retries: 重試次數
        retry_delay: 重試間隔（秒）
        expect_json: 是否期望JSON響應
    
    Returns:
        回應數據
    
    Raises:
        HttpError: 當HTTP請求失敗時
    """
    headers = headers or {}
    attempt = 0
    
    while attempt < retries:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        if expect_json:
                            try:
                                return await response.json()
                            except json.JSONDecodeError:
                                text = await response.text()
                                return {"success": True, "text": text, "content_type": response.content_type}
                        else:
                            text = await response.text()
                            return {"success": True, "text": text, "content_type": response.content_type}
                    else:
                        error_text = await response.text()
                        logger.error(f"HTTP GET 請求失敗: {url}, 狀態碼: {response.status}, 內容: {error_text}")
                        raise HttpError(response.status, error_text)
        except asyncio.TimeoutError:
            logger.warning(f"請求超時: {url}, 嘗試次數 {attempt+1}/{retries}")
        except aiohttp.ClientError as e:
            logger.warning(f"請求錯誤: {url}, 錯誤: {str(e)}, 嘗試次數 {attempt+1}/{retries}")
        except Exception as e:
            logger.error(f"未預期錯誤: {url}, 錯誤: {str(e)}")
            raise
        
        attempt += 1
        if attempt < retries:
            await asyncio.sleep(retry_delay)
    
    logger.error(f"請求重試次數已耗盡: {url}")
    raise HttpError(0, f"請求重試次數已耗盡 (嘗試 {retries} 次)")

async def async_post(url: str, data: Optional[Dict[str, Any]] = None, 
                    json_data: Optional[Dict[str, Any]] = None,
                    headers: Optional[Dict[str, str]] = None,
                    timeout: int = 10, retries: int = 3,
                    retry_delay: int = 1,
                    expect_json: bool = False) -> Dict[str, Any]:
    """
    執行異步POST請求
    
    Args:
        url: 目標URL
        data: 表單數據
        json_data: JSON數據
        headers: 請求標頭
        timeout: 請求超時（秒）
        retries: 重試次數
        retry_delay: 重試間隔（秒）
        expect_json: 是否期望JSON響應
    
    Returns:
        回應數據
    
    Raises:
        HttpError: 當HTTP請求失敗時
    """
    headers = headers or {}
    attempt = 0
    
    while attempt < retries:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, json=json_data, 
                                       headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        if expect_json:
                            try:
                                return await response.json()
                            except json.JSONDecodeError:
                                text = await response.text()
                                return {"success": True, "text": text, "content_type": response.content_type}
                        else:
                            text = await response.text()
                            return {"success": True, "text": text, "content_type": response.content_type}
                    else:
                        error_text = await response.text()
                        logger.error(f"HTTP POST 請求失敗: {url}, 狀態碼: {response.status}, 內容: {error_text}")
                        raise HttpError(response.status, error_text)
        except asyncio.TimeoutError:
            logger.warning(f"請求超時: {url}, 嘗試次數 {attempt+1}/{retries}")
        except aiohttp.ClientError as e:
            logger.warning(f"請求錯誤: {url}, 錯誤: {str(e)}, 嘗試次數 {attempt+1}/{retries}")
        except Exception as e:
            logger.error(f"未預期錯誤: {url}, 錯誤: {str(e)}")
            raise
        
        attempt += 1
        if attempt < retries:
            await asyncio.sleep(retry_delay)
    
    logger.error(f"請求重試次數已耗盡: {url}")
    raise HttpError(0, f"請求重試次數已耗盡 (嘗試 {retries} 次)")

def sync_get(url: str, headers: Optional[Dict[str, str]] = None,
            timeout: int = 10, retries: int = 3,
            retry_delay: int = 1,
            expect_json: bool = False) -> Dict[str, Any]:
    """
    執行同步GET請求
    
    Args:
        url: 目標URL
        headers: 請求標頭
        timeout: 請求超時（秒）
        retries: 重試次數
        retry_delay: 重試間隔（秒）
        expect_json: 是否期望JSON響應
    
    Returns:
        回應數據
    
    Raises:
        HttpError: 當HTTP請求失敗時
    """
    headers = headers or {}
    attempt = 0
    
    while attempt < retries:
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                if expect_json:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        return {"success": True, "text": response.text, "content_type": response.headers.get("Content-Type")}
                else:
                    return {"success": True, "text": response.text, "content_type": response.headers.get("Content-Type")}
            else:
                logger.error(f"HTTP GET 請求失敗: {url}, 狀態碼: {response.status_code}, 內容: {response.text}")
                raise HttpError(response.status_code, response.text)
        except requests.Timeout:
            logger.warning(f"請求超時: {url}, 嘗試次數 {attempt+1}/{retries}")
        except requests.RequestException as e:
            logger.warning(f"請求錯誤: {url}, 錯誤: {str(e)}, 嘗試次數 {attempt+1}/{retries}")
        except Exception as e:
            logger.error(f"未預期錯誤: {url}, 錯誤: {str(e)}")
            raise
        
        attempt += 1
        if attempt < retries:
            import time
            time.sleep(retry_delay)
    
    logger.error(f"請求重試次數已耗盡: {url}")
    raise HttpError(0, f"請求重試次數已耗盡 (嘗試 {retries} 次)")

def is_service_online(url: str, timeout: int = 5) -> Tuple[bool, str]:
    """
    檢查服務是否在線
    
    Args:
        url: 服務URL
        timeout: 請求超時（秒）
    
    Returns:
        (是否在線, 訊息)
    """
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return True, "服務正常運行"
        else:
            return False, f"服務回應異常 (狀態碼: {response.status_code})"
    except requests.Timeout:
        return False, "服務請求超時"
    except requests.ConnectionError:
        return False, "無法連接到服務"
    except Exception as e:
        return False, f"檢查服務時出錯: {str(e)}" 