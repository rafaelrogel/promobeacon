# PromoBeacon ESP32 - Retail Promotion Platform

A dual-mode retail promotion platform built on the ESP32 microcontroller, featuring WiFi Access Point with captive portal functionality and Bluetooth Low Energy (BLE) advertising with mobile device control capabilities.

## Overview

PromoBeacon enables retail stores to create interactive promotional experiences where customers can connect to a WiFi hotspot and receive promotional content through a captive portal interface. Store managers can remotely configure the promotion text, portal content, and monitor device status through a companion mobile application.

The system operates in two distinct modes. G mode (Promotion Mode) activates the WiFi Access Point with captive portal, BLE advertising, and full monitoring capabilities. E mode (Expansion Mode) provides a low-power standby state reserved for future feature expansion such as sensor integration, mesh networking, or additional connectivity options.

## Hardware Requirements

The firmware is designed to run on ESP32-WROOM-32 or ESP32-S3 variant modules with the following specifications. The ESP32 provides 520KB of SRAM and 4MB of shared Flash storage, which is sufficient for the complete promotional platform while leaving room for future feature development. The single 2.4GHz radio supports both WiFi and BLE through time-division multiplexing, managed by the ESP-IDF framework.

For battery-powered deployments, the system supports voltage monitoring through ADC pin 34 or 35, requiring a 10:1 voltage divider circuit to scale the maximum battery voltage (approximately 4.2V fully charged) to the ESP32's 0-3.3V ADC input range. The recommended circuit uses 1% precision resistors to ensure accurate battery level reporting.

## Software Architecture

### Firmware Components

The firmware architecture follows a modular design pattern with clear separation between subsystems. The main application handles system initialization, mode transitions, and the event loop that coordinates all subsystem operations. Each major feature area is encapsulated in its own module with well-defined interfaces.

The WiFi manager module handles Access Point configuration and client connection tracking. It supports optional WPA2 encryption and manages the DHCP server that assigns addresses to connected clients. The module also implements a DNS wildcard server that resolves all domain queries to the Access Point IP address, enabling the captive portal redirect functionality.

The BLE manager module implements advertising and GATT services for mobile device communication. The advertising component broadcasts the promotion message as the device name, enabling customers to discover the device without joining the WiFi network. The GATT service exposes characteristics for mode control, status reporting, and configuration updates, all accessible through the companion mobile application.

The web server module serves the captive portal HTML content and handles form submissions from connected clients. The server implements a minimalist HTTP protocol stack optimized for the embedded environment, processing requests synchronously within the main event loop to avoid the complexity of multi-threaded operation.

The status collector module tracks device metrics including connected client count, session duration, portal engagement time, and battery level. The module updates status fields passively during normal operation and packs the metrics into a 6-byte binary format for efficient BLE transmission.

The configuration manager module provides persistent storage for device settings using the ESP32's NVS (Non-Volatile Storage) system. Configuration values persist across power cycles and include the promotion text, portal HTML content, WiFi password, and last active mode.

### Mobile Application

The companion mobile application is built with Flutter, enabling a single codebase to target both iOS and Android platforms. The application uses the flutter_blue_plus library for BLE communication and the Provider pattern for state management.

The application provides device discovery through BLE scanning with service UUID filtering, ensuring only PromoBeacon devices appear in the scan results. Once connected, users can view real-time device status metrics, switch between G and E modes, and update the promotion text through a streamlined interface.

The application architecture follows clean architecture principles with separation between presentation, domain, and data layers. The presentation layer handles UI components and user interactions using Flutter's widget system. The domain layer contains business logic for device management and configuration parsing. The data layer manages BLE communication, persistent storage, and device state synchronization.

## Project Structure

The project is organized into two main directories corresponding to the firmware and mobile application components.

```
promobeacon-esp32/
├── firmware/
│   ├── main/
│   │   └── main.c                    # Application entry point
│   ├── include/
│   │   ├── g_mode.h                  # G mode interface
│   │   ├── e_mode.h                  # E mode interface
│   │   ├── ble_manager.h             # BLE interface
│   │   ├── wifi_manager.h            # WiFi interface
│   │   ├── web_server.h              # HTTP server interface
│   │   ├── status_collector.h        # Status interface
│   │   └── config_manager.h          # Configuration interface
│   ├── src/
│   │   ├── g_mode.c                  # G mode implementation
│   │   ├── e_mode.c                  # E mode implementation
│   │   ├── ble_manager.c             # BLE implementation
│   │   ├── wifi_manager.c            # WiFi implementation
│   │   ├── web_server.c              # HTTP server implementation
│   │   ├── status_collector.c        # Status implementation
│   │   └── config_manager.c          # Configuration implementation
│   ├── data/
│   │   ├── index.html                # Default portal HTML
│   │   └── styles.css                # Portal styles
│   ├── platformio.ini                # Build configuration
│   ├── partitions.csv                # Flash partition table
│   └── README.md                     # Firmware documentation
│
├── mobile_app/
│   ├── lib/
│   │   ├── main.dart                 # Application entry point
│   │   ├── providers/
│   │   │   └── device_provider.dart  # Device state management
│   │   ├── screens/
│   │   │   ├── scanner_screen.dart   # Device discovery UI
│   │   │   ├── dashboard_screen.dart # Main dashboard UI
│   │   │   ├── device_detail_screen.dart # Device detail UI
│   │   │   └── settings_screen.dart  # App settings UI
│   │   └── utils/
│   │       └── constants.dart        # Application constants
│   ├── pubspec.yaml                  # Flutter dependencies
│   └── README.md                     # Mobile app documentation
│
└── README.md                         # Project documentation
```

## Building the Firmware

### Prerequisites

Building the firmware requires PlatformIO, which provides a standardized development environment for ESP32 development. Install PlatformIO by running `pip install platformio` in your terminal. The installation includes all necessary toolchains and frameworks for ESP32 compilation.

### Build Process

Navigate to the firmware directory and run the build command to compile the firmware for the ESP32 target platform. The build process applies Link-Time Optimization to minimize code size and generates a binary image ready for upload to the device.

```bash
cd firmware
pio run -e esp32dev
```

### Upload to Device

Connect the ESP32 module to your computer via USB and upload the compiled firmware. The upload process automatically resets the device and transfers the binary image to the Flash memory.

```bash
pio run -e esp32dev -t upload
```

### Serial Monitor

After uploading, you can monitor the device's serial output to observe the boot sequence and runtime logs. The monitor runs at 115200 baud and displays diagnostic information from all firmware components.

```bash
pio device monitor
```

### Custom Partition Table

The project includes a custom partition table optimized for the promotional platform. The table allocates 2MB for the main application, 1MB for SPIFFS storage (HTML portal and assets), and reserves space for OTA update capabilities. The partition configuration is specified in `partitions.csv` and automatically applied during the build process.

## Building the Mobile Application

### Prerequisites

The mobile application requires Flutter 3.0 or later with support for iOS and Android platforms. Install Flutter by following the official installation guide for your operating system. Ensure that both iOS and Android toolchains are configured by running `flutter doctor`.

### Dependencies

Navigate to the mobile application directory and fetch the required dependencies using Flutter's package manager.

```bash
cd mobile_app
flutter pub get
```

### Platform-Specific Setup

For iOS deployment, configure the iOS project with the necessary permissions for Bluetooth access. Update the `Info.plist` file to include the Bluetooth privacy description and the background modes required for BLE communication.

For Android deployment, ensure that the minimum SDK version is set to API 21 or higher in the `android/app/build.gradle` file. Update the AndroidManifest.xml to include the Bluetooth permissions required for BLE communication.

### Running on Device

Connect a physical device (emulators do not support BLE communication) and run the application using Flutter's development tooling.

```bash
flutter run
```

### Building Release Packages

Generate a release build for distribution to end users. For iOS, this produces an `.ipa` archive file suitable for App Store submission. For Android, this produces an `.apk` or `.aab` bundle suitable for Play Store distribution.

```bash
# iOS release build
flutter build ipa

# Android release build
flutter build apk
```

## Configuration

### Promotion Text

The promotion text serves dual purposes as the WiFi Access Point SSID and the BLE advertising name. The text is limited to 29 characters to accommodate the BLE protocol overhead while remaining within the 32-character WiFi SSID limit. Configure the promotion text through the mobile application or by saving a new value to NVS storage.

### Portal HTML

The captive portal HTML content is served to clients that connect to the WiFi Access Point. The default portal includes a simple email capture form with responsive styling that works on mobile and desktop browsers. Customize the portal content by modifying the files in the `data` directory or by uploading new content through the mobile application.

### WiFi Security

The Access Point supports optional WPA2-PSK encryption for environments that require network security. When a password is configured, clients must enter the password to connect to the network. Disable encryption by clearing the password, which creates an open network suitable for customer-facing promotional deployments.

## Usage

### Initial Setup

After uploading the firmware and installing the mobile application, power on the ESP32 device. The device boots into G mode by default and begins advertising the promotion text over both WiFi and BLE. Use the mobile application to scan for nearby devices and establish a BLE connection for configuration and monitoring.

### Customer Experience

Customers in range of the device see the WiFi network with the promotion text as the SSID. When customers connect to the network, the device's DNS server redirects all web requests to the captive portal, where they can view promotional content and submit information through forms. The captive portal works automatically on iOS, Android, Windows, and macOS devices without requiring special configuration.

### Store Management

Store managers use the mobile application to monitor device status in real-time. The dashboard displays the number of connected clients, battery level (for battery-powered deployments), and session duration. Managers can toggle between G and E modes instantly and update the promotion text without physical access to the device.

## Memory Footprint

The firmware is designed to operate within the ESP32's 520KB SRAM limit while leaving sufficient headroom for feature expansion. The following memory estimates assume compilation with optimization level -Os and Link-Time Optimization enabled.

| Component | RAM Usage | Flash Usage |
|-----------|-----------|-------------|
| ESP-IDF WiFi Stack | 45 KB | 150 KB |
| ESP-IDF BLE Stack | 35 KB | 120 KB |
| FreeRTOS Kernel | 12 KB | 40 KB |
| WiFi AP Buffers | 12 KB | 2 KB |
| HTTP Server | 3 KB | 8 KB |
| DNS Server | 1 KB | 2 KB |
| BLE Advertising | 200 B | 4 KB |
| GATT Service | 100 B | 6 KB |
| Status Collection | 60 B | 2 KB |
| E Mode Stubs | 500 B | 4 KB |
| **Total G Mode** | **~320 KB** | **~338 KB** |

The G mode footprint of approximately 320KB leaves 200KB of headroom above the 400KB target and approximately 50KB available for E mode feature expansion. Flash consumption of 338KB leaves over 3.5MB available for HTML portal content, application data, and future firmware updates.

## Future Development

The E mode placeholder provides integration points for future feature expansion. Planned capabilities include sensor integration for environmental monitoring, mesh networking for multi-device coordination, and enhanced connectivity options for cloud integration. The clean separation between G mode and E mode code ensures that future development cannot destabilize the production promotional functionality.

## Troubleshooting

If the device does not appear in the mobile application's scan results, verify that Bluetooth is enabled on the mobile device and that the ESP32 is powered and operating correctly. Check the serial console for any error messages during initialization.

If the captive portal does not redirect on iOS devices, verify that the DNS server is responding to queries and that the HTTP server is serving content on port 80. Some iOS versions require specific HTTP headers in the redirect response, which the web server implementation provides.

If BLE connections fail immediately after connecting, verify that the GATT service UUIDs match between the firmware and mobile application. Mismatched UUIDs cause service discovery to fail, resulting in disconnection.

## License

This project is provided as-is for educational and commercial use. The firmware and mobile application components are designed for use with ESP32-based hardware platforms.

## Author

Developed by MiniMax Agent as a production-grade embedded systems solution for retail promotional applications.
