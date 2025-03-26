"""
Discord監控服務包入口點
"""

from discord_monitor_service.main import run

if __name__ == "__main__":
    import sys
    sys.exit(run()) 