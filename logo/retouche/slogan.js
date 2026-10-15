// Remplace le slogan « Un Moment Suspendu » par un nouveau texte, dans le même style
// Usage : node slogan.js <police-italique.woff2> "<nouveau slogan>" <entrée.png> <sortie.png> [...]
const fs = require('fs');
const { chromium } = require('playwright');

const [fontFile, slogan, ...files] = process.argv.slice(2);
const font = 'data:font/woff2;base64,' + fs.readFileSync(fontFile).toString('base64');
const SIZE = 2508, CENTER_X = 1257, BASELINE = 2042, FONT_PX = 136;
const BG = 'rgb(252,249,241)', INK = 'rgb(14,40,19)';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: SIZE, height: SIZE } });
  // calibrage : l'interlettrage qui donne au texte d'origine sa largeur mesurée (1185 px)
  await page.setContent(`<style>@font-face{font-family:CG;font-style:italic;font-weight:300 700;src:url(${font})}</style>
    <span id="t" style="font:italic 600 ${FONT_PX}px CG;white-space:nowrap">Un Moment Suspendu</span>`);
  await page.evaluate(() => document.fonts.ready);
  const w0 = await page.$eval('#t', (e) => e.getBoundingClientRect().width);
  const ls = (1185 - w0) / 17;
  for (let i = 0; i < files.length; i += 2) {
    const img = 'data:image/png;base64,' + fs.readFileSync(files[i]).toString('base64');
    await page.setContent(`<style>
      @font-face{font-family:CG;font-style:italic;font-weight:300 700;src:url(${font})}
      html,body{margin:0}
      #c{position:absolute;left:600px;top:1935px;width:1310px;height:152px;background:${BG}}
      #t{position:absolute;left:0;width:${SIZE}px;top:0;text-align:center;font:italic 600 ${FONT_PX}px CG;
         color:${INK};letter-spacing:${ls}px;white-space:nowrap;line-height:1}
    </style><img src="${img}" width="${SIZE}" height="${SIZE}" style="display:block">
    <div id="c"></div><div id="t">${slogan}</div>`);
    await page.evaluate(() => document.fonts.ready);
    // placement : centre horizontal et ligne de base du texte d'origine
    await page.evaluate(({ cx, base, size, ls }) => {
      const t = document.getElementById('t');
      const r = document.createRange(); r.selectNodeContents(t);
      const span = document.createElement('span'); span.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
      t.appendChild(span);
      const baseY = span.getBoundingClientRect().top;
      t.style.top = (base - baseY) + 'px';
      t.style.left = (cx - size / 2 + ls / 2) + 'px';
    }, { cx: CENTER_X, base: BASELINE, size: SIZE, ls });
    await page.screenshot({ path: files[i + 1] });
  }
  await browser.close();
})();
