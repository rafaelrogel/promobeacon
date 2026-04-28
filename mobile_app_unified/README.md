# PromoBeacon Manager - 統一Android控制應用

## 項目概述

PromoBeacon Manager 是一個原生Android應用程序，用於統一控制PromoBeacon ESP32設備的G模式（WiFi AP + Captive Portal）和E模式（BLE Beacon）。該應用程序支持模式切換、配置管理、狀態監控和設備操作。

## 功能特性

### 設備控制
- **模式切換**：在G模式和E模式之間實時切換
- **G模式配置**：設置WiFi SSID、密碼、宣傳文字
- **E模式配置**：設置廣播訊息、Beacon參數（Major、Minor、TX Power）

### 狀態監控
- 實時連接狀態顯示
- 廣播狀態監控
- 已連接客戶端數量
- 設備運行時間
- RSSI信號強度

### 設備操作
- 重新啟動設備
- 恢復出廠設定

## 技術架構

### 架構模式
- **Clean Architecture**（分層架構）
- **MVVM**（Model-View-ViewModel）
- **Repository Pattern**

### 技術棧
- **語言**：Kotlin
- **UI框架**：Jetpack Compose + Material Design 3
- **依賴注入**：Hilt
- **異步處理**：Kotlin Coroutines + Flow
- **藍牙通信**：Android BLE API

### 項目結構

```
com.promobeacon.manager/
├── data/
│   ├── ble/
│   │   └── BleClient.kt           # BLE GATT客戶端實現
│   ├── repository/
│   │   └── DeviceRepositoryImpl.kt # Repository實現
│   └── mapper/
├── domain/
│   ├── model/
│   │   └── DeviceModels.kt        # 領域模型定義
│   ├── repository/
│   │   └── DeviceRepository.kt    # Repository接口
│   └── usecase/
│       └── DeviceUseCases.kt      # 業務邏輯用例
├── ui/
│   ├── theme/
│   │   ├── Theme.kt               # 主題定義
│   │   └── Typography.kt          # 字體樣式
│   ├── components/
│   │   └── CommonComponents.kt    # 通用UI組件
│   ├── navigation/
│   │   └── Navigation.kt          # 導航路由
│   ├── scan/
│   │   ├── ScanScreen.kt          # 設備掃描頁面
│   │   └── ScanViewModel.kt       # 掃描ViewModel
│   └── dashboard/
│       ├── DashboardScreen.kt     # 設備控制台頁面
│       └── DashboardViewModel.kt  # 控制台ViewModel
├── di/
│   └── AppModule.kt               # Hilt依賴注入模組
└── util/
```

## 權限要求

### Android 12+ 權限
- `BLUETOOTH_SCAN`：掃描藍牙設備
- `BLUETOOTH_CONNECT`：連接藍牙設備
- `ACCESS_FINE_LOCATION`：定位服務（用於BLE掃描）

## 安裝與構建

### 環境要求
- Android Studio Hedgehog 或更高版本
- JDK 17 或更高版本
- Android SDK 34

### 構建步驟

1. 打開Android Studio
2. 選擇 "Open" 並導航到 `mobile_app_unified` 目錄
3. 等待Gradle同步完成
4. 連接設備或啟動模擬器
5. 點擊 "Run" 按鈕或使用 `Build > Make Project`

### 命令行構建

```bash
cd mobile_app_unified
./gradlew assembleDebug
```

## 使用說明

### 首次使用

1. 打開應用程序
2. 授予必要的藍牙和定位權限
3. 應用程序自動開始掃描附近的PromoBeacon設備
4. 點擊設備列表中的設備進行連接

### 控制設備

連接成功後，您將看到設備控制台：

1. **查看狀態**：頂部顯示連接狀態、模式、運行時間等
2. **切換模式**：點擊模式切換按鈕在G/E模式之間切換
3. **配置設置**：
   - G模式：設置WiFi SSID、密碼、宣傳文字
   - E模式：設置廣播訊息、Beacon參數
4. **設備操作**：重啟設備或恢復出廠設定

## GATT服務定義

### 統一服務UUID
```
12345678-1234-1234-1234-123456789ABC
```

### 特徵UUID

| 特徵 | UUID | 權限 | 說明 |
|------|------|------|------|
| Mode Control | 12345679-1234-1234-1234-123456789ABC | R/W | 模式切換控制 |
| Message | 1234567A-1234-1234-1234-123456789ABC | R/W | 廣播訊息 |
| Config | 1234567B-1234-1234-1234-123456789ABC | W | 配置命令 |
| Status | 1234567C-1234-1234-1234-123456789ABC | R/N | 設備狀態 |
| Promo Text | 1234567D-1234-1234-1234-123456789ABC | R/W | 宣傳文字 |

### 命令定義

| 命令 | 值 | 說明 |
|------|-----|------|
| CMD_MODE_G | 0x00 | 切換到G模式 |
| CMD_MODE_E | 0x01 | 切換到E模式 |
| CMD_REBOOT | 0x02 | 重啟設備 |
| CMD_RESET_DEFAULTS | 0x03 | 恢復出廠設定 |

## 版本歷史

### v2.0.0 (2026-01-10)
- 添加藍牙安全功能
- BLE配對支援6位數PIN碼
- 應用層認證使用32字元十六進制Token
- 5次失敗嘗試後裝置鎖定5分鐘
- 認證對話框UI
- 狀態指示器顯示認證狀態

### v1.0.0 (2024-01-07)
- 初始版本
- 支援設備掃描和連接
- 支援模式切換
- 支援G/E模式配置
- 支援狀態監控
- 支援設備操作

## 許可證

MIT License
