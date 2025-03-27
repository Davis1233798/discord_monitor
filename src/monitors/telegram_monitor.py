import aiohttp
from log import logger

class TelegramMonitor:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def check_health(self) -> bool:
        """檢查Telegram服務健康狀態"""
        try:
            # 發送測試訊息到指定頻道
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": "🔍 Telegram服務健康檢查",
                "parse_mode": "HTML"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("ok", False)
                    return False
        except Exception as e:
            logger.error(f"Telegram服務檢查失敗: {str(e)}")
            return False 