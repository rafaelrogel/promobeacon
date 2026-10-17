// Valida preço real v3: lê URLs de um arquivo, extrai título + linhas de preço do innerText
const WebSocket = require('ws');
const fs = require('fs');
const pageId = process.argv[2] || '27';
const file = process.argv[3] || 'urls.txt';
const urls = fs.readFileSync(file, 'utf8').split('\n').map(s => s.trim()).filter(Boolean);

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

async function getPrice(url) {
  await send('Page.navigate', {url});
  await sleep(8500);
  const title = await evalJS(`document.title || ''`);
  const lines = await evalJS(`(document.body?document.body.innerText:'').split('\\n').map(s=>s.trim()).filter(Boolean)`);
  if (!lines || !lines.length) return {url, err: 'empty', title};
  const priceLines = lines.filter(l => /(€|preço|preco|promo)/i.test(l) && /\d/.test(l)).slice(0, 10);
  return {url, title: String(title).slice(0, 90), priceLines};
}

ws.on('open', async () => {
  try {
    await send('Page.enable', {});
    for (const u of urls) {
      const r = await getPrice(u);
      console.log('### ' + JSON.stringify(r));
      await sleep(2500 + Math.random() * 2000);
    }
    console.log('DONE');
  } catch (e) { console.error('ERR', e.message); }
  ws.close();
  process.exit(0);
});
ws.on('error', e => { console.error('WSERR', e.message); process.exit(1); });
ws.on('message', data => {
  const msg = JSON.parse(data.toString());
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
});
setTimeout(() => { console.error('TIMEOUT'); process.exit(1); }, 180000);
