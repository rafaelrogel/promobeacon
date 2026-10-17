const WebSocket = require('ws');
const target = process.argv[2];
const origin = process.argv[3] || undefined;
const opts = {};
if (origin) opts.origin = origin;
const ws = new WebSocket(target, opts);
ws.on('open', () => { console.log('OPEN OK'); ws.close(); process.exit(0); });
ws.on('unexpected-response', (req, res) => {
  let b = '';
  res.on('data', (c) => (b += c));
  res.on('end', () => { console.log('RESP', res.statusCode, b.slice(0, 300)); process.exit(0); });
});
ws.on('error', (e) => { console.log('ERR', e.message); process.exit(0); });
setTimeout(() => { console.log('TIMEOUT'); process.exit(0); }, 5000);
