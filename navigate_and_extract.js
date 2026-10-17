const WebSocket = require('ws');
const ws = new WebSocket('ws://127.0.0.1:9222/devtools/page/32');
let seq = 1;
function send(method, params = {}) {
  const msg = { id: seq++, method, params };
  ws.send(JSON.stringify(msg));
  return msg.id;
}
ws.on('open', () => {
  console.log('Connected to DevTools');
  send('Page.enable');
  send('Runtime.enable');
  send('Page.navigate', { url: "https://www.decathlon.pt/p/calcado-de-tenis-ts990-crianca-amarelo/_/R-p-309138" });
});
ws.on('message', (data) => {
  const msg = JSON.parse(data);
  if msg.method === 'Page.frameStoppedLoading' && msg.params.frameId === msg.params.frameId) {
    console.log('Frame stopped loading');
    // Wait a bit for dynamic content
    setTimeout(() => {
      send('Runtime.evaluate', {
        expression: `
          (() => {
            // Try to find price elements
            const priceSelectors = [
              '.price', '[data-testid="price"]', '.product-price', '.price-value', '.dt-price'
            ];
            for (const sel of priceSelectors) {
              const el = document.querySelector(sel);
              if (el) {
                return { priceText: el.innerText.trim(), selector: sel };
              }
            }
            // Fallback: look for any text containing €
            const allText = document.body.innerText;
            const euroMatch = allText.match(/(\d+[.,]\d{2})\s*€/);
            if (euroMatch) {
              return { priceText: euroMatch[0], method: 'regex' };
            }
            return { priceText: null };
          })()
        `,
        returnByValue: true
      });
    }, 3000);
  }
  if (msg.id && msg.result) {
    if (msg.result.result && msg.result.result.value) {
      console.log('Result:', JSON.stringify(msg.result.result.value, null, 2));
      // Also get the page title
      send('Runtime.evaluate', {
        expression: `document.title`,
        returnByValue: true
      });
    }
  }
  if (msg.error) {
    console.error('Error:', msg.error);
  }
});
ws.on('close', () => console.log('Disconnected'));
