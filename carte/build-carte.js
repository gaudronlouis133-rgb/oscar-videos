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
  chef: 'Votre Chef',
  photoChef: 'src/chef.jpg',
};

const css = `
@font-face{font-family:CG;font-weight:300 700;src:url(${font('cg-normal-500.woff2')})}
@font-face{font-family:CG;font-style:italic;font-weight:300 700;src:url(${font('cg-italic-500.woff2')})}
@font-face{font-family:Caveat;font-weight:400 700;src:url(${font('caveat.woff2')})}
@font-face{font-family:Jost;font-weight:100 900;src:url(${font('jost.woff2')})}
@page{size:154mm 111mm;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
:root{--creme:#FCF9F1;--vert:#1C3A24;--or:#B8903F;--terre:#B4704F}
html,body{background:var(--creme)}
.page{width:154mm;height:111mm;position:relative;overflow:hidden;background:var(--creme);page-break-after:always}
/* RECTO */
.panneau{position:absolute;left:0;top:0;bottom:0;width:69mm;background:var(--creme);display:flex;align-items:center;justify-content:center}
.panneau img{width:52mm}
.photo,.photo2{position:absolute;background-size:cover;box-shadow:0 .8mm 2.4mm rgba(60,40,20,.22)}
.photo{left:71mm;top:9mm;width:63mm;height:53mm;background-image:url(${b64(here('src/salle-vases.jpg'), 'image/jpeg')});background-position:50% 60%}
.photo2{left:93mm;top:51mm;width:53mm;height:49mm;border:1.4mm solid var(--creme);background-image:url(${b64(here('src/dressage.jpg'), 'image/jpeg')});background-position:50% 52%}
.cadre-or{position:absolute;left:75mm;top:13mm;width:63mm;height:53mm;border:.35mm solid var(--or)}
.filet{position:absolute;left:67mm;top:22mm;bottom:22mm;width:.3mm;background:var(--or);opacity:.0}
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
.droite{position:absolute;left:86mm;right:10mm;top:10mm;bottom:9mm;display:flex;flex-direction:column}
.cadre{position:relative;height:50mm;background:#EFE6D4;border:.35mm solid var(--or);padding:1.2mm;box-shadow:0 .6mm 1.6mm rgba(60,40,20,.18);transform:rotate(-1.2deg)}
.cadre .photo-chef{width:100%;height:100%;background:#E6DAC2 50% 66%/cover;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1.6mm;color:var(--or)}
.cadre svg{width:15mm}
.cadre span{font:400 5pt Jost;letter-spacing:.25em}
.manuscrit{margin-top:3.6mm;font:500 10.6pt/1.06 Caveat;color:#1F3A5A}
.manuscrit .sig{display:block;text-align:right;margin-top:1.2mm;font-size:13pt}
.pied{margin-top:auto;font:400 5pt Jost;letter-spacing:.3em;color:var(--or);text-align:right}
`;

const star = `<svg class="etoile" viewBox="-16 -16 32 32"><path d="M0,-16 C2,-4 4,-2 16,0 C4,2 2,4 0,16 C-2,4 -4,2 -16,0 C-4,-2 -2,-4 0,-16 Z" fill="#B8903F"/></svg>`;

const toque = `<svg viewBox="0 0 60 60" fill="none" stroke="#B8903F" stroke-width="1.6" stroke-linejoin="round"><path d="M16,40 C6,38 4,24 13,20 C14,10 26,7 31,13 C37,6 50,10 49,20 C57,23 55,38 44,40 Z"/><path d="M17,40 L17,50 L43,50 L43,40"/><path d="M17,45 L43,45"/><path d="M24,40 L24,30 M30,40 L30,28 M36,40 L36,30" stroke-width="1.1"/></svg>`;

const recto = `<section class="page">
  <div class="panneau"><img src="${b64(here('src/logo-transparent.png'), 'image/png')}"></div>
  <div class="cadre-or"></div><div class="photo"></div><div class="photo2"></div>
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
    <div class="cadre"><div class="photo-chef" ${INFO.photoChef ? `style="background-image:url(${b64(here(INFO.photoChef), 'image/jpeg')})"` : ''}>
      ${INFO.photoChef ? '' : `${toque}<span>PHOTO DU CHEF</span>`}
    </div></div>
    <p class="manuscrit">Chers amis,<br>
      bienvenue à notre table. Ici, chaque assiette suit le rythme des saisons et le travail
      de nos producteurs. Merci d'être venus partager ce moment avec nous.
      <span class="sig">${INFO.chef}</span></p>
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
