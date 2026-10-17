const WebSocket = require('ws');

const PAGE_ID = process.argv[2] || '15';
const TARGET_URL = process.argv[3];
const WS_URL = `ws://127.0.0.1:9222/devtools/page/${PAGE_ID}`;

function cleanUrl(url) {
  if (!url) return '';
  try {
    const u = new URL(url);
    if (u.hostname.includes('google') && u.searchParams.has('adurl')) {
      let adurl = u.searchParams.get('adurl');
      if (adurl.startsWith('//')) adurl = 'https:' + adurl;
      try { u.href = adurl; } catch (e) {}
    }
    if (u.hostname.includes('google') && u.searchParams.has('q')) {
      try { u.href = u.searchParams.get('q'); } catch (e) {}
    }
    for (const key of [...u.searchParams.keys()]) {
      if (/^(utm_|gclid|gbraid|fbclid|msclkid|igshid|gad_source|gad_campaignid|clickref|shprz_campaign|esca|esme|esso|pin|ref|dclid)/i.test(key)) {
        u.searchParams.delete(key);
      }
    }
    let h = u.href;
    if (/^https?:\/\/(www\.)?google\.(pt|com)/.test(h)) return '';
    if (/awin1\.com|shoparize\.com|everysize\.com/.test(h) && !TARGET_URL) return h; // keep for redirect-resolve later
    h = h.replace(/[?&]$/, '');
    return h;
  } catch (e) { return ''; }
}

function parsePrice(text) {
  const matches = [...text.matchAll(/(\d+[.,]\d{2})\s*€|€\s*(\d+[.,]\d{2})/g)];
  if (!matches.length) return null;
  const prices = matches.map(m => parseFloat((m[1] || m[2]).replace(',', '.')));
  return Math.min(...prices);
}

function parseSize(text) {
  const range = text.match(/\b(3[0-8]|2[8-9]|4[0-2])\s*[-/]\s*(3[0-8]|4[0-2])\b/);
  if (range) return `${range[1]}-${range[2]}`;
  const single = text.match(/\b(3[0-8]|2[8-9]|4[0-2])\b(?=\s*(?:anos|tam|ano|€|,|\.|\s|$))/);
  if (single) return single[1];
  return null;
}

function storeFromUrl(url) {
  if (!url) return '';
  const host = url.replace(/^https?:\/\//, '').split('/')[0].toLowerCase();
  if (host.includes('decathlon')) return 'Decathlon';
  if (host.includes('sprinter')) return 'Sprinter';
  if (host.includes('lefties')) return 'Lefties';
  if (host.includes('zara')) return 'Zara';
  if (host.includes('kiabi')) return 'Kiabi';
  if (host.includes('geox')) return 'Geox';
  if (host.includes('nike')) return 'Nike';
  if (host.includes('adidas')) return 'Adidas';
  if (host.includes('amazon')) return 'Amazon';
  if (host.includes('worten')) return 'Worten';
  if (host.includes('elcorteingles')) return 'El Corte Inglés';
  if (host.includes('sportzone')) return 'Sportzone';
  if (host.includes('awin1') || host.includes('shoparize') || host.includes('everysize')) return 'comparador';
  const m = host.match(/([^.\/]+)\.(com|pt|es|eu|net)/);
  return m ? m[1] : host;
}

const EVAL_JS = `(() => {
  const links = [...document.querySelectorAll('a')];
  const out = [];
  const seen = new Set();
  for (const a of links) {
    const text = (a.innerText || '').replace(/\\s+/g, ' ').trim();
    if (!text.includes('€')) continue;
    let href = a.href || '';
    if (seen.has(text + '|' + href)) continue;
    seen.add(text + '|' + href);
    out.push({ text: text.slice(0, 400), href });
  }
  return JSON.stringify(out);
})()`;

async function main() {
  const ws = new WebSocket(WS_URL);
  let id = 0;
  const pending = new Map();

  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const mid = ++id;
    pending.set(mid, { resolve, reject });
    ws.send(JSON.stringify({ id: mid, method, params }));
  });

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message));
      else resolve(msg.result);
    }
  };

  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });

  if (TARGET_URL) {
    await send('Page.enable');
    await send('Page.navigate', { url: TARGET_URL });
    await new Promise(r => setTimeout(r, 7000));
    for (let i = 0; i < 3; i++) {
      await send('Runtime.evaluate', { expression: `window.scrollBy(0, ${600 + i * 500}); true`, returnByValue: true });
      await new Promise(r => setTimeout(r, 2000));
    }
    await send('Runtime.evaluate', { expression: 'window.scrollTo(0, 0); true', returnByValue: true });
    await new Promise(r => setTimeout(r, 1500));
  }

  const res = await send('Runtime.evaluate', { expression: EVAL_JS, returnByValue: true });
  const raw = JSON.parse(res.result.value);

  const items = [];
  for (const link of raw) {
    let href = link.href;
    if (!href) continue;
    const clean = cleanUrl(href);
    if (!clean) continue;
    if (/^https?:\/\/(www\.)?google\.(pt|com)/.test(clean)) continue;
    if (clean.startsWith('javascript:')) continue;
    const price = parsePrice(link.text);
    if (price === null) continue;
    const size = parseSize(link.text);
    const store = storeFromUrl(clean);
    const name = link.text
      .replace(/€[\s\S]*$/, '')
      .replace(/\b(?:comprar|ver|preço|desconto)\b/gi, '')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 70);
    items.push({ price, name, size, store, url: clean });
  }

  const byUrl = new Map();
  for (const it of items) {
    if (!byUrl.has(it.url) || it.price < byUrl.get(it.url).price) byUrl.set(it.url, it);
  }
  const unique = [...byUrl.values()];
  unique.sort((a, b) => a.price - b.price);
  console.log(JSON.stringify(unique.slice(0, 15), null, 1));
  ws.close();
  process.exit(0);
}

main().catch(e => { console.error('ERR', e.message); process.exit(1); });
