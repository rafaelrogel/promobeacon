const WebSocket = require('ws');
const ws = new WebSocket('ws://127.0.0.1:9222/devtools/page/32');
let seq = 1;
function send(method, params = {}) {
  const msg = { id: seq++, method, params };
  ws.send(JSON.stringify(msg));
  return msg.id;
}
ws.on('open', () => {
  console.log('Connected');
  send('Page.enable');
  send('Runtime.enable');
  // Navigate to product page
  send('Page.navigate', { url: "https://www.decathlon.pt/calcado-tenis-crianca-ts100-id_8351658.html" });
});
ws.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.method === 'Page.frameStoppedLoading') {
    console.log('Loaded product page');
    setTimeout(() => {
      send('Runtime.evaluate', {
        expression: `
          (() => {
            // Try to find price
            const priceEl = document.querySelector('[data-testid="price"], .price, .dt-price, .product-price, .price-value');
            if (priceEl) {
              return { price: priceEl.innerText.trim(), method: 'selector' };
            }
            // Look for any euro pattern
            const bodyText = document.body.innerText;
            const match = bodyText.match(/(\d+[.,]\d{2})\s*€/);
            if (match) {
              return { price: match[0], method: 'regex' };
            }
            return { price: null };
          })()
        `,
        returnByValue: true
      });
    }, 3000);
  }
  if (msg.id && msg.result) {
    if (msg.result.result && msg.result.result.value) {
      console.log('Price result:', JSON.stringify(msg.result.result.value));
    }
  }
  if (msg.error) {
    console.error('Error:', msg.error);
  }
});
ws.on('close', () => {
  console.log('Closed');
  process.exit(0);
});