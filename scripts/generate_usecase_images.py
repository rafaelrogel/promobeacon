import os
import shutil
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\usecase_assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

# 1. Pizzeria
src_pizzaria = r"C:\Users\rafae\.gemini\antigravity\brain\f49a2c98-5197-4c94-878c-80702aad8330\pizzaria.png"
if os.path.exists(src_pizzaria):
    shutil.copy(src_pizzaria, os.path.join(ASSETS_DIR, "case1_pizzeria.png"))

# 2. Reserva Imperial
src_luxury = r"C:\Users\rafae\.gemini\antigravity\brain\f49a2c98-5197-4c94-878c-80702aad8330\reserva_imperial.png"
if os.path.exists(src_luxury):
    shutil.copy(src_luxury, os.path.join(ASSETS_DIR, "case2_luxury.png"))

# 3. Funeral / Memorial
src_funeral = r"C:\Users\rafae\.gemini\antigravity\brain\f49a2c98-5197-4c94-878c-80702aad8330\funeraria.png"
if os.path.exists(src_funeral):
    shutil.copy(src_funeral, os.path.join(ASSETS_DIR, "case3_memorial.png"))

def create_banner(filename, bg_color1, bg_color2, icon_text, title_text, sub_text):
    w, h = 600, 360
    img = Image.new('RGB', (w, h), color=bg_color1)
    draw = ImageDraw.Draw(img)
    
    # Gradient background
    for y in range(h):
        r = int(bg_color1[0] + (bg_color2[0] - bg_color1[0]) * (y / h))
        g = int(bg_color1[1] + (bg_color2[1] - bg_color1[1]) * (y / h))
        b = int(bg_color1[2] + (bg_color2[2] - bg_color1[2]) * (y / h))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    
    # Border & frame
    draw.rectangle([12, 12, w-13, h-13], outline=(255, 255, 255, 120), width=3)
    draw.rectangle([18, 18, w-19, h-19], outline=(255, 255, 255, 40), width=1)
    
    try:
        font_lg = ImageFont.truetype("arial.ttf", 28)
        font_sm = ImageFont.truetype("arial.ttf", 18)
    except:
        font_lg = ImageFont.load_default()
        font_sm = ImageFont.load_default()
    
    # Text
    draw.text((w//2, 110), icon_text, fill=(255, 255, 255), anchor="mm", font=font_lg)
    draw.text((w//2, 180), title_text, fill=(255, 255, 255), anchor="mm", font=font_lg)
    draw.text((w//2, 230), sub_text, fill=(220, 230, 245), anchor="mm", font=font_sm)
    
    target_path = os.path.join(ASSETS_DIR, filename)
    img.save(target_path)
    print(f"Generated: {target_path}")

# 4. Dental Clinic
create_banner("case4_dental.png", (13, 148, 136), (6, 182, 212), "[+] DENTAL CARE", "CLINICA ODONTO MENDES", "Estetica Dental & Harmonizacao Facial")

# 5. IronGym Fitness
create_banner("case5_gym.png", (234, 88, 12), (249, 115, 22), ">>> FITNESS CLUB <<<", "IRONGYM CROSSFIT & FITNESS", "Treinos de Alta Performance - 24 Horas")

# 6. Vintage Barbershop
create_banner("case6_barber.png", (180, 83, 9), (217, 119, 6), "*** EST. 1984 ***", "VINTAGE BARBERSHOP & CO.", "Cortes Classicos, Barba & Chopp Artesanal")

# 7. Artisan Bakery
create_banner("case7_bakery.png", (194, 65, 12), (234, 88, 12), "~ ARTISAN OVEN ~", "PADARIA & BISTRO PAO D'OURO", "Fornos a Lenha & Paes de Fermentacao Natural")

# 8. Tokyo Cyber Ramen
create_banner("case8_ramen.png", (236, 72, 153), (139, 92, 246), "< TOKYO STREETS >", "TOKYO CYBER RAMEN LOUNGE", "Autentico Tonkotsu Ramen & Neon Arcade")

print("All 8 usecase image assets prepared!")
