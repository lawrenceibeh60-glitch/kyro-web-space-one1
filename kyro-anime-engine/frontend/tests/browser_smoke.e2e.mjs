import test from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseURL = process.env.KAE_BASE_URL || 'http://127.0.0.1:5000';

test('browser boots editor, generates a character, authors a rig, and opens export', async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  try {
    await page.goto(baseURL, { waitUntil: 'networkidle' });
    assert.match(await page.title(), /KAE/i);
    await page.locator('#newName').fill('KAE Browser Smoke');
    await page.locator('#create').click();
    await page.waitForURL(/editor\.html\?project=/);
    await page.locator('#canvas').waitFor({ state: 'visible' });
    await page.waitForFunction(() => window.kae?.state?.project?.settings?.width > 0);

    await page.locator('[data-ws="studio"]').click();
    await page.locator('[data-studio-tab="character"]').click();
    await page.locator('#generatorId').fill('browser_hero');
    await page.locator('#generatorName').fill('Browser Hero');
    await page.locator('#generateCharacter').click();
    await page.getByText(/Generated Browser Hero/i).waitFor({ timeout: 15000 });

    await page.locator('[data-studio-tab="rig"]').click();
    await page.waitForFunction(() => {
      const select = document.querySelector('#rigCharacter');
      return [...(select?.options || [])].some(option => option.value === 'browser_hero');
    });
    await page.locator('#rigCreate').click();
    await page.waitForFunction(() => document.querySelector('#rigEditor')?.hidden === false);
    await page.waitForFunction(() => document.querySelectorAll('#bonePart option').length > 1);
    await page.locator('#boneName').fill('Root');
    await page.locator('#boneAdd').click();
    await page.waitForFunction(() => document.querySelectorAll('#boneList .studio-bone').length === 1);

    await page.locator('[data-tool="weight"]').click();
    await page.locator('#weightRadius').waitFor({ state: 'visible' });
    await page.locator('#save').click();
    await page.locator('#exportBtn').click();
    await page.waitForFunction(() => document.querySelector('#exportDlg')?.hidden === false);

    assert.deepEqual(pageErrors, [], `browser runtime errors: ${pageErrors.join('; ')}`);
  } finally {
    await browser.close();
  }
});
