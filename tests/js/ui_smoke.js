// Test interfejsu (Chromium, Playwright): edycja danych, przeciąganie uchwytu, okna objaśnień, NDP, model STM, optymalizacja,
// eksport raportu, zapis i odczyt projektu. Uruchomienie: python build_html.py && node tests/js/ui_smoke.js [katalog_zrzutów]
'use strict';
const path = require('path');
const { chromium } = require('playwright');
const APP = path.resolve(__dirname, '..', '..', 'app', 'app.html');
const out = process.argv[2] || '';
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1500, height: 950 }, acceptDownloads: true });
  const pg = await ctx.newPage();
  await pg.addInitScript(() => { delete window.showSaveFilePicker; window.showSaveFilePicker = undefined; });
  const errs = [];
  pg.on('pageerror', e => errs.push(String(e)));
  pg.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
  const ok = (c, msg) => { if (!c) { console.log('✖ ' + msg); process.exitCode = 1; } else console.log('✔ ' + msg); };
  await pg.goto('file://' + APP);
  await pg.waitForTimeout(800);
  const status = async () => (await pg.textContent('#status')).trim();
  ok(/Spełniono warunkowo/.test(await status()), 'stan początkowy: ' + await status());
  // zmiana wysięgu obciążenia – pole liczbowe
  const ac = pg.locator('#inputs [data-k="geometry.right.a_c"]');
  await ac.fill('330'); await ac.press('Enter'); await pg.waitForTimeout(400);
  ok(await pg.evaluate(() => window.WU.V().geometry.right.a_c) === 330, 'pole a_c zapisane w danych');
  // błąd danych: a_c > l_c → zablokowanie wyniku
  await ac.fill('500'); await ac.press('Enter'); await pg.waitForTimeout(400);
  ok(/Błąd danych/.test(await status()), 'błąd geometrii blokuje wynik: ' + await status());
  await ac.fill('250'); await ac.press('Enter'); await pg.waitForTimeout(400);
  // przeciąganie uchwytu h_c na schemacie
  const h = pg.locator('#schWrap .hdl[data-h="h_c:R"]');
  const bb = await h.boundingBox();
  const hc0 = await pg.evaluate(() => window.WU.V().geometry.right.h_c);
  await pg.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2); await pg.mouse.down();
  await pg.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2 + 40, { steps: 6 }); await pg.mouse.up(); await pg.waitForTimeout(500);
  const hc1 = await pg.evaluate(() => window.WU.V().geometry.right.h_c);
  ok(hc1 > hc0 && hc1 % 5 === 0, `uchwyt h_c: ${hc0} → ${hc1} mm`);
  // dodanie i usunięcie oddziaływania
  await pg.click('#inputs [data-addact]'); await pg.waitForTimeout(300);
  ok(await pg.evaluate(() => window.WU.V().loads.actions.length) === 4, 'dodano oddziaływanie');
  await pg.click('#inputs [data-delact="3"]'); await pg.waitForTimeout(300);
  // Podsumowanie: tabela, okno „jak obliczono”, okno normy
  await pg.click('nav.tabs button[data-tab="sum"]'); await pg.waitForTimeout(400);
  const rows = await pg.locator('#p-sum tr[data-ci]').count();
  ok(rows > 30, 'tabela sprawdzeń: ' + rows + ' wierszy');
  await pg.locator('#p-sum tr[data-ci] td.val').nth(8).click(); await pg.waitForTimeout(200);
  ok(await pg.locator('#modal .dlg.expl').isVisible(), 'okno „Jak obliczono”');
  if (out) await pg.screenshot({ path: out + '/ui_explain.png' });
  await pg.keyboard.press('Escape');
  await pg.locator('#p-sum .nref').nth(10).click(); await pg.waitForTimeout(200);
  ok(await pg.locator('#modal .dlg.norm .nsec').count() > 0, 'objaśnienie punktu normy');
  await pg.keyboard.press('Escape');
  // NDP: potwierdzenie → wynik pozytywny w zakresie programu
  await pg.click('nav.tabs button[data-tab="data"]'); await pg.waitForTimeout(200);
  await pg.click('#inputs [data-ndp]'); await pg.waitForTimeout(200);
  if (out) await pg.screenshot({ path: out + '/ui_ndp.png' });
  await pg.check('#ndpOk'); await pg.click('#ndpClose'); await pg.waitForTimeout(500);
  ok(/Spełniono w zakresie programu/.test(await status()), 'po potwierdzeniu NDP: ' + await status());
  // Model STM: klik w element → okno elementu
  await pg.click('nav.tabs button[data-tab="stm"]'); await pg.waitForTimeout(400);
  await pg.locator('.stmwrap [data-ref="member:SR"]').first().click({ force: true }); await pg.waitForTimeout(200);
  ok(await pg.locator('#modal .dlg').isVisible() && /Pręt/.test(await pg.textContent('#modal h3')), 'okno elementu S_R');
  await pg.keyboard.press('Escape');
  // wariant: kopia + przełączenie
  await pg.click('nav.tabs button[data-tab="data"]'); await pg.click('[data-vadd]'); await pg.waitForTimeout(400);
  ok(await pg.evaluate(() => window.WU.getS().variants.length) === 2, 'drugi wariant');
  await pg.click('#adCmp'); await pg.waitForTimeout(400);
  ok(await pg.locator('#modal table.sched tr').count() === 3, 'porównanie wariantów');
  await pg.keyboard.press('Escape');
  // optymalizacja (mała siatka)
  await pg.click('nav.tabs button[data-tab="opt"]'); await pg.waitForTimeout(300);
  await pg.evaluate(() => { const o = window.WU.getS().meta.opt; o.hc = [450, 600, 50]; o.concretes = ['C30/37']; o.diameters = [16, 20]; });
  await pg.click('nav.tabs button[data-tab="data"]'); await pg.click('nav.tabs button[data-tab="opt"]'); await pg.waitForTimeout(200);
  await pg.click('#opGo'); await pg.waitForTimeout(4000);
  const nres = await pg.locator('.opttab tr').count();
  ok(nres >= 4, 'wyniki optymalizacji: ' + (nres - 1));
  if (out) await pg.screenshot({ path: out + '/ui_opt.png' });
  // raport: eksport HTML (pobranie w przeglądarce)
  await pg.click('nav.tabs button[data-tab="report"]'); await pg.waitForTimeout(500);
  ok((await pg.locator('#report h2').count()) >= 7, 'raport – rozdziały: ' + await pg.locator('#report h2').count());
  const [dl] = await Promise.all([pg.waitForEvent('download'), pg.click('#rpHtml')]);
  ok(/<h2>/.test(require('fs').readFileSync(await dl.path(), 'utf8')), 'pobrano raport HTML');
  const [dl2] = await Promise.all([pg.waitForEvent('download'), pg.click('#rpOdt')]);
  ok(require('fs').readFileSync(await dl2.path()).slice(30, 38).toString() === 'mimetype', 'pobrano raport .odt (ZIP OpenDocument)');
  const [dl3] = await Promise.all([pg.waitForEvent('download'), pg.click('#rpDxf')]);
  ok(/SECTION[\s\S]*ENTITIES[\s\S]*EOF/.test(require('fs').readFileSync(await dl3.path(), 'utf8')), 'pobrano DXF');
  // zapis projektu i ponowne wczytanie
  const [dl4] = await Promise.all([pg.waitForEvent('download'), pg.click('#bSave')]);
  const f = await dl4.path();
  ok(JSON.parse(require('fs').readFileSync(f, 'utf8')).format === 'KROTKI_WSPORNIK_ST', 'zapis projektu .kwst');
  await pg.click('#bNew'); await pg.waitForTimeout(200);
  if (await pg.locator('#modal [data-a="1"]').isVisible()) await pg.click('#modal [data-a="1"]');
  await pg.waitForTimeout(300);
  ok(await pg.evaluate(() => window.WU.getS().variants.length) === 1, 'nowy projekt (1 wariant)');
  const fcP = pg.waitForEvent('filechooser');
  await pg.click('#bOpen'); await pg.waitForTimeout(200);
  if (await pg.locator('#modal [data-a="1"]').isVisible()) await pg.click('#modal [data-a="1"]');
  const fc = await fcP; await fc.setFiles(f); await pg.waitForTimeout(700);
  ok(await pg.evaluate(() => window.WU.getS().variants.length) === 2, 'wczytano projekt (2 warianty)');
  console.log('błędy strony:', JSON.stringify(errs.slice(0, 5)));
  if (errs.length) process.exitCode = 1;
  await b.close();
})();
