"""
Discord監控服務主程式 - 程式入口點
"""

import asyncio
import os
from pathlib import Path
import signal
import sys
import logging
from aiohttp import web

from .config import config, ConfigurationError
from .utils.logging import get_logger
from .bot.client import MonitorBot
from .bot.commands import setup_commands
from .monitors.blockchain_monitor import BlockchainMonitor
from .monitors.web_monitor import WebCrawlerMonitor
from .monitors.n8n_monitor import N8nMonitor
from .monitors.telegram_monitor import TelegramMonitor

logger = get_logger(__name__)

# HTTP服務器處理函數
async def handle_request(request):
    """處理HTTP請求，返回服務狀態"""
    return web.Response(text="Discord Monitor Service is running")

# 啟動HTTP服務器
async def run_http_server():
    """啟動HTTP服務器，綁定到環境變數指定的端口"""
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.add_routes([web.get('/', handle_request)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"HTTP服務器已啟動在端口 {port}")

async def main():
    """
    主函數，初始化並啟動監控服務
    """
    try:
        # 顯示版本信息
        from . import __version__
        logger.info(f"Discord監控服務 v{__version__} 正在啟動...")
        
        # 啟動HTTP服務器
        await run_http_server()
        
        # 創建Discord機器人
        bot = MonitorBot()
        
        # 設置指令
        setup_commands(bot)
        
        # 創建監控器
        monitors = {
            "blockchain": BlockchainMonitor(
                name="區塊鏈監控服務",
                service_url=config.get("services.blockchain.url"),
                check_interval=config.get("monitoring.polling_interval", 60),
                api_key=config.get("services.blockchain.api_key")
            ),
            "webcrawler": WebCrawlerMonitor(
                name="網站爬蟲監控服務",
                service_url=config.get("services.webcrawler.url"),
                check_interval=config.get("monitoring.polling_interval", 60),
                api_key=config.get("services.webcrawler.api_key")
            ),
            "n8n": N8nMonitor(
                name="n8n工作流服務",
                service_url=config.get("services.n8n.url"),
                check_interval=config.get("monitoring.polling_interval", 60)
            ),
            "telegram": TelegramMonitor(
                name="Telegram通知服務",
                bot_token=config.get("services.telegram.bot_token"),
                chat_id=config.get("services.telegram.chat_id")
            )
        }
        
        # 註冊監控器到機器人
        for monitor_type, monitor in monitors.items():
            bot.register_monitor(monitor_type, monitor)
        
        # 啟動監控任務
        monitor_tasks = []
        for monitor in monitors.values():
            monitor_tasks.append(asyncio.create_task(monitor.monitor_service()))
        
        # 啟動機器人（這會阻塞，直到機器人停止）
        # 我們需要在新線程中運行機器人，所以它不會阻塞主線程
        import threading
        bot_thread = threading.Thread(target=bot.run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        # 等待監控任務
        await asyncio.gather(*monitor_tasks)
        
    except ConfigurationError as e:
        logger.critical(f"配置錯誤: {str(e)}")
        return 1
    except Exception as e:
        logger.critical(f"啟動服務時發生未預期錯誤: {str(e)}", exc_info=True)
        return 1
    
    return 0

def run():
    """
    運行Discord監控服務
    """
    # 設置事件循環
    try:
        # Windows上需要使用特定的事件循環政策
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
        # 獲取或創建事件循環
        loop = asyncio.get_event_loop()
        
        # 設置信號處理（僅適用於非Windows平台）
        if sys.platform != 'win32':
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(loop)))
        
        # 運行主函數
        exit_code = loop.run_until_complete(main())
        
        # 關閉事件循環
        loop.close()
        
        # 返回退出碼
        return exit_code
    
    except KeyboardInterrupt:
        logger.info("收到鍵盤中斷，正在關閉...")
        return 0
    except Exception as e:
        logger.critical(f"運行服務時發生未處理的錯誤: {str(e)}", exc_info=True)
        return 1

async def shutdown(loop):
    """
    優雅地關閉服務
    
    Args:
        loop: 事件循環
    """
    logger.info("正在關閉服務...")
    
    # 取消所有任務
    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    # 等待所有任務完成或取消
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # 停止事件循環
    loop.stop()

if __name__ == "__main__":
    sys.exit(run()) 