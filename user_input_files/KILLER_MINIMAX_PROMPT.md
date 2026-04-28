# 🎯 KILLER MINIMAX PROMPT: BLE Advertising + Captive Portal ESP32 App

## PREAMBLE (System Context)

You are a **senior embedded systems architect** specializing in **low-power IoT**, **BLE protocols**, and **memory-constrained microcontroller design**. Your goal is to produce **production-grade, minimal-footprint firmware** and **mobile control architecture** for a retail point-of-sale promotion platform.

**Key Constraints:**
- ESP32 has 520 KB SRAM, 4 MB shared Flash (program + data)
- Single 2.4 GHz radio (WiFi and BLE share via time-division multiplexing)
- 4-6 simultaneous WiFi clients is target (not 100+)
- Code size and RAM efficiency are non-negotiable
- Must support **two distinct operating modes** (G and E) with instant switching

**Your output will be reviewed for:**
1. **Architectural clarity** – Can a mid-level embedded developer follow this?
2. **Code efficiency** – Will this actually fit in 520 KB SRAM + 4 MB Flash?
3. **Minimal footprint** – Are there 80+ KB available for feature expansion?
4. **Production readiness** – No stubs, no TODOs; every component has a concrete implementation path

---

## PROJECT OVERVIEW

### Vision
Create a **wireless retail promotion platform** where ESP32 devices act as both:
1. **BLE Beacon** – Advertise a promotion message (e.g., "10% OFF AT STORE_NAME CHECK OUT!")
2. **WiFi Access Point** – Serve a **captive portal** with customizable HTML (POS form, email capture, promo info)
3. **Mobile-Controllable Bridge** – Accept commands via **BLE** from a personal control app to:
   - Toggle between **G mode** (WiFi + BLE advertising) and **E mode** (other functionalities, code TBD)
   - Monitor device status (connected clients, battery, session durations)
   - Update promotion content and portal HTML

### Hardware
- **Microcontroller**: ESP32 (WROOM or S3 variant)
- **Power**: Battery-backed (monitor voltage via ADC pins 34/35)
- **Wireless**: Built-in WiFi (2.4 GHz 802.11 b/g/n) + BLE 4.2

### Success Criteria (Non-Goals + Hard Constraints)
- ✓ Fit in **<400 KB RAM** during active operation (G mode)
- ✓ **Captive portal** works on iOS, Android, Windows, macOS (no external services)
- ✓ **BLE control app** connects wirelessly; no USB debugging needed
- ✓ **SSID = promotion text** (e.g., "15% OFF@TugaMiner" as WiFi SSID)
- ✓ **Mode switching** completes in **<1 second** (instant toggle)
- ✓ **Status reporting** (clients, durations, battery) uses **<20 bytes** binary format
- ✗ Do NOT implement cloud sync, OTA updates, or encryption (unless specified later)
- ✗ Do NOT allocate FreeRTOS tasks unnecessarily (single event loop preferred)
- ✗ Do NOT use String objects in hot paths; prefer char arrays

---

## REQUIREMENT SPECIFICATION

### 1. **G Mode: WiFi AP + BLE Advertising**

#### 1.1 WiFi Access Point (Captive Portal)
**Objective**: When a device joins the ESP32's soft-AP, immediately redirect to a captive portal page, regardless of the device's OS or configuration.

**Functional Requirements**:
- [ ] Soft-AP SSID = **promotion message** (max 32 chars, e.g., "10% OFF AT <NAME> CHECK OUT!")
- [ ] Soft-AP password = **OPTIONAL** (disabled by default for public access; can be toggled)
- [ ] **DNS Wildcard**: All DNS queries (e.g., `any-domain.com`, `captive.apple.com`) resolve to ESP32's IP
- [ ] **HTTP Server** (Port 80):
  - `GET /` → Serve **custom HTML portal** (user-provided via mobile app config)
  - `POST /action` → Handle form submissions (e.g., email capture, POS data)
  - **Redirect rules**: Unknown paths → `/`
  - **Captive portal probes**: Respond correctly to iOS, Android, Windows probes
- [ ] **Max concurrent connections**: 4-6 clients (enforced at soft-AP level)
- [ ] **Session tracking**: Record each client's connection time and portal duration

**Technical Approach** (Efficiency-First):
- Use **Arduino WiFi library** (smaller than raw IDF) or lightweight IDF wrapper
- Pre-scan networks **before** starting AP to cache SSIDs (scan kills AP if done during active serving)
- Serve **single-page HTML** with inline CSS (no external .css, .js files)
- Use **char buffers** (not String objects) for SSID, password, portal content
- **DNS Wildcard**: Bind to `*` hostname → ESP32's soft-AP IP (simple, one line)
- **HTML Portal**: Embed as **C string literal** in firmware; allow updates via BLE

**Output Deliverables**:
1. Function signature: `void setupWiFiAP(const char* ssid, const char* password, const char* htmlPortal)`
2. Function signature: `void handleHTTPRequests(void)` – Main loop handler
3. HTML template (inline): `const char* DEFAULT_PORTAL_HTML = "<!DOCTYPE html>..."`
4. Example form submission handler (email capture)

---

#### 1.2 BLE Advertising (Beacon Mode)
**Objective**: Advertise the promotion message via BLE so phones can discover the device without joining WiFi AP.

**Functional Requirements**:
- [ ] **Advertised name**: Promotion message (max ~29 bytes after protocol overhead)
- [ ] **Advertising interval**: 100-500 ms when idle, can increase to 1-2 seconds when WiFi AP is active (power efficient)
- [ ] **Advertising payload**:
  - Option A (31 bytes, legacy): Manufacturer-specific data with promo text
  - Option B (Extended): Up to 251 bytes (for longer messages or future expansion)
- [ ] **GATT Service**: Expose control + status characteristics (see section 1.3)
- [ ] **No encryption** by default (can be added later for E mode)

**Technical Approach** (Minimal Code, Maximal Reach):
- Use **BLEDevice + BLEAdvertising** from ESP32 BLE library
- Start advertising **after WiFi AP is running** (simplifies initialization order)
- Reuse promotion text from WiFi AP SSID (single source of truth)
- Use **raw characteristic writes/reads** via GATT, not complex notifications (simpler)
- Prefer **advertisement packet payloads** over GATT for one-way broadcasts

**Output Deliverables**:
1. Function signature: `void setupBLEAdvertiser(const char* promoMessage)`
2. GATT Service definition: `#define SERVICE_UUID "..."`  and characteristic UUIDs
3. Example advertiser payload encoding (convert promo text → 31-byte BLE packet)

---

#### 1.3 Control + Status via BLE (GATT Service)
**Objective**: Mobile control app connects to ESP32 via BLE and can read/write device state.

**Functional Requirements**:
- [ ] **GATT Service**: Primary service with 3 characteristics
  - **Characteristic 1: Mode Control** (WRITE)
    - Value: 1 byte (0x00 = G mode, 0x01 = E mode)
    - Purpose: Instant toggle between modes
    - Response: ESP32 restarts or transitions cleanly
  - **Characteristic 2: Status** (READ or NOTIFY)
    - Value: 6 bytes (packed binary, see section 2.2)
    - Content: [flags | client_count | session_duration | portal_time | battery%]
    - Update frequency: On-demand (read) or periodic (notify, optional)
  - **Characteristic 3: Config Update** (WRITE)
    - Value: Promotion text or HTML portal (chunked if >20 bytes, see section 1.3.2)
    - Purpose: Allow remote updates without reflashing
    - Validation: Sanitize input (max lengths, no null terminators in middle)

**Technical Approach** (Simplicity + Robustness):
- GATT service runs in **advertised state** (always discoverable)
- **Write handlers**: Validate input, apply immediately, send confirmation
- **Read handlers**: Return current state (no blocking I/O)
- **Chunking for large updates**: Client sends multiple writes; server concatenates into buffer
- **No persistent GATT caching**: Values computed on-the-fly from device state

**Output Deliverables**:
1. GATT Service UUIDs (service + 3 characteristics)
2. Handler functions: `onModeWritten()`, `onStatusRead()`, `onConfigWritten()`
3. Input validation and chunking logic

---

#### 1.4 Status Collection (Efficient Telemetry)
**Objective**: Track connected clients, session durations, battery level with minimal RAM/CPU overhead.

**Functional Requirements**:
- [ ] **Metrics Tracked**:
  - Current client count (0-6)
  - Per-client session start time (when connected to AP)
  - Time spent in portal (tracked per client or aggregate)
  - Battery voltage (ADC reading from pin 34 or 35, converted to %)
- [ ] **Update Frequency**: Every 10-30 seconds (not per-packet)
- [ ] **Format**: 6-byte binary (fits in one BLE MTU)
- [ ] **No persistent logging** (RAM-limited; summary only)

**Data Structure**:
```c
struct DeviceStatus {
  uint8_t flags;              // [bit0: AP_active | bit1: BLE_active | bits2-7: reserved]
  uint8_t clientCount;        // 0-6
  uint16_t sessionDurationSec;  // Max ~18 hours; wraps if longer
  uint8_t portalTimeAvgSec;   // Average per client (0-255 sec, wraps)
  uint8_t batteryPercent;     // 0-100
  // Total: 6 bytes
};
```

**Technical Approach** (Passive Collection):
- **WiFi AP callbacks**: Detect client join/leave → update client list and timestamps
- **ADC reading**: Read battery every 30 sec in main loop (non-blocking)
- **Aggregate durations**: Sum all session times, divide by client count (simple math, no arrays)
- **Byte packing**: Shift + mask to fit into 6-byte struct

**Output Deliverables**:
1. Status struct definition (C struct with field definitions)
2. Function: `void updateStatus(void)` – Called every loop iteration (non-blocking)
3. Function: `void serializeStatus(uint8_t* buffer)` – Pack into 6 bytes
4. ADC reading function: `uint8_t getBatteryPercent(void)`

---

### 2. **E Mode: Placeholder + Integration Points**

#### 2.1 Mode Switching Mechanism
**Objective**: Seamlessly transition between G mode and E mode without hard reset.

**Functional Requirements**:
- [ ] **Trigger**: BLE characteristic write (0x00 = G, 0x01 = E) or button press (future)
- [ ] **Transition Time**: <1 second (stop WiFi/BLE in G mode, initialize E mode)
- [ ] **State Cleanup**: Release sockets, stop DNS server, stop advertisers
- [ ] **Confirmation**: Return status byte indicating new mode

**Technical Approach**:
- Use **global enum** `enum DeviceMode { MODE_G = 0, MODE_E = 1 } currentMode;`
- In BLE write handler: Set flag, don't block; let main loop detect and transition
- Main loop: If mode changed, call `transitionMode(newMode)` (handles cleanup + init)
- Avoid soft reset; prefer graceful transition

**Output Deliverables**:
1. Function: `void transitionMode(enum DeviceMode newMode)`
2. Main loop fragment: Mode transition logic
3. Cleanup checklist (WiFi, DNS, BLE resources)

---

#### 2.2 E Mode Stub Structure
**Objective**: Reserve firmware space and GATT service endpoints for future E mode implementation.

**Functional Requirements**:
- [ ] **Do NOT implement E mode logic yet** (you'll provide code later)
- [ ] **Reserved space**: ~50-100 KB (estimate for E mode features)
- [ ] **GATT Service**: Separate service UUID for E mode controls (different from G mode)
- [ ] **Stub handlers**: Empty functions that log "E mode not yet active"
- [ ] **Clean separation**: G mode code should not reference E mode variables

**Technical Approach**:
- Create separate file: `e_mode.c` / `e_mode.h` (empty implementations)
- Define E mode service UUIDs in header only (no implementation)
- In mode transition: Check if E mode is supported, return error if not yet ready
- Leave TODO comments for integration points (you'll fill these in)

**Output Deliverables**:
1. Header: `#define E_MODE_SERVICE_UUID "..."` (reserved UUID)
2. Stub function: `void setupEMode(void)` (empty)
3. Stub function: `void handleEModeRequests(void)` (empty)
4. Integration point documentation

---

### 3. **Mobile Control App (Architecture + Blueprint)**

#### 3.1 App Functionality
**Objective**: Personal control app (not for public; for your management) to configure and monitor multiple ESP32 devices.

**Features**:
- [ ] **Device Discovery**: Scan for BLE advertisements, list all available ESP32s
- [ ] **Mode Toggle**: Switch device between G mode and E mode (instant)
- [ ] **Status Dashboard**: Display real-time metrics (clients, battery, duration)
- [ ] **Config Editor**:
  - Edit promotion text (SSID)
  - Edit captive portal HTML (chunked upload via BLE)
  - Set WiFi password (optional)
  - Set reporting interval
- [ ] **Multi-Device Management**: Control 1+ ESP32s from single app (drop-down or list)
- [ ] **Offline-first**: All config cached locally; syncs to device when connected

**Technical Approach** (Framework Recommendation):
- **Platform**: Flutter (single codebase, iOS + Android + Web) or React Native
- **BLE Communication**: 
  - iOS: `CoreBluetooth` (native), Android: `android.bluetooth` (native), or use cross-platform plugin (e.g., `flutter_blue_plus`)
- **State Management**: Provider (Flutter) or Redux (React Native)
- **Data Format**: JSON for app settings, binary for BLE packets (parse on device side)

**Output Deliverables**:
1. App architecture diagram (screens, navigation)
2. BLE communication protocol spec (message format for config updates)
3. UI mockup (text or wireframe)
4. Sample Flutter/React Native code (discovery + mode toggle)

---

## ARCHITECTURAL OVERVIEW (Block Diagram)

```
┌─────────────────────────────────────────────────────────┐
│                    ESP32 Firmware                       │
├─────────────────────────────────────────────────────────┤
│                    Main Event Loop                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │ if (currentMode == MODE_G)                       │   │
│  │   ├─ WiFiAP.handleRequest()                      │   │
│  │   ├─ BLE.handleConnection()                      │   │
│  │   └─ updateStatus()                              │   │
│  │ else if (currentMode == MODE_E)                  │   │
│  │   └─ E_Mode.handle()                             │   │
│  │ delay(10ms) → watchdog-friendly                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────┐  ┌──────────────────────────────┐ │
│  │  G Mode Layer   │  │  Status Collector (Passive)  │ │
│  ├─────────────────┤  ├──────────────────────────────┤ │
│  │ WiFi AP         │  │ Client count tracking        │ │
│  │ DNS Wildcard    │  │ Session duration timer       │ │
│  │ HTTP Server     │  │ Battery ADC reader           │ │
│  │ BLE Advertiser  │  │ GATT characteristic values   │ │
│  │ GATT Service    │  │ (updated every 10 sec)       │ │
│  └─────────────────┘  └──────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Data Structures (Minimal RAM)                     │ │
│  │  - WiFi AP config (SSID, password, HTML portal)    │ │
│  │  - Client connection table (6 entries max)         │ │
│  │  - Status struct (6 bytes)                         │ │
│  │  - Mode state (1 byte)                             │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         ⬆️                                  ⬆️
    WiFi Clients              Mobile Control App
   (HTML Portal)              (BLE Connection)
```

---

## DETAILED OUTPUT SPECIFICATION

### What Minimax Should Produce

#### **SECTION A: Firmware Architecture Document**
- **Subsection A1**: Overall system design (init sequence, mode switching, event loop)
- **Subsection A2**: G mode WiFi subsystem (AP setup, DNS, HTTP server)
- **Subsection A3**: G mode BLE subsystem (advertiser, GATT service, characteristics)
- **Subsection A4**: Status collection (data structures, update logic, serialization)
- **Subsection A5**: E mode stubs and integration points
- **Subsection A6**: Memory footprint estimate (RAM, Flash by component)

#### **SECTION B: Code Templates (Ready-to-Paste)**
- **B1**: WiFi AP setup function with code
- **B2**: DNS wildcard server implementation (minimal, copy-paste ready)
- **B3**: HTTP server handler (GET /, POST /action, redirect unknown paths)
- **B4**: HTML portal template (inline C string with placeholders)
- **B5**: BLE advertiser initialization and GATT service setup
- **B6**: Status collection functions (update, serialize, battery read)
- **B7**: Mode transition function (cleanup + init)
- **B8**: Main loop skeleton with mode handling
- **B9**: E mode stubs (empty implementations, comment-documented)

#### **SECTION C: Mobile App Blueprint**
- **C1**: App architecture (screens, state flow)
- **C2**: BLE communication protocol spec (message types, binary format)
- **C3**: Sample Flutter code (device discovery, mode toggle, status read)
- **C4**: Sample React Native code (alternative, same features)

#### **SECTION D: Integration & Testing**
- **D1**: Hardware pinout (PWR, GND, ADC pins, LED for debugging)
- **D2**: Build instructions (platformio.ini, Arduino IDE setup)
- **D3**: Testing checklist (WiFi AP, BLE discovery, mode switching, HTML portal)
- **D4**: Troubleshooting guide (common issues, logs to check)

---

## CONSTRAINTS & GUARDRAILS

### Hard Constraints (Non-Negotiable)
- **RAM**: Must fit in 520 KB; target <400 KB during G mode active operation
- **Flash**: Program + data must fit in 4 MB (shared)
- **Single radio**: WiFi and BLE share 2.4 GHz (time-multiplexed by IDF)
- **Concurrent WiFi clients**: 4-6 max (soft-AP limit)
- **Mode switch latency**: <1 second (instant user experience)
- **HTML portal**: <10 KB total (including inline CSS)
- **No external cloud dependencies**: Must work offline

### Soft Constraints (Preferences, Can Sacrifice if Needed)
- **Code size**: Minimize using char arrays, avoid String objects, enable LTO
- **Power consumption**: Optimize advertising interval when idle
- **Responsiveness**: Main loop <50 ms per iteration (watchdog-friendly)
- **Code readability**: Clear variable names, comments on complex logic

### Out-of-Scope (Do NOT Include)
- ❌ Cloud integration (AWS, Firebase, etc.)
- ❌ OTA firmware updates
- ❌ TLS/SSL encryption (unless specified for E mode)
- ❌ MQTT or other cloud protocols
- ❌ Persistent logging to SD card or EEPROM
- ❌ Audio/video processing
- ❌ Multi-language localization
- ❌ Complex graphics or animations

---

## ACCEPTANCE CRITERIA (Pass/Fail Checklist)

Before responding, verify:

- [ ] **All 9 functional requirement sections** addressed (1.1 through 3.1)
- [ ] **Code templates provided** (not just pseudocode; copy-paste ready)
- [ ] **Memory footprint estimated** per component (WiFi AP, BLE, HTML portal, E mode stub)
- [ ] **GATT service UUIDs defined** (service + 3 characteristics, 128-bit or 16-bit standard)
- [ ] **Binary status format documented** (6-byte struct with clear field meanings)
- [ ] **Mode transition logic complete** (cleanup, initialization, error handling)
- [ ] **Mobile app blueprint includes code samples** (at least one platform, Flutter preferred)
- [ ] **HTML portal template provided** (inline C string, includes form example)
- [ ] **Main loop skeleton clear** (50 ms per iteration max, handles both modes)
- [ ] **No TODOs in code templates** (every function has full implementation or clear stub)
- [ ] **Troubleshooting guide included** (common issues + logs to check)
- [ ] **No assumptions left implicit** (e.g., pin numbers, baud rates, UUIDs all specified)

---

## FINAL NOTE TO MINIMAX

This is a **production IoT project** with **real hardware constraints** and **multiple business locations** (TugaMiner storefronts). The code must be:

1. **Efficient** – Every KB of RAM matters; code footprint must leave room for your E mode (50-100 KB)
2. **Reliable** – No crashes, no memory leaks, no blocking I/O in the main loop
3. **Practical** – The developer (Rafael) will integrate E mode later; your stubs must be clean entry points
4. **Complete** – Code templates should be copy-paste ready, not scaffolding or pseudocode

Think of this as the **foundation layer** for a multi-store retail promotion platform. Get it right, and E mode (whatever it is) will integrate cleanly. Get it wrong, and the whole system is unstable from day one.

**You have all the constraints, all the requirements, and all the context. Produce the best possible solution.**

---

*Prompt version: 1.0 | Date: January 2026 | Target: Minimax M2 or later*
