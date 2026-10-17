#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare Heavy Luxury Real Estate Campaign for PromoBeacon (Filling ~1.8 MB of ESP32 Flash)
"""
import os
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"

def download_and_optimize(url, filename, target_size_kb, dimensions=(1280, 850)):
    print(f"Baixando imagem de alta resolucao para {filename}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw_path = SCRIPTS_DIR / f"raw_{filename}"
    with urllib.request.urlopen(req) as resp, open(raw_path, "wb") as f:
        f.write(resp.read())
    
    img = Image.open(raw_path)
    img = img.convert("RGB")
    img = img.resize(dimensions, Image.Resampling.LANCZOS)
    
    out_path = SCRIPTS_DIR / filename
    quality = 90
    img.save(out_path, "JPEG", quality=quality, optimize=True)
    
    # Adjust quality to meet target size roughly
    cur_size = os.path.getsize(out_path) / 1024
    print(f"-> {filename}: {cur_size:.1f} KB (Qualidade {quality})")
    if raw_path.exists():
        raw_path.unlink()
    return out_path

def create_dossie_pdf(foto1_path, foto2_path, foto3_path):
    print("Gerando Dossie Tecnico Multi-Pagina de Alta Definicao (PDF)...")
    
    # Pagina 1: Capa com Imagem da Fachada e Titulo Dourado
    img1 = Image.open(foto1_path).resize((1200, 800))
    page1 = Image.new("RGB", (1200, 1600), color=(15, 17, 21))
    page1.paste(img1, (0, 350))
    d1 = ImageDraw.Draw(page1)
    d1.rectangle([(0, 0), (1200, 340)], fill=(12, 14, 18))
    d1.rectangle([(0, 335), (1200, 340)], fill=(212, 175, 55))
    d1.text((80, 80), "RESERVA IMPERIAL", fill=(212, 175, 55))
    d1.text((80, 150), "MANSOES SUSPENSAS & PENTHOUSES PANORAMICAS", fill=(255, 255, 255))
    d1.text((80, 220), "DOSSIE DE APRESENTACAO EXCLUSIVA - EDICAO LIMITADA (12 UNIDADES)", fill=(180, 185, 195))
    d1.rectangle([(0, 1160), (1200, 1600)], fill=(18, 20, 25))
    d1.text((80, 1200), "ESPECIFICACOES DO EMPREENDIMENTO:", fill=(212, 175, 55))
    d1.text((80, 1260), "- Area Privativa: 650 m2 a 980 m2 | Pe-direito duplo de 6,20m no living", fill=(220, 220, 220))
    d1.text((80, 1310), "- 5 Suites Master com closets privativos e banheiros em marmore travertino", fill=(220, 220, 220))
    d1.text((80, 1360), "- 6 a 8 Vagas de Garagem Determinadas com ponto de recarga rapida para veiculos eletricos", fill=(220, 220, 220))
    d1.text((80, 1410), "- Heliponto homologado para aeronaves executivas de medio porte", fill=(220, 220, 220))
    d1.text((80, 1460), "- Elevadores biometricos de alta velocidade com acesso social privativo", fill=(220, 220, 220))

    # Pagina 2: Planta Humanizada & Living
    img2 = Image.open(foto2_path).resize((1200, 800))
    page2 = Image.new("RGB", (1200, 1600), color=(20, 22, 28))
    page2.paste(img2, (0, 100))
    d2 = ImageDraw.Draw(page2)
    d2.rectangle([(0, 0), (1200, 95)], fill=(12, 14, 18))
    d2.text((80, 30), "PLANTA HUMANIZADA & LIVING PANORAMICO INTEGRADO", fill=(212, 175, 55))
    
    # Desenho técnico de planta / blueprint
    d2.rectangle([(80, 950), (1120, 1500)], outline=(212, 175, 55), width=3)
    for x in range(130, 1100, 100):
        d2.line([(x, 950), (x, 1500)], fill=(40, 45, 55), width=1)
    for y in range(1000, 1500, 100):
        d2.line([(80, y), (1120, y)], fill=(40, 45, 55), width=1)
    d2.text((120, 980), "[SALAO SOCIAL 180m2]", fill=(212, 175, 55))
    d2.text((500, 980), "[TERRACO GOURMET & SPA 120m2]", fill=(212, 175, 55))
    d2.text((120, 1200), "[SUITE MASTER 85m2 COM BANHEIRA DE IMERSAO]", fill=(212, 175, 55))
    d2.text((650, 1200), "[ADEGA CLIMATIZADA 500 ROTULOS]", fill=(212, 175, 55))

    # Pagina 3: Lazer & Wellness
    img3 = Image.open(foto3_path).resize((1200, 800))
    page3 = Image.new("RGB", (1200, 1600), color=(15, 17, 21))
    page3.paste(img3, (0, 100))
    d3 = ImageDraw.Draw(page3)
    d3.rectangle([(0, 0), (1200, 95)], fill=(12, 14, 18))
    d3.text((80, 30), "INFINITY POOL & COMPLEXO DE SPA EXCLUSIVO", fill=(212, 175, 55))
    d3.rectangle([(0, 920), (1200, 1600)], fill=(12, 14, 18))
    d3.text((80, 960), "SUSTENTABILIDADE E CERTIFICACOES AMBIENTAIS LEED PLATINUM:", fill=(212, 175, 55))
    d3.text((80, 1020), "- Geracao de energia solar fotovoltaica para 100% das areas comuns", fill=(220, 220, 220))
    d3.text((80, 1070), "- Sistema de reuso de aguas pluviais para irrigacao automatizada dos jardins suspensos", fill=(220, 220, 220))
    d3.text((80, 1120), "- Vidros termoacusticos insulados com protecao UV e controle solar de ultima geracao", fill=(220, 220, 220))
    d3.text((80, 1170), "- Isolamento acustico de piso e tubulacoes em conformidade com padroes europeus", fill=(220, 220, 220))
    d3.text((80, 1280), "VALOR GERAL DE VENDAS E CONDICOES:", fill=(212, 175, 55))
    d3.text((80, 1340), "Unidades Tipo (650m2): A partir de R$ 18.500.000,00", fill=(255, 255, 255))
    d3.text((80, 1390), "Penthouses Triplex (980m2): A partir de R$ 34.000.000,00", fill=(255, 255, 255))
    d3.text((80, 1460), "Plantao de Atendimento VIP PromoBeacon: Av. Brigadeiro Faria Lima, 4500", fill=(180, 185, 195))

    pdf_path = SCRIPTS_DIR / "dossie.pdf"
    page1.save(pdf_path, "PDF", resolution=90.0, save_all=True, append_images=[page2, page3])
    print(f"-> dossie.pdf: {os.path.getsize(pdf_path) / 1024:.1f} KB")
    return pdf_path

def main():
    u1 = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=92&w=1440&auto=format&fit=crop"
    u2 = "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?q=92&w=1440&auto=format&fit=crop"
    u3 = "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?q=92&w=1440&auto=format&fit=crop"
    u4 = "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?q=92&w=1440&auto=format&fit=crop"
    
    f1 = download_and_optimize(u1, "foto1.jpg", target_size_kb=450, dimensions=(1440, 960))
    f2 = download_and_optimize(u2, "foto2.jpg", target_size_kb=450, dimensions=(1440, 960))
    f3 = download_and_optimize(u3, "foto3.jpg", target_size_kb=450, dimensions=(1440, 960))
    f4 = download_and_optimize(u4, "foto4.jpg", target_size_kb=450, dimensions=(1440, 960))
    pdf = create_dossie_pdf(f1, f2, f3)
    
    files = [f1, f2, f3, f4, pdf]
    total = sum(os.path.getsize(p) for p in files)
    print(f"\n==========================================")
    print(f"TOTAL DOS ARQUIVOS PESADOS: {total / (1024*1024):.2f} MB ({total:,} bytes)")
    print(f"OCUPACAO DO SPIFFS: ~{(total / 2752512)*100:.1f}% da particao de 2.75 MB")
    print(f"==========================================")

if __name__ == "__main__":
    main()
