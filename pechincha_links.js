const WebSocket = require('ws');
const pageId = process.argv[2] || '27';
const ws = new WebSocket('ws://127.0.0.1:9222/devtools/page/' + pageId);
let done = false;
const timer = setTimeout(() => { console.error('TIMEOUT'); process.exit(1); }, 15000);

ws.on('open', () => {
  ws.send(JSON.stringify({id: 1, method: 'Runtime.evaluate', params: {
    expression: `JSON.stringify(Array.from(document.querySelectorAll('a'))
      .filter(a => a.textContent.includes('€'))
      .map(a => ({text: a.textContent.trim().replace(/\\s+/g,' ').slice(0,120), href: a.href})))`,
    returnByValue: true
  }}));
});
ws.on('message', data => {
  const msg = JSON.parse(data.toString());
  if (msg.id === 1) {
    try {
      const val = msg.result && msg.result.result && msg.result.result.value;
      if (val) console.log(val);
    } catch(e) { console.error('parse err', e.message); }
    clearTimeout(timer);
    ws.close();
    process.exit(0);
  }
});
ws.on('error', e => { console.error('WS ERR', e.message); process.exit(1); });
