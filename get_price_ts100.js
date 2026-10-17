const WebSocket = require('ws');
// Use the product page ID we saw: 34
const ws = new WebSocket('ws://127.0.0.1:9222/devtools/page/34');
let seq = 1;
function send(method, params = {}) {
  const msg = { id: seq++, method, params };
  ws.send(JSON.stringify(msg));
  return msg.id;
}
ws.on('open', () => {
  console.log('Connected to product page');
  send('Page.enable');
  send('Runtime.enable');
});
ws.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.method === 'Page.frameStoppedLoading') {
    console.log('Frame stopped loading');
    setTimeout(() => {
      send('Runtime.evaluate', {
        expression: `
          (() => {
            // Try to find price
            const selectors = ['[data-testid=\"price\"]', '.price', '.dt-price', '.product-price', '.price-value', '.sale-price', '.regular-price'];
            for (const sel of selectors) {
              const el = document.querySelector(sel);
              if (el) {
                const text = el.innerText.trim();
                if (text) return { price: text, method: 'selector', selector: sel };
              }
            }
            // Look for any euro pattern in visible text
            const bodyText = document.body.innerText;
            const match = bodyText.match(/(\\d+[.,]\\d{2})\\s*€/);
            if (match) {
              return { price: match[0], method: 'regex' };
            }
            return { price: null };
          })()
        `,
        returnByValue: true
      });
    }, 5000);
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
