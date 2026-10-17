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
    def handle_data(self, data):
        if data.strip():
            self.data.append((self.current_tag, data.strip()))

def fetch(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    try:
        resp = urlopen(req, timeout=15)
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
    if len(prices) >= 2 and prices[1] < prices[0]:
        return prices[1]
    # Otherwise return the first price (or the only one)
    return prices[0]

def extract_name(text):
    # Try to get from <h1>
    parser = MyHTMLParser()
    parser.feed(text)
    for tag, data in parser.data:
        if tag == 'h1':
            return data[:100]
    # Fallback to title
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', text, re.IGNORECASE)
    if title_match:
        return title_match.group(1).strip()[:100]
    return "Produto"

def extract_sizes(text):
    # Look for the Disponibilidade line
    # Example: "Disponibilidade\n\n 25\n\n 26\n\n Lilás"
    # We'll extract numbers that are sizes (likely two-digit numbers)
    # But we need to be careful not to extract other numbers like prices.
    # Look for the line that contains "Disponibilidade" and then get the next lines until a non-number or text.
    lines = text.split('\n')
    sizes = []
    capture = False
    for line in lines:
        if 'Disponibilidade' in line:
            capture = True
            continue
        if capture:
            # If line is empty or contains non-digit (except maybe spaces and comma/dot for other things)
            # We'll assume sizes are integers possibly with leading/trailing spaces
            stripped = line.strip()
            if stripped.isdigit() and 20 <= int(stripped) <= 50:  # reasonable shoe size
                sizes.append(stripped)
            elif stripped and not stripped.replace('.', '').replace(',', '').isdigit():
                # Hit a non-number, stop capturing
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
    # First, get the main listing page
    listing_url = 'https://www.calcadoguimaraes.pt/catalogo/crianca/tenis-lifestyle_4427.html'
    print(f"Fetching listing: {listing_url}", file=sys.stderr)
    listing_html = fetch(listing_url)
    if not listing_html:
        print("Failed to fetch listing page", file=sys.stderr)
        sys.exit(1)
    
    # Extract product links from the listing
    # Pattern: href="/catalogo/crianca/tenis-lifestyle/produto/....html"
    # We'll look for absolute URLs as well
    link_pattern = r'href=["\'](https?://[^"\']*\/produto\/[^"\']*\.html)["\']'
    product_urls = set(re.findall(link_pattern, listing_html, re.IGNORECASE))
    # Also relative links
    rel_pattern = r'href=["\']([^"\']*\/produto\/[^"\']*\.html)["\']'
    rel_urls = re.findall(rel_pattern, listing_html, re.IGNORECASE)
    for rel in rel_urls:
        if rel.startswith('http'):
            product_urls.add(rel)
        else:
            # Make absolute
            if rel.startswith('/'):
                product_urls.add('https://www.calcadoguimaraes.pt' + rel)
            else:
                product_urls.add('https://www.calcadoguimaraes.pt/' + rel)
    
    print(f"Found {len(product_urls)} product URLs", file=sys.stderr)
    
    results = []
    for url in list(product_urls)[:30]:  # limit to first 30 to avoid too many requests
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
            # If no target sizes, maybe still include if we couldn't extract sizes? 
            # For safety, skip if we can't confirm size in range.
            continue
        store = extract_store(url)
        # Clean URL (remove query params)
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