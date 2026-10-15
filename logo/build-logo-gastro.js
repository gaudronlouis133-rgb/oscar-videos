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

// A — le dressage : trait de sauce au pinceau, quenelle sculptée, brin de thym
function brushArc(r, a0, a1, profile, n = 120) {
  const at = (s, rr) => {
    const ang = ((a0 + (a1 - a0) * s) * Math.PI) / 180;
    return [CX + Math.cos(ang) * rr, CY + Math.sin(ang) * rr];
  };
  const outer = [], inner = [];
  for (let i = 0; i <= n; i++) {
    const sN = i / n, t = profile(sN), rr = r + 5 * Math.sin(sN * Math.PI);
    outer.push(at(sN, rr + t / 2)); inner.push(at(sN, rr - t / 2));
  }
  return outer.concat(inner.reverse()).map((p) => p.map((v) => v.toFixed(1)).join(',')).join(' ');
}
function strand(r, a0, a1, d, from, to, w) {
  const pts = [];
  for (let i = 0; i <= 40; i++) {
    const sN = from + ((to - from) * i) / 40, ang = ((a0 + (a1 - a0) * sN) * Math.PI) / 180;
    const rr = r + d + 5 * Math.sin(sN * Math.PI);
    pts.push(`${(CX + Math.cos(ang) * rr).toFixed(1)},${(CY + Math.sin(ang) * rr).toFixed(1)}`);
  }
  return `<polyline points="${pts.join(' ')}" fill="none" stroke="url(#goldU)" stroke-width="${w}" stroke-linecap="round"/>`;
}
function dressage() {
  const r = 108, a0 = 160, a1 = 28;
  // corps du trait : attaque franche à gauche, s'affine vers la droite
  const body = brushArc(r, a0, a1, (x) => (x < 0.06 ? 24 * Math.sqrt(x / 0.06) : 24 * Math.pow(Math.max(0, 1 - (x - 0.06) / 0.62), 1.2)) + 0.2, 140);
  // fin de pinceau effilochée
  const strands = [[-7, 0.42, 0.84, 1.3], [-3.5, 0.4, 0.95, 1.9], [0, 0.38, 1, 2.4], [3.5, 0.42, 0.9, 1.6], [6.5, 0.46, 0.78, 1.1]]
    .map(([d, f, t, w]) => strand(r, a0, a1, d, f, t, w)).join('');
  const dots = [[1, 7], [2, 5], [3, 3.4]].map(([i, rad]) => {
    const ang = ((a1 - i * 10) * Math.PI) / 180, rr = r + 2;
    return `<circle cx="${(CX + Math.cos(ang) * rr).toFixed(1)}" cy="${(CY + Math.sin(ang) * rr).toFixed(1)}" r="${rad}" fill="url(#goldU)"/>`;
  }).join('');
  // brin de thym : feuilles opposées, de plus en plus petites vers la pointe
  const thyme = Array.from({ length: 11 }, (_, i) => {
    const t = (i + 1) / 12, x = -64 + 128 * t, y = -9 * Math.sin(t * Math.PI) + 4 * t, l = 9.5 - t * 5;
    return [1, -1].map((side) => `<path transform="translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${side * 58 + 12})"
      d="M0,0 C${l * 0.42},${-l * 0.3} ${l * 0.38},${-l * 0.82} 0,${-l} C${-l * 0.38},${-l * 0.82} ${-l * 0.42},${-l * 0.3} 0,0 Z"/>`).join('');
  }).join('');
  return `
    <polygon points="${body}" fill="url(#goldU)"/>${strands}${dots}
    <g transform="translate(${CX - 4} ${CY - 6}) rotate(-12)">
      <ellipse cx="4" cy="20" rx="60" ry="9" fill="#E9D9B4" opacity=".45"/>
      <path d="M-62,6 C-52,-18 -18,-26 14,-24 C42,-22 60,-10 64,4 C56,20 28,28 0,28 C-30,28 -54,22 -62,6 Z" fill="url(#quenelle)" stroke="url(#goldU)" stroke-width="1.5" stroke-linejoin="round"/>
      <path d="M-58,5 C-34,-6 12,-10 60,3" fill="none" stroke="url(#goldU)" stroke-width="1.1" stroke-linecap="round"/>
      <path d="M-50,-10 C-28,-20 8,-22 40,-16" fill="none" stroke="#C9A24F" stroke-width=".9" stroke-opacity=".6" stroke-linecap="round"/>
      <path d="M-46,14 C-20,10 18,10 52,10" fill="none" stroke="#C9A24F" stroke-width=".9" stroke-opacity=".5" stroke-linecap="round"/>
    </g>
    <g transform="translate(${CX + 30} ${CY - 34}) rotate(-22) scale(.9)" fill="#3E6A4A">
      <path d="M-70,6 C-36,-12 20,-14 66,-4" fill="none" stroke="#3E6A4A" stroke-width="1.4" stroke-linecap="round"/>
      <path d="M-70,6 C-74,8 -78,12 -80,16" fill="none" stroke="#5E5040" stroke-width="1.4" stroke-linecap="round"/>${thyme}
      <circle cx="68" cy="-4" r="2.2"/>
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
    <linearGradient id="goldU" x1="400" y1="160" x2="680" y2="420" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#A9792A"/><stop offset=".45" stop-color="#E2C27A"/><stop offset=".7" stop-color="#C39A45"/><stop offset="1" stop-color="#9A6C22"/></linearGradient>
    <linearGradient id="quenelle" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFDF7"/><stop offset=".55" stop-color="#FBF2DF"/><stop offset="1" stop-color="#EEDDB6"/></linearGradient>
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
