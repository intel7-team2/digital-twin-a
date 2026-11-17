// Set NODE_PATH to the installed or Codex-bundled node_modules directory.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
(async () => {
 const executablePath = process.env.PLAN_BROWSER || ['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','C:/Program Files/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
 const browser = await chromium.launch({ ...(executablePath ? { executablePath } : {}), headless: true });
 try {
  const stem = process.argv[2] || 'plan_v0.15';
  const qa = path.resolve(__dirname, '../.qa', stem);
  fs.mkdirSync(qa, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 1100, height: 1200 }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(path.resolve(__dirname, '../' + stem + '.html')).href);
  await page.evaluate(() => document.fonts.ready);
  if (await page.evaluate(() => [...document.fonts].some(font => font.family === 'PlanHeadline'))) {
   const cdp = await page.context().newCDPSession(page);
   await cdp.send('DOM.enable');
   await cdp.send('CSS.enable');
   const { root } = await cdp.send('DOM.getDocument');
   for (const selector of ['h1', 'h2', '.cover .task']) {
    const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector });
    const { fonts } = await cdp.send('CSS.getPlatformFontsForNode', { nodeId });
    if (!fonts.length || fonts.some(font => font.postScriptName !== 'H2hdrM')) {
     throw new Error('Reference headline font substituted: ' + selector);
    }
   }
   await cdp.detach();
   console.log('Verified HY헤드라인M rendering for title and section headings');
  }
  const brokenImages = await page.locator('img').evaluateAll(images => images.filter(img => !img.complete || !img.naturalWidth).map(img => img.src));
  if (brokenImages.length) throw new Error('Missing images: ' + brokenImages.join(', '));
  await page.emulateMedia({ media: 'print' });
  const checks = await page.locator('section.page').evaluateAll(pages => pages.map((p, i) => {
   const footer = p.querySelector('footer');
   const contentBottom = Math.max(...[...p.children].filter(e => e !== footer).map(e => e.getBoundingClientRect().bottom));
   return { page: i + 1, height: p.clientHeight, scroll: p.scrollHeight, clearance: Math.round(footer.getBoundingClientRect().top - contentBottom) };
  }));
  console.log(JSON.stringify({ print: checks }));
  if (checks.some(p => p.scroll > p.height + 1 || p.clearance < 12)) throw new Error('Content overflow or footer collision');
  await page.pdf({ path: path.resolve(__dirname, '../' + stem + '.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true });
  await page.emulateMedia({ media: 'screen' });
  await page.screenshot({ path: path.join(qa, 'desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 375, height: 900 });
  await page.screenshot({ path: path.join(qa, 'phone.png'), fullPage: true });
  await page.locator('.equipment-figure').screenshot({ path: path.join(qa, 'phone-equipment.png') });
  await page.locator('section.page').nth(2).screenshot({ path: path.join(qa, 'phone-goals.png') });
  await page.locator('section.page').nth(6).screenshot({ path: path.join(qa, 'phone-io.png') });
  await page.locator('section.page').nth(8).screenshot({ path: path.join(qa, 'phone-interface.png') });
  if (['plan_v0.14', 'plan_v0.15'].includes(stem)) {
   await page.locator('section.page').nth(9).screenshot({ path: path.join(qa, 'phone-address.png') });
   await page.locator('section.page').nth(11).screenshot({ path: path.join(qa, 'phone-schedule.png') });
  }
  await page.locator('section.page').nth(4).screenshot({ path: path.join(qa, 'phone-inspection.png') });
  await page.locator('section.page').nth(5).screenshot({ path: path.join(qa, 'phone-lot.png') });
  await page.locator('section.page').nth(7).screenshot({ path: path.join(qa, 'phone-transfer.png') });
  const mobile = await page.evaluate(() => ({ width: innerWidth, contentWidth: document.documentElement.scrollWidth }));
  console.log(JSON.stringify({ mobile }));
  if (mobile.contentWidth > mobile.width) throw new Error('Phone layout overflows');
 } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
