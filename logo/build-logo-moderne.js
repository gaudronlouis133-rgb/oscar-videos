// Logo « La Table des Saisons » — trois emblèmes minimalistes, esprit luxe moderne
// Usage : node logo/build-logo-moderne.js <dossier-polices> <dossier-sortie>
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [fontDir, outDir] = process.argv.slice(2);
const font = (f) => 'data:font/woff2;base64,' + fs.readFileSync(path.join(fontDir, f)).toString('base64');

const CX = 540, CY = 330, R = 128;
const GREEN = '#1F3B2D', GOLD = 'url(#gold)';

// 1 — Suspendu : l'assiette, un fil, une perle d'or en suspension
const suspendu = () => `
  <circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="${GOLD}" stroke-width="2"/>
  <line x1="${CX}" y1="${CY - R}" x2="${CX}" y2="${CY + 6}" stroke="#C3A15A" stroke-width="1.2"/>
  <circle cx="${CX}" cy="${CY + 24}" r="18" fill="url(#pearl)"/>`;

// 2 — Saisons : l'assiette en quatre arcs, un par saison
const saisons = () => {
  const cols = ['#B9CFB0', '#D9B45E', '#C98F7E', '#A9BCC4'];
  const gap = 7;
  const arcs = cols.map((c, i) => {
    const a0 = (-90 + i * 90 + gap) * Math.PI / 180, a1 = (-90 + (i + 1) * 90 - gap) * Math.PI / 180;
    const p = (a) => `${(CX + Math.cos(a) * R).toFixed(1)},${(CY + Math.sin(a) * R).toFixed(1)}`;
    return `<path d="M${p(a0)} A${R},${R} 0 0 1 ${p(a1)}" fill="none" stroke="${c}" stroke-width="5" stroke-linecap="round"/>`;
  }).join('');
  return `${arcs}<circle cx="${CX}" cy="${CY}" r="${R - 22}" fill="none" stroke="${GOLD}" stroke-width="1"/>
    <circle cx="${CX}" cy="${CY}" r="6" fill="${GOLD}"/>`;
};

// 3 — Couvert : assiette pleine, fourchette et couteau réduits à des lignes
const couvert = () => `
  <circle cx="${CX}" cy="${CY}" r="${R - 24}" fill="none" stroke="${GOLD}" stroke-width="2"/>
  <circle cx="${CX}" cy="${CY}" r="${R - 44}" fill="none" stroke="${GOLD}" stroke-width="1"/>
  <g stroke="#C3A15A" stroke-width="2" stroke-linecap="round" fill="none">
    <path d="M${CX - 152},${CY - 70} V${CY - 30} M${CX - 140},${CY - 70} V${CY - 30} M${CX - 164},${CY - 70} V${CY - 30}"/>
    <path d="M${CX - 164},${CY - 30} Q${CX - 152},${CY - 18} ${CX - 140},${CY - 30} M${CX - 152},${CY - 24} V${CY + 80}"/>
    <path d="M${CX + 152},${CY - 70} C${CX + 166},${CY - 50} ${CX + 166},${CY - 14} ${CX + 152},${CY - 2} V${CY + 80}"/>
  </g>
  <circle cx="${CX}" cy="${CY}" r="5" fill="${GOLD}"/>`;

const VARIANTS = { suspendu, saisons, couvert };

function svg(v) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080">
  <defs>
    <linearGradient id="gold" x1="380" y1="180" x2="700" y2="480" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#B08A3E"/><stop offset=".5" stop-color="#E3CA8A"/><stop offset="1" stop-color="#A9823A"/>
    </linearGradient>
    <radialGradient id="pearl" cx=".35" cy=".3" r=".8">
      <stop offset="0" stop-color="#F6E7BC"/><stop offset=".5" stop-color="#D2AE5E"/><stop offset="1" stop-color="#9C7630"/>
    </radialGradient>
  </defs>
  <rect width="1080" height="1080" fill="#F7F3EA"/>
  ${VARIANTS[v]()}
  <g text-anchor="middle" fill="${GREEN}">
    <text x="551" y="618" font-family="CG" font-size="76" font-weight="500" letter-spacing="22">LA TABLE</text>
    <text x="551" y="712" font-family="CG" font-size="76" font-weight="500" letter-spacing="22">DES SAISONS</text>
    <line x1="510" y1="770" x2="570" y2="770" stroke="#C3A15A" stroke-width="1.5"/>
    <text x="544.5" y="822" font-family="Jost" font-size="22" font-weight="300" letter-spacing="9">UN MOMENT SUSPENDU</text>
  </g>
</svg>`;
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const css = `@font-face{font-family:CG;font-weight:300 700;src:url(${font('cg-normal-500.woff2')})}
    @font-face{font-family:Jost;font-weight:100 900;src:url(${font('jost.woff2')})}
    html,body{margin:0}`;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 2 });
  for (const v of Object.keys(VARIANTS)) {
    const s = svg(v);
    fs.writeFileSync(path.join(outDir, `logo-moderne-${v}.svg`), s);
    await page.setContent(`<style>${css}</style>${s}`);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(outDir, `logo-moderne-${v}.png`) });
  }
  await browser.close();
})();
