// Carte postale « La Table des Saisons » — format A6 (148 × 105 mm) + 3 mm de fond perdu
// Usage : node carte/build-carte.js <dossier-polices>
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const fontDir = process.argv[2];
const b64 = (f, mime) => `data:${mime};base64,` + fs.readFileSync(f).toString('base64');
const font = (f) => b64(path.join(fontDir, f), 'font/woff2');
const here = (f) => path.join(__dirname, f);

// Coordonnées : à remplacer par les vraies informations du restaurant
const INFO = {
  telephone: '00 00 00 00 00',
  adresse: 'Adresse du restaurant<br>Code postal Ville',
  site: 'www.latabledessaisons.fr',
  instagram: '@latabledessaisons',
};

const css = `
@font-face{font-family:CG;font-weight:300 700;src:url(${font('cg-normal-500.woff2')})}
@font-face{font-family:CG;font-style:italic;font-weight:300 700;src:url(${font('cg-italic-500.woff2')})}
@font-face{font-family:Jost;font-weight:100 900;src:url(${font('jost.woff2')})}
@page{size:154mm 111mm;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
:root{--creme:#FCF9F1;--vert:#1C3A24;--or:#B8903F;--terre:#B4704F}
html,body{background:var(--creme)}
.page{width:154mm;height:111mm;position:relative;overflow:hidden;background:var(--creme);page-break-after:always}
/* RECTO */
.panneau{position:absolute;left:0;top:0;bottom:0;width:67mm;background:var(--creme);display:flex;align-items:center;justify-content:center}
.panneau img{width:52mm}
.photo{position:absolute;left:67mm;top:0;right:0;bottom:0;background:url(${b64(here('src/salle-3-web.jpg'), 'image/jpeg')}) 40% 45%/cover}
.filet{position:absolute;left:67mm;top:0;bottom:0;width:.5mm;background:var(--or)}
/* VERSO */
.verso{color:var(--vert)}
.milieu{position:absolute;left:79mm;top:14mm;bottom:14mm;width:.25mm;background:var(--or)}
.gauche{position:absolute;left:11mm;top:12mm;width:61mm;bottom:12mm;display:flex;flex-direction:column}
.etoile{width:5mm;height:5mm;margin-bottom:3mm}
h1{font:italic 600 17pt/1.05 CG;margin-bottom:3.2mm}
.texte{font:300 7.6pt/1.55 Jost;color:#33463A;margin-bottom:3mm}
.signature{font:italic 500 10pt/1.2 CG;margin-bottom:auto}
.page{margin:0}
.contact{font:400 6.3pt/1.75 Jost;letter-spacing:.06em;color:#33463A}
.contact div{display:grid;grid-template-columns:19mm 1fr}
.contact b{font-weight:500;letter-spacing:.18em;color:var(--or);font-size:5.6pt}
.droite{position:absolute;left:86mm;right:11mm;top:12mm;bottom:12mm}
.timbre{position:absolute;right:0;top:0;width:21mm;height:25mm;border:.3mm dashed var(--or);border-radius:1mm;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1.5mm}
.timbre img{width:13mm;opacity:.9}
.timbre span{font:400 4.6pt Jost;letter-spacing:.25em;color:var(--or)}
.lignes{position:absolute;left:0;right:0;bottom:6mm}
.lignes div{border-bottom:.25mm solid #CDBB93;height:9.5mm}
.pied{position:absolute;left:0;right:0;bottom:0;font:400 5pt Jost;letter-spacing:.3em;color:var(--or);text-align:right}
`;

const star = `<svg class="etoile" viewBox="-16 -16 32 32"><path d="M0,-16 C2,-4 4,-2 16,0 C4,2 2,4 0,16 C-2,4 -4,2 -16,0 C-4,-2 -2,-4 0,-16 Z" fill="#B8903F"/></svg>`;

const recto = `<section class="page">
  <div class="panneau"><img src="${b64(here('src/logo-transparent.png'), 'image/png')}"></div>
  <div class="photo"></div><div class="filet"></div>
</section>`;

const verso = `<section class="page verso">
  <div class="gauche">
    ${star}
    <h1>Merci d'avoir partagé<br>le temps des saveurs</h1>
    <p class="texte">Au fil des saisons, notre cuisine se réinvente avec les plus beaux produits du moment.
      Gardez cette carte en souvenir, ou envoyez-la à quelqu'un qui aime les bonnes tables.</p>
    <p class="signature">À très bientôt,<br>l'équipe de La Table des Saisons</p>
    <div class="contact">
      <div><b>RÉSERVATIONS</b>${INFO.telephone}</div>
      <div><b>ADRESSE</b>${INFO.adresse}</div>
      <div><b>SITE</b>${INFO.site}</div>
      <div><b>INSTAGRAM</b>${INFO.instagram}</div>
    </div>
  </div>
  <div class="milieu"></div>
  <div class="droite">
    <div class="timbre"><img src="${b64(here('src/logo.png'), 'image/png')}" style="display:none"><span>TIMBRE</span></div>
    <div class="lignes"><div></div><div></div><div></div><div></div></div>
    <div class="pied">LA TABLE DES SAISONS</div>
  </div>
</section>`;

(async () => {
  const out = here('export');
  fs.mkdirSync(out, { recursive: true });
  const html = `<!doctype html><meta charset="utf-8"><style>${css}</style>${recto}${verso}`;
  fs.writeFileSync(here('carte-postale.html'), html);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 582, height: 420 }, deviceScaleFactor: 300 / 96 });
  await page.setContent(html);
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: path.join(out, 'carte-postale-impression.pdf'), width: '154mm', height: '111mm', printBackground: true });
  for (const [name, part] of [['recto', recto], ['verso', verso]]) {
    await page.setContent(`<!doctype html><meta charset="utf-8"><style>${css}</style>${part}`);
    await page.evaluate(() => document.fonts.ready);
    await (await page.$('.page')).screenshot({ path: path.join(out, `carte-postale-${name}.png`) });
  }
  await browser.close();
})();
