const http = require('http');
function getJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => { try { resolve(JSON.parse(data)); } catch (e) { reject(e); } });
    }).on('error', reject);
  });
}
const WebSocket = require('ws');
async function main() {
  const pages = await getJSON('http://127.0.0.1:9222/json/list');
  const target = pages.find((p) => p.url && p.url.includes('google.pt/search') && !p.url.includes('aclk'));
  if (!target) { console.log('NO_PAGE'); process.exit(0); }
  console.log('USING PAGE', target.id, target.url);
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 0; const pending = {};
  ws.on('message', (msg) => { const m = JSON.parse(msg); if (m.id && pending[m.id]) { pending[m.id](m); delete pending[m.id]; } });
  const send = (method, params = {}) => new Promise((res) => { const mid = ++id; pending[mid] = res; ws.send(JSON.stringify({ id: mid, method, params })); });
  await new Promise((res) => ws.on('open', res));
  const expr = process.argv[2] || 'document.title + " ||| " + document.body.innerText.slice(0, 3000)';
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  console.log(JSON.stringify(r.result.result.value || r.result, null, 1).slice(0, 5000));
  ws.close(); process.exit(0);
}
main().catch((e) => { console.error('ERR', e.message); process.exit(1); });
