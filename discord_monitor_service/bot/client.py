"""
Discord機器人客戶端 - 處理Discord連接和訊息發送
"""

import discord
from discord.ext import commands, tasks
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
import time
from datetime import datetime
import traceback

from ..config import config
from ..utils.logging import get_logger
from ..monitors.base_monitor import Alert, AlertLevel, ServiceStatus

logger = get_logger(__name__)

# 定義顏色
STATUS_COLORS = {
    ServiceStatus.ONLINE: discord.Color.green(),
    ServiceStatus.DEGRADED: discord.Color.gold(),
    ServiceStatus.OFFLINE: discord.Color.red(),
    ServiceStatus.UNKNOWN: discord.Color.light_grey()
}

ALERT_COLORS = {
    AlertLevel.CRITICAL: discord.Color.dark_red(),
    AlertLevel.HIGH: discord.Color.red(),
    AlertLevel.MEDIUM: discord.Color.gold(),
    AlertLevel.LOW: discord.Color.blue(),
    AlertLevel.INFO: discord.Color.green()
}

class MonitorBot(commands.Bot):
    """Discord監控機器人，用於顯示監控資訊和發送警報"""
    
    def __init__(self):
        """初始化Discord機器人"""
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix="!", intents=intents)
        
        # 頻道快取
        self._channels: Dict[str, discord.TextChannel] = {}
        
        # 儀表板訊息ID
        self._dashboard_message_id = None
        
        # 最後更新時間
        self._last_status_update = 0
        
        # 已發送的警報ID集合（防止重複發送）
        self._sent_alerts = set()
        
        # 監控器註冊表
        self._monitors = {}
        
        # 是否已初始化
        self._initialized = False
    
    async def setup_hook(self):
        """設置鉤子，在機器人準備好時調用"""
        self.status_task.start()
        logger.info("機器人狀態更新任務已啟動")
    
    async def on_ready(self):
        """當機器人已連接並準備好時調用"""
        logger.info(f"機器人已連接為 {self.user.name} (ID: {self.user.id})")
        
        try:
            await self._initialize()
        except Exception as e:
            logger.error(f"初始化機器人時發生錯誤: {str(e)}")
            traceback.print_exc()
    
    async def _initialize(self):
        """初始化機器人，獲取頻道並發送初始儀表板"""
        if self._initialized:
            return
        
        # 獲取所有需要的頻道
        await self._fetch_channels()
        
        # 發送初始儀表板
        general_channel = self._channels.get("general")
        if general_channel:
            try:
                dashboard_embed = discord.Embed(
                    title="📊 系統監控儀表板",
                    description="正在初始化監控服務...",
                    color=discord.Color.blue()
                )
                dashboard_embed.set_footer(text=f"上次更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                dashboard_message = await general_channel.send(embed=dashboard_embed)
                self._dashboard_message_id = dashboard_message.id
                logger.info(f"初始儀表板已發送，訊息ID: {self._dashboard_message_id}")
            except Exception as e:
                logger.error(f"發送初始儀表板時發生錯誤: {str(e)}")
        
        self._initialized = True
    
    async def _fetch_channels(self):
        """獲取所有配置的頻道"""
        try:
            guild_id = config.get("discord.guild_id")
            if not guild_id:
                logger.error("無法獲取頻道: 未設定guild_id")
                return
            
            guild = self.get_guild(int(guild_id))
            if not guild:
                logger.error(f"無法找到伺服器: {guild_id}")
                return
            
            # 獲取頻道ID
            channel_ids = {
                "general": config.get("discord.channels.general"),
                "blockchain": config.get("discord.channels.blockchain"),
                "webcrawler": config.get("discord.channels.webcrawler"),
                "n8n": config.get("discord.channels.n8n"),
                "alerts": config.get("discord.channels.alerts")
            }
            
            # 獲取頻道對象
            for name, channel_id in channel_ids.items():
                if channel_id:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        self._channels[name] = channel
                        logger.info(f"已獲取頻道: {name} ({channel.name})")
                    else:
                        logger.warning(f"無法找到頻道: {name} (ID: {channel_id})")
                else:
                    logger.warning(f"未設定頻道ID: {name}")
        
        except Exception as e:
            logger.error(f"獲取頻道時發生錯誤: {str(e)}")
    
    def register_monitor(self, monitor_type: str, monitor):
        """
        註冊監控器
        
        Args:
            monitor_type: 監控器類型（例如 "blockchain"）
            monitor: 監控器實例
        """
        self._monitors[monitor_type] = monitor
        logger.info(f"已註冊監控器: {monitor_type} ({monitor.name})")
    
    @tasks.loop(seconds=30)
    async def status_task(self):
        """定期更新狀態的背景任務"""
        if not self._initialized:
            return
        
        try:
            # 更新儀表板
            await self._update_dashboard()
            
            # 檢查並發送新警報
            await self._send_new_alerts()
            
        except Exception as e:
            logger.error(f"更新狀態時發生錯誤: {str(e)}")
            traceback.print_exc()
    
    async def _update_dashboard(self):
        """更新監控儀表板"""
        # 獲取總覽頻道
        general_channel = self._channels.get("general")
        if not general_channel or not self._dashboard_message_id:
            return
        
        try:
            # 獲取儀表板訊息
            dashboard_message = await general_channel.fetch_message(self._dashboard_message_id)
            
            # 創建儀表板嵌入
            dashboard_embed = discord.Embed(
                title="📊 系統監控儀表板",
                description="即時監控狀態總覽",
                color=discord.Color.blue()
            )
            
            # 添加各服務狀態
            for monitor_type, monitor in self._monitors.items():
                status = monitor.status
                status_emoji = "🟢" if status == ServiceStatus.ONLINE else "🟠" if status == ServiceStatus.DEGRADED else "🔴" if status == ServiceStatus.OFFLINE else "⚪"
                dashboard_embed.add_field(
                    name=f"{status_emoji} {monitor.name}",
                    value=f"狀態: {status}\n訊息: {monitor.status_message}\n上次檢查: <t:{int(monitor.last_check_time)}:R>",
                    inline=False
                )
            
            # 添加頁腳
            dashboard_embed.set_footer(text=f"上次更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 更新訊息
            await dashboard_message.edit(embed=dashboard_embed)
            self._last_status_update = time.time()
            logger.debug("儀表板已更新")
            
        except discord.NotFound:
            logger.warning(f"找不到儀表板訊息 (ID: {self._dashboard_message_id})，將創建新訊息")
            try:
                dashboard_embed = discord.Embed(
                    title="📊 系統監控儀表板",
                    description="正在初始化監控服務...",
                    color=discord.Color.blue()
                )
                dashboard_embed.set_footer(text=f"上次更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                dashboard_message = await general_channel.send(embed=dashboard_embed)
                self._dashboard_message_id = dashboard_message.id
            except Exception as e:
                logger.error(f"創建新儀表板訊息時發生錯誤: {str(e)}")
        
        except Exception as e:
            logger.error(f"更新儀表板時發生錯誤: {str(e)}")
    
    async def _send_new_alerts(self):
        """檢查並發送新警報"""
        for monitor_type, monitor in self._monitors.items():
            # 獲取頻道
            channel_name = monitor_type
            channel = self._channels.get(channel_name)
            alerts_channel = self._channels.get("alerts")
            
            if not (channel or alerts_channel):
                continue
            
            # 獲取最近的警報
            alerts = monitor.get_recent_alerts()
            
            for alert in alerts:
                # 創建唯一ID以防止重複發送
                alert_id = f"{alert.monitor_name}_{alert.title}_{alert.timestamp}"
                
                if alert_id not in self._sent_alerts:
                    self._sent_alerts.add(alert_id)
                    
                    # 創建警報嵌入
                    embed = self._create_alert_embed(alert)
                    
                    # 發送到特定服務頻道
                    if channel:
                        try:
                            await channel.send(embed=embed)
                        except Exception as e:
                            logger.error(f"發送警報到頻道 {channel.name} 時發生錯誤: {str(e)}")
                    
                    # 發送到總警報頻道（如果警報等級夠高）
                    if alerts_channel and alert.level in [AlertLevel.CRITICAL, AlertLevel.HIGH]:
                        try:
                            await alerts_channel.send(embed=embed)
                        except Exception as e:
                            logger.error(f"發送警報到警報頻道時發生錯誤: {str(e)}")
    
    def _create_alert_embed(self, alert: Alert) -> discord.Embed:
        """
        從警報創建Discord嵌入
        
        Args:
            alert: 警報對象
            
        Returns:
            格式化的Discord嵌入
        """
        # 獲取警報等級對應的顏色
        color = ALERT_COLORS.get(alert.level, discord.Color.default())
        
        # 創建標題前綴
        prefix = "🔴" if alert.level == AlertLevel.CRITICAL else "🟠" if alert.level == AlertLevel.HIGH else "🟡" if alert.level == AlertLevel.MEDIUM else "🔵" if alert.level == AlertLevel.LOW else "🟢"
        
        # 創建嵌入
        embed = discord.Embed(
            title=f"{prefix} {alert.title}",
            description=alert.message,
            color=color,
            timestamp=datetime.fromtimestamp(alert.timestamp)
        )
        
        # 添加警報詳情
        for key, value in alert.details.items():
            if value is not None:
                embed.add_field(name=key, value=str(value)[:1024], inline=True)
        
        # 添加監控器信息
        embed.set_footer(text=f"監控器: {alert.monitor_name} | 等級: {alert.level}")
        
        return embed
    
    async def send_message_to_channel(self, channel_name: str, message: str, embed: Optional[discord.Embed] = None):
        """
        發送訊息到指定頻道
        
        Args:
            channel_name: 頻道名稱（如"general", "blockchain"等）
            message: 要發送的訊息
            embed: 要發送的嵌入（可選）
        """
        channel = self._channels.get(channel_name)
        if not channel:
            logger.warning(f"無法發送訊息: 未找到頻道 {channel_name}")
            return
        
        try:
            await channel.send(content=message, embed=embed)
            logger.debug(f"已發送訊息到頻道 {channel_name}")
        except Exception as e:
            logger.error(f"發送訊息到頻道 {channel_name} 時發生錯誤: {str(e)}")
    
    @status_task.before_loop
    async def before_status_task(self):
        """在開始狀態任務前等待機器人準備就緒"""
        await self.wait_until_ready()
    
    def run_bot(self):
        """運行機器人"""
        try:
            token = config.get("discord.bot_token")
            if not token:
                logger.error("無法啟動機器人: 未設定bot_token")
                return
            
            super().run(token)
        except Exception as e:
            logger.error(f"啟動機器人時發生錯誤: {str(e)}")
            traceback.print_exc() 