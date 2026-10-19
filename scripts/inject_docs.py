import re
from pathlib import Path

INDEX_PATH = Path("web_installer/index.html")
content = INDEX_PATH.read_text(encoding="utf-8")

# 1. Add Documentation Tab Button
tab_button = """        <button class="tab-btn" onclick="switchTab('docs')">
            <span>📚</span> Help Center & Docs
        </button>"""

if 'onclick="switchTab(\'docs\')"' not in content:
    content = content.replace(
        """        <button class="tab-btn" onclick="switchTab('verifier')">
            <span>🔍</span> Verifier & Linter
        </button>""",
        """        <button class="tab-btn" onclick="switchTab('verifier')">
            <span>🔍</span> Verifier & Linter
        </button>\n""" + tab_button
    )

# 2. Add Documentation Styles
docs_styles = """
        /* TAB 4: Documentation & Help Center Styles */
        .docs-container {
            max-width: 960px;
            margin: 0 auto;
        }

        .docs-search-wrapper {
            position: relative;
            margin-bottom: 24px;
        }

        .docs-search-input {
            width: 100%;
            padding: 16px 20px 16px 48px;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            color: #fff;
            font-size: 1.05rem;
            transition: all 0.2s;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }

        .docs-search-input:focus {
            outline: none;
            border-color: var(--primary-light);
            background: rgba(15, 23, 42, 0.95);
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.25);
        }

        .docs-search-icon {
            position: absolute;
            left: 18px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.25rem;
            opacity: 0.6;
            pointer-events: none;
        }

        .docs-filter-chips {
            display: flex;
            gap: 8px;
            margin-bottom: 28px;
            flex-wrap: wrap;
        }

        .docs-chip {
            padding: 8px 16px;
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.2s;
        }

        .docs-chip:hover {
            color: #fff;
            background: rgba(255, 255, 255, 0.08);
        }

        .docs-chip.active {
            background: linear-gradient(135deg, var(--primary), #4f46e5);
            color: #fff;
            border-color: transparent;
            box-shadow: 0 2px 10px rgba(99, 102, 241, 0.3);
        }

        .docs-spotlight {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.1));
            border: 1px solid rgba(129, 140, 248, 0.3);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 32px;
            position: relative;
            overflow: hidden;
        }

        .docs-spotlight::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 250px;
            height: 250px;
            background: radial-gradient(circle, rgba(129, 140, 248, 0.2) 0%, transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        }

        .docs-section-title {
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #fff;
        }

        .docs-accordion-item {
            background: rgba(22, 30, 49, 0.65);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            margin-bottom: 12px;
            overflow: hidden;
            transition: all 0.2s;
        }

        .docs-accordion-item:hover {
            border-color: rgba(255, 255, 255, 0.15);
        }

        .docs-accordion-header {
            padding: 18px 22px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            user-select: none;
            transition: background 0.2s;
        }

        .docs-accordion-header:hover {
            background: rgba(255, 255, 255, 0.03);
        }

        .docs-accordion-title {
            font-size: 1.02rem;
            font-weight: 600;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .docs-accordion-chevron {
            font-size: 0.85rem;
            color: var(--text-muted);
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .docs-accordion-item.open .docs-accordion-chevron {
            transform: rotate(180deg);
        }

        .docs-accordion-body {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.35s cubic-bezier(0.4, 0, 0.2, 1);
            background: rgba(15, 23, 42, 0.35);
        }

        .docs-accordion-item.open .docs-accordion-body {
            max-height: 2500px;
        }

        .docs-content {
            padding: 20px 24px;
            color: #cbd5e1;
            font-size: 0.95rem;
            line-height: 1.65;
            border-top: 1px solid var(--card-border);
        }

        .docs-content p {
            margin-bottom: 14px;
        }

        .docs-content ul, .docs-content ol {
            margin-left: 20px;
            margin-bottom: 14px;
        }

        .docs-content li {
            margin-bottom: 6px;
        }

        .docs-table {
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 0.88rem;
        }

        .docs-table th, .docs-table td {
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid var(--card-border);
        }

        .docs-table th {
            background: rgba(30, 41, 59, 0.5);
            color: #fff;
            font-weight: 600;
        }

        .docs-table tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        .docs-code-block {
            background: #090d16;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 14px 18px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.85rem;
            color: #e2e8f0;
            margin: 14px 0;
            overflow-x: auto;
            position: relative;
        }

        .docs-code-copy-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px;
            color: var(--text-muted);
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .docs-code-copy-btn:hover {
            color: #fff;
            background: rgba(99, 102, 241, 0.4);
            border-color: var(--primary-light);
        }

        .docs-tag {
            display: inline-block;
            padding: 2px 8px;
            background: rgba(99, 102, 241, 0.18);
            border-radius: 4px;
            color: #a5b4fc;
            font-size: 0.82rem;
            font-family: monospace;
        }

        .docs-callout {
            padding: 14px 18px;
            border-radius: 10px;
            margin: 14px 0;
            border-left: 4px solid;
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .docs-callout-info {
            background: rgba(56, 189, 248, 0.08);
            border-color: #38bdf8;
            color: #bae6fd;
        }

        .docs-callout-warning {
            background: rgba(245, 158, 11, 0.08);
            border-color: #f59e0b;
            color: #fde68a;
        }

        .docs-callout-tip {
            background: rgba(16, 185, 129, 0.08);
            border-color: #10b981;
            color: #a7f3d0;
        }
"""

if '.docs-container' not in content:
    content = content.replace("/* TAB 3: Verifier Styles */", docs_styles + "\n        /* TAB 3: Verifier Styles */")

# 3. Add Documentation HTML Panel
docs_panel = """        <!-- TAB 4: DOCUMENTATION & HELP CENTER -->
        <div id="tab-docs" class="panel">
            <div class="docs-container">
                
                <!-- Search & Filters -->
                <div class="docs-search-wrapper">
                    <span class="docs-search-icon">🔍</span>
                    <input type="text" class="docs-search-input" id="docs-search" placeholder="Search documentation, guides, FAQs, error codes, REST endpoints..." oninput="filterDocs()">
                </div>

                <div class="docs-filter-chips">
                    <button class="docs-chip active" onclick="setDocFilter('all')">All Documentation</button>
                    <button class="docs-chip" onclick="setDocFilter('assets')">📁 /assets/ & Media</button>
                    <button class="docs-chip" onclick="setDocFilter('quickstart')">🚀 Getting Started</button>
                    <button class="docs-chip" onclick="setDocFilter('captive')">📡 Captive Portal</button>
                    <button class="docs-chip" onclick="setDocFilter('analytics')">📊 Visitor Analytics</button>
                    <button class="docs-chip" onclick="setDocFilter('battery')">🔋 Battery & Power</button>
                    <button class="docs-chip" onclick="setDocFilter('regulatory')">🌐 Regulatory & RF</button>
                    <button class="docs-chip" onclick="setDocFilter('security')">🔒 Security & Passwords</button>
                    <button class="docs-chip" onclick="setDocFilter('api')">💻 REST API & cURL</button>
                    <button class="docs-chip" onclick="setDocFilter('faq')">❓ FAQ</button>
                </div>

                <!-- SPOTLIGHT BANNER: ASSET MANAGEMENT & /assets/ -->
                <div class="docs-spotlight doc-item" data-category="assets" data-keywords="assets storage media images pdf upload path menu flyer logo">
                    <div style="display: flex; align-items: flex-start; gap: 16px;">
                        <span style="font-size: 2.2rem;">📁</span>
                        <div>
                            <h3 style="font-size: 1.25rem; font-weight: 700; color: #fff; margin-bottom: 8px;">
                                The Golden Rule of Media: Always Use the <code class="docs-tag">/assets/</code> Path
                            </h3>
                            <p style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 12px; line-height: 1.5;">
                                <b>Do customer images, PDFs, and media files have to be placed in <code>/assets/</code>?</b><br>
                                <b>YES.</b> The ESP32 PromoBeacon firmware mounts a dedicated <b>2.7 MB BigStorage SPIFFS partition</b> directly mapped to the <code class="docs-tag">/assets/*</code> web endpoint.
                            </p>
                            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 12px;">
                                When crafting your HTML portal, always reference your local files with the prefix:
                                <br>
                                • <code class="docs-tag">&lt;img src="/assets/my_logo.png"&gt;</code> &nbsp;|&nbsp; 
                                • <code class="docs-tag">&lt;a href="/assets/menu.pdf"&gt;Download Menu&lt;/a&gt;</code>
                            </p>
                            <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                                <a href="#doc-assets-guide" class="btn btn-primary" style="padding: 8px 16px; font-size: 0.85rem;" onclick="openAccordion('doc-assets-guide')">
                                    📖 Read Complete Asset Guide
                                </a>
                                <button class="btn btn-secondary" style="padding: 8px 16px; font-size: 0.85rem;" onclick="copyCodeSnippet('code-asset-example')">
                                    📋 Copy Sample HTML with /assets/
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SECTION 1: GETTING STARTED & FLASHING -->
                <div class="docs-section-title">
                    <span>🚀</span> Getting Started & Flashing Guide
                </div>

                <div class="docs-accordion-item doc-item" id="doc-quickstart" data-category="quickstart" data-keywords="flash install usb webserial driver cp2102 ch340 boot button baudrate chrome edge">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">🔌 Hardware Connection & 1-Click WebSerial Flasher</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>PromoBeacon supports all standard ESP32 development boards (ESP32-C3, ESP32-S3, ESP32 classic). Flashing requires zero command-line tools—it runs 100% in your browser via the WebSerial API.</p>
                            
                            <h4>Step-by-Step Installation:</h4>
                            <ol>
                                <li><b>USB Cable Type:</b> Connect the ESP32 to your PC using a <b>USB Data Cable</b> (verify it is not a charge-only cable).</li>
                                <li><b>Browser Requirements:</b> Open this website in <b>Google Chrome</b>, <b>Microsoft Edge</b>, or <b>Opera</b> on desktop (Safari and Firefox do not support WebSerial).</li>
                                <li><b>Drivers:</b> Most modern Windows/macOS systems recognize the board automatically. If your serial port does not appear, install the <a href="https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers" target="_blank" style="color:#818cf8;">CP210x Driver</a> or <a href="http://www.wch-ic.com/downloads/CH341SER_EXE.html" target="_blank" style="color:#818cf8;">WCH CH340 Driver</a>.</li>
                                <li><b>Click "Start Installation":</b> Switch to the <i>USB Flasher</i> tab, select your COM port, and click Connect.</li>
                                <li><b>Clean Install (Recommended):</b> Check the <b>"Erase Device"</b> option to format the flash cleanly and provision the 2.7MB BigStorage partition.</li>
                            </ol>

                            <div class="docs-callout docs-callout-warning">
                                <b>Troubleshooting Stuck Flashing ("Failed to connect"):</b><br>
                                Some ESP32-C3 boards require manual bootloader entry: press and hold the <b>BOOT</b> button, tap the <b>RESET (RST/EN)</b> button once, and release <b>BOOT</b>. Then click <i>Connect</i> in your browser.
                            </div>
                        </div>
                    </div>
                </div>

                <div class="docs-accordion-item doc-item" id="doc-first-boot" data-category="quickstart" data-keywords="first boot ssid password default setup 192.168.4.1 connect">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">✨ First Boot & Initial Configuration</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>Once flashed, the ESP32 reboots immediately and begins broadcasting its default open Wi-Fi network:</p>
                            <ul>
                                <li><b>Default SSID:</b> <code class="docs-tag">PROMOBEACON</code></li>
                                <li><b>Security:</b> Open (No password required)</li>
                                <li><b>Gateway IP:</b> <code class="docs-tag">http://192.168.4.1/</code></li>
                                <li><b>Default Admin Password:</b> <code class="docs-tag">12345</code></li>
                            </ul>
                            <p>To configure your campaign, connect any smartphone, tablet, or laptop to <b>PROMOBEACON</b>. The captive portal popup will trigger automatically. You can also visit <code>http://192.168.4.1/setup</code> in your browser to change the SSID, set promotional text, or update regulatory domain settings.</p>
                        </div>
                    </div>
                </div>

                <!-- SECTION 2: ASSET MANAGEMENT (/assets/) -->
                <div class="docs-section-title" style="margin-top: 28px;">
                    <span>📁</span> Asset Architecture & Media Management
                </div>

                <div class="docs-accordion-item doc-item" id="doc-assets-guide" data-category="assets" data-keywords="assets spiffs storage upload pdf images video font html css js folder">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">📦 Complete Guide: Storing Images, PDFs, and Files in /assets/</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>PromoBeacon is completely autonomous: it does not use the internet or cloud hosting. All content delivered to nearby customers lives inside the ESP32's internal <b>2.7 MB BigStorage flash memory</b>.</p>

                            <h4>1. How Asset Routing Works:</h4>
                            <p>When a customer smartphone visits your portal and requests an asset, the ESP32 web server resolves the path seamlessly:</p>
                            <table class="docs-table">
                                <thead>
                                    <tr>
                                        <th>Requested URL in HTML</th>
                                        <th>Internal Storage Path</th>
                                        <th>MIME Type Returned</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><code>/assets/menu.pdf</code></td>
                                        <td><code>/storage/assets/menu.pdf</code> (or <code>/storage/menu.pdf</code>)</td>
                                        <td><code>application/pdf</code></td>
                                        <td><span class="badge badge-pass">Recommended</span></td>
                                    </tr>
                                    <tr>
                                        <td><code>/assets/hero.jpg</code></td>
                                        <td><code>/storage/hero.jpg</code></td>
                                        <td><code>image/jpeg</code></td>
                                        <td><span class="badge badge-pass">Supported</span></td>
                                    </tr>
                                    <tr>
                                        <td><code>/assets/style.css</code></td>
                                        <td><code>/storage/style.css</code></td>
                                        <td><code>text/css</code></td>
                                        <td><span class="badge badge-pass">Supported</span></td>
                                    </tr>
                                    <tr>
                                        <td><code>/assets/icon.svg</code></td>
                                        <td><code>/storage/icon.svg</code></td>
                                        <td><code>image/svg+xml</code></td>
                                        <td><span class="badge badge-pass">Supported</span></td>
                                    </tr>
                                </tbody>
                            </table>

                            <h4>2. How to Upload Files to the Beacon:</h4>
                            <ul>
                                <li><b>Method A — Built-in Web Manager:</b> Connect to the beacon's Wi-Fi, open your browser, and navigate to <code class="docs-tag">http://192.168.4.1/upload</code>. Enter your admin password (default <code>12345</code>), select your PDF or image, specify the filename (e.g. <code>menu.pdf</code>), and click Upload.</li>
                                <li><b>Method B — No-Code Visual Builder:</b> In the <i>No-Code Builder</i> tab above, choose your PDF flyer or image. The builder will automatically pack it into your campaign bundle.</li>
                                <li><b>Method C — REST API (cURL):</b> Developers can upload files via terminal using the command below:</li>
                            </ul>

                            <div class="docs-code-block" id="code-curl-upload">
                                <button class="docs-code-copy-btn" onclick="copyCodeSnippet('code-curl-upload')">Copy cURL</button>
# Upload a PDF menu via cURL (connected to PromoBeacon Wi-Fi):
curl -X POST "http://192.168.4.1/upload?name=menu.pdf" \\
     -H "X-Admin-Pwd: 12345" \\
     -H "Content-Type: application/pdf" \\
     --data-binary "@./cardapio.pdf"
                            </div>

                            <div class="docs-callout docs-callout-tip">
                                <b>Media Size Best Practices:</b><br>
                                • Compress PDFs using online tools (SmallPDF, Ghostscript) to keep them between 150 KB and 800 KB for instantaneous downloads.<br>
                                • Convert photos to <b>WebP</b> or JPEG (80% quality, max width 1080px).<br>
                                • Inline small icons as SVGs directly into the HTML to save HTTP requests!
                            </div>
                        </div>
                    </div>
                </div>

                <div class="docs-accordion-item doc-item" id="doc-offline-rule" data-category="assets" data-keywords="offline cdn fonts internet zero external delay timeout linter">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">🚫 The Zero-Dependency Offline Rule (Why External CDNs Fail)</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p><b>CRITICAL:</b> Because the PromoBeacon Wi-Fi is an isolated local network with no internet connection, <b>any external link will FAIL</b>:</p>
                            <ul>
                                <li>❌ <code>&lt;link href="https://fonts.googleapis.com/css2..."&gt;</code> &rarr; <b>Fails</b> (phone will wait 30 seconds for DNS timeout).</li>
                                <li>❌ <code>&lt;script src="https://cdn.jsdelivr.net/..."&gt;</code> &rarr; <b>Fails</b> (script never loads, breaking page layout).</li>
                                <li>❌ <code>&lt;img src="https://mysite.com/photo.jpg"&gt;</code> &rarr; <b>Fails</b> (broken image icon displayed).</li>
                            </ul>
                            
                            <h4>The Native Font Solution:</h4>
                            <p>Use modern native system font stacks. They look beautiful, load in 0.0 milliseconds, and match the user's OS perfectly:</p>
                            <div class="docs-code-block" id="code-font-stack">
                                <button class="docs-code-copy-btn" onclick="copyCodeSnippet('code-font-stack')">Copy CSS</button>
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.5;
    margin: 0;
    padding: 0;
}
                            </div>
                            <p>Use our <b>Verifier & Linter</b> tab to scan your HTML before deployment. It will flag external dependencies and auto-fix them with a single click.</p>
                        </div>
                    </div>
                </div>

                <!-- SECTION 3: CAPTIVE PORTAL & MULTI-OS COMPATIBILITY -->
                <div class="docs-section-title" style="margin-top: 28px;">
                    <span>📡</span> Captive Portal Engine & OS Compatibility
                </div>

                <div class="docs-accordion-item doc-item" id="doc-captive-engine" data-category="captive" data-keywords="captive portal dns wildcard udp 53 cna generate_204 ncsi hotspot detect ios android windows macos">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">⚡ How the Auto-Popup Trigger Works (Android, iOS & Windows)</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>PromoBeacon implements a carrier-grade dual-layer captive detection engine:</p>
                            
                            <h4>1. DNS Wildcard Mirror (UDP Port 53)</h4>
                            <p>The firmware runs an ultra-fast DNS daemon that intercepts all domain name queries (e.g. <code>google.com</code>, <code>apple.com</code>, <code>facebook.com</code>) and immediately answers with the beacon's IP address: <b>192.168.4.1</b>.</p>

                            <h4>2. RFC Multi-OS Probe Interceptors:</h4>
                            <ul>
                                <li><b>Google Android (Android 10 to 14+):</b> Intercepts <code>/generate_204</code>, <code>/gen_204</code>, and RFC 8908 <code>/portal.json</code>. Instead of returning HTTP 204 (No Content), it responds with <b>HTTP 302 Redirect</b> to <code>http://192.168.4.1/</code>, triggering the "Sign in to Wi-Fi" system notification immediately.</li>
                                <li><b>Apple iOS, iPadOS & macOS:</b> Intercepts <code>/hotspot-detect.html</code> and <code>/success.txt</code>. Triggers the native <b>CNA (Captive Network Assistant)</b> full-screen slide-over sheet.</li>
                                <li><b>Microsoft Windows (10 / 11):</b> Intercepts <code>/ncsi.txt</code> and <code>/connecttest.txt</code>, prompting the Windows Action Center network login banner.</li>
                            </ul>

                            <div class="docs-callout docs-callout-info">
                                <b>Why is HTTPS Port 443 Closed (TCP RST)?</b><br>
                                When mobile browsers (Chrome, Safari) test for captive networks, if port 443 is open with a self-signed certificate, the user sees an alarming <i>"Your connection is not private / NET::ERR_CERT_AUTHORITY_INVALID"</i> warning. By deliberately rejecting port 443 with TCP RST, the operating system falls back instantly to HTTP port 80 without any security warnings!
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SECTION 4: GLOBAL REGULATORY DOMAINS -->
                <div class="docs-section-title" style="margin-top: 28px;">
                    <span>🌐</span> Global Regulatory Domains & RF EIRP Power (194 Countries)
                </div>

                <div class="docs-accordion-item doc-item" id="doc-regulatory" data-category="regulatory" data-keywords="regulatory country code fcc ce telec eirp anatel srrc channels 1-11 1-13 power">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">🌍 Regulatory Compliance: FCC, CE, Japan & Anatel Auto-Adaptation</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>Wi-Fi regulations differ across continents. Operating a beacon with incorrect power or forbidden channels can violate telecommunication laws. PromoBeacon features an integrated <b>Regulatory Domain Engine</b> powered by ESP-IDF <code>esp_wifi_set_country()</code>:</p>

                            <table class="docs-table">
                                <thead>
                                    <tr>
                                        <th>Region / Country</th>
                                        <th>Regulatory Body</th>
                                        <th>Country Code</th>
                                        <th>Allowed Channels</th>
                                        <th>Max RF Power</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><b>United States / Canada</b></td>
                                        <td>FCC</td>
                                        <td><code>US</code></td>
                                        <td>Channels 1 – 11</td>
                                        <td>30 dBm (1000 mW)</td>
                                    </tr>
                                    <tr>
                                        <td><b>European Union (CE)</b></td>
                                        <td>ETSI / CE</td>
                                        <td><code>EU</code></td>
                                        <td>Channels 1 – 13</td>
                                        <td>20 dBm (100 mW)</td>
                                    </tr>
                                    <tr>
                                        <td><b>Brazil</b></td>
                                        <td>Anatel</td>
                                        <td><code>BR</code></td>
                                        <td>Channels 1 – 13</td>
                                        <td>30 dBm (1000 mW)</td>
                                    </tr>
                                    <tr>
                                        <td><b>Japan</b></td>
                                        <td>MIC / Telec</td>
                                        <td><code>JP</code></td>
                                        <td>Channels 1 – 14</td>
                                        <td>20 dBm (100 mW)</td>
                                    </tr>
                                    <tr>
                                        <td><b>World Safe (Default)</b></td>
                                        <td>Global Safe Baseline</td>
                                        <td><code>01</code></td>
                                        <td>Channels 1 – 11</td>
                                        <td>20 dBm (CE Safe)</td>
                                    </tr>
                                </tbody>
                            </table>

                            <p><b>How to set your country:</b> Connect to the beacon, visit <code class="docs-tag">http://192.168.4.1/setup</code>, select your country from the dropdown, and click Save. The device re-calibrates its radio transmission power and frequency boundaries instantly.</p>
                        </div>
                    </div>
                </div>

                <!-- SECTION 5: HARDWARE, BATTERY & GOLDEN HOURS -->
                <div class="docs-section-title" style="margin-top: 28px;">
                    <span>🔋</span> Hardware, Battery Sizing & Golden Hours
                </div>

                <div class="docs-accordion-item doc-item" id="doc-battery" data-category="battery" data-keywords="battery power bank mah runtime consumption golden hours scheduling schedule sleep">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">⏱️ Battery Life Calculator & Golden Hours Power Scheduling</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>PromoBeacon can be powered via any standard 5V USB source (wall charger, vehicle USB, solar battery, or portable power bank).</p>

                            <h4>1. Energy Profile & Consumption:</h4>
                            <ul>
                                <li><b>Active Transmission (Clients loading media):</b> ~95 mA to 120 mA</li>
                                <li><b>Idle Beaconing (Broadcasting SSID, waiting):</b> ~22 mA to 35 mA</li>
                                <li><b>Deep Sleep (Scheduled off-hours):</b> &lt; 5 mA</li>
                            </ul>

                            <h4>2. Battery Sizing Matrix:</h4>
                            <table class="docs-table">
                                <thead>
                                    <tr>
                                        <th>USB Power Bank Size</th>
                                        <th>24/7 Continuous Mode</th>
                                        <th>With Golden Hours (8h/day)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><b>Mini 2,500 mAh</b></td>
                                        <td>~24 to 28 hours</td>
                                        <td><b>Up to 3 Days</b></td>
                                    </tr>
                                    <tr>
                                        <td><b>Standard 5,000 mAh</b></td>
                                        <td>~50 to 56 hours</td>
                                        <td><b>Up to 7 Days (1 Week)</b></td>
                                    </tr>
                                    <tr>
                                        <td><b>Heavy Duty 10,000 mAh</b></td>
                                        <td>~100 to 115 hours</td>
                                        <td><b>Up to 14 Days (2 Weeks)</b></td>
                                    </tr>
                                    <tr>
                                        <td><b>AC Wall Adapter (5V 1A)</b></td>
                                        <td>Infinite / Continuous</td>
                                        <td>Infinite / Continuous</td>
                                    </tr>
                                </tbody>
                            </table>

                            <h4>3. Enabling Golden Hours:</h4>
                            <p>In retail stores and restaurants, foot traffic peaks during lunch and dinner. Setting Golden Hours powers down the Wi-Fi radio outside business hours, multiplying battery longevity by up to <b>300%</b>.</p>
                        </div>
                    </div>
                </div>

                <!-- SECTION 6: VISITOR ANALYTICS (/stats.csv) -->
                <div class="docs-section-title" style="margin-top: 28px;">
                    <span>📊</span> Foot-Traffic Analytics & Visitor Metrics
                </div>

                <div class="docs-accordion-item doc-item" id="doc-analytics" data-category="analytics" data-keywords="analytics csv stats metrics foot traffic dwell time visitors export gdpr">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">📈 How to Download and Interpret Visitor Analytics (/stats.csv)</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>Every time a customer connects and views your portal, PromoBeacon anonymously records connection metrics into its internal ring buffer.</p>

                            <h4>Exporting Data:</h4>
                            <p>Connect to the beacon's Wi-Fi and navigate to: <code class="docs-tag">http://192.168.4.1/stats.csv</code></p>
                            <p>A standard CSV file will download immediately. You can open it in <b>Microsoft Excel</b>, <b>Google Sheets</b>, or <b>Apple Numbers</b>.</p>

                            <h4>CSV Data Fields:</h4>
                            <ul>
                                <li><code>device_id</code>: Unique hardware identifier of your PromoBeacon.</li>
                                <li><code>client_count</code>: Total unique smartphones detected during the current session.</li>
                                <li><code>uptime_sec</code>: Number of seconds the beacon has been continuously running.</li>
                                <li><code>mac</code>: Anonymized/hashed client identifier for GDPR and privacy compliance.</li>
                                <li><code>connect_count</code>: Number of times this specific visitor returned to your location.</li>
                                <li><code>session_duration_sec</code>: Dwell time—how long the customer stayed within wireless range.</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- SECTION 7: SECURITY & PASSWORDS -->
                <div class="docs-section-title" style="margin-top: 28px;">
                    <span>🔒</span> Security Architecture & Brute-Force Lockout
                </div>

                <div class="docs-accordion-item doc-item" id="doc-security" data-category="security" data-keywords="security password admin lockout rate limit x-admin-pwd reset factory 12345">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">🛡️ Admin Security & 5-Minute Brute-Force Lockout</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>Because the Wi-Fi network is intentionally open so any customer can view your promotion, the administrative management interfaces (<code>/setup</code>, <code>/upload</code>, <code>/update</code>) are fortified with industrial security measures:</p>

                            <h4>1. Dedicated Admin Password</h4>
                            <p>Only authorized owners can change settings or upload files. The default password is <code class="docs-tag">12345</code>. We strongly advise changing this in <i>/setup</i> during deployment.</p>

                            <h4>2. Automated Brute-Force Protection (Rate Limiter)</h4>
                            <p>If an attacker attempts to guess passwords, the firmware enforces strict rate limiting:</p>
                            <ul>
                                <li><b>Failed Attempt Threshold:</b> 5 consecutive incorrect passwords.</li>
                                <li><b>Security Response:</b> The server issues an <code>HTTP 429 Too Many Requests</code> and locks all administrative routes for <b>5 minutes</b>.</li>
                                <li><b>Customer Portal Integrity:</b> During the lockout, the public promotional landing page continues serving customers without any interruption.</li>
                            </ul>

                            <div class="docs-callout docs-callout-info">
                                <b>Forgot your Admin Password?</b><br>
                                Simply reconnect the ESP32 to your PC via USB and reflash using this web installer with the <i>"Erase Device"</i> option checked. It will restore factory defaults in under 30 seconds.
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SECTION 8: DEVELOPER REST API & CURL -->
                <div class="docs-section-title" style="margin-top: 28px;">
                    <span>💻</span> Developer REST API & cURL Reference
                </div>

                <div class="docs-accordion-item doc-item" id="doc-api" data-category="api" data-keywords="api curl rest json endpoints post get http developer automation">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">⚡ HTTP Endpoints & Automated Scripting Reference</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>PromoBeacon can be completely automated through simple HTTP requests while connected to its Wi-Fi network:</p>

                            <table class="docs-table">
                                <thead>
                                    <tr>
                                        <th>Endpoint</th>
                                        <th>Method</th>
                                        <th>Auth Header</th>
                                        <th>Description</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><code>/</code></td>
                                        <td>GET</td>
                                        <td>None</td>
                                        <td>Serves the active promotional landing page.</td>
                                    </tr>
                                    <tr>
                                        <td><code>/assets/{filename}</code></td>
                                        <td>GET</td>
                                        <td>None</td>
                                        <td>Streams static assets (PDFs, images, CSS) from BigStorage.</td>
                                    </tr>
                                    <tr>
                                        <td><code>/setup</code></td>
                                        <td>POST</td>
                                        <td><code>X-Admin-Pwd</code></td>
                                        <td>Updates SSID, Promo Title, Country Code, and Admin Password.</td>
                                    </tr>
                                    <tr>
                                        <td><code>/upload?name={file}</code></td>
                                        <td>POST</td>
                                        <td><code>X-Admin-Pwd</code></td>
                                        <td>Binary streaming upload directly into SPIFFS flash.</td>
                                    </tr>
                                    <tr>
                                        <td><code>/update</code></td>
                                        <td>POST</td>
                                        <td><code>X-Admin-Pwd</code></td>
                                        <td>Over-The-Air (OTA) firmware binary update.</td>
                                    </tr>
                                    <tr>
                                        <td><code>/stats.csv</code></td>
                                        <td>GET</td>
                                        <td>None</td>
                                        <td>Downloads visitor analytics CSV.</td>
                                    </tr>
                                    <tr>
                                        <td><code>/portal.json</code></td>
                                        <td>GET</td>
                                        <td>None</td>
                                        <td>RFC 8908 Captive Portal JSON status API.</td>
                                    </tr>
                                </tbody>
                            </table>

                            <h4>Example: Change SSID via cURL:</h4>
                            <div class="docs-code-block" id="code-curl-setup">
                                <button class="docs-code-copy-btn" onclick="copyCodeSnippet('code-curl-setup')">Copy cURL</button>
curl -X POST "http://192.168.4.1/setup" \\
     -H "X-Admin-Pwd: 12345" \\
     -H "Content-Type: application/x-www-form-urlencoded" \\
     -d "promo_text=PROMOBEACON_STORE&wifi_pwd=&admin_pwd=12345&country_code=US"
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SECTION 9: COMPREHENSIVE FAQ -->
                <div class="docs-section-title" style="margin-top: 28px;">
                    <span>❓</span> Frequently Asked Questions (FAQ)
                </div>

                <div class="docs-accordion-item doc-item" data-category="faq" data-keywords="faq internet sim card monthly fee subscription cost cloud">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">Does PromoBeacon require an internet connection, SIM card, or monthly subscription?</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p><b>No.</b> PromoBeacon is 100% standalone and autonomous. It creates its own hyper-local micro-network. There are no monthly fees, no SIM cards, no cloud servers, and no external subscriptions ever required.</p>
                        </div>
                    </div>
                </div>

                <div class="docs-accordion-item doc-item" data-category="faq" data-keywords="faq multiple users simultaneous connections capacity limits">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">How many customers can connect to a single beacon simultaneously?</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>An ESP32 AP comfortably handles <b>8 to 10 active concurrent connections</b> downloading files at the exact same second. Because users typically view the menu or coupon for 30–60 seconds and disconnect, a single PromoBeacon effortlessly reaches <b>thousands of visitors per day</b> in busy commercial venues.</p>
                        </div>
                    </div>
                </div>

                <div class="docs-accordion-item doc-item" data-category="faq" data-keywords="faq range distance coverage meters feet antenna">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">What is the effective broadcast range of the beacon?</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>With standard PCB onboard antennas, effective range is <b>60 to 100 meters (200 to 320 feet)</b> in direct line of sight, and <b>20 to 35 meters</b> through indoor brick or concrete walls. Using an external SMA antenna model extends line-of-sight range beyond 150 meters.</p>
                        </div>
                    </div>
                </div>

                <div class="docs-accordion-item doc-item" data-category="faq" data-keywords="faq android warning internet not available keep connection">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">Why does Android show "Wi-Fi has no internet access"? Is that normal?</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p><b>Yes, this is completely normal and expected.</b> Modern mobile operating systems detect that PromoBeacon is a dedicated captive marketing portal without an outbound internet gateway. When prompted with <i>"Wi-Fi has no internet access. Tap to view options"</i>, simply tap <b>"Keep Wi-Fi connection"</b> to browse the local digital content.</p>
                        </div>
                    </div>
                </div>

                <div class="docs-accordion-item doc-item" data-category="faq" data-keywords="faq multiple beacons same location interference cluster">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">Can I place multiple PromoBeacons in the same store or venue?</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p><b>Yes!</b> You can deploy a beacon cluster. For example: one beacon at the entrance broadcasting <i>"WELCOME_COUPON"</i>, and another in the bar area broadcasting <i>"DRINKS_MENU"</i>. To avoid RF channel congestion, configure them on non-overlapping Wi-Fi channels (Channels 1, 6, and 11).</p>
                        </div>
                    </div>
                </div>

                <div class="docs-accordion-item doc-item" data-category="faq" data-keywords="faq ios cna sheet auto close cancel done">
                    <div class="docs-accordion-header" onclick="toggleAccordion(this)">
                        <span class="docs-accordion-title">How does Apple iPhone / iPad handle the captive popup?</span>
                        <span class="docs-accordion-chevron">▼</span>
                    </div>
                    <div class="docs-accordion-body">
                        <div class="docs-content">
                            <p>When an iOS device joins the beacon, Apple's <b>Captive Network Assistant (CNA)</b> automatically slides up from the bottom of the screen, displaying your landing page instantly in full screen without requiring the user to open Safari.</p>
                        </div>
                    </div>
                </div>

                <!-- SAMPLE TEMPLATE SNIPPET FOR COPYING -->
                <div style="display: none;" id="code-asset-example">
&lt;!DOCTYPE html&gt;
&lt;html lang="en"&gt;
&lt;head&gt;
    &lt;meta charset="UTF-8"&gt;
    &lt;meta name="viewport" content="width=device-width, initial-scale=1.0"&gt;
    &lt;title&gt;My Restaurant&lt;/title&gt;
    &lt;style&gt;
        body { font-family: -apple-system, sans-serif; text-align: center; background: #0f172a; color: #fff; padding: 24px; }
        .logo { max-width: 160px; margin-bottom: 20px; }
        .btn { display: inline-block; background: #6366f1; color: white; padding: 14px 28px; border-radius: 12px; text-decoration: none; font-weight: bold; margin-top: 16px; }
    &lt;/style&gt;
&lt;/head&gt;
&lt;body&gt;
    &lt;!-- Notice all local files are referenced via /assets/ --&gt;
    &lt;img src="/assets/logo.png" class="logo" alt="Logo"&gt;
    &lt;h1&gt;Welcome to Our Lounge&lt;/h1&gt;
    &lt;p&gt;View our seasonal menu directly on your smartphone:&lt;/p&gt;
    &lt;a href="/assets/menu.pdf" class="btn"&gt;📄 Open PDF Menu&lt;/a&gt;
&lt;/body&gt;
&lt;/html&gt;
                </div>

            </div>
        </div>
"""

if 'id="tab-docs"' not in content:
    content = content.replace(
        """    <div class="footer">
        PromoBeacon Suite v2.2.0 • Compatible with entire ESP32, S3, and C3 Fleet • BigStorage 2.7MB Enabled
    </div>""",
        docs_panel + """
    <div class="footer">
        PromoBeacon Suite v2.2.0 • Compatible with entire ESP32, S3, and C3 Fleet • BigStorage 2.7MB Enabled
    </div>"""
    )

# 4. Add Interactive JavaScript for Search, Filter & Accordions
docs_js = """
        // TAB 4: Documentation Interactive Controls
        function toggleAccordion(header) {
            const item = header.parentElement;
            const isOpen = item.classList.contains('open');
            // Close other accordions in the same section if desired, or toggle
            item.classList.toggle('open');
        }

        function openAccordion(id) {
            const item = document.getElementById(id);
            if (item) {
                item.classList.add('open');
                item.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }

        function filterDocs() {
            const query = document.getElementById('docs-search').value.toLowerCase().trim();
            const items = document.querySelectorAll('.doc-item');
            const activeChip = document.querySelector('.docs-chip.active');
            const currentCat = activeChip ? activeChip.getAttribute('onclick').match(/'([^']+)'/)[1] : 'all';

            items.forEach(item => {
                const cat = item.getAttribute('data-category');
                const keywords = (item.getAttribute('data-keywords') || '').toLowerCase();
                const text = item.innerText.toLowerCase();

                const matchesCat = (currentCat === 'all' || cat === currentCat);
                const matchesQuery = (!query || text.includes(query) || keywords.includes(query));

                if (matchesCat && matchesQuery) {
                    item.style.display = 'block';
                    if (query.length > 2 && item.classList.contains('docs-accordion-item')) {
                        item.classList.add('open'); // Auto expand matching results
                    }
                } else {
                    item.style.display = 'none';
                }
            });
        }

        function setDocFilter(category) {
            document.querySelectorAll('.docs-chip').forEach(c => c.classList.remove('active'));
            const chip = Array.from(document.querySelectorAll('.docs-chip')).find(c => c.getAttribute('onclick').includes(`'${category}'`));
            if (chip) chip.classList.add('active');
            filterDocs();
        }

        function copyCodeSnippet(id) {
            const el = document.getElementById(id);
            if (!el) return;
            // Extract text without the copy button text
            let text = el.innerText.replace('Copy cURL', '').replace('Copy CSS', '').trim();
            navigator.clipboard.writeText(text).then(() => {
                alert('📋 Code snippet copied to clipboard!');
            }).catch(() => {
                prompt('Copy snippet:', text);
            });
        }
"""

if 'function toggleAccordion' not in content:
    content = content.replace(
        "// Initial preview render and Color Wheel setup on load",
        docs_js + "\n        // Initial preview render and Color Wheel setup on load"
    )

INDEX_PATH.write_text(content, encoding="utf-8")
print("SUCCESS: Comprehensive Documentation & Help Center injected into web_installer/index.html")
print(f"Total file size: {len(content)} characters")
