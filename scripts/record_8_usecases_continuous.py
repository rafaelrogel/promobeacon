import os
import time
import subprocess
from playwright.sync_api import sync_playwright

ASSETS_DIR = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\usecase_assets"
RECORDINGS_DIR = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\recordings"
FINAL_MP4 = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\8_usecases_full_flow.mp4"
WEB_MP4 = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\web_installer\8_usecases_full_flow.mp4"

os.makedirs(RECORDINGS_DIR, exist_ok=True)

usecases = [
    {
        "id": 1,
        "category": "FOOD & BEVERAGE",
        "title": "Bella Napoli Pizzeria",
        "ssid": "Bella_Napoli_Pizza",
        "theme_selector": "text=Hot Pizzeria",
        "theme_selector": ".tpl-chip:has-text('Hot Pizzeria')",
        "headline": "Artisanal Wood-Fired Pizza & 20% OFF Lunch",
        "desc": "Welcome to Bella Napoli! Browse our authentic Italian wood-fired pizza menu and show this screen to your server for 20% off your bill.",
        "image": os.path.join(ASSETS_DIR, "case1_pizzeria.png"),
        "btn1_text": "🍕 Download Pizza Menu (PDF)",
        "btn1_url": "#menu-download"
    },
    {
        "id": 2,
        "category": "HOSPITALITY & LUXURY",
        "title": "Reserva Imperial Resort",
        "ssid": "Reserva_Imperial_VIP",
        "theme_selector": ".tpl-chip:has-text('Royal Luxury')",
        "headline": "Exclusive 5-Star Stay & Holistic Spa Treatments",
        "desc": "Welcome honored guest. Connect seamlessly to our high-speed guest network, explore poolside cocktails, and reserve private spa services.",
        "image": os.path.join(ASSETS_DIR, "case2_luxury.png"),
        "btn1_text": "⚜️ Spa & Wellness Catalog (PDF)",
        "btn1_url": "#spa-catalog"
    },
    {
        "id": 3,
        "category": "MEMORIAL & RESPECT",
        "title": "Memorial Parque da Paz",
        "ssid": "Memorial_Parque_Paz",
        "theme_selector": ".tpl-chip:has-text('Solemn / Serene')",
        "headline": "Cerimonias, Homenagens & Apoio Familiar",
        "desc": "Um ambiente de serenidade e respeito. Consulte a programacao das homenagens, mapa do memorial e suporte ao visitante.",
        "image": os.path.join(ASSETS_DIR, "case3_memorial.png"),
        "btn1_text": "🕊️ Horarios das Cerimonias (PDF)",
        "btn1_url": "#cerimonias"
    },
    {
        "id": 4,
        "category": "HEALTH & MEDICAL",
        "title": "Clinica Odonto Mendes",
        "ssid": "Odonto_Mendes_WiFi",
        "theme_selector": ".tpl-chip:has-text('Emerald Garden')",
        "headline": "Clareamento a Laser & Harmonizacao Facial",
        "desc": "Bem-vindo a nossa recepcao. Conecte-se e veja nossa tabela de procedimentos ortodonticos, esteticos e condicoes especiais.",
        "image": os.path.join(ASSETS_DIR, "case4_dental.png"),
        "btn1_text": "🦷 Catalogo de Procedimentos (PDF)",
        "btn1_url": "#procedimentos"
    },
    {
        "id": 5,
        "category": "SPORTS & FITNESS",
        "title": "IronGym Fitness Club",
        "ssid": "IronGym_Free_WiFi",
        "theme_selector": ".tpl-chip:has-text('Hot Pizzeria')",
        "headline": "Crossfit, Musculacao & Spinning 24 Horas",
        "desc": "Bem-vindo a comunidade IronGym! Confira o quadro de aulas de hoje (WOD do dia), conheca os planos e ganhe 3 dias de passe livre.",
        "image": os.path.join(ASSETS_DIR, "case5_gym.png"),
        "btn1_text": "💪 Grade de Horarios & WOD (PDF)",
        "btn1_url": "#wod"
    },
    {
        "id": 6,
        "category": "BARBERSHOP & LIFESTYLE",
        "title": "Vintage Barbershop Co",
        "ssid": "Vintage_Barbershop_VIP",
        "theme_selector": ".tpl-chip:has-text('Hot Pizzeria')",
        "headline": "Corte Classico, Barba na Toalha Quente & Chopp",
        "desc": "Enquanto aguarda sua vez no sofa de couro, confira o cardapio do nosso bar artesanal e escolha seu estilo no lookbook.",
        "image": os.path.join(ASSETS_DIR, "case6_barber.png"),
        "btn1_text": "✂️ Tabela de Servicos & Estilos",
        "btn1_url": "#servicos"
    },
    {
        "id": 7,
        "category": "ARTISAN BAKERY & CAFE",
        "title": "Padaria Pao de Ouro",
        "ssid": "Pao_de_Ouro_WiFi",
        "theme_selector": ".tpl-chip:has-text('Hot Pizzeria')",
        "headline": "Fornos a Lenha, Paes Artesanais & Cafes",
        "desc": "Sinta o aroma do cafe recem passado e pao quentinho saindo a todo momento. Confira nossa tabela de fornadas do dia.",
        "image": os.path.join(ASSETS_DIR, "case7_bakery.png"),
        "btn1_text": "🥐 Tabela de Fornadas & Cafes (PDF)",
        "btn1_url": "#fornadas"
    },
    {
        "id": 8,
        "category": "CYBERPUNK DINING",
        "title": "Tokyo Cyber Ramen",
        "ssid": "Tokyo_Cyber_Ramen",
        "theme_selector": ".tpl-chip:has-text('Cyberpunk')",
        "headline": "Authentic Tonkotsu Ramen & Neon Arcade Cocktails",
        "desc": "Welcome to the future of Tokyo street dining. Download our secret craft cocktail list or scan for unlimited gyoza perks.",
        "image": os.path.join(ASSETS_DIR, "case8_ramen.png"),
        "btn1_text": "🍜 Secret Ramen & Cocktails Menu",
        "btn1_url": "#secret-menu"
    }
]

def show_overlay_banner(page, step_text, detail_text, duration_sec=2.5):
    page.evaluate("""({step, detail}) => {
        let el = document.getElementById('demo-overlay-banner');
        if (!el) {
            el = document.createElement('div');
            el.id = 'demo-overlay-banner';
            el.style.position = 'fixed';
            el.style.top = '24px';
            el.style.left = '50%';
            el.style.transform = 'translateX(-50%)';
            el.style.background = 'linear-gradient(135deg, rgba(30, 27, 75, 0.95), rgba(15, 23, 42, 0.95))';
            el.style.border = '2px solid #818cf8';
            el.style.boxShadow = '0 20px 40px rgba(0,0,0,0.8), 0 0 25px rgba(99,102,241,0.5)';
            el.style.borderRadius = '16px';
            el.style.padding = '14px 28px';
            el.style.zIndex = '999999';
            el.style.textAlign = 'center';
            el.style.color = '#ffffff';
            el.style.fontFamily = 'system-ui, -apple-system, sans-serif';
            el.style.backdropFilter = 'blur(12px)';
            el.style.transition = 'all 0.3s ease';
            document.body.appendChild(el);
        }
        el.innerHTML = `
            <div style="font-size: 0.85rem; font-weight: 800; letter-spacing: 1.5px; color: #38bdf8; text-transform: uppercase;">${step}</div>
            <div style="font-size: 1.15rem; font-weight: 700; color: #ffffff; margin-top: 4px;">${detail}</div>
        `;
        el.style.display = 'block';
        el.style.opacity = '1';
    }""", {"step": step_text, "detail": detail_text})
    time.sleep(duration_sec)

def hide_overlay_banner(page):
    page.evaluate("""() => {
        let el = document.getElementById('demo-overlay-banner');
        if (el) el.style.opacity = '0';
    }""")

def smooth_type(page, selector, text):
    page.click(selector)
    page.fill(selector, "")
    for char in text:
        page.type(selector, char, delay=15)
        time.sleep(0.01)

def run():
    print("=== Starting Full-Flow Continuous Video Recording (8 Use Cases) ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir=RECORDINGS_DIR,
            record_video_size={"width": 1600, "height": 900},
            viewport={"width": 1600, "height": 900}
        )
        page = context.new_page()
        page.goto("http://localhost:8055")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # 1. VIRGIN PROMOBEACON STATE INTRO
        show_overlay_banner(page, "STAGE 1 - HARDWARE ONBOARDING", "PromoBeacon Out-of-the-Box: Factory Fresh & Ready", duration_sec=3)
        page.evaluate("switchTab('flasher')")
        time.sleep(2)

        # 2. ITERATE OVER 8 USE CASES
        for case in usecases:
            cid = case["id"]
            cat = case["category"]
            title = case["title"]
            ssid = case["ssid"]
            print(f"\n>>> Recording Case {cid}/8: {title} ({cat}) <<<")

            # Banner intro for case
            show_overlay_banner(page, f"CASE {cid}/8: {cat}", f"{title} - Hotspot & Captive Portal Setup", duration_sec=2.5)

            # Switch to No-Code Builder
            page.evaluate("switchTab('builder')")
            time.sleep(0.8)

            # Pick Theme Chip
            chip = page.locator(case["theme_selector"]).first
            if chip.is_visible():
                chip.click()
                time.sleep(0.8)

            # Title
            smooth_type(page, "#cfg-title", title)
            time.sleep(0.5)

            # SSID
            smooth_type(page, "#cfg-ssid", ssid)
            time.sleep(0.5)

            # Headline / Catchphrase
            smooth_type(page, "#cfg-subtitle", case["headline"])
            time.sleep(0.5)

            # Description
            smooth_type(page, "#cfg-desc", case["desc"])
            time.sleep(0.5)

            # Buttons
            smooth_type(page, "#cfg-btn1-text", case["btn1_text"])
            smooth_type(page, "#cfg-btn1-url", case["btn1_url"])
            time.sleep(0.5)

            # Upload Real Image File
            if os.path.exists(case["image"]):
                print(f"  Uploading image: {case['image']}")
                page.set_input_files("#cfg-img-file", case["image"])
                time.sleep(1)

            # Check Auto-Fix / Standards Button
            page.evaluate("updateSsidValidation()")
            time.sleep(1)

            # Scroll phone preview to demonstrate live reactive captive portal
            show_overlay_banner(page, f"HOTSPOT CONCLUDED - IEEE 802.11 VERIFIED", f"SSID: '{ssid}' Broadcast Active | Live Portal Rendered", duration_sec=2)
            time.sleep(1)

            # SIMULATE CLIENT CONNECTING TO HOTSPOT & INTERACTING WITH CAPTIVE PORTAL
            show_overlay_banner(page, f"CLIENT ACCESS SIMULATION", f"Connecting Smartphone to Wi-Fi '{ssid}' -> Captive Portal", duration_sec=2)
            
            # Show interactive full portal popup
            page.evaluate("""() => {
                let html = generatePortalHtml();
                let modal = document.getElementById('demo-portal-modal');
                if (!modal) {
                    modal = document.createElement('div');
                    modal.id = 'demo-portal-modal';
                    modal.style.position = 'fixed';
                    modal.style.top = '0';
                    modal.style.left = '0';
                    modal.style.width = '100vw';
                    modal.style.height = '100vh';
                    modal.style.background = 'rgba(0,0,0,0.85)';
                    modal.style.zIndex = '999998';
                    modal.style.display = 'flex';
                    modal.style.justifyContent = 'center';
                    modal.style.alignItems = 'center';
                    modal.style.backdropFilter = 'blur(8px)';
                    document.body.appendChild(modal);
                }
                modal.innerHTML = `
                    <div style="background:#1e293b; border-radius:24px; padding:16px; border:2px solid #6366f1; width:380px; height:680px; box-shadow:0 25px 60px rgba(0,0,0,0.9); display:flex; flex-direction:column; position:relative;">
                        <div style="display:flex; justify-content:space-between; align-items:center; padding-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.1); margin-bottom:8px;">
                            <span style="font-size:0.75rem; color:#10b981; font-weight:700;">● Wi-Fi Connected: 192.168.4.1</span>
                            <span style="font-size:0.75rem; color:#94a3b8; font-family:monospace;">Hotspot Active</span>
                        </div>
                        <iframe id="modal-portal-frame" style="width:100%; height:100%; border:none; border-radius:12px; background:#0f172a;"></iframe>
                    </div>
                `;
                modal.style.display = 'flex';
                let doc = document.getElementById('modal-portal-frame').contentWindow.document;
                doc.open();
                doc.write(html);
                doc.close();
            }""")
            time.sleep(3)

            # Close modal and return to studio
            page.evaluate("""() => {
                let modal = document.getElementById('demo-portal-modal');
                if (modal) modal.style.display = 'none';
            }""")
            hide_overlay_banner(page)
            time.sleep(1)

        # FINAL OUTRO
        show_overlay_banner(page, "BENCHMARK COMPLETE", "All 8 Hotspots Successfully Built, Verified & Deployed!", duration_sec=3)
        time.sleep(2)

        page.close()
        context.close()
        browser.close()

    print("Browser closed. Locating recorded video file...")
    recorded_files = [os.path.join(RECORDINGS_DIR, f) for f in os.listdir(RECORDINGS_DIR) if f.endswith(".webm")]
    if recorded_files:
        latest_webm = max(recorded_files, key=os.path.getmtime)
        print(f"Converting latest webm: {latest_webm} -> {FINAL_MP4} via ffmpeg...")
        cmd = [
            "ffmpeg", "-y",
            "-i", latest_webm,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            FINAL_MP4
        ]
        subprocess.run(cmd, check=True)
        print(f"SUCCESS: Generated {FINAL_MP4} (Size: {os.path.getsize(FINAL_MP4):,} bytes)")
        
        # Copy to web_installer directory for direct browser viewing
        subprocess.run(["copy", FINAL_MP4, WEB_MP4], shell=True)
        print("Copied to web_installer directory!")
    else:
        print("Error: No recorded webm file found.")

if __name__ == "__main__":
    run()
