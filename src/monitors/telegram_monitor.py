import aiohttp
from log import logger

class TelegramMonitor:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def check_health(self) -> bool:
        """檢查Telegram服務健康狀態"""
        try:
            # 使用getMe方法檢查bot是否有效
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("ok", False)
                    return False
        except Exception as e:
            logger.error(f"Telegram服務檢查失敗: {str(e)}")
            return False 