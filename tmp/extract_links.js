const WebSocket = require('ws');

const ws = new WebSocket('ws://127.0.0.1:9222/devtools/page/40');

ws.on('open', () => {
  console.log('Connected to devtools');
  
  // Enable DOM and Page domains
  ws.send(JSON.stringify({id: 1, method: 'DOM.enable'}));
  ws.send(JSON.stringify({id: 2, method: 'Page.enable'}));
  ws.send(JSON.stringify({id: 3, method: 'Runtime.enable'}));
  
  // Wait a bit then get document
  setTimeout(() => {
    ws.send(JSON.stringify({
      id: 4,
      method: 'DOM.getDocument',
      params: {depth: -1}
    }));
  }, 1000);
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  
  if (msg.id === 4 && msg.result) { // DOM.getDocument response
    const documentNodeId = msg.result.root.nodeId;
    
    // Query all anchor elements
    ws.send(JSON.stringify({
      id: 5,
      method: 'DOM.querySelectorAll',
      params: {
        nodeId: documentNodeId,
        selector: 'a'
      }
    }));
  }
  
  if (msg.id === 5 && msg.result) { // querySelectorAll response
    const nodeIds = msg.result.nodeIds;
    
    // Get attributes for each node
    nodeIds.forEach((nodeId, index) => {
      setTimeout(() => {
        ws.send(JSON.stringify({
          id: 6 + index,
          method: 'DOM.getAttributes',
          params: {nodeId}
        }));
      }, index * 50);
    });
  }
  
  if (msg.id >= 6 && msg.id < 6 + 100 && msg.result) { // getAttributes responses
    const attrs = {};
    for (let i = 0; i < msg.result.length; i += 2) {
      attrs[msg.result[i]] = msg.result[i+1];
    }
    
    if (attrs.href && attrs.href.includes('google') && attrs.href.includes('/url?q=')) {
      // Extract the actual URL from Google redirect
      try {
        const urlMatch = attrs.href.match(/[?&]q=([^&]+)/);
        if (urlMatch) {
          const decodedUrl = decodeURIComponent(urlMatch[1]);
          console.log(decodedUrl);
        }
      } catch (e) {
        // Ignore errors
      }
    }
  }
  
  if (msg.method === 'Page.loadEventFired') {
    console.log('Page loaded');
  }
});