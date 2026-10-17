const WebSocket = require('ws');

const ws = new WebSocket('ws://127.0.0.1:9222/devtools/page/42');

let requestId = 0;

ws.on('open', () => {
  console.log('Connected to DevTools');
  // Enable domains
  ws.send(JSON.stringify({id: ++requestId, method: 'Page.enable'}));
  ws.send(JSON.stringify({id: ++requestId, method: 'Runtime.enable'}));
  ws.send(JSON.stringify({id: ++requestId, method: 'DOM.enable'}));
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.id === requestId && msg.method === 'Page.enable') {
    // Now get document root
    ws.send(JSON.stringify({id: ++requestId, method: 'DOM.getDocument', params: {depth: -1}}));
  } else if (msg.id === requestId && msg.method === 'DOM.getDocument') {
    const root = msg.result.root;
    // Query all <a> elements
    ws.send(JSON.stringify({id: ++requestId, method: 'DOM.querySelectorAll', params: {nodeId: root.nodeId, selector: 'a'}}));
  } else if (msg.id === requestId && msg.method === 'DOM.querySelectorAll') {
    const nodeIds = msg.result.nodeIds;
    // For each node, get outerHTML or textContent and href
    const promises = nodeIds.map(id => {
      return new Promise((resolve, reject) => {
        ws.send(JSON.stringify({id: ++requestId, method: 'DOM.getOuterHTML', params: {nodeId: id}}, (err, resp) => {
          if (err) reject(err);
          else resolve({nodeId: id, outerHTML: resp.result.outerHTML});
        }));
      });
    });
    Promise.all(promises).then(results => {
      const links = [];
      results.forEach(r => {
        const html = r.outerHTML;
        // Extract href and innerText roughly
        const hrefMatch = html.match(/href=["']([^"']*)["']/i);
        const textMatch = html.match(/>([^<]*)</i);
        if (hrefMatch && textMatch) {
          const href = hrefMatch[1];
          const text = textMatch[1];
          if (text.includes('€') && href.includes('google.aclk')) {
            // Extract adurl parameter
            const url = new URL(href, 'https://www.google.pt');
            const adurl = url.searchParams.get('adurl');
            if (adurl) {
              try {
                const decoded = decodeURIComponent(adurl);
                // Remove utm, gclid, gbraid etc
                const clean = decoded.replace(/[?&](utm_[^=&]*|gclid|gbraid)=[^&]*/g, '');
                links.push({url: clean, text});
              } catch (e) {
                console.error('Failed to decode adurl', adurl, e);
              }
            }
          }
        }
      });
      console.log('Found links:', links.length);
      links.slice(0, 20).forEach(l => console.log(l.url));
      // Output as JSON for easy capture
      console.log(JSON.stringify(links.map(l => l.url)));
      ws.close();
    });
  }
});

ws.on('close', () => {
  console.log('Disconnected');
});