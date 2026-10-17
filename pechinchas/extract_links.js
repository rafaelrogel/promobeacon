const WebSocket = require('ws');
const url = process.argv[2];
const ws = new WebSocket(url);
let id = 0;
const pending = {};

function send(method, params) {
  return new Promise((resolve, reject) => {
    const msgId = ++id;
    pending[msgId] = { resolve, reject };
    ws.send(JSON.stringify({ id: msgId, method, params: params || {} }));
  });
}

ws.on('message', (data) => {
  const msg = JSON.parse(data.toString());
  if (msg.id && pending[msg.id]) {
    if (msg.error) pending[msg.id].reject(new Error(JSON.stringify(msg.error)));
    else pending[msg.id].resolve(msg.result);
    delete pending[msg.id];
  }
});

ws.on('open', async () => {
  try {
    await send('Runtime.enable');
    await new Promise(r => setTimeout(r, 1500));
    // light scroll to load more results
    await send('Runtime.evaluate', { expression: 'window.scrollBy(0, 600); true;' });
    await new Promise(r => setTimeout(r, 2500));
    await send('Runtime.evaluate', { expression: 'window.scrollBy(0, 400); true;' });
    await new Promise(r => setTimeout(r, 2500));

    const js = `
      (() => {
        const out = [];
        const anchors = Array.from(document.querySelectorAll('a'));
        const seen = new Set();
        for (const a of anchors) {
          const txt = (a.innerText || '').replace(/\\s+/g, ' ').trim();
          if (!txt.includes('€')) continue;
          let href = a.href || '';
          if (href.includes('google.pt/url?') || href.includes('/aclk?')) {
            try {
              const u = new URL(href);
              const ad = u.searchParams.get('adurl');
              if (ad) href = ad;
              else if (u.searchParams.get('q') && href.includes('google')) continue;
            } catch(e) {}
          }
          // cleanup tracking params
          try {
            const u = new URL(href);
            ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','gbraid','fbclid','gclsrc','dclid'].forEach(p => u.searchParams.delete(p));
            href = u.toString();
          } catch(e) {}
          const key = txt + '|' + href;
          if (seen.has(key)) continue;
          seen.add(key);
          out.push({ txt, href });
        }
        return JSON.stringify(out);
      })()
    `;
    const res = await send('Runtime.evaluate', { expression: js, returnByValue: true });
    console.log(res.result.value);
  } catch (e) {
    console.error('ERR', e.message);
    process.exit(1);
  } finally {
    ws.close();
    process.exit(0);
  }
});

ws.on('error', (e) => { console.error('WS_ERR', e.message); process.exit(1); });
