# Screenshot Guide for Naukri Dhaba

## Quick Setup (Do NOT waste time trying other tools)

Skip playwright install, snap chromium, html2image, selenium — they all fail in this environment.
Go straight to what works:

### 1. Install puppeteer-core (one-time)
```bash
npm install puppeteer-core
```
Add `node_modules/`, `package.json`, `package-lock.json` to `.gitignore`.

### 2. Chrome binary path
Playwright's chromium was already downloaded and works:
```
/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome
```
If this path stops working, reinstall:
```bash
pip install playwright && python -m playwright install chromium
```
Then find the binary:
```bash
find ~/.cache/ms-playwright/ -name "chrome" 2>/dev/null
```

### 3. Take screenshots — copy-paste this script

```javascript
// Save as /tmp/take_screenshots.js
const puppeteer = require('/home/user/naukri-dhaba/node_modules/puppeteer-core');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
    headless: true,
  });

  const htmlPath = 'file:///home/user/naukri-dhaba/PATH_TO_FILE.html';
  const outDir = '/home/user/naukri-dhaba/preview-screenshots';

  // Desktop (1280px)
  const desktopPage = await browser.newPage();
  await desktopPage.setViewport({ width: 1280, height: 900 });
  await desktopPage.goto(htmlPath, { waitUntil: 'networkidle0' });
  await desktopPage.screenshot({
    path: path.join(outDir, 'desktop', 'FILENAME-desktop.png'),
    fullPage: true,
  });

  // Mobile (390px - iPhone 14)
  const mobilePage = await browser.newPage();
  await mobilePage.setViewport({ width: 390, height: 844, isMobile: true });
  await mobilePage.goto(htmlPath, { waitUntil: 'networkidle0' });
  await mobilePage.screenshot({
    path: path.join(outDir, 'mobile', 'FILENAME-mobile.png'),
    fullPage: true,
  });

  await browser.close();
  console.log('Done!');
})();
```

Run with:
```bash
node /tmp/take_screenshots.js
```

### 4. View screenshots
Use the Read tool on the .png files — it renders them visually.

### 5. Output locations
- Desktop: `preview-screenshots/desktop/`
- Mobile: `preview-screenshots/mobile/`
