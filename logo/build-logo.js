// Génère le logo « La Table des Saisons » en deux versions (plein / contour)
// Usage : node logo/build-logo.js <dossier-polices> <dossier-sortie>
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [fontDir, outDir] = process.argv.slice(2);
const font = (f) => 'data:font/woff2;base64,' + fs.readFileSync(path.join(fontDir, f)).toString('base64');

const CX = 540, CY = 300;          // centre de l'assiette
const R_OUT = 205, R_IN = 168;     // bords de l'assiette

// Pétale en coordonnées locales : large, pointe arrondie inclinée, bord droit retourné (comme la photo)
function petal(L, W) {
  const body = `M0,0 C${W * 0.9},${-L * 0.12} ${W * 1.3},${-L * 0.5} ${W * 1.0},${-L * 0.8}
    C${W * 0.85},${-L * 0.96} ${W * 0.5},${-L * 1.03} ${W * 0.25},${-L}
    C${-W * 0.25},${-L * 0.95} ${-W * 0.9},${-L * 0.75} ${-W * 0.98},${-L * 0.45}
    C${-W * 1.02},${-L * 0.2} ${-W * 0.5},${-L * 0.05} 0,0 Z`;
  const fold = `M${W * 1.4},${-L * 0.3} C${W * 0.55},${-L * 0.5} ${W * 0.6},${-L * 0.8} ${W * 0.05},${-L * 1.1}`;
  const curl = fold + ` L${W * 2},${-L * 1.1} Z`;
  const rib = `M0,${-L * 0.12} C${W * 0.05},${-L * 0.45} ${W * 0.12},${-L * 0.7} ${W * 0.18},${-L * 0.86}`;
  return { body, curl, fold, rib };
}

const outer = [
  { a: -14, L: 186, k: -12 }, { a: 46, L: 166, k: -9 }, { a: 106, L: 180, k: -13 },
  { a: 168, L: 160, k: -8 }, { a: 228, L: 178, k: -12 }, { a: 290, L: 164, k: -10 },
];
const inner = [{ a: 18, L: 92, k: -16 }, { a: 138, L: 88, k: -16 }, { a: 258, L: 94, k: -16 }];

let uid = 0;
function flower(style) {
  const filled = style === 'plein';
  const draw = (list, layer) => list.map(({ a, L, k }) => {
    const p = petal(L, L * 0.34), id = `pc${uid++}`;
    const clip = `<clipPath id="${id}"><path d="${p.body}"/></clipPath>`;
    if (filled) {
      return `<g transform="rotate(${a}) skewX(${k})">${clip}
        <path d="${p.body}" fill="url(#rose${layer})"/>
        <g clip-path="url(#${id})">
          <path d="${p.curl}" fill="url(#curl)"/>
          <path d="${p.fold}" fill="none" stroke="#5E332E" stroke-opacity=".35" stroke-width="2.5"/>
          <path d="${p.body}" fill="none" stroke="#F8E9E3" stroke-width="5"/>
        </g>
        <path d="${p.rib}" fill="none" stroke="#5E332E" stroke-opacity=".3" stroke-width="1.6" stroke-linecap="round"/>
        <path d="${p.body}" fill="none" stroke="#5E332E" stroke-opacity=".25" stroke-width="1"/>
      </g>`;
    }
    return `<g transform="rotate(${a}) skewX(${k})">${clip}
      <path d="${p.body}" fill="${layer === 'B' ? '#F3E2DC' : '#EBD3CB'}"/>
      <g clip-path="url(#${id})">
        <path d="${p.curl}" fill="#FBF3EF"/>
        <path d="${p.fold}" fill="none" stroke="url(#goldU)" stroke-width="2"/>
      </g>
      <path d="${p.rib}" fill="none" stroke="url(#goldU)" stroke-width="1.3" stroke-linecap="round" stroke-opacity=".7"/>
      <path d="${p.body}" fill="none" stroke="url(#goldU)" stroke-width="2.8" stroke-linejoin="round"/>
    </g>`;
  }).join('');

  // pistils en spirale (sens de rotation des pétales)
  const stamens = Array.from({ length: 7 }, (_, i) => {
    const a = i * (360 / 7) + 10, len = 40 + (i % 3) * 9;
    return `<g transform="rotate(${a})">
      <path d="M0,0 C8,${-len * 0.4} 16,${-len * 0.75} 13,${-len}" fill="none" stroke="url(#goldU)" stroke-width="1.8" stroke-linecap="round"/>
      <ellipse cx="13" cy="${-len - 3}" rx="3.2" ry="5" fill="url(#goldU)" transform="rotate(22 13 ${-len - 3})"/>
    </g>`;
  }).join('');

  return `<g transform="translate(${CX} ${CY}) rotate(-4)">
    ${draw(outer, 'B')}${draw(inner, 'F')}
    ${stamens}
    <circle r="7" fill="url(#goldU)"/>
  </g>`;
}

function cutlery() {
  // fourchette (gauche) et couteau (droite), fins et élancés
  const fork = `<g transform="translate(300 300)">
    <path d="M-14,-150 L-14,-92 M0,-158 L0,-92 M14,-150 L14,-92" stroke="url(#gold)" stroke-width="3" stroke-linecap="round"/>
    <path d="M-17,-100 C-17,-70 -6,-62 -3,-50 L-5,120 C-5,132 5,132 5,120 L3,-50 C6,-62 17,-70 17,-100"
      fill="none" stroke="url(#gold)" stroke-width="3" stroke-linejoin="round"/>
  </g>`;
  const knife = `<g transform="translate(780 300)">
    <path d="M-4,-160 C14,-130 18,-70 10,-18 L4,-14 L5,120 C5,132 -5,132 -5,120 L-4,-14 C-6,-60 -10,-120 -4,-160 Z"
      fill="none" stroke="url(#gold)" stroke-width="3" stroke-linejoin="round"/>
    <path d="M-4,-14 L10,-18" stroke="url(#gold)" stroke-width="2"/>
  </g>`;
  return fork + knife;
}

function svg(style) {
  const filled = style === 'plein';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080">
  <defs>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#A9792A"/><stop offset=".45" stop-color="#E2C27A"/>
      <stop offset=".7" stop-color="#C39A45"/><stop offset="1" stop-color="#9A6C22"/>
    </linearGradient>
    <linearGradient id="goldU" x1="-200" y1="-200" x2="200" y2="200" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#A9792A"/><stop offset=".45" stop-color="#E2C27A"/>
      <stop offset=".7" stop-color="#C39A45"/><stop offset="1" stop-color="#9A6C22"/>
    </linearGradient>
    <radialGradient id="roseB" cx="0" cy="0" r="195" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#7A4640"/><stop offset=".5" stop-color="#A86F66"/><stop offset="1" stop-color="#C08A80"/>
    </radialGradient>
    <radialGradient id="roseF" cx="0" cy="0" r="100" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#5E332E"/><stop offset="1" stop-color="#9C645C"/>
    </radialGradient>
    <linearGradient id="curl" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#E9C9BF"/><stop offset="1" stop-color="#C9958B"/>
    </linearGradient>
    <radialGradient id="bg" cx=".5" cy=".38" r=".75">
      <stop offset="0" stop-color="#FCF8F1"/><stop offset="1" stop-color="#F1E9DC"/>
    </radialGradient>
  </defs>
  <rect width="1080" height="1080" fill="url(#bg)"/>
  ${cutlery()}
  <circle cx="${CX}" cy="${CY}" r="${R_OUT}" fill="${filled ? '#FBF6EE' : 'none'}" stroke="url(#gold)" stroke-width="4"/>
  <circle cx="${CX}" cy="${CY}" r="${R_IN}" fill="none" stroke="url(#gold)" stroke-width="1.6"/>
  ${flower(style)}
  <g font-family="CG" text-anchor="middle" fill="#1E2622">
    <text x="540" y="652" font-size="122" font-weight="500" letter-spacing="10">LA TABLE</text>
    <text x="540" y="718" font-size="40" font-weight="600" letter-spacing="14">DES</text>
    <line x1="250" y1="704" x2="470" y2="704" stroke="#C29A4E" stroke-width="2"/>
    <line x1="610" y1="704" x2="830" y2="704" stroke="#C29A4E" stroke-width="2"/>
    <text x="540" y="838" font-size="134" font-weight="500" letter-spacing="12">SAISONS</text>
    <text x="540" y="912" font-size="46" font-style="italic" letter-spacing="2" fill="#3A2E2B">Un Moment Suspendu</text>
    <line x1="330" y1="972" x2="515" y2="972" stroke="#C29A4E" stroke-width="1.6"/>
    <line x1="565" y1="972" x2="750" y2="972" stroke="#C29A4E" stroke-width="1.6"/>
    <path transform="translate(540 972)" d="M0,-16 C2,-4 4,-2 16,0 C4,2 2,4 0,16 C-2,4 -4,2 -16,0 C-4,-2 -2,-4 0,-16 Z" fill="url(#gold)"/>
  </g>
</svg>`;
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const css = `@font-face{font-family:CG;font-weight:500 600;src:url(${font('cg-normal-500.woff2')})}
    @font-face{font-family:CG;font-style:italic;font-weight:500;src:url(${font('cg-italic-500.woff2')})}
    html,body{margin:0}`;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 2 });
  for (const style of ['plein', 'contour']) {
    const s = svg(style);
    fs.writeFileSync(path.join(outDir, `logo-${style}.svg`), s);
    await page.setContent(`<style>${css}</style>${s}`);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(outDir, `logo-${style}.png`) });
  }
  await browser.close();
})();
