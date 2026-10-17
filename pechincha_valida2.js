// Valida preço real v2: extrai TODAS as linhas com € e JSON-LD price
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
  return r.result && r.result.result && r.result.result.value;
}

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function getPrice(url) {
  await send('Page.navigate', {url});
  await sleep(8000);
  const title = await evalJS(`document.title || ''`);
  const expr = `(() => {
    const t = document.body ? document.body.innerText : '';
    const lines = t.split('\\n').map(l=>l.trim()).filter(Boolean);
    // linhas que parecem preço
    const priceLines = lines.filter(l => /^(€\\s?\\d|\\d[.,]\\d{2}\\s?€|Promoção|Preço)/.test(l) || /€\s?\\d+[.,]\d{2}/.test(l)).slice(0,6);
    // JSON-LD
    let ld = null;
    try {
      const s = document.querySelector('script[type="application/ld+json"]');
      if (s) {
        const j = JSON.parse(s.textContent);
        const walk = (o) => {
          if (!o || typeof o !== 'object') return null;
          if (o['@type'] === 'Product' && o.offers) return o;
          for (const k of Object.keys(o)) { const r = walk(o[k]); if (r) return r; }
          return null;
        };
        const prod = walk(j);
        if (prod && prod.offers) {
          const off = Array.isArray(prod.offers) ? prod.offers[0] : prod.offers;
          ld = {price: off.price, currency: off.currency, avail: off.availability};
        }
      }
    } catch(e) {}
    return JSON.stringify({title, priceLines, ld});
  })()`;
  const r = await evalJS(expr);
  return {url, data: r};
}

ws.on('open', async () => {
  try {
    await send('Page.enable', {});
    for (const u of urls) {
      const r = await getPrice(u);
      console.log('RESULT ' + JSON.stringify(r));
      await sleep(2500 + Math.random()*2000);
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
setTimeout(() => { console.error('TIMEOUT'); process.exit(1); }, 180000);
