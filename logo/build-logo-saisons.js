// Logo « La Table des Saisons » — assiette aux 4 saisons, palette fraîche
// Usage : node logo/build-logo-saisons.js <dossier-polices> <dossier-sortie>
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [fontDir, outDir] = process.argv.slice(2);
const font = (f) => 'data:font/woff2;base64,' + fs.readFileSync(path.join(fontDir, f)).toString('base64');

const CX = 540, CY = 290, R_OUT = 186, R_IN = 152;
const GREEN = '#1D4A2C';

const leaf = (x, y, len, w, rot, fill, rib = '#FFFFFF') => `
  <g transform="translate(${x} ${y}) rotate(${rot})">
    <path d="M0,0 C${w},${-len * 0.3} ${w * 0.9},${-len * 0.75} 0,${-len} C${-w * 0.9},${-len * 0.75} ${-w},${-len * 0.3} 0,0 Z" fill="${fill}"/>
    <path d="M0,${-len * 0.05} Q${w * 0.12},${-len * 0.5} 0,${-len * 0.92}" stroke="${rib}" stroke-opacity=".55" stroke-width="1" fill="none"/>
  </g>`;

// Printemps : fleurs de cerisier
const blossom = (x, y, r, rot = 0) => {
  const petals = Array.from({ length: 5 }, (_, i) => `
    <path transform="rotate(${i * 72})" d="M0,0 C${r * 0.55},${-r * 0.25} ${r * 0.6},${-r * 0.95} ${r * 0.12},${-r} L0,${-r * 0.88} L${-r * 0.12},${-r} C${-r * 0.6},${-r * 0.95} ${-r * 0.55},${-r * 0.25} 0,0 Z"
      fill="url(#petal)" stroke="#E9B8C1" stroke-width=".8"/>`).join('');
  const stamens = Array.from({ length: 8 }, (_, i) => {
    const a = (i * 45 * Math.PI) / 180, l = r * 0.42;
    return `<line x1="0" y1="0" x2="${Math.cos(a) * l}" y2="${Math.sin(a) * l}" stroke="#E2B94F" stroke-width=".8"/>
      <circle cx="${Math.cos(a) * l}" cy="${Math.sin(a) * l}" r="1.4" fill="#E2B94F"/>`;
  }).join('');
  return `<g transform="translate(${x} ${y}) rotate(${rot})">${petals}${stamens}<circle r="${r * 0.14}" fill="#F0C9A0"/></g>`;
};
const spring = `
  <path d="M-38,40 C-20,18 0,4 34,-30 M-6,10 C4,-6 6,-20 2,-36" stroke="#8A7A5E" stroke-width="2.4" fill="none" stroke-linecap="round"/>
  ${leaf(-22, 26, 22, 8, -120, '#8CC56A')}${leaf(18, -12, 20, 7, 70, '#9ED27A')}${leaf(-2, -10, 18, 6, -30, '#8CC56A')}
  ${blossom(-12, 6, 20, 10)}${blossom(22, -24, 16, 40)}${blossom(2, -38, 12, -20)}
  <ellipse cx="34" cy="-32" rx="4.5" ry="6.5" fill="#F7D5DB" stroke="#E9B8C1" stroke-width=".8" transform="rotate(45 34 -32)"/>
  <ellipse cx="-30" cy="32" rx="4" ry="6" fill="#F7D5DB" stroke="#E9B8C1" stroke-width=".8" transform="rotate(-50 -30 32)"/>`;

// Été : rondelle de citron et basilic
const lemonSegs = Array.from({ length: 8 }, (_, i) => `<path transform="rotate(${i * 45})" d="M0,-2.5 L-6,-15.5 Q0,-18.5 6,-15.5 Z" fill="#FBE98A"/>`).join('');
const summer = `
  ${leaf(-6, 30, 40, 15, -40, 'url(#basil)')}${leaf(-6, 30, 36, 14, 18, 'url(#basil)')}${leaf(-6, 30, 26, 10, -85, 'url(#basil)')}
  <path d="M-6,30 L-10,44" stroke="#6FA34E" stroke-width="2.2" stroke-linecap="round"/>
  <g transform="translate(18 10)">
    <circle r="22" fill="#F6D84C"/><circle r="19.5" fill="#FFFBE6"/><circle r="17.5" fill="#FFF6C9"/>${lemonSegs}
    <circle r="2" fill="#FFFBE6"/>
  </g>
  ${leaf(30, -14, 16, 6, 40, '#A6D985')}`;

// Automne (version lumineuse) : feuilles de ginkgo et raisin blanc
const ginkgo = (x, y, s, rot) => `
  <g transform="translate(${x} ${y}) rotate(${rot}) scale(${s})">
    <path d="M0,0 L0,20" stroke="#C9A443" stroke-width="2" stroke-linecap="round"/>
    <path d="M0,0 C-8,-6 -26,-16 -29,-33 Q-15,-45 -3,-40 L0,-33 L3,-40 Q15,-45 29,-33 C26,-16 8,-6 0,0 Z" fill="url(#ginkgo)" stroke="#D9B651" stroke-width=".8"/>
    ${[-24, -12, 0, 12, 24].map((d) => `<path d="M0,-2 L${d},-35" stroke="#FFF7D6" stroke-opacity=".7" stroke-width=".7"/>`).join('')}
  </g>`;
const grapes = [[0, 0], [11, 1], [-11, 1], [5, 10], [-6, 10], [0, 20], [16, 11], [-16, 11], [9, 20]]
  .map(([x, y]) => `<circle cx="${x}" cy="${y}" r="6.5" fill="url(#grape)" stroke="#A9C46B" stroke-width=".6"/>
    <circle cx="${x - 2}" cy="${y - 2}" r="1.6" fill="#FFFFFF" opacity=".8"/>`).join('');
const autumn = `
  ${ginkgo(-18, 0, 1.0, -28)}${ginkgo(10, -14, 0.8, 24)}
  <path d="M14,6 C16,10 18,14 18,16" stroke="#8FA85A" stroke-width="1.8" fill="none"/>
  ${leaf(28, 10, 16, 7, 60, '#9ED27A')}
  <g transform="translate(16 22)">${grapes}</g>`;

// Hiver (version fraîche) : brin de sapin vert sauge, baies blanches, flocon givré
const needles = (x0, y0, x1, y1, n, len) => Array.from({ length: n }, (_, i) => {
  const t = (i + 1) / (n + 1), x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t;
  const a = Math.atan2(y1 - y0, x1 - x0), l = len * (1 - t * 0.45);
  return [0.75, -0.75].map((d) => `<line x1="${x}" y1="${y}" x2="${x + Math.cos(a + d) * l}" y2="${y + Math.sin(a + d) * l}"/>`).join('');
}).join('');
const flake = Array.from({ length: 6 }, (_, i) => `<g transform="rotate(${i * 60})">
  <line x1="0" y1="0" x2="0" y2="-13"/><line x1="0" y1="-8" x2="-4" y2="-11"/><line x1="0" y1="-8" x2="4" y2="-11"/></g>`).join('');
const winter = `
  <g stroke="#7FAE8E" stroke-width="1.3" stroke-linecap="round">${needles(-34, 34, 26, -30, 12, 15)}</g>
  <g stroke="#9CC4A6" stroke-width="1.1" stroke-linecap="round">${needles(-6, 4, -30, -26, 6, 10)}</g>
  <path d="M-34,34 L26,-30 M-6,4 L-30,-26" stroke="#7C8F6E" stroke-width="2" stroke-linecap="round"/>
  ${[[14, 22], [22, 28], [8, 30], [18, 36]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="5" fill="#FFFFFF" stroke="#C9D8CF" stroke-width="1"/>`).join('')}
  <path d="M6,14 L14,22 M14,22 L22,28" stroke="#9AAE8C" stroke-width="1" fill="none"/>
  <g transform="translate(30 4)" stroke="#8DB6C9" stroke-width="1.5" stroke-linecap="round">${flake}</g>`;

function plate() {
  const q = 66;
  const gap = 18, rin = R_IN - 10;
  return `
  <circle cx="${CX}" cy="${CY}" r="${R_OUT}" fill="#FFFDF8" stroke="url(#gold)" stroke-width="4"/>
  <circle cx="${CX}" cy="${CY}" r="${R_IN}" fill="none" stroke="url(#gold)" stroke-width="1.8"/>
  <g stroke="#C9A24F" stroke-width="1.4">
    <line x1="${CX}" y1="${CY - rin}" x2="${CX}" y2="${CY - gap}"/><line x1="${CX}" y1="${CY + gap}" x2="${CX}" y2="${CY + rin}"/>
    <line x1="${CX - rin}" y1="${CY}" x2="${CX - gap}" y2="${CY}"/><line x1="${CX + gap}" y1="${CY}" x2="${CX + rin}" y2="${CY}"/>
  </g>
  <path transform="translate(${CX} ${CY})" d="M0,-15 C1.5,-4 4,-1.5 15,0 C4,1.5 1.5,4 0,15 C-1.5,4 -4,1.5 -15,0 C-4,-1.5 -1.5,-4 0,-15 Z" fill="url(#gold)"/>
  <g transform="translate(${CX - q} ${CY - q}) scale(1.25)">${spring}</g>
  <g transform="translate(${CX + q} ${CY - q}) scale(1.25)">${summer}</g>
  <g transform="translate(${CX - q} ${CY + q}) scale(1.25)">${autumn}</g>
  <g transform="translate(${CX + q} ${CY + q}) scale(1.25)">${winter}</g>`;
}

// couverts fins qui épousent l'assiette
const cutlery = `<g fill="none" stroke="url(#goldV)" stroke-linecap="round" stroke-width="3">
  <path d="M318,176 C316,210 318,238 322,258 M330,174 C329,208 330,236 333,258 M342,176 C342,210 342,236 344,258"/>
  <path d="M318,250 C320,268 330,274 333,276 C336,274 346,268 344,250"/>
  <path d="M333,276 C326,330 336,390 384,452" stroke-width="3.6"/>
  <path d="M752,170 C778,200 790,248 772,292 C770,300 764,304 760,306 C764,360 752,410 712,456" stroke-width="3.4"/>
  <path d="M752,170 C760,214 762,262 760,306" stroke-width="2"/>
</g>`;

function svg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080">
  <defs>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#B38533"/><stop offset=".45" stop-color="#E6C878"/><stop offset=".75" stop-color="#C9A04A"/><stop offset="1" stop-color="#A6782A"/>
    </linearGradient>
    <linearGradient id="goldV" x1="0" y1="170" x2="0" y2="460" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#E6C878"/><stop offset=".5" stop-color="#B98A35"/><stop offset="1" stop-color="#D9B868"/>
    </linearGradient>
    <radialGradient id="petal" cx=".5" cy=".7" r=".8"><stop offset="0" stop-color="#F6CBD3"/><stop offset=".55" stop-color="#FFF5F6"/><stop offset="1" stop-color="#FFFFFF"/></radialGradient>
    <linearGradient id="basil" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#5FA544"/><stop offset="1" stop-color="#A8DC80"/></linearGradient>
    <linearGradient id="ginkgo" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#E9C95B"/><stop offset="1" stop-color="#F6E7A6"/></linearGradient>
    <radialGradient id="grape" cx=".35" cy=".35" r=".8"><stop offset="0" stop-color="#EEF5C8"/><stop offset="1" stop-color="#BFD682"/></radialGradient>
  </defs>
  <rect width="1080" height="1080" fill="#FBF8F0"/>
  ${cutlery}
  ${plate()}
  <g font-family="CG" text-anchor="middle" fill="${GREEN}" font-weight="600">
    <text x="540" y="598" font-size="104" letter-spacing="2"><tspan font-size="128">L</tspan>A <tspan font-size="128">T</tspan>ABLE</text>
    <text x="540" y="668" font-size="50" letter-spacing="6">DES</text>
    <line x1="258" y1="652" x2="455" y2="652" stroke="#C9A24F" stroke-width="1.8"/>
    <line x1="625" y1="652" x2="822" y2="652" stroke="#C9A24F" stroke-width="1.8"/>
    <text x="540" y="782" font-size="118" letter-spacing="3"><tspan font-size="146">S</tspan>AISONS</text>
    <text x="540" y="878" font-size="52" font-style="italic" font-weight="500" letter-spacing="1.5">Un Moment Suspendu</text>
    <line x1="340" y1="938" x2="515" y2="938" stroke="#C9A24F" stroke-width="1.6"/>
    <line x1="565" y1="938" x2="740" y2="938" stroke="#C9A24F" stroke-width="1.6"/>
    <path transform="translate(540 938)" d="M0,-16 C2,-4 4,-2 16,0 C4,2 2,4 0,16 C-2,4 -4,2 -16,0 C-4,-2 -2,-4 0,-16 Z" fill="url(#gold)"/>
  </g>
</svg>`;
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const css = `@font-face{font-family:CG;font-weight:500 700;src:url(${font('cg-normal-500.woff2')})}
    @font-face{font-family:CG;font-style:italic;font-weight:500;src:url(${font('cg-italic-500.woff2')})}
    html,body{margin:0}`;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 2 });
  const s = svg();
  fs.writeFileSync(path.join(outDir, 'logo-saisons.svg'), s);
  await page.setContent(`<style>${css}</style>${s}`);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(outDir, 'logo-saisons.png') });
  await browser.close();
})();
