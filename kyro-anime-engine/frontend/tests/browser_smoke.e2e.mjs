import test from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { transformPoint } from '../js/animation/rig_deformer.js';
import { createRenderCache } from '../js/rendering/render_cache.js';
import { createDrawQueue } from '../js/rendering/draw_queue.js';

const baseURL = process.env.KAE_BASE_URL || 'http://127.0.0.1:5000';

test('render cache enforces LRU and memory bounds', () => {
  const cache = createRenderCache({ maxEntries: 2, maxBytes: 8 });
  cache.set('a', 'A', 4);
  cache.set('b', 'B', 4);
  assert.equal(cache.get('a'), 'A');
  cache.set('c', 'C', 4);
  assert.equal(cache.has('b'), false, 'least-recently-used entry should be evicted');
  assert.equal(cache.get('a'), 'A');
  assert.equal(cache.get('c'), 'C');
  assert.ok(cache.bytes <= 8);
  assert.equal(cache.stats.hits, 3);
});

test('draw queue coalesces repeated invalidations into one scheduled frame', () => {
  let nextId = 0;
  const pending = new Map();
  const draws = [];
  const queue = createDrawQueue(() => draws.push('draw'), {
    request(callback) { const id = ++nextId; pending.set(id, callback); return id; },
    cancel(id) { pending.delete(id); },
  });
  queue.request(); queue.request(); queue.request();
  assert.equal(pending.size, 1);
  const [id, callback] = [...pending.entries()][0];
  pending.delete(id); callback();
  assert.deepEqual(draws, ['draw']);
  assert.equal(queue.pending, false);
  assert.equal(queue.stats.requested, 3);
  assert.equal(queue.stats.completed, 3);
});

test('hierarchical skinning moves child pivots with parent bones', () => {
  const root = { id: 'root', pivot: { x: 0, y: 0 }, rotation: 90 };
  const child = { id: 'child', parent_id: 'root', pivot: { x: 10, y: 0 }, rotation: 90 };
  const rig = { bones: [root, child], constraints: [] };
  const point = transformPoint([10, 10], [root, child], 0, null, rig);
  assert.ok(Math.abs(point.x) < 1e-8, `expected x≈0, received ${point.x}`);
  assert.ok(Math.abs(point.y) < 1e-8, `expected y≈0, received ${point.y}`);
});

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

    // A double-click on an empty exposure cell should author a real blank drawing cel.
    await page.locator('#addLayer').click();
    const celTarget = await page.evaluate(() => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      const layer = scene.layers.find(item => item.id === state.layerId);
      if (!layer) throw new Error('New timeline layer was not selected');
      const scroll = document.querySelector('#dopeScroll');
      const canvas = document.querySelector('#dope');
      const rect = canvas.getBoundingClientRect();
      const frame = Math.min(5, state.project.settings.duration_frames - 1);
      const px = Math.max(10, (scroll.clientWidth - 12) / state.project.settings.duration_frames);
      return {
        x: rect.left + 6 + frame * px + px / 2 - scroll.scrollLeft,
        y: rect.top + 18 + 10 - scroll.scrollTop,
        layerId: layer.id,
        frame,
      };
    });
    await page.mouse.dblclick(celTarget.x, celTarget.y);
    await page.waitForFunction(({ layerId, frame }) => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      const layer = scene.layers.find(item => item.id === layerId);
      return state.frame === frame && layer?.exposures?.some(exposure => exposure.start === frame
        && exposure.length === 1 && !!state.project.drawings[exposure.drawing]);
    }, celTarget);
    await page.locator('#clearExposure').click();
    await page.waitForFunction(({ layerId, frame }) => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      const layer = scene.layers.find(item => item.id === layerId);
      return !layer?.exposures?.some(exposure => frame >= exposure.start && frame < exposure.start + exposure.length);
    }, celTarget);
    await page.locator('#undo').click();
    await page.waitForFunction(({ layerId, frame }) => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      const layer = scene.layers.find(item => item.id === layerId);
      return layer?.exposures?.some(exposure => frame >= exposure.start && frame < exposure.start + exposure.length);
    }, celTarget);
    await page.locator('#redo').click();
    await page.waitForFunction(({ layerId, frame }) => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      const layer = scene.layers.find(item => item.id === layerId);
      return !layer?.exposures?.some(exposure => frame >= exposure.start && frame < exposure.start + exposure.length);
    }, celTarget);
    // Exercise the editable clipping-path controls and verify undoable project data.
    await page.locator('[data-tab="object"]').click();
    await page.locator('#layerClipPath').fill('[["M",0,0],["L",200,0],["L",200,200],["Z"]]');
    await page.locator('#layerClipApply').click();
    await page.waitForFunction(() => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      return scene.layers.find(layer => layer.id === state.layerId)?.clip_path?.length === 4;
    });
    await page.locator('#layerClipClear').click();
    await page.waitForFunction(() => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      return !scene.layers.find(layer => layer.id === state.layerId)?.clip_path;
    });
    await page.locator('[data-tab="tool"]').click();

    // The AI workspace has been removed from the production editor UI.
    assert.equal(await page.locator('#aiLaunch').count(), 0, 'AI workspace launch control must not appear');
    assert.equal(await page.locator('#aiStudio').count(), 0, 'AI workspace overlay must not be mounted');

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
    const motion = await page.evaluate(async () => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      const { evaluateRigAnimation } = await import('/js/animation/animation_clips.js');
      const thigh = rig.bones.find(bone => bone.character_part_id === 'left_thigh');
      const first = evaluateRigAnimation(rig, 0).bones[thigh.id];
      const later = evaluateRigAnimation(rig, 20).bones[thigh.id];
      return { first, later };
    });
    assert.ok(Number.isFinite(motion.first) && Number.isFinite(motion.later));
    assert.notEqual(motion.first, motion.later, 'the generated thigh bone must actually animate');

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
    const pixelSignature = () => page.evaluate(() => {
      const canvas = document.querySelector('#canvas');
      const context = canvas.getContext('2d');
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      let hash = 2166136261;
      for (let index = 0; index < pixels.length; index += 4) {
        hash ^= pixels[index]; hash = Math.imul(hash, 16777619);
        hash ^= pixels[index + 1]; hash = Math.imul(hash, 16777619);
        hash ^= pixels[index + 2]; hash = Math.imul(hash, 16777619);
      }
      return hash >>> 0;
    });
    const firstFrame = await page.locator('#frameReadout').textContent();
    const firstPixels = await pixelSignature();
    await page.locator('#play').click();
    await page.waitForFunction(initial => document.querySelector('#frameReadout')?.textContent !== initial, firstFrame, { timeout: 5000 });
    await page.waitForTimeout(100);
    const laterPixels = await pixelSignature();
    assert.notEqual(firstPixels, laterPixels, 'playing the rigged character must change rendered canvas pixels');
    await page.locator('#play').click();

    // Author and evaluate a saved character motion path in the actual rig UI.
    await page.locator('#motionPathStart').fill('0');
    await page.locator('#motionPathDuration').fill('20');
    await page.locator('#motionPathFromX').fill('0');
    await page.locator('#motionPathFromY').fill('0');
    await page.locator('#motionPathToX').fill('200');
    await page.locator('#motionPathToY').fill('40');
    await page.locator('#motionPathEasing').selectOption('linear');
    await page.locator('#motionPathApply').click();
    await page.waitForFunction(() => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      return rig?.animation?.type === 'motion_path'
        && rig.animation.path_duration_frames === 20
        && rig.animation.path_to_x === 200;
    });
    const pathMotion = await page.evaluate(async () => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      const { evaluateRigAnimation } = await import('/js/animation/animation_clips.js');
      return {
        first: evaluateRigAnimation(rig, 0).rootOffset,
        last: evaluateRigAnimation(rig, 20).rootOffset,
      };
    });
    assert.equal(pathMotion.first.x, 0);
    assert.equal(pathMotion.last.x, 200);
    assert.equal(pathMotion.last.y, 40);

    // Cubic Bezier motion paths use the saved control points, not straight-line interpolation.
    await page.locator('#motionPathC1X').fill('50');
    await page.locator('#motionPathC1Y').fill('100');
    await page.locator('#motionPathC2X').fill('150');
    await page.locator('#motionPathC2Y').fill('100');
    await page.locator('#motionPathEasing').selectOption('bezier');
    await page.locator('#motionPathApply').click();
    const curvedMotion = await page.evaluate(async () => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      const { evaluateRigAnimation } = await import('/js/animation/animation_clips.js');
      return evaluateRigAnimation(rig, 10).rootOffset;
    });
    assert.ok(Math.abs(curvedMotion.x - 100) < 1e-6);
    assert.ok(Math.abs(curvedMotion.y - 80) < 1e-6, `expected Bezier arc y≈80, got ${curvedMotion.y}`);

    // Pose Library captures a named pose and applies it as non-destructive rotation keys.
    await page.locator('#rigPoseName').fill('Smoke Pose');
    await page.locator('#rigPoseSave').click();
    await page.waitForFunction(() => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      return rig?.poses?.some(pose => pose.name === 'Smoke Pose' && Object.keys(pose.rotations || {}).length === rig.bones.length);
    });
    const savedPoseId = await page.locator('#rigPoseSelect').inputValue();
    assert.ok(savedPoseId, 'saved pose must be selectable');
    await page.locator('#rigPoseApply').click();
    await page.waitForFunction(() => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      return rig.bones.some(bone => (bone.tracks?.rotation || []).some(key => key.t === window.kae.state.frame));
    });

    // IK target schema accepts its real constraint shape and can be switched to FK mode.
    const ikPair = await page.evaluate(() => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      return {
        upper: rig.bones.find(bone => bone.name === 'Left Thigh')?.id,
        lower: rig.bones.find(bone => bone.name === 'Left Shin')?.id,
      };
    });
    assert.ok(ikPair.upper && ikPair.lower && ikPair.upper !== ikPair.lower);
    await page.locator('#ikUpperBone').selectOption(ikPair.upper);
    await page.locator('#ikLowerBone').selectOption(ikPair.lower);
    await page.locator('#ikTargetX').fill('600');
    await page.locator('#ikTargetY').fill('400');
    await page.locator('#ikEnabled').check();
    await page.locator('#ikApply').click();
    await page.waitForFunction(() => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      return rig.constraints.some(item => item.type === 'ik_two_bone' && item.enabled === true
        && item.upper_bone_id && item.lower_bone_id && item.target);
    });
    await page.locator('#ikEnabled').uncheck();
    await page.locator('#ikApply').click();
    await page.waitForFunction(() => {
      const rig = window.kae.state.project.rigs.find(item => item.character_id === 'browser_hero');
      return rig.constraints.some(item => item.type === 'ik_two_bone' && item.enabled === false);
    });

    // Head/face orientation writes editable transform keys on the active drawing layer.
    await page.locator('#faceYaw').fill('35');
    await page.locator('#facePitch').fill('20');
    await page.locator('#faceRoll').fill('-12');
    await page.locator('#faceDepth').fill('1.25');
    await page.locator('#facePoseKey').click();
    await page.waitForFunction(() => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      const layer = scene.layers.find(item => item.id === state.layerId);
      return ['rotation_y', 'rotation', 'scale_x', 'scale_y'].every(channel =>
        layer?.tracks?.[channel]?.some(key => key.t === state.frame));
    });
    const faceKeys = await page.evaluate(() => {
      const state = window.kae.state;
      const scene = state.project.scenes.find(item => item.id === state.sceneId);
      const layer = scene.layers.find(item => item.id === state.layerId);
      return {
        yaw: layer.tracks.rotation_y.find(key => key.t === state.frame)?.v,
        roll: layer.tracks.rotation.find(key => key.t === state.frame)?.v,
        depth: layer.tracks.scale_x.find(key => key.t === state.frame)?.v,
      };
    });
    assert.equal(faceKeys.yaw, 35);
    assert.equal(faceKeys.roll, -12);
    assert.equal(faceKeys.depth, 1.25);

    // Detailed face construction guides persist through the project editor settings schema.
    await page.locator('#kaeGuidesEnabled').check();
    await page.locator('#kaeGuideHead').check();
    await page.locator('#kaeGuideEyes').check();
    await page.locator('#kaeGuideNose').check();
    await page.locator('#kaeGuideMouth').check();
    await page.locator('#kaeGuideEars').check();
    await page.locator('#kaeGuideHairline').check();
    await page.waitForFunction(() => {
      const guides = window.kae.state.project.editor_settings?.guides;
      return guides?.enabled && guides.head && guides.eyes && guides.nose && guides.mouth && guides.ears && guides.hairline;
    });

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

    await page.goto(baseURL, { waitUntil: 'networkidle' });
    await page.locator('[data-template="cinematic"]').click();
    await page.waitForURL(/editor\.html\?project=/);
    await page.locator('[data-ws="studio"]').click();
    await page.locator('[data-studio-tab="rig"]').click();
    await page.locator('#rigCharacter').selectOption('character_walker');
    await page.waitForFunction(() => !document.querySelector('#rigTurnApply')?.disabled);
    await page.locator('#turnStartFrame').fill('20');
    await page.locator('#turnDuration').fill('12');
    await page.locator('#rigTurnApply').click();
    await page.waitForFunction(() => {
      const scene = window.kae.state.project.scenes.find(item => item.id === window.kae.state.sceneId);
      const front = scene.layers.find(layer => layer.id === 'layer_walker_head_front');
      const profile = scene.layers.find(layer => layer.id === 'layer_walker_head_profile');
      return front?.tracks?.rotation_y?.some(key => key.t === 26 && key.v === 45)
        && front?.tracks?.opacity?.some(key => key.t === 32 && key.v === 0)
        && profile?.tracks?.opacity?.some(key => key.t === 32 && key.v === 1);
    });

    assert.deepEqual(pageErrors, [], `browser runtime errors: ${pageErrors.join('; ')}`);
  } finally {
    await browser.close();
  }
});


test('Geometry Nodes builds procedural shapes and persists graph data in the project', async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  try {
    await page.goto(baseURL, { waitUntil: 'networkidle' });
    await page.locator('#newName').fill('KAE Geometry Nodes Smoke');
    await page.locator('#create').click();
    await page.waitForURL(/editor\.html\?project=/);
    await page.waitForFunction(() => window.kae?.state?.project?.settings?.width > 0);
    await page.locator('#wtabs [data-ws="nodes"]').click();
    await page.locator('#geoCanvas').waitFor({ state: 'visible' });
    await page.locator('#geoCanvas .geo-node').first().click();
    const radius = page.locator('#geoInspector input').first();
    await radius.fill('64');
    await radius.press('Enter');
    await page.locator('#geoNodeType').selectOption('array');
    await page.locator('#geoAddNode').click();
    await page.waitForFunction(() => window.kae.state.project.node_graphs?.[0]?.nodes?.some(node => node.type === 'array'));
    await page.locator('#geoNodeType').selectOption('star');
    await page.locator('#geoAddNode').click();
    await page.waitForFunction(() => window.kae.state.project.node_graphs?.[0]?.nodes?.some(node => node.type === 'star'));
    await page.locator('#geoNodeType').selectOption('wave');
    await page.locator('#geoAddNode').click();
    await page.waitForFunction(() => window.kae.state.project.node_graphs?.[0]?.nodes?.some(node => node.type === 'wave'));
    await page.locator('#geoNodeType').selectOption('math');
    await page.locator('#geoAddNode').click();
    await page.waitForFunction(() => window.kae.state.project.node_graphs?.[0]?.nodes?.some(node => node.type === 'math'));
    await page.locator('#geoInspector select').selectOption('abs_x');
    await page.waitForFunction(() => window.kae.state.project.node_graphs[0].nodes.find(node => node.type === 'math')?.params?.operation === 'abs_x');
    await page.locator('#geoNodeType').selectOption('switch');
    await page.locator('#geoAddNode').click();
    await page.waitForFunction(() => window.kae.state.project.node_graphs?.[0]?.nodes?.some(node => node.type === 'switch'));
    await page.locator('#geoInspector input[type="checkbox"]').uncheck();
    await page.waitForFunction(() => window.kae.state.project.node_graphs[0].nodes.find(node => node.type === 'switch')?.params?.enabled === false);
    await page.locator('#geoNodeType').selectOption('animate');
    await page.locator('#geoAddNode').click();
    await page.waitForFunction(() => window.kae.state.project.node_graphs?.[0]?.nodes?.some(node => node.type === 'animate'));
    await page.locator('#geoNodeType').selectOption('style');
    await page.locator('#geoAddNode').click();
    await page.waitForFunction(() => window.kae.state.project.node_graphs?.[0]?.nodes?.some(node => node.type === 'style'));
    await page.locator('#geoNodeType').selectOption('opacity');
    await page.locator('#geoAddNode').click();
    await page.waitForFunction(() => window.kae.state.project.node_graphs?.[0]?.nodes?.some(node => node.type === 'opacity'));
    await page.locator('#geoNodeType').selectOption('mask');
    await page.locator('#geoAddNode').click();
    await page.waitForFunction(() => window.kae.state.project.node_graphs?.[0]?.nodes?.some(node => node.type === 'mask'));
    await page.locator('#save').click();
    await page.waitForFunction(() => window.kae.state.dirty === false);
    const projectUrl = page.url();
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.kae?.state?.project?.node_graphs?.length > 0);
    const saved = await page.evaluate(() => {
      const graph = window.kae.state.project.node_graphs[0];
      return {
        radius: graph.nodes.find(node => node.type === 'circle')?.params?.radius,
        hasArray: graph.nodes.some(node => node.type === 'array'),
        hasStar: graph.nodes.some(node => node.type === 'star'),
        hasWave: graph.nodes.some(node => node.type === 'wave'),
        hasMath: graph.nodes.some(node => node.type === 'math'),
        hasSwitch: graph.nodes.some(node => node.type === 'switch'),
        hasAnimate: graph.nodes.some(node => node.type === 'animate'),
        hasStyle: graph.nodes.some(node => node.type === 'style'),
        hasOpacity: graph.nodes.some(node => node.type === 'opacity'),
        hasMask: graph.nodes.some(node => node.type === 'mask'),
        graphCount: window.kae.state.project.node_graphs.length,
      };
    });
    assert.equal(saved.radius, 64);
    assert.equal(saved.hasArray, true);
    assert.equal(saved.hasStar, true);
    assert.equal(saved.hasWave, true);
    assert.equal(saved.hasMath, true);
    assert.equal(saved.hasSwitch, true);
    assert.equal(saved.hasAnimate, true);
    assert.equal(saved.hasStyle, true);
    assert.equal(saved.hasOpacity, true);
    assert.equal(saved.hasMask, true);
    assert.ok(saved.graphCount >= 1);
    assert.deepEqual(pageErrors, [], 'geometry node runtime errors: ' + pageErrors.join('; '));
  } finally {
    await browser.close();
  }
});

test('Android-sized browser keeps editor tools and timeline reachable without an AI workspace overlay', async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    screen: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
  });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  try {
    await page.goto(baseURL, { waitUntil: 'networkidle' });
    await page.locator('#newName').fill('KAE Android Layout');
    await page.locator('#create').click();
    await page.waitForURL(/editor\.html\?project=/);
    await page.locator('#canvas').waitFor({ state: 'visible' });
    assert.equal(await page.locator('#aiLaunch').count(), 0, 'mobile editor must not show an AI workspace launcher');
    assert.equal(await page.locator('#aiStudio').count(), 0, 'mobile editor must not mount an AI workspace overlay');

    const layout = await page.evaluate(() => {
      const rect = selector => {
        const node = document.querySelector(selector);
        if (!node) return null;
        const box = node.getBoundingClientRect();
        const style = getComputedStyle(node);
        return {
          x: box.x, y: box.y, right: box.right, bottom: box.bottom,
          width: box.width, height: box.height,
          overflowY: style.overflowY,
        };
      };
      return {
        viewport: { width: innerWidth, height: innerHeight },
        bodyWidth: document.body.scrollWidth,
        app: rect('.app'),
        canvas: rect('#canvas'),
        shelf: rect('.shelf'),
        timeline: rect('#slotC'),
      };
    });
    assert.ok(layout.canvas.width > 0 && layout.canvas.height > 0, 'mobile canvas should remain visible');
    assert.ok(layout.timeline.height >= 150, 'timeline should retain a usable mobile height');
    assert.ok(layout.timeline.width > 0, 'mobile timeline should remain visible and reachable');
    assert.deepEqual(pageErrors, [], `mobile browser runtime errors: ${pageErrors.join('; ')}`);
  } finally {
    await context.close();
    await browser.close();
  }
});
