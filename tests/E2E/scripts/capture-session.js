'use strict';
const { chromium } = require('@playwright/test');
const readline = require('readline');

(async () => {
  process.env.DISPLAY = ':99';

  const browser = await chromium.launch({
    headless: false,
    args: ['--no-sandbox', '--window-size=1280,900'],
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto('https://search.dalia.education');

  const rl = readline.createInterface({ input: process.stdin });
  await new Promise((resolve) => rl.question('', resolve));
  rl.close();

  const sessionPath = '/session/auth.json';
  await context.storageState({ path: sessionPath });
  console.log(`\nSession saved to ${sessionPath}`);

  await browser.close();
  process.exit(0);
})();
