import sys
import re
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

def fetch(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = urlopen(req, timeout=10)
        return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Failed to fetch {url}: {e}", file=sys.stderr)
        return None

def extract_price(text):
    # Look for price patterns like €12,99 or €12.99 or 12,99 € etc.
    patterns = [
        r'€\s*(\d+[.,]\d{2})',
        r'(\d+[.,]\d{2})\s*€',
        r'&euro;\s*(\d+[.,]\d{2})',
        r'(\d+[.,]\d{2})\s*&euro;',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            price_str = m.group(1).replace(',', '.')
            try:
                return float(price_str)
            except:
                pass
    return None

def extract_name(text):
    # Try to get from <title> or <h1>
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', text, re.IGNORECASE)
    if title_match:
        return title_match.group(1).strip()[:100]
    h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', text, re.IGNORECASE)
    if h1_match:
        return h1_match.group(1).strip()[:100]
    return "Produto"

def extract_size(text):
    # Look for patterns like tamanho 32, 33, etc.
    size_match = re.search(r'tamanho\s*(\d{2})', text, re.IGNORECASE)
    if size_match:
        return size_match.group(1)
    # Also look for isolated numbers 32-38 maybe
    size_match2 = re.search(r'\b(3[2-8])\b', text)
    if size_match2:
        return size_match2.group(1)
    return ""

def extract_store(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if 'decathlon' in host:
        return 'Decathlon'
    if 'sprintersports' in host:
        return 'SPRINTER'
    if 'lefties' in host:
        return 'Lefties'
    if 'spartoo' in host:
        return 'Spartoo'
    if 'adidas' in host:
        return 'Adidas'
    if 'jdsports' in host:
        return 'JD Sports'
    if 'sportsdirect' in host:
        return 'Sports Direct'
    if 'lalaut' in host:
        return 'La Redoute'
    if 'calcadoguimaraes' in host:
        return 'Guimarães'
    if 'hm.com' in host:
        return 'H&M'
    if 'newbalance' in host:
        return 'New Balance'
    if 'pisamonas' in host:
        return 'Pisamonas'
    return host

def main():
    # Read URLs from command line or default list
    urls = sys.argv[1:] if len(sys.argv) > 1 else [
        'https://www.decathlon.pt/todos-os-desportos/tenis/calcado-de-tenis-crianca',
        'https://www.spartoo.pt/selecao-tenis-403-criancas.php',
        'https://www.adidas.pt/sapatos-crianca',
        'https://www.jdsports.pt/crianca/c/calcado/',
        'https://www.sportsdirect.pt/tennis/tennis-footwear/kids-tennis-shoes',
        'https://www.laredoute.pt/lndng/ctlg.aspx?artcl=tenis-para-crianca',
        'https://www.calcadoguimaraes.pt/catalogo/crianca/tenis-lifestyle_4427.html',
        'https://www2.hm.com/pt_pt/crianca/comprar-por-produto/sapatos/tenis.html',
        'https://www.newbalance.pt/pt/outlet/crianca/tenis/',
        'https://www.pisamonas.pt/',
    ]
    results = []
    for url in urls:
        print(f"Processing {url}", file=sys.stderr)
        html = fetch(url)
        if not html:
            continue
        price = extract_price(html)
        if price is None or price > 20:
            continue
        name = extract_name(html)
        size = extract_size(html)
        store = extract_store(url)
        # Clean URL: remove utm etc.
        clean_url = url.split('?')[0]  # simple
        results.append({
            'price': price,
            'name': name,
            'size': size,
            'store': store,
            'url': clean_url
        })
    # Sort by price
    results.sort(key=lambda x: x['price'])
    # Output report
    print("Pechinchas de ténis infantil em Portugal (preço verificado ≤ €20):")
    for i, r in enumerate(results[:10], 1):
        size_info = f" (tam {r['size']})" if r['size'] else ""
        print(f"{i}. {r['name']}{size_info} - {r['price']:.2f}€ - {r['store']} - {r['url']}")
    if not results:
        print("Nenhuma oferta relevante encontrada com preço verificado ≤ €20.")

if __name__ == '__main__':
    main()