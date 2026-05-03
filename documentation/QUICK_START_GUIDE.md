# PromoBeacon Manager - Quick Start Guide

Welcome to the **PromoBeacon** retail ecosystem. This guide will help you configure your device and start capturing customer insights.

## 1. Initial Connection
1.  Power on your PromoBeacon device (USB 5V).
2.  Open the **PromoBeacon Manager** app on your Android device.
3.  Tap **Scan** and select your device from the list.
4.  When the login dialog appears, enter the administrator password.
    *   **Default Password:** `12345`

## 2. WiFi Configuration (G-Mode)
Once authenticated, you can customize how the beacon appears to customers:

*   **Network Name (SSID):** The public name of your WiFi (e.g., `Store_Vip_Offers`).
*   **WiFi Password:** Leave empty for an **Open Network** to maximize customer engagement.
*   **Default Message:** A short greeting shown on the default landing page (e.g., `Welcome to our store!`).
    *   *Note: This message is hidden if you upload a custom HTML portal.*

## 3. Custom Landing Page (Captive Portal)
Create a branded experience by uploading your own HTML:

1.  Prepare a single `index.html` file.
2.  **Images:** Since the beacon has no internet access, images must be embedded using **Base64 encoding** inside the HTML file.
3.  **Size Limit:** The total file size must be under **16KB**.
4.  In the app, tap **Upload Portal (HTML)** and select your file.
5.  **Validation:** Connect to the beacon's WiFi with your phone to see your new branded portal in action.

## 4. Retail Analytics & Metrics
The PromoBeacon automatically logs nearby devices to help you understand your store's traffic.

1.  Connect your phone to the **Beacon's WiFi network**.
2.  In the app, tap **Export Stats (CSV)**.
3.  The app will download a `.csv` file to your device.
4.  **Metrics included:**
    *   **Visit Frequency:** Identify repeat customers.
    *   **Dwell Time:** Measure how long customers stay in specific areas.
    *   **Hourly Traffic:** Optimize staff schedules based on peak hours.

## 5. Maintenance & Troubleshooting
*   **Reboot:** Use this if the device becomes unresponsive or to apply network changes.
*   **Factory Reset:** Clears all custom HTML and network settings.
    *   *SSID will revert to "PromoBeacon" and password to "12345".*
*   **Range:** The beacon covers approximately 20-30 meters in open space. Positioning it higher (above 2m) improves signal stability.

---
*PromoBeacon - Smart Retail Intelligence*
