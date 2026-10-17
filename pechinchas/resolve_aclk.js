const http = require('http');

function req(method, path, body) {
  return new Promise((resolve, reject) => {
    const r = http.request({ host: '127.0.0.1', port: 9222, path, method }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve(d));
    });
    r.on('error', reject);
    if (body) r.write(body);
    r.end();
  });
}

async function main() {
  const aclk = process.argv[2];
  const created = await req('PUT', '/json/new?' + aclk);
  const page = JSON.parse(created);
  console.log('NEW_TAB', page.id);
  await new Promise(r => setTimeout(r, 7000));
  const list = JSON.parse(await req('GET', '/json/list'));
  const tab = list.find(p => p.id === page.id);
  console.log('FINAL_URL', tab ? tab.url : 'NOT_FOUND');
  try { await req('GET', '/json/close/' + page.id); } catch (e) {}
  process.exit(0);
}
main().catch(e => { console.error('ERR', e.message); process.exit(1); });
