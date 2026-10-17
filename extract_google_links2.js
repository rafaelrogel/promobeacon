const WebSocket = require('ws');

const wsUrl = 'ws://127.0.0.1:9222/devtools/page/15';
const ws = new WebSocket(wsUrl);

let sequenceId = 0;

function send(method, params = {}) {
  sequenceId++;
  const message = {
    id: sequenceId,
    method,
    params
  };
  ws.send(JSON.stringify(message));
  return sequenceId; // returns the id of the message
}

ws.on('open', () => {
  console.log('Connected to DevTools');
  // Enable Page and Runtime domains
  send('Page.enable');
  send('Runtime.enable');
  // Wait a bit for enable to take effect
  setTimeout(() => {
    // We are already on the search page, but let's reload to ensure we have the latest
    send('Page.reload', {});
  }, 1000);
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.method === 'Page.loadEventFired') {
    console.log('Page loaded');
    // Now we can extract the links
    extractLinks();
  }
  // Handle the result of Runtime.evaluate
  if (msg.id === evaluateId && msg.method === 'Runtime.evaluateDone') {
    const result = msg.result.result.value;
    console.log('Extracted results:', result);
    // Process the results: filter those with price, sort by price ascending
    const pricedResults = result.filter(r => r.price !== null);
    pricedResults.sort((a, b) => a.price - b.price);
    // Take top 10
    const top10 = pricedResults.slice(0, 10);
    console.log('Top 10 by price:', top10);
    // Now we need to validate each by fetching the product page
    // But note: the href might be a Google redirect. We need to follow it or extract the real URL.
    // For simplicity, we'll try to fetch the href directly and see if we get a product page.
    // However, we are in a Node.js environment, we can use http or https to fetch.
    // But we are supposed to use web_fetch or pinchtab. Let's use web_fetch via the OpenClaw tool? 
    // We cannot call external tools from this script easily. Instead, we'll output the links and then use another method.
    // For now, let's just output the top 10 with the href and we'll validate them separately.
    // We'll write the links to a file.
    const fs = require('fs');
    fs.writeFileSync('/tmp/google_results.json', JSON.stringify(top10, null, 2));
    console.log('Results written to /tmp/google_results.json');
    ws.close();
  }
});

let evaluateId = null;

function extractLinks() {
  // JavaScript to extract search results
  const script = `
    (() => {
      const results = [];
      // Google search result selectors may vary
      const gBlocks = document.querySelectorAll('div.g');
      gBlocks.forEach(block => {
        const linkEl = block.querySelector('a');
        if (!linkEl) return;
        const href = linkEl.getAttribute('href');
        // Get the text content of the block to look for prices
        const text = block.innerText;
        // Look for price patterns: € followed by digits, optionally with comma or dot
        const priceMatches = text.match(/€\\s*(\\d+[.,]?\\d*)/g);
        let price = null;
        if (priceMatches) {
          // Take the first price found
          const priceStr = priceMatches[0].replace('€', '').replace(',', '.').trim();
          price = parseFloat(priceStr);
        }
        // Also look for size patterns (like tamanho 32, or 32-34)
        const sizeMatches = text.match(/tamanho\\s*(\\d+[-\\s]?\\d*)/i);
        let size = null;
        if (sizeMatches) {
          size = sizeMatches[1].replace(/\s/g, '');
        }
        // Extract title from h3 or similar
        const titleEl = block.querySelector('h3');
        const title = titleEl ? titleEl.innerText : '';
        results.push({
          href,
          text,
          price,
          size,
          title
        });
      });
      return results;
    })()
  `;
  evaluateId = send('Runtime.evaluate', { expression: script, returnByValue: true });
}

ws.on('close', () => {
  console.log('Disconnected');
});

ws.on('error', (err) => {
  console.error('WebSocket error:', err);
});