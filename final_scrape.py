import sys
import re
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data = []
        self.current_tag = ''
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.attrs = dict(attrs)
    def handle_data(self, data):
        if data.strip():
            self.data.append((self.current_tag, data.strip(), self.attrs.copy()))

def fetch(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    try:
        resp = urlopen(req, timeout=20)
        return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Failed to fetch {url}: {e}", file=sys.stderr)
        return None

def extract_price(text):
    # Find all price patterns
    price_pattern = r'(\d+[.,]\d{2})\s*€'
    matches = re.findall(price_pattern, text)
    prices = []
    for m in matches:
        try:
            price = float(m.replace(',', '.'))
            prices.append(price)
        except:
            pass
    if not prices:
        return None
    # If there are two prices and the second is lower, assume it's the discounted price
    # Also look for context like "(Poupa" or "desconto"
    lower_text = text.lower()
    if len(prices) >= 2:
        # Check if there's a discount indicator between the two prices?
        # We'll just take the minimum price as a heuristic
        return min(prices)
    else:
        return prices[0]

def extract_name(text):
    parser = MyHTMLParser()
    parser.feed(text)
    # Look for h1
    for tag, data, attrs in parser.data:
        if tag == 'h1':
            return data[:200]
    # Fallback to title
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', text, re.IGNORECASE)
    if title_match:
        return title_match.group(1).strip()[:200]
    return "Produto"

def extract_sizes(text):
    # Look for the Disponibilidade section
    # We'll try to find the line with "Disponibilidade" and then collect the following numeric lines until we hit non-numeric or a label like "Cor"
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
                # Consider it a size if it's in a reasonable range for children's shoes
                num = int(stripped)
                if 20 <= num <= 40:
                    sizes.append(stripped)
            else:
                # If we hit a non-empty line that's not a digit, stop capturing
                if stripped:
                    break
    return sizes

def extract_store(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if 'calcadoguimaraes' in host:
        return 'Calçado Guimarães'
    return host

def main():
    listing_url = 'https://www.calcadoguimaraes.pt/catalogo/crianca/tenis-lifestyle_4427.html'
    print(f"Fetching listing: {listing_url}", file=sys.stderr)
    listing_html = fetch(listing_url)
    if not listing_html:
        print("Failed to fetch listing page", file=sys.stderr)
        sys.exit(1)
    
    # Extract product links from the listing
    # Look for hrefs that contain '/produto/' and end with .html
    link_pattern = r'href=["\']([^"\']*\/produto\/[^"\']*\.html)["\']'
    product_urls = set(re.findall(link_pattern, listing_html, re.IGNORECASE))
    # Make absolute URLs
    abs_urls = set()
    for url in product_urls:
        if url.startswith('http'):
            abs_urls.add(url)
        else:
            if url.startswith('/'):
                abs_urls.add('https://www.calcadoguimaraes.pt' + url)
            else:
                abs_urls.add('https://www.calcadoguimaraes.pt/' + url)
    
    print(f"Found {len(abs_urls)} product URLs", file=sys.stderr)
    
    results = []
    for url in list(abs_urls)[:50]:  # limit to first 50
        print(f"Processing product: {url}", file=sys.stderr)
        html = fetch(url)
        if not html:
            continue
        price = extract_price(html)
        if price is None or price > 20:
            continue
        name = extract_name(html)
        sizes = extract_sizes(html)
        # Filter sizes for our ranges: 32-34 (7 anos) and 36-38 (10 anos)
        target_sizes = [s for s in sizes if s in ['32','33','34','36','37','38']]
        if not target_sizes:
            continue
        store = extract_store(url)
        clean_url = url.split('?')[0]
        results.append({
            'price': price,
            'name': name,
            'sizes': target_sizes,
            'store': store,
            'url': clean_url
        })
    
    # Sort by price
    results.sort(key=lambda x: x['price'])
    
    # Output report
    print("Pechinchas de ténis infantil em Portugal (preço verificado ≤ €20, tamanhos adequados):")
    print("(Priorizando tamanhos 32-34 para 7 anos e 36-38 para 10 anos)")
    for i, r in enumerate(results[:15], 1):
        sizes_str = '/'.join(r['sizes'])
        print(f"{i}. {r['name']} (tam {sizes_str}) - {r['price']:.2f}€ - {r['store']} - {r['url']}")
    if not results:
        print("Nenhuma oferta relevante encontrada com preço verificado ≤ €20 e tamanhos adequados.")

if __name__ == '__main__':
    main()