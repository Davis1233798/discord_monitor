# Discord 監控服務

這是一個用於監控多種服務的Discord機器人應用程式，整合了區塊鏈監控、網站爬蟲、n8n服務和Telegram通知服務的狀態監控功能。

## 功能特點

- 針對每個服務提供獨立的Discord訊息頻道
- 統一的監控儀表板界面
- 即時警報和通知系統
- 簡化通知策略：所有通知統一發送到Discord
- 支援的服務：
  - 區塊鏈監控服務
  - 網站爬蟲監控服務
  - n8n工作流自動化服務
  - Telegram通知服務

## 安裝步驟

### 前置需求

- Python 3.8 或更高版本
- pip (Python 套件管理器)
- Discord 開發者帳戶和機器人權杖
- 各監控服務的Webhook URL

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

5. 編輯 `.env` 檔案並填入必要的設定值

## 環境變數配置

### Discord機器人配置
- `DISCORD_BOT_TOKEN`: Discord機器人令牌
- `DISCORD_GUILD_ID`: Discord伺服器ID
- `DISCORD_GENERAL_CHANNEL_ID`: 一般頻道ID
- `DISCORD_BLOCKCHAIN_CHANNEL_ID`: 區塊鏈監控頻道ID
- `DISCORD_WEBCRAWLER_CHANNEL_ID`: 網站爬蟲監控頻道ID
- `DISCORD_N8N_CHANNEL_ID`: n8n監控頻道ID
- `DISCORD_TELEGRAM_CHANNEL_ID`: Telegram監控頻道ID
- `DISCORD_ALERTS_CHANNEL_ID`: 警報頻道ID

### 服務URL配置
- `BLOCKCHAIN_SERVICE_URL`: 區塊鏈監控服務URL
- `WEBCRAWLER_SERVICE_URL`: 網站爬蟲監控服務URL
- `N8N_SERVICE_URL`: n8n服務URL

### Webhook配置
- `BLOCKCHAIN_DISCORD_WEBHOOK_URL`: 區塊鏈服務專用Discord Webhook
- `WEBCRAWLER_DISCORD_WEBHOOK_URL`: 網站爬蟲服務專用Discord Webhook

### Telegram配置
- `TELEGRAM_BOT_TOKEN`: Telegram機器人令牌
- `TELEGRAM_CHAT_ID`: Telegram聊天ID

### 一般配置
- `POLLING_INTERVAL`: 服務輪詢間隔（秒）
- `ALERT_COOLDOWN`: 警報冷卻時間（秒）
- `LOG_LEVEL`: 日誌級別

## 部署方式

### 本地部署

啟動監控服務:
```bash
python -m discord_monitor_service
```

### Docker部署

使用Docker容器:
```bash
docker build -t discord-monitor-service .
docker run -p 10000:10000 --env-file .env discord-monitor-service
```

### Render雲端部署

1. 在Render.com建立新服務
2. 選擇Docker部署
3. 連接GitHub倉庫
4. 配置環境變數
5. 部署

## 各服務設置

### 區塊鏈監控服務

1. 在Render上部署`onchain_monitor`
2. 設置環境變數:
   - `MORALIS_API_KEY`
   - `BITQUERY_API_KEY`
   - `ETHERSCAN_API_KEY`
   - `DISCORD_WEBHOOK_URL`
   - `BLOCKCHAIN_DISCORD_WEBHOOK_URL`

### 網站爬蟲監控服務

1. 在Vercel上部署`monitor_flask`
2. 設置環境變數:
   - `DISCORD_WEBHOOK_URL`
   - `WEBCRAWLER_DISCORD_WEBHOOK_URL`

### 創建Discord Webhook

1. Discord伺服器設定 → 整合 → Webhook
2. 為每個服務建立專用Webhook
3. 複製Webhook URL並設置到相應服務的環境變數中

## 使用方法

### 監控儀表板

監控儀表板會自動顯示在`DISCORD_GENERAL_CHANNEL_ID`指定的頻道中，包含以下信息:
- 各服務即時狀態
- 上次檢查時間
- 運行時間

### Discord命令

- `/status`：顯示各服務當前狀態
- `/monitor <service_name>`：手動觸發指定服務的監控
- `/test <service_name>`：測試指定服務的連接
- `/alert`：顯示最近的警報
- `/help`：顯示可用命令

## 注意事項

- 所有通知均整合到Discord，不再使用Telegram發送通知
- 各監控服務需要單獨部署，然後通過Discord整合
- 專用的Discord Webhook使每個服務能發送訊息到指定頻道
- 主服務會監控Telegram API的狀態，但不再透過Telegram發送通知

## 故障排除

- 確保所有環境變數已正確設置
- 檢查Discord機器人有足夠的權限
- 使用`LOG_LEVEL=DEBUG`啟動服務以獲取詳細日誌
- 確保端口正確映射（Docker和Render部署）

## 貢獻指南

歡迎提交問題和功能請求。如需貢獻程式碼，請遵循以下步驟:
1. Fork 此儲存庫
2. 創建功能分支
3. 提交更改
4. 推送到分支
5. 創建合併請求

## 授權

本專案採用 MIT 授權 - 詳情請見 [LICENSE](LICENSE) 檔案 