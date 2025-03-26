# Discord 監控服務

這是一個用於監控多種服務的Discord機器人應用程式，整合了區塊鏈監控、網站爬蟲和n8n服務的狀態監控功能。

## 功能特點

- 針對每個服務提供獨立的Discord訊息頻道
- 統一的監控儀表板界面
- 即時警報和通知系統
- 支援的服務：
  - 區塊鏈監控服務
  - 網站爬蟲監控服務
  - n8n工作流自動化服務

## 安裝步驟

### 前置需求

- Python 3.8 或更高版本
- pip (Python 套件管理器)
- Discord 開發者帳戶和機器人權杖

### 安裝流程

1. 複製此儲存庫:
```bash
git clone https://github.com/yourusername/discord_monitor_service.git
cd discord_monitor_service
```

2. 創建並啟用虛擬環境:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/MacOS
source venv/bin/activate
```

3. 安裝相依套件:
```bash
pip install -r requirements.txt
```

4. 複製 `.env.example` 檔案並重命名為 `.env`:
```bash
cp .env.example .env
```

5. 編輯 `.env` 檔案並填入必要的設定值:
   - Discord 機器人權杖
   - 頻道 ID
   - 各項服務的 API 金鑰和端點

## 使用方法

啟動監控服務:
```bash
python -m discord_monitor_service
```

或使用 Docker 方式部署:
```bash
docker-compose up -d
```

## 監控面板

監控面板提供以下功能:
- 各服務即時狀態監控
- 警報歷史記錄
- 系統健康狀態
- 操作統計

## 配置選項

在 `config.py` 中可以自定義以下設定:
- 輪詢頻率
- 警報閾值
- 通知策略
- 記錄層級

## 貢獻指南

歡迎提交問題和功能請求。如需貢獻程式碼，請遵循以下步驟:
1. Fork 此儲存庫
2. 創建功能分支
3. 提交更改
4. 推送到分支
5. 創建合併請求

## 授權

本專案採用 MIT 授權 - 詳情請見 [LICENSE](LICENSE) 檔案 