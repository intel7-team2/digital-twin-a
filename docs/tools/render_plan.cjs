const { chromium } = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const path = require('path');
const {pathToFileURL} = require('url');
(async()=>{
 const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const stem=process.argv[2] || 'plan_v0.3';
 const page=await browser.newPage({viewport:{width:1100,height:1200},deviceScaleFactor:1});
 await page.goto(pathToFileURL(path.resolve(__dirname,'../'+stem+'.html')).href);
 await page.evaluate(()=>document.fonts.ready);
 const checks=await page.locator('section.page').evaluateAll(pages=>pages.map((p,i)=>{const f=p.querySelector('.footer,footer');return {page:i+1,height:p.clientHeight,scroll:p.scrollHeight,footer:f.getBoundingClientRect().top,contentBottom:f.previousElementSibling.getBoundingClientRect().bottom}}));
 console.log(JSON.stringify(checks));
 await page.pdf({path:path.resolve(__dirname,'../'+stem+'.pdf'),format:'A4',printBackground:true,preferCSSPageSize:true});
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
