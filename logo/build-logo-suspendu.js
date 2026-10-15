// Logo final « La Table des Saisons » — emblème Suspendu et ses déclinaisons
// Usage : node logo/build-logo-suspendu.js <dossier-polices> <dossier-sortie>
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [fontDir, outDir] = process.argv.slice(2);
const font = (f) => 'data:font/woff2;base64,' + fs.readFileSync(path.join(fontDir, f)).toString('base64');

const THEMES = {
  clair: { bg: '#F7F3EA', text: '#1F3B2D', line: '#C3A15A' },
  vert: { bg: '#1F3B2D', text: '#F3EBDA', line: '#CDAE68' },
};

// L'assiette, un fil d'or, une perle en suspension
function emblem(cx, cy, r, t) {
  const pr = r * 0.14;
  return `<g>
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="url(#gold)" stroke-width="${r * 0.016}"/>
    <line x1="${cx}" y1="${cy - r}" x2="${cx}" y2="${cy + r * 0.19 - pr}" stroke="${t.line}" stroke-width="${r * 0.009}"/>
    <circle cx="${cx}" cy="${cy + r * 0.19}" r="${pr}" fill="url(#pearl)"/>
    <ellipse cx="${cx - pr * 0.35}" cy="${cy + r * 0.19 - pr * 0.4}" rx="${pr * 0.28}" ry="${pr * 0.18}" fill="#FFF8E4" opacity=".7" transform="rotate(-30 ${cx - pr * 0.35} ${cy + r * 0.19 - pr * 0.4})"/>
  </g>`;
}

const defs = `<defs>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1" gradientUnits="objectBoundingBox">
    <stop offset="0" stop-color="#B08A3E"/><stop offset=".5" stop-color="#E3CA8A"/><stop offset="1" stop-color="#A9823A"/>
  </linearGradient>
  <radialGradient id="pearl" cx=".35" cy=".3" r=".8">
    <stop offset="0" stop-color="#F6E7BC"/><stop offset=".5" stop-color="#D2AE5E"/><stop offset="1" stop-color="#93702C"/>
  </radialGradient>
</defs>`;

// lettres espacées : on décale de la moitié de l'interlettrage pour un vrai centrage
const txt = (x, y, size, ls, fam, weight, fill, s, anchor = 'middle') =>
  `<text x="${anchor === 'middle' ? x + ls / 2 : x}" y="${y}" font-family="${fam}" font-size="${size}" font-weight="${weight}" letter-spacing="${ls}" fill="${fill}" text-anchor="${anchor}">${s}</text>`;

function vertical(t) {
  return { w: 1080, h: 1080, body: `<rect width="1080" height="1080" fill="${t.bg}"/><g transform="translate(0 34)">
    ${emblem(540, 330, 128, t)}
    ${txt(540, 618, 76, 22, 'CG', 500, t.text, 'LA TABLE')}
    ${txt(540, 712, 76, 22, 'CG', 500, t.text, 'DES SAISONS')}
    <line x1="510" y1="770" x2="570" y2="770" stroke="${t.line}" stroke-width="1.5"/>
    ${txt(540, 822, 22, 9, 'Jost', 300, t.text, 'UN MOMENT SUSPENDU')}</g>` };
}

function horizontal(t) {
  return { w: 1800, h: 600, body: `<rect width="1800" height="600" fill="${t.bg}"/>
    ${emblem(390, 300, 150, t)}
    <line x1="620" y1="170" x2="620" y2="430" stroke="${t.line}" stroke-width="1.2"/>
    ${txt(690, 268, 78, 20, 'CG', 500, t.text, 'LA TABLE', 'start')}
    ${txt(690, 360, 78, 20, 'CG', 500, t.text, 'DES SAISONS', 'start')}
    ${txt(692, 430, 22, 9, 'Jost', 300, t.text, 'UN MOMENT SUSPENDU', 'start')}` };
}

function icone(t) {
  return { w: 1080, h: 1080, body: `<rect width="1080" height="1080" fill="${t.bg}"/>${emblem(540, 540, 300, t)}` };
}

const OUTPUTS = [
  ['principal', vertical, 'clair'], ['principal-fond-vert', vertical, 'vert'],
  ['horizontal', horizontal, 'clair'], ['horizontal-fond-vert', horizontal, 'vert'],
  ['icone', icone, 'clair'], ['icone-fond-vert', icone, 'vert'],
];

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const css = `@font-face{font-family:CG;font-weight:300 700;src:url(${font('cg-normal-500.woff2')})}
    @font-face{font-family:Jost;font-weight:100 900;src:url(${font('jost.woff2')})}
    html,body{margin:0}`;
  const browser = await chromium.launch();
  for (const [name, fn, theme] of OUTPUTS) {
    const { w, h, body } = fn(THEMES[theme]);
    const s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">${defs}${body}</svg>`;
    fs.writeFileSync(path.join(outDir, `suspendu-${name}.svg`), s);
    const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
    await page.setContent(`<style>${css}</style>${s}`);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(outDir, `suspendu-${name}.png`) });
    await page.close();
  }
  await browser.close();
})();
