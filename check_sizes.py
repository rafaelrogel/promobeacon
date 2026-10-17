import sys
import re
from urllib.request import urlopen, Request

def fetch(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = urlopen(req, timeout=10)
        return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Failed to fetch {url}: {e}", file=sys.stderr)
        return None

def extract_price(text):
    price_pattern = r'(\d+[.,]\d{2})\s*€'
    matches = re.findall(price_pattern, text)
    prices = []
    for m in matches:
        try:
            prices.append(float(m.replace(',', '.')))
        except:
            pass
    if not prices:
        return None
    return min(prices) if len(prices) >= 2 else prices[0]

def extract_sizes(text):
    lines = text.split('\n')
    sizes = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if 'Disponibilidade' in stripped:
            capture = True
            continue
        if capture:
            if stripped.isdigit():
                num = int(stripped)
                if 20 <= num <= 40:
                    sizes.append(stripped)
            else:
                if stripped:
                    break
    return sizes

def extract_name(text):
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', text, re.IGNORECASE)
    if title_match:
        return title_match.group(1).strip()[:200]
    return "Produto"

products = [
    ('https://www.calcadoguimaraes.pt/catalogo/crianca/tenis-lifestyle/produto/cg-ref-007250_151103007250.html', 'CG Ref 007250'),
    ('https://www.calcadoguimaraes.pt/catalogo/crianca/tenis-lifestyle/produto/lilo-stich-ref-000359_144003000359.html', 'Lilo & Stitch Ref 000359'),
    ('https://www.calcadoguimaraes.pt/catalogo/crianca/tenis-lifestyle/produto/cg-ref-000133_151103000133.html', 'CG Ref 000133'),
    ('https://www.calcadoguimaraes.pt/catalogo/crianca/tenis-lifestyle/produto/sonic-ref-001123_144003001123.html', 'Sonic Ref 001123'),
    ('https://www.calcadoguimaraes.pt/catalogo/crianca/tenis-lifestyle/produto/cg-ref-025673_151103025673.html', 'CG Ref 025673'),
]

for url, name in products:
    print(f"\n{name}: {url}")
    html = fetch(url)
    if not html:
        print("  Failed to fetch")
        continue
    price = extract_price(html)
    sizes = extract_sizes(html)
    pname = extract_name(html)
    print(f"  Price: {price}€")
    print(f"  Sizes: {sizes}")
    print(f"  Name: {pname[:50]}")