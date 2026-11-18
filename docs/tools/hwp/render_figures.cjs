// Render docs/assets/hwp/fig-*.html to PNG at 2.5x. Set NODE_PATH to a node_modules with playwright.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
(async () => {
  const dir = path.resolve(__dirname, '../../assets/hwp');
  const executablePath = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));
  const browser = await chromium.launch({ ...(executablePath ? { executablePath } : {}), headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1000, height: 800 }, deviceScaleFactor: 2.5 });
    for (const name of fs.readdirSync(dir).filter(f => f.endsWith('.html'))) {
      await page.goto(pathToFileURL(path.join(dir, name)).href);
      await page.evaluate(() => document.fonts.ready);
      const out = path.join(dir, name.replace('.html', '.png'));
      await page.locator('#fig').screenshot({ path: out });
      console.log('rendered', path.basename(out));
    }
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
