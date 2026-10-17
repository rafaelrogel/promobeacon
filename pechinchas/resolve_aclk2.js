const WebSocket = require('ws');
const ws = new WebSocket('ws://127.0.0.1:9222/devtools/page/9');
let id = 0;
const pending = {};

function send(method, params) {
  return new Promise((resolve, reject) => {
    const msgId = ++id;
    pending[msgId] = { resolve, reject };
    ws.send(JSON.stringify({ id: msgId, method, params: params || {} }));
  });
}
ws.on('message', data => {
  const msg = JSON.parse(data.toString());
  if (msg.id && pending[msg.id]) {
    if (msg.error) pending[msg.id].reject(new Error(JSON.stringify(msg.error)));
    else pending[msg.id].resolve(msg.result);
    delete pending[msg.id];
  }
});
ws.on('open', async () => {
  try {
    await send('Page.enable');
    await send('Runtime.enable');
    for (const [name, url] of Object.entries(JSON.parse(process.argv[2]))) {
      try {
        await send('Page.navigate', { url });
        await new Promise(r => setTimeout(r, 9000));
        const res = await send('Runtime.evaluate', { expression: 'location.href', returnByValue: true });
        console.log(name, '=>', res.result.value);
      } catch (e) {
        console.log(name, '=> ERR', e.message.slice(0, 120));
      }
      await new Promise(r => setTimeout(r, 2000));
    }
  } catch (e) { console.error('FATAL', e.message); }
  finally { ws.close(); process.exit(0); }
});
ws.on('error', e => { console.error('WS_ERR', e.message); process.exit(1); });
