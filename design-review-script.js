const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  const screenshotsDir = '/Users/alexander/code/revrx/design-review-screenshots';
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  // Navigate to landing page
  await page.goto('http://localhost:3003', { waitUntil: 'networkidle' });

  // Capture console messages
  const consoleMessages = [];
  page.on('console', msg => consoleMessages.push({ type: msg.type(), text: msg.text() }));

  // Desktop viewport (1440px)
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(screenshotsDir, 'desktop-1440px.png'), fullPage: true });
  console.log('✓ Desktop screenshot captured (1440px)');

  // Test hover states on primary CTA
  await page.hover('a[href="/register"]');
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(screenshotsDir, 'desktop-cta-hover.png'), fullPage: false });
  console.log('✓ CTA hover state captured');

  // Scroll and test sticky header
  await page.evaluate(() => window.scrollTo(0, 500));
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(screenshotsDir, 'desktop-scroll-sticky-header.png'), fullPage: false });
  console.log('✓ Sticky header behavior captured');

  // Tablet viewport (768px)
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto('http://localhost:3003', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(screenshotsDir, 'tablet-768px.png'), fullPage: true });
  console.log('✓ Tablet screenshot captured (768px)');

  // Mobile viewport (375px)
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('http://localhost:3003', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(screenshotsDir, 'mobile-375px.png'), fullPage: true });
  console.log('✓ Mobile screenshot captured (375px)');

  // Test keyboard navigation
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:3003', { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(screenshotsDir, 'keyboard-navigation-focus.png'), fullPage: false });
  console.log('✓ Keyboard navigation captured');

  // Get accessibility snapshot
  const snapshot = await page.accessibility.snapshot();
  fs.writeFileSync(
    path.join(screenshotsDir, 'accessibility-tree.json'),
    JSON.stringify(snapshot, null, 2)
  );
  console.log('✓ Accessibility tree captured');

  // Save console messages
  fs.writeFileSync(
    path.join(screenshotsDir, 'console-messages.json'),
    JSON.stringify(consoleMessages, null, 2)
  );
  console.log('✓ Console messages captured');

  // Test all interactive elements
  const interactiveElements = await page.evaluate(() => {
    const links = Array.from(document.querySelectorAll('a'));
    return links.map(link => ({
      text: link.textContent.trim(),
      href: link.getAttribute('href'),
      hasHoverStyles: window.getComputedStyle(link).transition !== 'all 0s ease 0s'
    }));
  });

  fs.writeFileSync(
    path.join(screenshotsDir, 'interactive-elements.json'),
    JSON.stringify(interactiveElements, null, 2)
  );
  console.log('✓ Interactive elements analyzed');

  await browser.close();
  console.log('\n✅ Design review capture complete!');
  console.log(`Screenshots saved to: ${screenshotsDir}`);
})();
