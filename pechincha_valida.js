// Valida preço real abrindo cada URL no Chrome do tablet via CDP
const WebSocket = require('ws');
const pageId = process.argv[2] || '27';
const urls = JSON.parse(process.argv[3] || '[]');

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
  const v = r.result && r.result.result && r.result.result.value;
  return v;
}

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function getPrice(url) {
  await send('Page.navigate', {url});
  await sleep(9000);
  // extrai linhas com € do corpo
  const text = await evalJS(`document.body ? document.body.innerText : ''`);
  if (!text) return {url, err: 'no body'};
  const lines = text.split('\n').filter(l => l.includes('€'));
  const priceLine = lines.find(l => /€\s?\d+[.,]\d{2}/.test(l)) || (lines[0] || '');
  const title = await evalJS(`document.title || ''`);
  return {url, title: String(title).slice(0,80), priceLine: String(priceLine).slice(0,80), nLines: lines.length};
}

ws.on('open', async () => {
  try {
    await send('Page.enable', {});
    const results = [];
    for (const u of urls) {
      const r = await getPrice(u);
      results.push(r);
      console.log('RESULT', JSON.stringify(r));
      await sleep(3000 + Math.random()*2000);
    }
    console.log('DONE');
  } catch (e) {
    console.error('ERR', e.message);
  }
  ws.close();
  process.exit(0);
});
ws.on('error', e => { console.error('WSERR', e.message); process.exit(1); });
ws.on('message', data => {
  const msg = JSON.parse(data.toString());
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  }
});
setTimeout(() => { console.error('TIMEOUT'); process.exit(1); }, 120000);
