const clone = value => JSON.parse(JSON.stringify(value));
const sameJson = (left, right) => JSON.stringify(left) === JSON.stringify(right);

function addUniqueById(target, incoming, idOf, canAdd = () => true) {
  const ids = new Set(target.map(idOf));
  let added = 0;
  let skipped = 0;
  for (const item of incoming) {
    const id = idOf(item);
    if (typeof id !== 'string' || ids.has(id) || !canAdd(item)) {
      skipped++;
      continue;
    }
    target.push(clone(item));
    ids.add(id);
    added++;
  }
  return { added, skipped };
}

function importableLayers(layers, drawings, conflictingDrawings) {
  return (Array.isArray(layers) ? layers : []).filter(layer => {
    if (!Array.isArray(layer?.exposures)) return true;
    return layer.exposures.every(exposure =>
      typeof exposure?.drawing === 'string'
      && drawings.has(exposure.drawing)
      && !conflictingDrawings.has(exposure.drawing));
  });
}

export function mergeProjectAdditively(current, incoming) {
  const project = {
    ...current,
    drawings: { ...(current.drawings || {}) },
    scenes: (current.scenes || []).map(scene => ({
      ...scene,
      layers: [...(scene.layers || [])],
      lights: [...(scene.lights || [])],
    })),
    characters: [...(current.characters || [])],
    effects: [...(current.effects || [])],
    rigs: [...(current.rigs || [])],
    palette: [...(current.palette || [])],
    audio: [...(current.audio || [])],
  };
  const added = { drawings: 0, scenes: 0, layers: 0, lights: 0, characters: 0, effects: 0, rigs: 0, palette: 0 };
  const skipped = { drawings: 0, scenes: 0, layers: 0, lights: 0, characters: 0, effects: 0, rigs: 0, audio: 0 };
  const conflictingDrawings = new Set();
  const drawings = project.drawings || (project.drawings = {});
  const incomingDrawings = incoming.drawings && typeof incoming.drawings === 'object'
    ? incoming.drawings
    : {};

  for (const [key, drawing] of Object.entries(incomingDrawings)) {
    if (!Object.hasOwn(drawings, key)) {
      drawings[key] = clone(drawing);
      added.drawings++;
    } else if (!sameJson(drawings[key], drawing)) {
      conflictingDrawings.add(key);
      skipped.drawings++;
    }
  }

  const availableDrawingIds = new Set(Object.keys(drawings));
  const scenes = project.scenes || (project.scenes = []);
  const scenesById = new Map(scenes.map(scene => [scene.id, scene]));
  const importedScenes = Array.isArray(incoming.scenes) ? incoming.scenes : [];
  for (const sourceScene of importedScenes) {
    if (!sourceScene || typeof sourceScene !== 'object' || typeof sourceScene.id !== 'string') {
      skipped.scenes++;
      continue;
    }
    const incomingLayers = importableLayers(sourceScene.layers, availableDrawingIds, conflictingDrawings);
    const targetScene = scenesById.get(sourceScene.id);
    if (!targetScene) {
      scenes.push({ ...clone({ ...sourceScene, layers: [] }), layers: clone(incomingLayers) });
      scenesById.set(sourceScene.id, scenes[scenes.length - 1]);
      added.scenes++;
      added.layers += incomingLayers.length;
      skipped.layers += (sourceScene.layers || []).length - incomingLayers.length;
      added.lights += Array.isArray(sourceScene.lights) ? sourceScene.lights.length : 0;
      continue;
    }

    for (const [key, value] of Object.entries(sourceScene)) {
      if (key !== 'layers' && key !== 'lights' && targetScene[key] === undefined) {
        targetScene[key] = clone(value);
      }
    }
    const targetLayers = targetScene.layers || (targetScene.layers = []);
    const layerResult = addUniqueById(targetLayers, incomingLayers, layer => layer?.id);
    added.layers += layerResult.added;
    skipped.layers += layerResult.skipped + (sourceScene.layers || []).length - incomingLayers.length;

    const targetLights = targetScene.lights || (targetScene.lights = []);
    const lightResult = addUniqueById(
      targetLights,
      Array.isArray(sourceScene.lights) ? sourceScene.lights : [],
      light => light?.id,
    );
    added.lights += lightResult.added;
    skipped.lights += lightResult.skipped;
  }

  const characterResult = addUniqueById(
    project.characters || (project.characters = []),
    Array.isArray(incoming.characters) ? incoming.characters : [],
    character => character?.id,
  );
  added.characters += characterResult.added;
  skipped.characters += characterResult.skipped;

  const effectResult = addUniqueById(
    project.effects || (project.effects = []),
    Array.isArray(incoming.effects) ? incoming.effects : [],
    effect => effect?.id,
    effect => project.scenes.some(scene => scene.id === effect?.scene_id)
      && Number.isInteger(effect?.start_frame ?? 0)
      && Number.isInteger(effect?.end_frame ?? project.settings.duration_frames - 1)
      && (effect.start_frame ?? 0) >= 0
      && (effect.end_frame ?? project.settings.duration_frames - 1) < project.settings.duration_frames
      && (effect.start_frame ?? 0) <= (effect.end_frame ?? project.settings.duration_frames - 1),
  );
  added.effects += effectResult.added;
  skipped.effects += effectResult.skipped;

  const currentRigs = project.rigs || (project.rigs = []);
  const rigResult = addUniqueById(
    currentRigs,
    Array.isArray(incoming.rigs) ? incoming.rigs : [],
    rig => rig?.id,
    rig => project.characters.some(character => character.id === rig?.character_id)
      && !currentRigs.some(existing => existing.character_id === rig?.character_id),
  );
  added.rigs += rigResult.added;
  skipped.rigs += rigResult.skipped;

  const palette = project.palette || (project.palette = []);
  const paletteValues = new Set(palette);
  for (const color of Array.isArray(incoming.palette) ? incoming.palette : []) {
    if (typeof color === 'string' && !paletteValues.has(color)) {
      palette.push(color);
      paletteValues.add(color);
      added.palette++;
    }
  }

  const currentAudioIds = new Set((project.audio || []).map(clip => clip.id));
  skipped.audio = (Array.isArray(incoming.audio) ? incoming.audio : [])
    .filter(clip => !currentAudioIds.has(clip?.id)).length;

  return { project, added, skipped };
}
