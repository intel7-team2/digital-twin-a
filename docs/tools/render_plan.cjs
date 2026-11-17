// Set NODE_PATH to the installed or Codex-bundled node_modules directory.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
(async () => {
 const executablePath = process.env.PLAN_BROWSER || ['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','C:/Program Files/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
 const browser = await chromium.launch({ ...(executablePath ? { executablePath } : {}), headless: true });
 try {
  const stem = process.argv[2] || 'plan_v0.7';
  const qa = path.resolve(__dirname, '../.qa', stem);
  fs.mkdirSync(qa, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 1100, height: 1200 }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(path.resolve(__dirname, '../' + stem + '.html')).href);
  await page.evaluate(() => document.fonts.ready);
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
  await page.locator('section.page').nth(2).screenshot({ path: path.join(qa, 'phone-goals.png') });
  await page.locator('section.page').nth(4).screenshot({ path: path.join(qa, 'phone-io.png') });
  await page.locator('section.page').nth(5).screenshot({ path: path.join(qa, 'phone-interface.png') });
  const mobile = await page.evaluate(() => ({ width: innerWidth, contentWidth: document.documentElement.scrollWidth }));
  console.log(JSON.stringify({ mobile }));
  if (mobile.contentWidth > mobile.width) throw new Error('Phone layout overflows');
 } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
