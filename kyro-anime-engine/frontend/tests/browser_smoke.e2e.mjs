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
    await page.locator('#rigAuto').click();
    await page.waitForFunction(() => document.querySelectorAll('#boneList .studio-bone').length > 1);
    await page.waitForFunction(() => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      const names = new Set((rig?.bones || []).map(bone => bone.name));
      return ['Left Thigh', 'Left Shin', 'Left Foot', 'Left Upper Arm', 'Left Forearm', 'Left Hand']
        .every(name => names.has(name));
    });
    await page.locator('#rigWalkEnabled').check();
    await page.locator('#rigWalkCycle').fill('32');
    await page.locator('#rigWalkStride').evaluate(input => {
      input.value = '30';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await page.locator('#rigWalkApply').click();
    await page.waitForFunction(() => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      return rig?.animation?.type === 'walk' && rig.animation.enabled === true
        && rig.animation.cycle_frames === 32 && rig.animation.stride === 30;
    });

    await page.locator('[data-tool="weight"]').click();
    await page.locator('#weightRadius').waitFor({ state: 'visible' });
    const target = await page.evaluate(async () => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      const layer = scene.layers.find(item => item.id === state.layerId);
      const exposure = [...(layer.exposures || [])].reverse().find(item =>
        state.frame >= item.start && state.frame < item.start + item.length);
      const drawing = state.project.drawings[exposure.drawing];
      let stroke = null, point = null, field = null, index = 0;
      for (const item of drawing.strokes) {
        if (Array.isArray(item.points) && item.points.length) {
          stroke = item; point = item.points[0]; field = 'skin_weights'; break;
        }
        if (Array.isArray(item.commands)) {
          for (const command of item.commands) {
            if (command[0] !== 'Z' && command.length >= 3) {
              stroke = item; point = [command[1], command[2]]; field = 'command_skin_weights'; break;
            }
          }
          if (stroke) break;
        }
      }
      if (!stroke || !point) throw new Error('Generated character drawing has no editable geometry');
      const { evaluateTransform } = await import('/js/animation/pose_evaluator.js');
      const { fromLocal } = await import('/js/rendering/geometry.js');
      const transform = evaluateTransform(layer, state.frame);
      const [worldX, worldY] = fromLocal(transform, point[0], point[1]);
      const canvas = document.querySelector('#canvas');
      const rect = canvas.getBoundingClientRect();
      return {
        x: rect.left + state.view.panX + worldX * state.view.zoom,
        y: rect.top + state.view.panY + worldY * state.view.zoom,
        drawingId: exposure.drawing,
        strokeId: stroke.id,
        field,
      };
    });
    await page.mouse.move(target.x, target.y);
    await page.mouse.down();
    await page.mouse.move(target.x + 2, target.y + 2, { steps: 2 });
    await page.mouse.up();
    await page.waitForFunction(({ drawingId, strokeId, field }) => {
      const stroke = window.kae.state.project.drawings[drawingId].strokes.find(item => item.id === strokeId);
      return Array.isArray(stroke?.[field]) && stroke[field].some(influences =>
        Array.isArray(influences) && influences.some(item => item.bone_id === window.kae.state.weightBoneId));
    }, target);
    const firstFrame = await page.locator('#frameReadout').textContent();
    await page.locator('#play').click();
    await page.waitForFunction(initial => document.querySelector('#frameReadout')?.textContent !== initial, firstFrame, { timeout: 5000 });
    await page.locator('#play').click();
    await page.locator('#save').click();
    await page.locator('#exportBtn').click();
    await page.waitForFunction(() => document.querySelector('#exportDlg')?.hidden === false);
    await page.locator('#exStart').fill('1');
    await page.locator('#exEnd').fill('1');
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 20000 }),
      page.locator('#exGo').click(),
    ]);
    assert.match(download.suggestedFilename(), /\.zip$/i);
    await page.waitForFunction(() => document.querySelector('#exMsg')?.textContent?.startsWith('Done:'), null, { timeout: 20000 });

    assert.deepEqual(pageErrors, [], `browser runtime errors: ${pageErrors.join('; ')}`);
  } finally {
    await browser.close();
  }
});
