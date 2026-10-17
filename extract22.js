const WebSocket = require('ws');
const http = require('http');
const https = require('https');

// Function to fetch the list of pages from Chrome DevTools
function getPages() {
  return new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const pages = JSON.parse(data);
          resolve(pages);
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

// Function to connect to the DevTools WebSocket and evaluate script
function evaluateOnPage(wsUrl, script) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let responseId = 1;

    ws.on('open', () => {
      // Enable Page and Runtime domains
      ws.send(JSON.stringify({ id: responseId++, method: 'Page.enable' }));
      ws.send(JSON.stringify({ id: responseId++, method: 'Runtime.enable' }));

      // Wait for the enable commands to complete, then evaluate
      const enableHandler = (message) => {
        const msg = JSON.parse(message);
        if (msg.id && (msg.id === responseId - 2 || msg.id === responseId - 1)) {
          if (msg.error) {
            reject(new Error(`Failed to enable domain: ${msg.error.message}`));
            ws.close();
            return;
          }
          // After both enables, evaluate
          if (msg.id === responseId - 1) {
            ws.removeListener('message', enableHandler);
            ws.send(JSON.stringify({ id: responseId++, method: 'Runtime.evaluate', params: { expression: script, returnByValue: true } }));
          }
        }
      };

      ws.on('message', enableHandler);

      // Handle the evaluate response
      const evaluateHandler = (message) => {
        const msg = JSON.parse(message);
        if (msg.id && msg.id === responseId - 1) {
          ws.removeListener('message', evaluateHandler);
          ws.close();
          if (msg.error) {
            reject(new Error(`Evaluation error: ${msg.error.message}`));
          } else {
            resolve(msg.result && msg.result.value ? msg.result.value : msg.result);
          }
        }
      };

      ws.on('message', evaluateHandler);
    });

    ws.on('error', (err) => {
      reject(err);
      ws.close();
    });

    ws.on('close', () => {
      // Cleanup listeners if needed
    });
  });
}

// Function to fetch a URL and return text (using https)
function fetchUrl(url) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith('https') ? https : http;
    const request = lib.get(url, (response) => {
      if (response.statusCode < 200 || response.statusCode >= 300) {
        reject(new Error(`HTTP status ${response.statusCode}`));
        return;
      }
      let data = '';
      response.on('data', chunk => data += chunk);
      response.on('end', () => resolve(data));
    });
    request.on('error', reject);
    request.end();
  });
}

// Main function
(async () => {
  try {
    // Get the list of pages
    const pages = await getPages();

    // Find the page that matches our search
    const targetPage = pages.find(page =>
      page.url && page.url.includes('https://www.google.pt/search?q=t%C3%A9nis+infantil+barato+Portugal')
    );

    if (!targetPage) {
      console.error('Could not find the target page. Make sure the search page is open.');
      process.exit(1);
    }

    // The script to extract links as described
    const extractScript = `
      (() => {
        const links = Array.from(document.querySelectorAll('a'));
        const results = [];
        for (const link of links) {
          const text = link.innerText || link.textContent;
          if (text && text.includes('€')) {
            let href = link.href;
            // Filter for google search links (aclk redirects)
            if (href && href.includes('aclk')) {
              try {
                const urlObj = new URL(href);
                // Extract the adurl parameter (the actual destination)
                const adurl = urlObj.searchParams.get('adurl');
                if (adurl) {
                  // Clean UTM and similar parameters
                  const cleanUrl = new URL(adurl);
                  cleanUrl.searchParams.delete('utm_source');
                  cleanUrl.searchParams.delete('utm_medium');
                  cleanUrl.searchParams.delete('utm_campaign');
                  cleanUrl.searchParams.delete('gclid');
                  cleanUrl.searchParams.delete('gbraid');
                  // Also remove any other known tracking parameters if needed
                  results.push({
                    text: text.trim(),
                    url: cleanUrl.toString()
                  });
                }
              } catch (e) {
                // If URL parsing fails, skip
                console.warn('Failed to parse URL:', href, e);
              }
            }
          }
        }
        // Sort by price (extract price from text, assuming format like €XX.XX or €X,XX)
        results.sort((a, b) => {
          const priceA = parseFloat(a.text.match(/[\\d,]+(?:\\.[\\d]{2})?/)[0].replace(',', '.'));
          const priceB = parseFloat(b.text.match(/[\\d,]+(?:\\.[\\d]{2})?/)[0].replace(',', '.'));
          return priceA - priceB;
        });
        // Return top 10
        return results.slice(0, 10);
      })()
    `;

    const extractedLinks = await evaluateOnPage(targetPage.webSocketDebuggerUrl, extractScript);

    // Now we need to validate each link by fetching the page and checking the real price
    const validatedItems = [];

    for (const item of extractedLinks) {
      try {
        // Fetch the product page
        const html = await fetchUrl(item.url);

        // We'll use a simple regex to find a price in euros on the page.
        // This is a simplification; in reality, we might need to use a parser like cheerio.
        // But for the sake of this example, we'll look for a pattern like €XX,XX or €XX.XX
        const priceMatch = html.match(/€\\s*([\\d,.]+)/);
        if (!priceMatch) {
          console.warn(`Could not find price on ${item.url}`);
          continue;
        }
        let priceStr = priceMatch[1].replace(',', '.');
        // Sometimes there might be multiple numbers, take the first one that looks like a price
        // We'll just take the first match and hope it's the main price.
        const price = parseFloat(priceStr);

        // If price is greater than 20, skip unless there's a big discount (we don't have discount info here)
        // For now, we'll just skip if > 20 as per instructions (unless big discount, but we can't detect that easily)
        if (price > 20) {
          console.warn(`Price ${price} > 20, skipping ${item.url}`);
          continue;
        }

        // Extract product name from the page (title tag or h1)
        let name = item.text; // fallback to the snippet text
        const titleMatch = html.match(/<title>([^<]+)<\/title>/i);
        if (titleMatch) {
          name = titleMatch[1].trim();
        } else {
          const h1Match = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
          if (h1Match) {
            name = h1Match[1].trim();
          }
        }

        // Try to extract size from the name or snippet
        let size = '';
        const sizeMatch = name.match(/\\b(\\d{2})(?:\\s*-\\s*\\d{2})?\\b/);
        if (sizeMatch) {
          size = sizeMatch[0];
        }

        // Try to extract store from the URL
        let store = '';
        try {
          const urlObj = new URL(item.url);
          store = urlObj.hostname.replace('www.', '');
        } catch (e) {
          store = 'unknown';
        }

        validatedItems.push({
          price: price.toFixed(2),
          name: name.length > 50 ? name.substring(0, 47) + '...' : name,
          size: size,
          store: store,
          url: item.url
        });

        // We only want a few items, break if we have enough (say 5)
        if (validatedItems.length >= 5) {
          break;
        }
      } catch (err) {
        console.warn(`Error processing ${item.url}: ${err.message}`);
        continue;
      }
    }

    // Output the report in pt-BR, ≤ 15 lines
    if (validatedItems.length === 0) {
      console.log('Nenhuma pechincha relevante encontrada.');
    } else {
      console.log('Pechinchas de ténis infantil em Portugal:');
      validatedItems.forEach((item, index) => {
        console.log(`${index + 1}. ${item.name} - ${item.price}€ - Tamanho: ${item.size || 'N/A'} - Loja: ${item.store} - Link: ${item.url}`);
      });
    }
  } catch (err) {
    console.error('Erro na extração:', err);
    process.exit(1);
  }
})();