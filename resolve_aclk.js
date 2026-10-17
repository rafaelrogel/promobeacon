// Resolve a Google aclk redirect to final adurl via CDP: navigate and capture URL
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
  const target = pages.find((p) => p.id === '22');
  if (!target) { console.log('NO_PAGE'); process.exit(0); }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 0; const pending = {};
  ws.on('message', (msg) => { const m = JSON.parse(msg); if (m.id && pending[m.id]) { pending[m.id](m); delete pending[m.id]; } });
  const send = (method, params = {}) => new Promise((res) => { const mid = ++id; pending[mid] = res; ws.send(JSON.stringify({ id: mid, method, params })); });
  await new Promise((res) => ws.on('open', res));
  const expr = `
    (async () => {
      const out = [];
      const acls = [];
      document.querySelectorAll('a').forEach((a) => {
        const t = (a.innerText || '').trim();
        if (!t || t.length > 300) return;
        if (!/€/.test(t)) return;
        if (a.href && a.href.includes('/aclk')) acls.push({ t: t.replace(/\\s+/g,' ').slice(0,120), href: a.href });
      });
      for (const it of acls.slice(0, 8)) {
        try {
          const resp = await fetch(it.href, { redirect: 'follow' });
          out.push({ text: it.t, finalUrl: resp.url });
        } catch (e) { out.push({ text: it.t, err: e.message }); }
      }
      return JSON.stringify(out);
    })()
  `;
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  console.log(JSON.stringify(JSON.parse(r.result.result.value), null, 1));
  ws.close(); process.exit(0);
}
main().catch((e) => { console.error('ERR', e.message); process.exit(1); });
