# Discord監控服務 - 架構與設計文檔

## 服務目的

本服務旨在整合多個現有監控服務，透過Discord界面提供統一的監控介面和通知系統。這種集中式的監控方法可以大幅提高團隊對於不同系統異常狀況的響應速度，同時降低監控成本和技術人員的精力分散度。

## 核心問題與解決方案

### 問題
- 多個獨立監控服務管理困難
- 通知分散在不同平台
- 缺乏統一的服務狀態視圖
- 無法實現跨服務的相關性分析

### 解決方案
- 中央化的Discord監控界面
- 服務特定的頻道隔離與總覽儀表板結合
- 統一的警報管理和歷史記錄
- 標準化的通知格式和嚴重性分類

## 架構設計

### 系統組件
```
discord_monitor_service/
├── discord_monitor_service/          # 主模組
│   ├── __init__.py
│   ├── main.py                       # 程式入口點
│   ├── config.py                     # 配置管理
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── client.py                 # Discord機器人客戶端
│   │   ├── commands.py               # 機器人指令
│   │   └── formatting.py             # 訊息格式化
│   ├── core/
│   │   ├── __init__.py
│   │   ├── service_manager.py        # 服務管理器
│   │   ├── alerting.py               # 警報系統
│   │   └── dashboard.py              # 儀表板更新邏輯
│   ├── monitors/
│   │   ├── __init__.py
│   │   ├── base_monitor.py           # 監控器基類
│   │   ├── blockchain_monitor.py     # 區塊鏈監控
│   │   ├── web_monitor.py            # 網站爬蟲監控
│   │   ├── n8n_monitor.py            # n8n服務監控
│   │   └── telegram_monitor.py       # Telegram服務監控
│   └── utils/
│       ├── __init__.py
│       ├── logging.py                # 日誌工具
│       ├── http.py                   # HTTP請求工具
│       ├── parsing.py                # 資料解析工具
│       └── metrics.py                # 指標收集工具
├── tests/                            # 單元測試
├── .env.example                      # 環境變數範例
├── config.yaml                       # 配置檔案
├── LICENSE
├── README.md
├── requirements.txt
├── Dockerfile                        # Docker容器化配置
└── render.yaml                       # Render部署配置
```

## 設計原則

本服務遵循SOLID設計原則:

### 單一職責原則 (Single Responsibility Principle)
每個類和模組僅負責單一功能領域:
- `monitors` 負責不同服務的監控邏輯
- `bot` 處理Discord相關功能
- `core` 負責系統核心業務邏輯

### 開放封閉原則 (Open/Closed Principle)
系統設計為可擴展而不需修改現有代碼:
- `base_monitor.py` 定義抽象監控器接口
- 新服務可通過實現這個接口輕鬆添加

### 里氏替換原則 (Liskov Substitution Principle)
子類可以完全替代其父類:
- 所有監控器繼承自 `BaseMonitor` 並保持一致的行為模式
- 允許系統處理任何監控器，不需要知道具體實現

### 接口隔離原則 (Interface Segregation Principle)
接口被設計為小而專一:
- 監控器接口僅包含必要的監控方法
- Discord機器人接口專注於通訊

### 依賴反轉原則 (Dependency Inversion Principle)
高層模組不依賴低層模組，而是依賴抽象:
- `service_manager.py` 依賴監控器接口，而不是具體實現
- 使用依賴注入簡化測試和配置

## 技術實現細節

### 簡化版監控邏輯

為了提高穩定性和可靠性，我們對服務監控邏輯進行了簡化，主要目標是檢查服務是否可以連接並在線運行，而不是檢查詳細的服務狀態和特定功能。

#### 修改後的監控策略

1. **基礎連通性優先**:
   - 不再嘗試訪問可能不存在的子路徑（如 `/stats`、`/alerts` 等）
   - 只檢查主URL的連接狀態和基本響應
   - 避免對不同內容類型響應的過度解析

2. **靈活的響應處理**:
   - 同時支持JSON和非JSON（如HTML、純文本）響應
   - 添加 `expect_json` 參數，允許調用者指定是否期望JSON響應
   - 使用適當的錯誤處理來防止JSON解析失敗

3. **內容識別模式**:
   - 區塊鏈監控服務: 檢查回應中是否包含 "Monitor is running"
   - 網站爬蟲服務: 檢查JSON回應中的 "status" 字段是否為 "success"
   - n8n服務: 檢查響應內容中是否包含 "n8n" 關鍵字
   - Telegram服務: 檢查API響應中的 "ok" 字段是否為 true

4. **簡化警報生成**:
   - 只針對連接性和基本健康檢查生成警報
   - 減少警報數量，避免雜訊

#### HTTP工具改進

在 `utils/http.py` 中，我們進行了以下改進:

1. **返回格式統一**: 所有HTTP請求都返回包含以下字段的字典:
   - `success`: 表示請求是否成功
   - `text`: 原始回應內容
   - `content_type`: 回應內容類型

2. **異常處理**: 改進了錯誤處理邏輯，避免嘗試對非JSON回應進行JSON解析

3. **靈活配置**: 添加了更多參數來控制請求行為，例如 `expect_json`

### 服務監控模型
每個監控器負責:
1. 連接目標服務
2. 確定服務是否在線
3. 生成基本健康報告
4. 觸發相應警報

### 各監控服務的角色與關聯

#### 區塊鏈監控服務
- **主要功能**: 監控區塊鏈服務的可用性和基本運行狀態
- **資料通道**: 直接向Discord頻道發送通知，使用專用或通用的Discord Webhook
- **檢測邏輯**: 檢查服務是否可連接，並檢查回應中是否包含特定文本

#### 網站爬蟲監控服務
- **主要功能**: 監控網站爬蟲服務的運行狀態與數據收集情況
- **資料通道**: 直接向Discord頻道發送通知，使用專用或通用的Discord Webhook
- **檢測邏輯**: 確認服務響應，並可能檢查爬蟲任務的成功率

#### n8n工作流監控服務
- **主要功能**: 確保n8n自動化工作流平台的正常運作
- **資料通道**: 直接向Discord頻道發送通知，使用Discord Webhook
- **檢測邏輯**: 檢查服務主頁面是否可訪問並包含"n8n"關鍵字

#### Telegram監控服務
- **主要功能**: 監控Telegram通知服務的正常運作狀態
- **資料通道**: 通過Discord系統傳送Telegram服務的狀態信息
- **檢測邏輯**: 使用Telegram API的getMe方法檢查Telegram機器人是否在線並正常運作

#### Discord主監控服務
- **主要功能**: 中央集成所有監控信息，提供統一界面
- **資料整合**: 收集所有服務的監控數據，並提供統一的儀表板
- **頻道管理**: 將各服務的警報分發到對應的頻道，重要警報同時發送到警報頻道

### 通知流程架構
```
[服務] ---監控--> [各服務自己的監控模組] ---發送通知--> [Discord頻道]
                                          |
[Telegram API] <--監控-- [Telegram監控模組] ---|
                                          |
[區塊鏈服務] <--監控-- [區塊鏈監控模組] -------|
                                          |
[網站爬蟲服務] <--監控-- [網站爬蟲監控模組] ---|
                                          |
[n8n服務] <--監控-- [n8n監控模組] ------------|
```

### 事件處理流程
1. 監控器檢測到異常事件
2. 事件被轉發到警報系統
3. 警報系統評估嚴重性和歸類
4. 通知被格式化並發送到適當頻道
5. 事件被記錄到數據庫中供儀表板使用

### 通知優先級系統
- **緊急**: 立即需要注意的嚴重問題 (服務完全離線)
- **高**: 需要儘快處理的問題 (服務部分功能失效)
- **中**: 非緊急但需要關注的問題 (性能下降)
- **低**: 提示性質的資訊 (預警或改進建議)

## 部署與維護

### 部署架構
- **Discord監控服務**: 部署在Render上，作為中央監控服務
- **區塊鏈監控服務**: 獨立部署在Render上，通過Webhook與Discord整合
- **Web爬蟲監控服務**: 部署在Vercel上，通過Webhook與Discord整合

### 環境變數管理
- 所有敏感設定 (例如API金鑰、令牌) 通過環境變數注入
- 使用同步功能確保服務間設定一致性
- 專門的Webhook URL用於將特定服務的消息發送到對應的Discord頻道

### 聚合通知策略
- 把所有的Telegram通知轉移到Discord平台
- 使用專門的Discord頻道代替不同的通知平台
- 透過Discord的通知設定進行細粒度通知控制

## 擴展性設計

系統被設計為可輕鬆擴展以支持:
- 新的監控服務類型
- 額外的通知渠道 (除了Discord)
- 更多的分析和報告功能
- 外部API整合 