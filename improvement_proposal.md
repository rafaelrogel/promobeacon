# Code Improvement Proposal for Promobeacon Repository

## Executive Summary
The Promobeacon ESP32 firmware and mobile application contain several areas for improvement in code quality, reliability, security, and maintainability. This proposal outlines identified issues and actionable recommendations.

## 1. Build and Compilation Issues
### 1.1 Compilation Errors
- **MACRO usage**: Several errors in `main.c` involving undefined `MACSTR` macro usage in `ESP_LOGI` calls. Fix includes proper inclusion of `esp_system.h` or defining `MACSTR` correctly.
- **Event ID undeclared**: `IP_EVENT_AP_STA_GOT_IP` is undefined; include the correct header (`esp_event.h`) or replace with appropriate macro.
- **Legacy ADC calibration**: Deprecated ADC calibration driver warnings; migrate to `esp_adc/adc_cali.h` and `esp_adc/adc_cali_scheme.h`.
- **Header redefinitions**: Multiple redefinition warnings in `portal_content.h` and `ble_manager.h` due to missing header guards or duplicated macro definitions; add proper `#ifndef` guards and consolidate shared macros into a common header.

### 1.2 Configuration Mismatch
- The current `partitions.csv` defines flash size as 2MB, but the project expects 4MB. Update `sdkconfig.defaults` or use `menuconfig` to set flash size correctly.

## 2. Code Quality and Maintainability
### 2.1 Modularization
- Break large source files (`ble_manager.c`, `web_server.c`, `status_collector.c`) into smaller, cohesive modules with single responsibilities. This improves readability and testability.
- Extract constant values (e.g., UUIDs, HTTP status codes) into dedicated header files.
- Use clearer naming conventions (`update_ble_advertising_name` vs `update_ble_advertising_name`) for consistency.

### 2.2 Error Handling
- Implement consistent error checking for all system calls (WiFi, BLE, file I/O). Where failures are ignored, add appropriate fallback or reporting mechanisms.
- Propagate errors upward rather than returning generic success codes.

## 3. Security Enhancements
### 3.1 Secure defaults
- Enable WPA2-PSK encryption for the WiFi Access Point by default; provide UI to disable only when required.
- Use secure random number generators for session identifiers and tokens.

### 3.2 Input Validation
- Validate user-provided promotion text length and content before storing or transmitting to prevent buffer overflows and injection attacks.
- Authenticate OTA firmware updates using signed manifests.

## 4. Testing and Continuous Integration
### 4.1 Unit Testing
- Integrate unit tests for core modules using the Unity testing framework.
- Add tests for configuration manager persistence, BLE advertisement parsing, and HTTP server response handling.

### 4.2 CI Pipeline
- Set up GitHub Actions to run:
  - Build verification on ESP32 target.
  - Linting with `clang-tidy` and `clang-format` check.
  - Unit test execution with coverage reporting.
  - Static analysis for code quality.

## 5. Documentation and Code Style
### 5.1 API Documentation
- Generate Doxygen documentation from annotated headers and source files.
- Keep documentation in sync with code changes to avoid drift.

### 5.2 Code Style
- Enforce consistent coding style via `.clang-format` configuration.
- Remove dead or unreachable code flagged by compiler warnings.
- Add comprehensive comments for public interfaces.

## 6. Performance and Memory Optimization
### 6.1 Memory Footprint
- Review static buffer allocations; reduce where possible and consider dynamic allocation.
- Optimize OTA buffer management to avoid unnecessary peaks in RAM usage.

### 6.2 Build Optimizations
- Enable Link Time Optimization (`-flto`) and size optimization (`-Os`) flags.
- Conduct periodic code size audits to ensure footprint stays within 4MB flash and 320KB RAM budgets.

## 7. Future Feature Support (E Mode)
- Define a clear roadmap for E mode features, either implement missing functionality or remove placeholder code to reduce technical debt.
- Separate E mode implementation into dedicated directories to prevent contamination of production G mode code.

## 8. Mobile Application Improvements
- Upgrade Flutter to latest stable version with null safety.
- Refactor device provider to use `Riverpod` for better state management.
- Implement robust reconnection logic for BLE disconnections.
- Ensure UI complies with accessibility standards (contrast ratios, scalable text).

## Conclusion
Implementing these improvements will enhance the robustness, security, and maintainability of the Promobeacon system, reducing the risk of production failures and facilitating future feature development. Prioritization can be guided by impact: fixing compilation errors and security hardening are immediate; modularization and CI setup provide long-term benefits.