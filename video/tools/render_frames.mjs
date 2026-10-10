// Usage: node render_frames.mjs <url> <outDir> [fps] [png]
// Drives the page's window.render(t) and screenshots every frame.
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const [url, out, fpsArg, fmt] = process.argv.slice(2);
const png = fmt === 'png';
const fps = Number(fpsArg || 30);
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(url);
await page.evaluate(() => window.assetsReady);
const dur = await page.evaluate(() => window.DUR);
const n = Math.round(dur * fps);
for (let i = 0; i < n; i++) {
  await page.evaluate(t => window.render(t), i / fps);
  await page.screenshot(png ? { path: `${out}/f${String(i).padStart(5, '0')}.png`, omitBackground: true }
                         : { path: `${out}/f${String(i).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 92 });
}
await browser.close();
console.log(`rendered ${n} frames`);
