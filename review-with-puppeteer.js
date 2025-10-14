const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  const screenshotsDir = '/Users/alexander/code/revrx/design-review-screenshots';
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  // Capture console messages
  const consoleMessages = [];
  page.on('console', msg => consoleMessages.push({ type: msg.type(), text: msg.text() }));

  // Desktop viewport (1440px)
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto('http://localhost:3003', { waitUntil: 'networkidle2' });
  await page.screenshot({ path: path.join(screenshotsDir, 'desktop-1440px.png'), fullPage: true });
  console.log('✓ Desktop screenshot captured (1440px)');

  // Tablet viewport (768px)
  await page.setViewport({ width: 768, height: 1024 });
  await page.goto('http://localhost:3003', { waitUntil: 'networkidle2' });
  await page.screenshot({ path: path.join(screenshotsDir, 'tablet-768px.png'), fullPage: true });
  console.log('✓ Tablet screenshot captured (768px)');

  // Mobile viewport (375px)
  await page.setViewport({ width: 375, height: 667 });
  await page.goto('http://localhost:3003', { waitUntil: 'networkidle2' });
  await page.screenshot({ path: path.join(screenshotsDir, 'mobile-375px.png'), fullPage: true });
  console.log('✓ Mobile screenshot captured (375px)');

  // Save console messages
  fs.writeFileSync(
    path.join(screenshotsDir, 'console-messages.json'),
    JSON.stringify(consoleMessages, null, 2)
  );
  console.log('✓ Console messages captured');

  await browser.close();
  console.log('\n✅ Design review capture complete!');
})();
