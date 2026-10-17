const { execSync } = require('child_process');

const items = [
  { price: 1.18, name: "Bouncing sneaker", size: null, store: "hermes", url: "https://www.hermes.com/pt/en/product/bouncing-sneaker-H261014Zv90/?size=365&gad_source=1&gad_campaignid=20858115034" },
  { price: 2.99, name: "Calçado leve barefoot com tiras autoaderentes criança, stepper first azul", size: null, store: "Decathlon", url: "https://www.decathlon.pt/p/calcado-leve-barefoot-com-tiras-autoaderentes-crianca-stepper-first-azul/361045/c364c298m8930069?gad_source=1&gad_campaignid=24212883506" },
  { price: 2.99, name: "Puma Calçado De Criança Carina Jelly Heaven, Rosa", size: null, store: "awin1", url: "https://www.awin1.com/pclick.php?p=43992589699&a=626889&m=22132&clickref=PTgclid%28Cj0KCQjwt9jVBhDXARIsAFSP-6fLacng4n-i1Cx_CxDWcMvaqDV6heVMSWXPxp_dn9RWSba9qJvcdVEaAjRWEALw_wcB%29&gad_source=1&gad_campaignid=22746782584" },
  { price: 2.99, name: "Sapatilhas de futsal 100 criança", size: null, store: "Decathlon", url: "https://www.decathlon.pt/p/sapatilhas-de-futsal-100-crianca/347304/c200c200c32m8882900?gad_source=1&gad_campaignid=24212883506" },
  { price: 2.99, name: "Quechua Calçado De Caminhada Com Banda Aderente 24 - 31 Criança", size: "31", store: "awin1", url: "https://www.awin1.com/pclick.php?p=41672040189&a=626889&m=22132&clickref=PTgclid%28Cj0KCQjwt9jVBhDXARIsAFSP-6cwsxX8xM02KirjWSltFkpXAlrmJwlM4bUVSrG1Uplm7RXCpXYo_CEaAtFUEALw_wcB%29&gad_source=1&gad_campaignid=22746782584" },
  { price: 2.99, name: "Calçado de educação física com banda autoaderente criança pw 100 preto", size: null, store: "Decathlon", url: "https://www.decathlon.pt/p/calcado-de-educacao-fisica-com-banda-autoaderente-crianca-pw-100-preto/161592/c382c227m8403427?gad_source=1&gad_campaignid=22426019941" },
  { price: 2.99, name: "Sapatilhas de educação física criança swift tread azul verde", size: null, store: "Decathlon", url: "https://www.decathlon.pt/p/sapatilhas-de-educacao-fisica-crianca-swift-tread-azul-verde/372908/c5c130m8968047?gad_source=1&gad_campaignid=24212883506" },
  { price: 2.99, name: "Puma Rickie 2.0 - Sapatilhas Menino tamanho 29", size: "29", store: "Sprinter", url: "https://www.sprintersports.com/pt/puma-rickie-2-0-0397327?gad_source=1&gad_campaignid=23712300620" },
  { price: 2.99, name: "Puma St Runner V4 - Preto - Sapatilhas Velcro Menino", size: "20", store: "Sprinter", url: "https://www.sprintersports.com/pt/puma-st-runner-v4-0382945?gad_source=1&gad_campaignid=23712300620" },
  { price: 2.99, name: "Nike Court Borough Low Recraft - Branco - Ténis Menino", size: "28", store: "Sprinter", url: "https://www.sprintersports.com/pt/nike-court-borough-low-recraft-0357110?gad_source=1&gad_campaignid=23712300620" },
  { price: 2.99, name: "Puma Calçado Criança (36-39), Flyer Lite Preto E Branco", size: "36", store: "awin1", url: "https://www.awin1.com/pclick.php?p=44889642790&a=626889&m=22132&clickref=PTgclid%28Cj0KCQjwt9jVBhDXARIsAFSP-6eYWx6TNAxkjkbXlC-chvgtzo8ldw-q2dQ0KQlBBh6FdwXSTCppAeoaAkKpEALw_wcB%29&gad_source=1&gad_campaignid=22746782584" },
  { price: 2.99, name: "Skechers Sapatilhas De Educação Física Criança Dyna", size: "40", store: "awin1", url: "https://www.awin1.com/pclick.php?p=45143609631&a=626889&m=22132&clickref=PTgclid%28Cj0KCQjwt9jVBhDXARIsAFSP-6d-qeWNkPenAM0vFozkf9-wPlk4WjUhg6a_plIEX5o_MM-WKex2wYUaAs83EALw_wcB%29&gad_source=1&gad_campaignid=22746782584" }
];

function cleanUrl(url) {
  try {
    const u = new URL(url);
    for (const key of [...u.searchParams.keys()]) {
      if (/^(utm_|gclid|gbraid|fbclid|msclkid|igshid|gad_source|gad_campaignid|clickref|ref|dclid)/i.test(key)) {
        u.searchParams.delete(key);
      }
    }
    let h = u.href.replace(/[?&]$/, '');
    return h;
  } catch (e) { return url; }
}

function resolveAwin(url) {
  // follow redirects quickly to get final store URL
  try {
    const out = execSync(`curl -s -o /dev/null -L --max-time 20 -w '%{url_effective}' '${url.replace(/'/g, "\\'")}'`, { encoding: 'utf8' }).trim();
    return out || url;
  } catch (e) {
    return url;
  }
}

for (const it of items) {
  let url = it.url;
  let store = it.store;
  if (store === 'awin1') {
    url = resolveAwin(url);
    const host = (url.replace(/^https?:\/\//, '').split('/')[0] || '').toLowerCase();
    const m = host.match(/([^.\/]+)\.(com|pt|es|eu|net)/);
    store = m ? m[1] : host;
  }
  it.url = cleanUrl(url);
  it.store = store;
  console.log(`${it.price.toFixed(2)}€ | ${it.name} | ${it.size ? 'tam ' + it.size : 'tam ?'} | ${store} | ${it.url}`);
}
