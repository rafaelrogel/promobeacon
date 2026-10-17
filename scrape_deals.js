const axios = require('axios');
const cheerio = require('cheerio');
const { URL } = require('url');

// Function to fetch a page and return HTML
async function fetchPage(url) {
  try {
    const response = await axios.get(url, {
      timeout: 10000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    return response.data;
  } catch (error) {
    console.warn(`Failed to fetch ${url}: ${error.message}`);
    return null;
  }
}

// Function to extract price from text (using regex)
function extractPriceFromText(text) {
  const match = text.match(/€\s*([\d,.]+)/);
  if (match) {
    let priceStr = match[1].replace(',', '.');
    // Sometimes there are multiple numbers, we take the first one that looks like a price
    // We'll just return the first match
    return parseFloat(priceStr);
  }
  return null;
}

// Function to extract product name from page
function extractName($) {
  // Try common selectors for product name
  const selectors = [
    'h1',
    '.product-name',
    '.product-title',
    '[data-testid="product-title"]',
    'title'
  ];
  for (const selector of selectors) {
    const text = $(selector).first().text().trim();
    if (text) {
      return text;
    }
  }
  return '';
}

// Function to extract size from text (look for patterns like 32, 33, 34, 35, 36, 37, 38)
function extractSize(text) {
  const match = text.match(/\b(3[2-8])\b/);
  return match ? match[0] : '';
}

// Function to extract store from URL
function extractStore(url) {
  try {
    const hostname = new URL(url).hostname.replace('www.', '');
    return hostname;
  } catch (e) {
    return 'unknown';
  }

}

// Main function
(async () => {
  const sites = [
    {
      name: 'Decathlon',
      url: 'https://www.decathlon.pt/todos-os-desportos/tenis/calcado-de-tenis-crianca',
      productLinkSelector: '.product-link, .product-img-link, a[href*="/p/"]' // Adjust based on site structure
    },
    {
      name: 'Sprinter',
      url: 'https://www.sprintersports.com/pt/calcado/infantil/',
      productLinkSelector: '.product-link, a[href*="/p/"], .product-item a'
    },
    {
      name: 'Lefties',
      url: 'https://www.lefties.com/pt/menino/zapatillas_10200154.html',
      productLinkSelector: '.product-link, a[href*="/product/"], .product-item a'
    }
  ];

  const results = [];

  for (const site of sites) {
    console.log(`Fetching ${site.name}...`);
    const html = await fetchPage(site.url);
    if (!html) {
      continue;
    }

    const $ = cheerio.load(html);
    const productLinks = [];

    $(site.productLinkSelector).each((_, element) => {
      const href = $(element).attr('href');
      if (href) {
        let fullUrl;
        try {
          fullUrl = new URL(href, site.url).toString();
        } catch (e) {
          // If URL is invalid, skip
          return;
        }
        // Avoid duplicates and ensure it's a product link (basic check)
        if (fullUrl && !productLinks.includes(fullUrl) && fullUrl.length > 10) {
          productLinks.push(fullUrl);
        }
      }
    });

    // Limit to 5 product links per site
    for (const productUrl of productLinks.slice(0, 5)) {
      console.log(`  Checking product: ${productUrl}`);
      const productHtml = await fetchPage(productUrl);
      if (!productHtml) {
        continue;
      }

      const $$ = cheerio.load(productHtml);
      const price = extractPriceFromText($$.html());
      if (price === null || price > 20) {
        console.log(`    Price ${price} > 20 or not found, skipping`);
        continue;
      }

      const name = extractName($$);
      const size = extractSize($$.text() + ' ' + name);
      const store = extractStore(productUrl);

      results.push({
        price: price.toFixed(2),
        name: name.length > 50 ? name.substring(0, 47) + '...' : name,
        size: size || 'N/A',
        store: store,
        url: productUrl
      });

      // Break if we have enough results (say 10 total)
      if (results.length >= 10) {
        break;
      }
    }

    if (results.length >= 10) {
      break;
    }
  }

  // Output the report in pt-BR, ≤ 15 lines
  if (results.length === 0) {
    console.log('Nenhuma pechincha relevante encontrada.');
  } else {
    console.log('Pechinchas de ténis infantil em Portugal:');
    results.forEach((item, index) => {
      console.log(`${index + 1}. ${item.name} - ${item.price}€ - Tamanho: ${item.size} - Loja: ${item.store} - Link: ${item.url}`);
    });
  }
})();