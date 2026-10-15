// Logo « La Table des Saisons » — trois emblèmes gastronomiques dans l'assiette
// Usage : node logo/build-logo-gastro.js <dossier-polices> <dossier-sortie>
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [fontDir, outDir] = process.argv.slice(2);
const font = (f) => 'data:font/woff2;base64,' + fs.readFileSync(path.join(fontDir, f)).toString('base64');

const CX = 540, CY = 290, R_OUT = 186, R_IN = 152;
const GREEN = '#1D4A2C';

// Trois emblèmes gastronomiques pour l'intérieur de l'assiette
const STAR = 'M0,-15 C1.5,-4 4,-1.5 15,0 C4,1.5 1.5,4 0,15 C-1.5,4 -4,1.5 -15,0 C-4,-1.5 -1.5,-4 0,-15 Z';

// A — le dressage : un trait de sauce au pinceau, points de sauce, quenelle et brin de thym
function dressage() {
  const n = 90, r = 104, a0 = 148, a1 = 352, outer = [], inner = [];
  for (let i = 0; i <= n; i++) {
    const s = i / n, ang = ((a0 + (a1 - a0) * s) * Math.PI) / 180;
    const t = 22 * Math.pow(Math.sin(Math.PI * Math.min(1, s * 1.05)), 0.6) * (1 - 0.65 * s) + 0.4;
    const rr = r + 6 * Math.sin(s * Math.PI * 1.3);
    outer.push([CX + Math.cos(ang) * (rr + t / 2), CY + Math.sin(ang) * (rr + t / 2)]);
    inner.push([CX + Math.cos(ang) * (rr - t / 2), CY + Math.sin(ang) * (rr - t / 2)]);
  }
  const pts = outer.concat(inner.reverse()).map((p) => p.map((v) => v.toFixed(1)).join(',')).join(' ');
  const streaks = [-5, -1.5, 3].map((d, k) => {
    const seg = [];
    for (let i = 8 + k * 6; i <= 55 + k * 8; i++) {
      const s = i / n, ang = ((a0 + (a1 - a0) * s) * Math.PI) / 180, rr = r + d + 6 * Math.sin(s * Math.PI * 1.3);
      seg.push(`${(CX + Math.cos(ang) * rr).toFixed(1)},${(CY + Math.sin(ang) * rr).toFixed(1)}`);
    }
    return `<polyline points="${seg.join(' ')}" fill="none" stroke="#F3E2B0" stroke-width=".9" stroke-opacity=".7" stroke-linecap="round"/>`;
  }).join('');
  const dots = [[0, 9], [1, 6.5], [2, 4.5]].map(([i, rad]) => {
    const ang = ((a1 + 14 + i * 13) * Math.PI) / 180, rr = r - 2 - i * 2;
    return `<circle cx="${CX + Math.cos(ang) * rr}" cy="${CY + Math.sin(ang) * rr}" r="${rad}" fill="url(#gold)"/>`;
  }).join('');
  // brin de thym : tige fine et feuilles opposées
  const thyme = Array.from({ length: 8 }, (_, i) => {
    const t = (i + 1) / 9, x = -56 + 112 * t, y = -8 * Math.sin(t * Math.PI), l = 8 - t * 3.5;
    return [1, -1].map((side) => `<path transform="translate(${x} ${y}) rotate(${side * 55 - 10})"
      d="M0,0 C${l * 0.35},${-l * 0.3} ${l * 0.35},${-l * 0.8} 0,${-l} C${-l * 0.35},${-l * 0.8} ${-l * 0.35},${-l * 0.3} 0,0 Z"/>`).join('');
  }).join('');
  return `
    <polygon points="${pts}" fill="url(#gold)"/>${dots}
    <g transform="translate(${CX + 10} ${CY + 8}) rotate(-24)">
      <path d="M-62,0 C-44,-25 44,-25 62,0 C44,25 -44,25 -62,0 Z" fill="#FFFDF8" stroke="url(#gold)" stroke-width="2.6"/>
      <path d="M-48,-2 C-26,-15 24,-16 48,-4" fill="none" stroke="#C9A24F" stroke-width="1" stroke-linecap="round" stroke-opacity=".7"/>
      <path d="M-40,7 C-18,-1 20,-2 44,4" fill="none" stroke="#C9A24F" stroke-width="1" stroke-linecap="round" stroke-opacity=".55"/>
    </g>
    <g transform="translate(${CX + 10} ${CY - 30}) rotate(-20) scale(1.25)" fill="#3E6A4A">
      <path d="M-62,4 C-30,-12 20,-12 60,-2" fill="none" stroke="#3E6A4A" stroke-width="1.3" stroke-linecap="round"/>${thyme}
    </g>`;
}

// B — la cloche de service
function cloche() {
  return `<g transform="translate(${CX} ${CY + 22})" fill="none" stroke="url(#gold)" stroke-linecap="round" stroke-linejoin="round">
    <path d="M-86,10 L86,10" stroke="#C39A45" stroke-width="4"/>
    <path d="M-70,24 C-40,29 40,29 70,24" stroke="#C39A45" stroke-width="2"/>
    <path d="M-74,10 C-74,-58 -34,-86 0,-86 C34,-86 74,-58 74,10" stroke-width="4"/>
    <path d="M-52,-14 C-50,-46 -30,-66 -8,-72" stroke-width="2.2" stroke-opacity=".75"/>
    <path d="M-10,-86 C-10,-92 -6,-95 0,-95 C6,-95 10,-92 10,-86" stroke-width="3"/>
    <circle cx="0" cy="-102" r="7" fill="url(#gold)" stroke="none"/>
    <path transform="translate(70 -88) scale(.9)" d="${STAR}" fill="url(#gold)" stroke="none"/>
    <path transform="translate(-78 -66) scale(.5)" d="${STAR}" fill="url(#gold)" stroke="none"/>
  </g>`;
}

// C — le monogramme de la maison
function monogramme() {
  return `<g font-family="CG" text-anchor="middle" font-style="italic" font-weight="500" fill="url(#goldT)">
    <text x="${CX - 30}" y="${CY + 40}" font-size="200">T</text>
    <text x="${CX + 36}" y="${CY + 68}" font-size="200">S</text>
  </g>
  <path transform="translate(${CX} ${CY - 124}) scale(.75)" d="${STAR}" fill="url(#gold)"/>
  <line x1="${CX - 50}" y1="${CY + 112}" x2="${CX + 50}" y2="${CY + 112}" stroke="#C9A24F" stroke-width="1.4"/>`;
}

const VARIANTS = { dressage, cloche, monogramme };

function plate(content) {
  return `
  <circle cx="${CX}" cy="${CY}" r="${R_OUT}" fill="#FFFDF8" stroke="url(#gold)" stroke-width="4"/>
  <circle cx="${CX}" cy="${CY}" r="${R_IN}" fill="none" stroke="url(#gold)" stroke-width="1.8"/>
  ${content}`;
}

// couverts fins qui épousent l'assiette
const cutlery = `<g fill="none" stroke="url(#goldV)" stroke-linecap="round" stroke-width="3">
  <path d="M318,176 C316,210 318,238 322,258 M330,174 C329,208 330,236 333,258 M342,176 C342,210 342,236 344,258"/>
  <path d="M318,250 C320,268 330,274 333,276 C336,274 346,268 344,250"/>
  <path d="M333,276 C326,330 336,390 384,452" stroke-width="3.6"/>
  <path d="M752,170 C778,200 790,248 772,292 C770,300 764,304 760,306 C764,360 752,410 712,456" stroke-width="3.4"/>
  <path d="M752,170 C760,214 762,262 760,306" stroke-width="2"/>
</g>`;

function svg(variant) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080">
  <defs>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#B38533"/><stop offset=".45" stop-color="#E6C878"/><stop offset=".75" stop-color="#C9A04A"/><stop offset="1" stop-color="#A6782A"/>
    </linearGradient>
    <linearGradient id="goldV" x1="0" y1="170" x2="0" y2="460" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#E6C878"/><stop offset=".5" stop-color="#B98A35"/><stop offset="1" stop-color="#D9B868"/>
    </linearGradient>
    <linearGradient id="goldT" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9E7026"/><stop offset=".5" stop-color="#D9B862"/><stop offset="1" stop-color="#A97B2C"/></linearGradient>
    <radialGradient id="petal" cx=".5" cy=".7" r=".8"><stop offset="0" stop-color="#F6CBD3"/><stop offset=".55" stop-color="#FFF5F6"/><stop offset="1" stop-color="#FFFFFF"/></radialGradient>
    <linearGradient id="basil" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#5FA544"/><stop offset="1" stop-color="#A8DC80"/></linearGradient>
    <linearGradient id="ginkgo" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#E9C95B"/><stop offset="1" stop-color="#F6E7A6"/></linearGradient>
    <radialGradient id="grape" cx=".35" cy=".35" r=".8"><stop offset="0" stop-color="#EEF5C8"/><stop offset="1" stop-color="#BFD682"/></radialGradient>
  </defs>
  <rect width="1080" height="1080" fill="#FBF8F0"/>
  ${cutlery}
  ${plate(VARIANTS[variant]())}
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
  for (const v of Object.keys(VARIANTS)) {
    const s = svg(v);
    fs.writeFileSync(path.join(outDir, `logo-gastro-${v}.svg`), s);
    await page.setContent(`<style>${css}</style>${s}`);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(outDir, `logo-gastro-${v}.png`) });
  }
  await browser.close();
})();
