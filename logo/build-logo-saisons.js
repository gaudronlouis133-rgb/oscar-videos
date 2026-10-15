// Logo « La Table des Saisons » — assiette aux 4 saisons, palette fraîche
// Usage : node logo/build-logo-saisons.js <dossier-polices> <dossier-sortie>
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [fontDir, outDir] = process.argv.slice(2);
const font = (f) => 'data:font/woff2;base64,' + fs.readFileSync(path.join(fontDir, f)).toString('base64');

const CX = 540, CY = 290, R_OUT = 186, R_IN = 152;
const GREEN = '#1D4A2C';

// Style gravure botanique : trait fin, nervures, lavis très léger
const INK = '#3E6A4A', WASH = 'rgba(126,176,112,.16)', GOLD_INK = '#B48E36';

function leaf(x, y, len, w, rot, o = {}) {
  const { bend = 0, ink = INK, wash = WASH, veins = 3, sw = 1.1 } = o;
  const vein = Array.from({ length: veins }, (_, i) => {
    const t = (i + 1) / (veins + 1), mx = bend * t * t, my = -len * t, k = (1 - t * 0.55) * w * 0.8;
    return `<path d="M${mx},${my} Q${mx + k * 0.6},${my - len * 0.05} ${mx + k},${my - len * 0.13}"/>
      <path d="M${mx},${my} Q${mx - k * 0.6},${my - len * 0.05} ${mx - k},${my - len * 0.13}"/>`;
  }).join('');
  return `<g transform="translate(${x} ${y}) rotate(${rot})" stroke="${ink}" stroke-linecap="round" stroke-linejoin="round">
    <path d="M0,0 C${w * 1.05},${-len * 0.2} ${w * 0.95 + bend * 0.5},${-len * 0.72} ${bend},${-len}
      C${-w * 0.85 + bend * 0.5},${-len * 0.72} ${-w * 1.05},${-len * 0.22} 0,0 Z" fill="${wash}" stroke-width="${sw}"/>
    <path d="M0,${len * 0.08} L0,0 Q${bend * 0.25},${-len * 0.5} ${bend},${-len}" fill="none" stroke-width="${sw * 0.8}"/>
    <g fill="none" stroke-width=".55" stroke-opacity=".75">${vein}</g>
  </g>`;
}

// Printemps : branche de cerisier en fleurs
function blossom(x, y, r, rot = 0, tilt = 1) {
  const petal = `M0,-${r * 0.16} C${r * 0.5},${-r * 0.3} ${r * 0.62},${-r * 0.82} ${r * 0.24},${-r}
    Q${r * 0.1},${-r * 0.97} 0,${-r * 0.86} Q${-r * 0.1},${-r * 0.97} ${-r * 0.24},${-r}
    C${-r * 0.62},${-r * 0.82} ${-r * 0.5},${-r * 0.3} 0,-${r * 0.16} Z`;
  const petals = Array.from({ length: 5 }, (_, i) => `<g transform="rotate(${i * 72})">
    <path d="${petal}" fill="rgba(236,178,190,.32)" stroke="#B9707E" stroke-width=".9" stroke-linejoin="round"/>
    <path d="M0,${-r * 0.22} Q${r * 0.04},${-r * 0.5} 0,${-r * 0.72}" fill="none" stroke="#B9707E" stroke-width=".45" stroke-opacity=".6"/>
  </g>`).join('');
  const stamens = Array.from({ length: 11 }, (_, i) => {
    const an = (i * 360 / 11 + 8) * Math.PI / 180, l = r * (0.38 + (i % 3) * 0.06);
    const ex = Math.cos(an) * l, ey = Math.sin(an) * l;
    return `<path d="M0,0 Q${ex * 0.5 + ey * 0.1},${ey * 0.5 - ex * 0.1} ${ex},${ey}" fill="none" stroke="${GOLD_INK}" stroke-width=".55"/>
      <circle cx="${ex}" cy="${ey}" r=".95" fill="${GOLD_INK}"/>`;
  }).join('');
  return `<g transform="translate(${x} ${y}) rotate(${rot}) scale(1 ${tilt})">${petals}${stamens}
    <circle r="${r * 0.1}" fill="#C98F5A"/></g>`;
}
const bud = (x, y, rot, s = 1) => `<g transform="translate(${x} ${y}) rotate(${rot}) scale(${s})">
  <path d="M0,0 C4.5,-4 4.5,-11 0,-15 C-4.5,-11 -4.5,-4 0,0 Z" fill="rgba(236,178,190,.45)" stroke="#B9707E" stroke-width=".9"/>
  <path d="M0,1 C3,-2 4,-5 3.5,-7 M0,1 C-3,-2 -4,-5 -3.5,-7" fill="none" stroke="${INK}" stroke-width=".9" stroke-linecap="round"/>
</g>`;
const spring = `
  <g fill="none" stroke="#6E5C46" stroke-linecap="round">
    <path d="M-46,46 C-28,30 -14,16 0,2 C12,-10 26,-26 44,-38" stroke-width="1.9"/>
    <path d="M-10,12 C-12,-4 -16,-20 -24,-36" stroke-width="1.3"/>
    <path d="M22,-20 C24,-30 26,-38 24,-46" stroke-width="1"/>
    <path d="M-28,30 l-6,-2 M8,-6 l5,2" stroke-width="1"/>
  </g>
  ${leaf(-30, 32, 20, 7, -110, { bend: -3, veins: 2 })}${leaf(4, -2, 18, 6, 55, { bend: 3, veins: 2 })}
  ${leaf(-22, -30, 15, 5, -35, { bend: -2, veins: 2 })}
  ${bud(44, -38, 50)}${bud(24, -46, 8, 0.85)}${bud(-25, -37, -25, 0.8)}
  ${blossom(-8, 14, 19, 12, 0.92)}${blossom(24, -14, 15, 40, 0.8)}${blossom(-22, -16, 11, -10, 0.85)}`;

// Été : branche de citronnier
const lemonDots = [[-8, -6], [-2, -9], [6, -7], [10, -1], [-11, 2], [3, 6], [-5, 8], [9, 7], [0, 0], [-14, -3]]
  .map(([x, y]) => `<circle cx="${x}" cy="${y}" r=".6" fill="${GOLD_INK}" opacity=".55"/>`).join('');
const smallFlower = (x, y, r, rot) => `<g transform="translate(${x} ${y}) rotate(${rot})">${Array.from({ length: 5 }, (_, i) =>
  `<path transform="rotate(${i * 72})" d="M0,-1.5 C${r * 0.35},${-r * 0.4} ${r * 0.25},${-r * 0.9} 0,${-r} C${-r * 0.25},${-r * 0.9} ${-r * 0.35},${-r * 0.4} 0,-1.5 Z"
     fill="#FFFFFF" stroke="${INK}" stroke-width=".7"/>`).join('')}<circle r="1.6" fill="${GOLD_INK}"/></g>`;
const summer = `
  <path d="M-44,-34 C-24,-24 -6,-14 8,-2 C16,6 18,12 18,16" fill="none" stroke="#6E5C46" stroke-width="1.7" stroke-linecap="round"/>
  ${leaf(-30, -27, 30, 9, -70, { bend: -4, veins: 4 })}${leaf(-14, -18, 34, 10, -10, { bend: 4, veins: 4 })}
  ${leaf(-2, -9, 30, 9, 60, { bend: 3, veins: 4 })}${leaf(8, -2, 26, 8, 105, { bend: 3, veins: 3 })}
  <g transform="translate(16 30) rotate(-18)">
    <path d="M-20,0 C-20,-13 -9,-17 0,-17 C9,-17 20,-13 21,-2 Q26,0 21,2 C20,13 9,17 0,17 C-9,17 -20,13 -21,2 Q-25,0 -20,0 Z"
      fill="rgba(240,212,96,.38)" stroke="${GOLD_INK}" stroke-width="1.1" stroke-linejoin="round"/>
    <path d="M-12,-9 Q-4,-14 6,-12" fill="none" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" opacity=".8"/>
    ${lemonDots}
  </g>
  <path d="M18,16 L17,13" stroke="${INK}" stroke-width="1.2"/>
  ${smallFlower(-38, -40, 7, 10)}${smallFlower(30, -26, 6, -20)}
  <path d="M8,-2 C18,-10 24,-18 30,-26" fill="none" stroke="#6E5C46" stroke-width="1" stroke-linecap="round"/>`;

// Automne (lumineux) : feuilles de ginkgo
function ginkgo(x, y, s, rot) {
  const veins = Array.from({ length: 13 }, (_, i) => {
    const t = -1 + (i * 2) / 12, ex = t * 27, ey = -35 + Math.abs(t) * 3 + t * t * 5;
    return `<path d="M0,-1 Q${ex * 0.4},${ey * 0.55} ${ex},${ey}"/>`;
  }).join('');
  return `<g transform="translate(${x} ${y}) rotate(${rot}) scale(${s})" stroke="${GOLD_INK}" stroke-linecap="round" stroke-linejoin="round">
    <path d="M0,0 C1,8 0,16 -2,24" fill="none" stroke-width="1.2"/>
    <path d="M0,0 C-9,-6 -25,-17 -29,-31 Q-25,-37 -18,-39 Q-12,-41 -8,-38 Q-4,-41 -2,-37 L0,-31 L2,-37 Q5,-41 9,-38 Q14,-41 19,-38 Q26,-37 29,-31 C25,-17 9,-6 0,0 Z"
      fill="rgba(232,198,98,.28)" stroke-width="1.1"/>
    <g fill="none" stroke-width=".45" stroke-opacity=".8">${veins}</g>
  </g>`;
}
const autumn = `
  ${ginkgo(-6, 14, 1.05, -32)}${ginkgo(8, 6, 0.85, 26)}${ginkgo(-24, 30, 0.6, -70)}
  ${leaf(22, 30, 22, 6, 70, { bend: 2, veins: 3 })}${leaf(26, 26, 18, 5, 120, { bend: 2, veins: 2 })}
  <path d="M-6,36 C6,32 16,30 30,30" fill="none" stroke="#6E5C46" stroke-width="1.2" stroke-linecap="round"/>`;

// Hiver (frais) : branche de sapin et baies de symphorine
function fir(x0, y0, x1, y1, cx, cy, n, len) {
  const pt = (t) => [(1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1];
  let out = `<path d="M${x0},${y0} Q${cx},${cy} ${x1},${y1}" fill="none" stroke="#6E5C46" stroke-width="1.5"/>`;
  for (let i = 1; i <= n; i++) {
    const t = i / (n + 1), [x, y] = pt(t), [xa, ya] = pt(Math.min(1, t + 0.01));
    const a = Math.atan2(ya - y, xa - x), l = len * (1 - t * 0.5);
    for (const d of [0.6, -0.6]) {
      const ex = x + Math.cos(a + d) * l, ey = y + Math.sin(a + d) * l;
      out += `<path d="M${x},${y} Q${x + Math.cos(a + d * 0.7) * l * 0.6},${y + Math.sin(a + d * 0.7) * l * 0.6} ${ex},${ey}"/>`;
    }
  }
  return out;
}
const berries = [[14, 22, 4.6], [22, 27, 4.2], [12, 31, 4], [21, 36, 3.6]]
  .map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="#FFFFFF" stroke="#8FAE9C" stroke-width=".9"/>
    <circle cx="${x - r * 0.35}" cy="${y - r * 0.35}" r="${r * 0.25}" fill="#DCE9E3"/>`).join('');
const winter = `
  <g stroke="#4F7F62" stroke-width=".8" stroke-linecap="round" fill="none">
    ${fir(-42, 38, 30, -38, -10, -6, 26, 13)}
    ${fir(-14, 8, -36, -30, -30, -8, 10, 9)}
  </g>
  <path d="M4,10 C10,16 14,20 14,22 M10,16 C16,22 20,24 22,27 M8,22 C10,26 12,28 12,31" fill="none" stroke="#7E8F78" stroke-width=".9"/>
  ${leaf(4, 10, 12, 4, 70, { veins: 1 })}
  ${berries}`;

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
  <g transform="translate(${CX - q + 2} ${CY - q + 12}) scale(1.08)">${spring}</g>
  <g transform="translate(${CX + q + 2} ${CY - q + 14}) scale(1.08)">${summer}</g>
  <g transform="translate(${CX - q + 6} ${CY + q - 4}) scale(1.15)">${autumn}</g>
  <g transform="translate(${CX + q - 2} ${CY + q - 4}) scale(1.15)">${winter}</g>`;
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
