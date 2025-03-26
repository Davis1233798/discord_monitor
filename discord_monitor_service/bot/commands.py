"""
Discord機器人指令 - 處理Discord機器人的指令
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, Any, List, Optional
import traceback
from datetime import datetime, timedelta
import time

from ..utils.logging import get_logger
from ..monitors.base_monitor import ServiceStatus, AlertLevel, Alert
from ..config import config

logger = get_logger(__name__)

def setup_commands(bot):
    """
    設置Discord機器人指令
    
    Args:
        bot: Discord機器人實例
    """
    # 添加指令組
    bot.add_cog(MonitorCommands(bot))
    bot.add_cog(AdminCommands(bot))
    
    logger.info("Discord機器人指令已設置")

class MonitorCommands(commands.Cog):
    """監控相關指令"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="status", help="顯示所有服務的當前狀態")
    async def status(self, ctx):
        """顯示所有服務的當前狀態"""
        embed = discord.Embed(
            title="📊 服務狀態",
            description="當前所有監控服務的狀態",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for monitor_type, monitor in self.bot._monitors.items():
            status = monitor.status
            status_emoji = "🟢" if status == ServiceStatus.ONLINE else "🟠" if status == ServiceStatus.DEGRADED else "🔴" if status == ServiceStatus.OFFLINE else "⚪"
            
            embed.add_field(
                name=f"{status_emoji} {monitor.name}",
                value=f"狀態: {status}\n訊息: {monitor.status_message}\n上次檢查: <t:{int(monitor.last_check_time)}:R>",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="alerts", help="顯示最近的警報")
    async def alerts(self, ctx, count: int = 5):
        """
        顯示最近的警報
        
        Args:
            count: 要顯示的警報數量，默認5個
        """
        if count < 1:
            count = 1
        elif count > 20:
            count = 20
        
        all_alerts = []
        
        for monitor_type, monitor in self.bot._monitors.items():
            all_alerts.extend(monitor.get_recent_alerts(count=count*2))  # 獲取更多以便排序
        
        # 按時間排序並截取指定數量
        all_alerts = sorted(all_alerts, key=lambda x: x.timestamp, reverse=True)[:count]
        
        if not all_alerts:
            await ctx.send("目前沒有任何警報")
            return
        
        embed = discord.Embed(
            title="🚨 最近警報",
            description=f"顯示最近 {len(all_alerts)} 個警報",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        for alert in all_alerts:
            # 獲取適當的前綴
            prefix = "🔴" if alert.level == AlertLevel.CRITICAL else "🟠" if alert.level == AlertLevel.HIGH else "🟡" if alert.level == AlertLevel.MEDIUM else "🔵" if alert.level == AlertLevel.LOW else "🟢"
            
            # 格式化時間
            alert_time = datetime.fromtimestamp(alert.timestamp)
            time_str = f"<t:{int(alert.timestamp)}:R>"
            
            embed.add_field(
                name=f"{prefix} {alert.title} ({alert.monitor_name})",
                value=f"{alert.message}\n時間: {time_str}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="service", help="顯示特定服務的詳細信息")
    async def service(self, ctx, service_name: str):
        """
        顯示特定服務的詳細信息
        
        Args:
            service_name: 服務名稱
        """
        monitor = None
        
        # 嘗試查找匹配的監控器
        for monitor_type, mon in self.bot._monitors.items():
            if service_name.lower() in monitor_type.lower() or service_name.lower() in mon.name.lower():
                monitor = mon
                break
        
        if not monitor:
            await ctx.send(f"找不到服務 `{service_name}`。請使用 `!status` 查看所有可用服務。")
            return
        
        # 創建服務信息嵌入
        status = monitor.status
        status_emoji = "🟢" if status == ServiceStatus.ONLINE else "🟠" if status == ServiceStatus.DEGRADED else "🔴" if status == ServiceStatus.OFFLINE else "⚪"
        
        embed = discord.Embed(
            title=f"{status_emoji} {monitor.name} 詳細信息",
            description=f"服務URL: {monitor.service_url}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="狀態", value=status, inline=True)
        embed.add_field(name="訊息", value=monitor.status_message, inline=True)
        embed.add_field(name="上次檢查", value=f"<t:{int(monitor.last_check_time)}:R>", inline=True)
        embed.add_field(name="檢查間隔", value=f"{monitor.check_interval}秒", inline=True)
        
        # 添加最近的警報
        recent_alerts = monitor.get_recent_alerts(count=3)
        if recent_alerts:
            alert_text = ""
            for alert in recent_alerts:
                prefix = "🔴" if alert.level == AlertLevel.CRITICAL else "🟠" if alert.level == AlertLevel.HIGH else "🟡" if alert.level == AlertLevel.MEDIUM else "🔵" if alert.level == AlertLevel.LOW else "🟢"
                alert_text += f"{prefix} **{alert.title}**: {alert.message} (<t:{int(alert.timestamp)}:R>)\n"
            
            embed.add_field(name="最近警報", value=alert_text or "無最近警報", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="help", help="顯示可用指令列表")
    async def help_command(self, ctx):
        """顯示可用指令列表"""
        embed = discord.Embed(
            title="📋 可用指令",
            description="以下是所有可用的監控指令",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="!status", value="顯示所有服務的當前狀態", inline=False)
        embed.add_field(name="!alerts [數量]", value="顯示最近的警報，可指定數量（默認5個）", inline=False)
        embed.add_field(name="!service <服務名稱>", value="顯示特定服務的詳細信息", inline=False)
        
        # 僅對管理員顯示管理指令
        if ctx.author.guild_permissions.administrator:
            embed.add_field(name="管理員指令", value="以下指令僅限管理員使用", inline=False)
            embed.add_field(name="!refresh", value="強制刷新所有服務的狀態", inline=False)
            embed.add_field(name="!interval <服務名稱> <間隔秒數>", value="修改服務的檢查間隔", inline=False)
        
        await ctx.send(embed=embed)

class AdminCommands(commands.Cog):
    """管理員專用指令"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="refresh", help="強制刷新所有服務的狀態")
    @commands.has_permissions(administrator=True)
    async def refresh(self, ctx):
        """強制刷新所有服務的狀態（僅限管理員）"""
        await ctx.send("正在刷新所有服務狀態...")
        
        try:
            # 強制更新儀表板
            await self.bot._update_dashboard()
            await ctx.send("✅ 服務狀態已更新")
        except Exception as e:
            logger.error(f"強制刷新時發生錯誤: {str(e)}")
            await ctx.send(f"❌ 刷新時發生錯誤: {str(e)}")
    
    @commands.command(name="interval", help="修改服務的檢查間隔")
    @commands.has_permissions(administrator=True)
    async def set_interval(self, ctx, service_name: str, interval: int):
        """
        修改服務的檢查間隔（僅限管理員）
        
        Args:
            service_name: 服務名稱
            interval: 新的檢查間隔（秒）
        """
        if interval < 10:
            await ctx.send("⚠️ 檢查間隔不能小於10秒")
            return
        
        monitor = None
        
        # 嘗試查找匹配的監控器
        for monitor_type, mon in self.bot._monitors.items():
            if service_name.lower() in monitor_type.lower() or service_name.lower() in mon.name.lower():
                monitor = mon
                break
        
        if not monitor:
            await ctx.send(f"找不到服務 `{service_name}`。請使用 `!status` 查看所有可用服務。")
            return
        
        # 更新檢查間隔
        old_interval = monitor.check_interval
        monitor.check_interval = interval
        
        await ctx.send(f"✅ 已將 {monitor.name} 的檢查間隔從 {old_interval} 秒更改為 {interval} 秒")
    
    @commands.command(name="test", help="發送測試警報")
    @commands.has_permissions(administrator=True)
    async def test_alert(self, ctx, service_name: str, level: str = "info"):
        """
        發送測試警報（僅限管理員）
        
        Args:
            service_name: 服務名稱
            level: 警報等級（info, low, medium, high, critical）
        """
        monitor = None
        
        # 嘗試查找匹配的監控器
        for monitor_type, mon in self.bot._monitors.items():
            if service_name.lower() in monitor_type.lower() or service_name.lower() in mon.name.lower():
                monitor = mon
                break
        
        if not monitor:
            await ctx.send(f"找不到服務 `{service_name}`。請使用 `!status` 查看所有可用服務。")
            return
        
        # 轉換警報等級
        level_map = {
            "info": AlertLevel.INFO,
            "low": AlertLevel.LOW,
            "medium": AlertLevel.MEDIUM,
            "high": AlertLevel.HIGH,
            "critical": AlertLevel.CRITICAL
        }
        
        alert_level = level_map.get(level.lower(), AlertLevel.INFO)
        
        # 創建測試警報
        test_alert = Alert(
            monitor_name=monitor.name,
            title="測試警報",
            message=f"這是一個測試警報，由管理員 {ctx.author.name} 發送",
            level=alert_level,
            details={
                "測試用戶": str(ctx.author),
                "頻道": str(ctx.channel),
                "時間": datetime.now().isoformat()
            }
        )
        
        # 添加到監控器的警報列表
        monitor.alerts.append(test_alert)
        
        # 創建並發送警報嵌入
        embed = self.bot._create_alert_embed(test_alert)
        await ctx.send("測試警報已創建:", embed=embed)
    
    @refresh.error
    @set_interval.error
    @test_alert.error
    async def admin_command_error(self, ctx, error):
        """管理員指令錯誤處理"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("⛔ 你沒有執行此指令的權限，需要管理員權限")
        else:
            logger.error(f"執行管理員指令時發生錯誤: {str(error)}")
            await ctx.send(f"❌ 指令執行時發生錯誤: {str(error)}")
            traceback.print_exc() 