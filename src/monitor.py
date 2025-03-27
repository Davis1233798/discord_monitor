import os

class Monitor:
    def __init__(self):
        # 初始化Telegram監控器
        self.telegram_monitor = TelegramMonitor(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            chat_id=os.getenv("TELEGRAM_CHAT_ID")
        ) 