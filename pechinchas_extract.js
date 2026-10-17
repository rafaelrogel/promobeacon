// Extract product links with prices from Google search results page via CDP
const http = require('http');

function getJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
      });
    }).on('error', reject);
  });
}

const WebSocket = require('ws');

async function main() {
  const pages = await getJSON('http://127.0.0.1:9222/json/list');
  const target = pages.find((p) => p.url && p.url.includes('google.pt/search'));
  if (!target) {
    console.log('NO_PAGE');
    return;
  }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 0;
  const pending = {};
  ws.on('message', (msg) => {
    const m = JSON.parse(msg);
    if (m.id && pending[m.id]) { pending[m.id](m); delete pending[m.id]; }
  });
  const send = (method, params = {}) => new Promise((res) => {
    const mid = ++id;
    pending[mid] = res;
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  await new Promise((res) => ws.on('open', res));

  const js = `
    (() => {
      const results = [];
      const seen = new Set();
      document.querySelectorAll('a').forEach((a) => {
        const t = (a.innerText || '').trim();
        if (!t || t.length > 300) return;
        const m = t.match(/€\\s?\\d+[.,]?\\d*/);
        if (!m) return;
        let href = a.href || '';
        // extract adurl from aclk redirects
        try {
          if (href.includes('/aclk')) {
            const u = new URL(href);
            const adurl = u.searchParams.get('adurl');
            if (adurl) href = adurl;
          }
        } catch (e) {}
        // clean tracking params
        try {
          const u = new URL(href);
          ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','gbraid','fbclid','dclid','wbraid'].forEach((p) => u.searchParams.delete(p));
          href = u.href;
        } catch (e) {}
        if (!href.startsWith('http')) return;
        if (href.includes('google.') && !href.includes('adurl')) return;
        const key = t + href;
        if (seen.has(key)) return;
        seen.add(key);
        results.push({ text: t.replace(/\\s+/g, ' ').slice(0, 220), href });
      });
      // scroll to load more
      window.scrollTo(0, document.body.scrollHeight);
      return JSON.stringify(results);
    })()
  `;
  const r = await send('Runtime.evaluate', { expression: js, returnByValue: true });
  const items = JSON.parse(r.result.result.value);
  // second pass after scroll
  await new Promise((res) => setTimeout(res, 2500));
  const js2 = `
    (() => {
      const results = [];
      const seen = new Set();
      document.querySelectorAll('a').forEach((a) => {
        const t = (a.innerText || '').trim();
        if (!t || t.length > 300) return;
        const m = t.match(/€\\s?\\d+[.,]?\\d*/);
        if (!m) return;
        let href = a.href || '';
        try {
          if (href.includes('/aclk')) {
            const u = new URL(href);
            const adurl = u.searchParams.get('adurl');
            if (adurl) href = adurl;
          }
        } catch (e) {}
        try {
          const u = new URL(href);
          ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','gbraid','fbclid','dclid','wbraid'].forEach((p) => u.searchParams.delete(p));
          href = u.href;
        } catch (e) {}
        if (!href.startsWith('http')) return;
        if (href.includes('google.') && !href.includes('adurl')) return;
        const key = t + href;
        if (seen.has(key)) return;
        seen.add(key);
        results.push({ text: t.replace(/\\s+/g, ' ').slice(0, 220), href });
      });
      return JSON.stringify(results);
    })()
  `;
  const r2 = await send('Runtime.evaluate', { expression: js2, returnByValue: true });
  const items2 = JSON.parse(r2.result.result.value);
  const all = [...items, ...items2];
  const uniq = [];
  const keys = new Set();
  for (const it of all) {
    const k = it.href;
    if (keys.has(k)) continue;
    keys.add(k);
    uniq.push(it);
  }
  console.log(JSON.stringify(uniq, null, 1));
  ws.close();
  process.exit(0);
}

main().catch((e) => { console.error('ERR', e.message); process.exit(1); });
