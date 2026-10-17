const { execSync } = require('child_process');

const links = [
  ['Up Gaga tam33 SportZone', 'https://www.google.pt/aclk?sa=L&ai=DChsSEwjmmZO80oaXAxX3nVAGHea4Mp4YACICCAEQTRoCZGc&co=1&ase=2&cce=2&category=acrcp_v1_33&sig=AOD64_2I3SnDFsVo_nxKrP1H'],
  ['adidas 3.0 K Amazon', 'https://www.google.pt/aclk?sa=L&ai=DChsSEwjmmZO80oaXAxX3nVAGHea4Mp4YACICCAEQKRoCZGc&co=1&ase=2&sph=&cce=2&category=acrcp_v1_33&sig=AOD64_2ouBd5Xn8gMHQ'],
  ['Puma Catch Kids Amazon', 'https://www.google.pt/aclk?sa=L&ai=DChsSEwjmmZO80oaXAxX3nVAGHea4Mp4YACICCAEQSxoCZGc&co=1&ase=2&sph=&cce=2&category=acrcp_v1_33&sig=AOD64_0P9DhKVTSW4qs'],
  ['Umbro Nateo tam32 Kia', 'https://www.google.pt/aclk?sa=L&ai=DChsSEwjmmZO80oaXAxX3nVAGHea4Mp4YACICCAEQTxoCZGc&ae=2&co=1&ase=2&sph=&cce=2&category=acrcp_v1_71&sig=AOD64_0XIH9kxV'],
  ['Bluey Menina tam24 SportZone', 'https://www.google.pt/aclk?sa=L&ai=DChsSEwjmmZO80oaXAxX3nVAGHea4Mp4YACICCAEQIxoCZGc&co=1&ase=2&cce=2&category=acrcp_v1_33&sig=AOD64_18r4aXaHLHIoyOf167'],
];

function clean(u) {
  try {
    const x = new URL(u);
    ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','utm_id','utm_productid','utm_freeze_token','gclid','gbraid','fbclid','gclsrc','dclid','gad_source','gad_campaignid','gad_campaign','gad','gclid','srsltid','ref','shprz_campaign','clickref'].forEach(p => x.searchParams.delete(p));
    return x.toString();
  } catch (e) { return u; }
}

for (const [name, u] of links) {
  try {
    const out = execSync(`curl -s -o /dev/null -w '%{url_effective}' -L --max-time 15 -A "Mozilla/5.0 (Linux; Android 13; SM-T220) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36" "${u}"`, { timeout: 20000 }).toString();
    console.log(name, '=>', clean(out));
  } catch (e) {
    console.log(name, '=> ERR', e.message.slice(0, 100));
  }
}
