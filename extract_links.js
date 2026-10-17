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
});
ws.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.method === 'Page.frameStoppedLoading') {
    console.log('Frame stopped loading');
    // Now extract links
    send('Runtime.evaluate', {
      expression: `
        (() => {
          const links = Array.from(document.querySelectorAll('a'))
            .map(a => ({
              href: a.href,
              text: a.innerText.trim()
            }))
            .filter(a => a.text.includes('€') || a.text.includes('$') || a.text.includes('£'));
          return links.slice(0, 20);
        })()
      `,
      returnByValue: true
    });
  }
  if (msg.id && msg.result) {
    if (msg.result.result && msg.result.result.value) {
      console.log('Links:', JSON.stringify(msg.result.result.value, null, 2));
    }
  }
  if (msg.error) {
    console.error('Error:', msg.error);
  }
});
ws.on('close', () => console.log('Disconnected'));
