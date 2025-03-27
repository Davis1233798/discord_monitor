import aiohttp
from log import logger

class TelegramMonitor:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        logger.info(f"初始化Telegram監控器 (bot_token長度: {len(bot_token) if bot_token else 0}, chat_id: {chat_id})")

    async def check_health(self) -> bool:
        """檢查Telegram服務健康狀態"""
        try:
            # 使用getMe方法檢查bot是否有效
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            logger.debug(f"正在檢查Telegram服務，URL: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    logger.debug(f"Telegram API回應狀態碼: {response.status}")
                    if response.status == 200:
                        result = await response.json()
                        success = result.get("ok", False)
                        logger.info(f"Telegram服務檢查結果: {'成功' if success else '失敗'}")
                        return success
                    logger.warning(f"Telegram服務回應異常狀態碼: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Telegram服務檢查失敗: {str(e)}")
            return False 