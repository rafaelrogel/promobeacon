// Valida 1 URL: navega, aguarda redirects, extrai título + preços
const WebSocket = require('ws');
const pageId = process.argv[2] || '27';
const url = process.argv[3];

const ws = new WebSocket('ws://127.0.0.1:9222/devtools/page/' + pageId);
let idc = 0;
const pending = new Map();
function send(method, params) {
  return new Promise((resolve) => {
    const id = ++idc;
    pending.set(id, resolve);
    ws.send(JSON.stringify({id, method, params}));
  });
}
async function evalJS(expr) {
  const r = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
  return r.result && r.result.result && r.result.result.value;
}
async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

ws.on('open', async () => {
  await send('Page.enable', {});
  await send('Page.navigate', {url});
  await sleep(12000);
  const title = await evalJS(`document.title || ''`);
  const href = await evalJS(`location.href`);
  const lines = await evalJS(`(document.body?document.body.innerText:'').split('\\n').map(s=>s.trim()).filter(Boolean)`);
  const priceLines = lines ? lines.filter(l => /(€|preço|preco)/i.test(l) && /\d/.test(l)).slice(0, 8) : [];
  console.log(JSON.stringify({title: String(title).slice(0,90), href: String(href).slice(0,120), priceLines}));
  console.log('DONE');
  ws.close();
  process.exit(0);
});
ws.on('error', e => { console.error('WSERR', e.message); process.exit(1); });
ws.on('message', data => {
  const msg = JSON.parse(data.toString());
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
});
setTimeout(() => { console.error('TIMEOUT'); process.exit(1); }, 40000);
