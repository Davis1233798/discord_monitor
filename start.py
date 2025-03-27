#!/usr/bin/env python3
"""
Discord 監控服務啟動腳本
"""
from discord_monitor_service.main import run

if __name__ == "__main__":
    import sys
    sys.exit(run())