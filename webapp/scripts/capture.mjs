import puppeteer from 'puppeteer';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function capture() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
  
  const targetUrl = process.argv[2] || 'http://localhost:3000';
  const outputPath = process.argv[3] || path.resolve(__dirname, '../../source/screenshot_current.png');
  
  console.log(`Navigating to ${targetUrl}...`);
  await page.goto(targetUrl, { waitUntil: 'networkidle0', timeout: 30000 });
  
  // Wait a small delay to ensure any layout renders cleanly
  await new Promise(r => setTimeout(r, 1000));
  
  await page.screenshot({ path: outputPath });
  console.log(`Saved screenshot to ${outputPath}`);
  await browser.close();
}

capture().catch(err => {
  console.error('Error capturing screenshot:', err);
  process.exit(1);
});
