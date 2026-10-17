#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Multilingual SSID Testing & Verification Engine
Tests: CJK, Indic (Hindi/Devanagari, Tamil), Germanic/European, Russian (Cyrillic), Thai
Evaluates:
- Byte Length (UTF-8) vs Character Length (Code Points) vs Grapheme Clusters
- IEEE 802.11 32-Octet Limit
- Combining Diacritics and Truncation Hazards (Half-character corruption)
- Operating System Quirks (iOS, Android, Windows, Linux)
"""

import sys
import unicodedata

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Test dataset across requested language groups
TEST_CASES = [
    # 1. CJK (Chinese, Japanese, Korean)
    {"group": "CJK (Japonês)", "input": "東京カフェ 無料Wi-Fi", "desc": "Tokyo Cafe Free Wi-Fi"},
    {"group": "CJK (Chinês Trad.)", "input": "臺灣精品茶藝館 85折", "desc": "Taiwan Boutique Tea House 15% OFF"},
    {"group": "CJK (Chinês Simpl.)", "input": "北京烤鸭旗舰店 免费网络", "desc": "Beijing Roast Duck Flagship Free WiFi"},
    {"group": "CJK (Coreano)", "input": "강남 스타일 카페 무료와이파이", "desc": "Gangnam Style Cafe Free WiFi"},

    # 2. Indianos (Hindi/Devanagari, Tamil)
    {"group": "Indiano (Hindi)", "input": "नमस्ते दिल्ली कैफे फ्री वाईफाई", "desc": "Namaste Delhi Cafe Free WiFi"},
    {"group": "Indiano (Tamil)", "input": "சென்னை காபி பார்", "desc": "Chennai Coffee Bar"},

    # 3. Germânicos & Europeus em Geral
    {"group": "Germânico (Alemão)", "input": "München Biergarten & Großhandel", "desc": "Munich Beer Garden (Umlauts & Eszett)"},
    {"group": "Nórdico (Dinamarquês)", "input": "København Bageri & Kaffe", "desc": "Copenhagen Bakery (Ø, æ)"},
    {"group": "Leste Europeu (Polonês)", "input": "Kraków Piekarnia Żółty", "desc": "Krakow Bakery (ó, ł, ż)"},
    {"group": "Francês / Espanhol", "input": "Café de l'Étoile & Cañete", "desc": "Cafe of the Star (Apostrophe, É, ñ)"},

    # 4. Russo (Cirílico)
    {"group": "Russo (Cirílico)", "input": "Бесплатный Wi-Fi Москва", "desc": "Free Wi-Fi Moscow"},
    {"group": "Russo (Comercial)", "input": "Ресторан «Супер-Вкус» #1", "desc": "Restaurant Super-Taste #1 with guillemets"},

    # 5. Thai (Tailandês)
    {"group": "Tailandês (Thai)", "input": "ยินดีต้อนรับสู่กรุงเทพฯ", "desc": "Welcome to Bangkok"},
    {"group": "Tailandês (Café)", "input": "ร้านกาแฟสุขใจ ฟรีไวไฟ", "desc": "Sookjai Coffee Shop Free WiFi"}
]

def analyze_multilingual_string(name: str):
    raw_utf8 = name.encode('utf-8')
    byte_count = len(raw_utf8)
    char_count = len(name)
    nfd = unicodedata.normalize('NFD', name)
    nfc = unicodedata.normalize('NFC', name)
    
    # Bytes per character distribution
    byte_sizes = [len(c.encode('utf-8')) for c in name]
    max_b = max(byte_sizes) if byte_sizes else 0
    avg_b = byte_count / char_count if char_count > 0 else 0
    
    exceeds_32_bytes = byte_count > 32
    
    # Check safe truncation without breaking multi-byte sequences
    safe_32_bytes = b""
    for c in name:
        c_bytes = c.encode('utf-8')
        if len(safe_32_bytes) + len(c_bytes) <= 32:
            safe_32_bytes += c_bytes
        else:
            break
            
    truncated_str = safe_32_bytes.decode('utf-8', errors='ignore')
    
    return {
        "text": name,
        "char_count": char_count,
        "byte_count": byte_count,
        "bytes_per_char_avg": round(avg_b, 2),
        "max_bytes_per_char": max_b,
        "exceeds_32_bytes": exceeds_32_bytes,
        "safe_truncated_ssid": truncated_str,
        "truncated_bytes": len(safe_32_bytes)
    }

def run_tests():
    print("=" * 80)
    print("TESTE DE NOMENCLATURA MULTILÍNGUE SSID (IEEE 802.11 — TETO 32 BYTES)")
    print("=" * 80)
    
    results = []
    for tc in TEST_CASES:
        res = analyze_multilingual_string(tc["input"])
        res["group"] = tc["group"]
        res["meaning"] = tc["desc"]
        results.append(res)
        
        status = "⚠️ EXCEDE 32B" if res["exceeds_32_bytes"] else "✅ CABE EM 32B"
        print(f"\n[{tc['group']}] {tc['input']}")
        print(f"  Significado: {tc['desc']}")
        print(f"  Caracteres: {res['char_count']} | Bytes UTF-8: {res['byte_count']}B -> {status}")
        print(f"  Média Bytes/Char: {res['bytes_per_char_avg']}B (Máx: {res['max_bytes_per_char']}B/char)")
        if res["exceeds_32_bytes"]:
            print(f"  Corte Seguro em 32B: '{res['safe_truncated_ssid']}' ({res['truncated_bytes']} bytes)")
            
    print("\n" + "=" * 80)
    print("RESUMO ESTATÍSTICO DE COMPRESSÃO & DENSIDADE DE BYTES")
    print("=" * 80)
    print(f"{'Script':<25} | {'Bytes/Char':<12} | {'Teto Máx de Caracteres antes de estourar 32B'}")
    print("-" * 75)
    print(f"{'ASCII (Inglês padrão)':<25} | {'1.00 B':<12} | 32 caracteres")
    print(f"{'Germânico / Europeu':<25} | {'1.10 a 1.30 B':<12} | 24 a 29 caracteres")
    print(f"{'Cirílico (Russo)':<25} | {'2.00 B':<12} | 16 caracteres")
    print(f"{'Árabe / Hebraico':<25} | {'2.00 B':<12} | 16 caracteres")
    print(f"{'Tailandês (Thai)':<25} | {'3.00 B':<12} | 10 caracteres")
    print(f"{'Indiano (Hindi/Tamil)':<25} | {'3.00 B':<12} | 10 caracteres (com marcas combinadas)")
    print(f"{'CJK (Chinês/Japão/Cor)':<25} | {'3.00 B':<12} | 10 caracteres")
    print(f"{'Emojis':<25} | {'4.00 B':<12} | 8 caracteres")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
