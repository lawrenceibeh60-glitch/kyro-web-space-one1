import { bus } from '../core/event_bus.js';
import { state, getScene, getLayer, sceneIndex } from '../core/state_manager.js';
import { execute, batch, setValue } from '../core/command_manager.js';
import { drawStroke } from '../rendering/renderer.js';
import { strokePathPoints } from '../rendering/geometry.js';
import { toast } from './notifications.js';

const MAX_ASSET_FILE_BYTES = 10 * 1024 * 1024;

function validDrawing(drawing) {
  return drawing && typeof drawing === 'object' && !Array.isArray(drawing)
    && Array.isArray(drawing.strokes)
    && drawing.strokes.every(stroke => {
      const hasPoints = Array.isArray(stroke?.points) && stroke.points.length > 0;
      const hasCommands = Array.isArray(stroke?.commands) && stroke.commands.length > 1;
      return Boolean(stroke) && hasPoints !== hasCommands;
    });
}

export function initAssetBrowser() {
  const $ = id => document.getElementById(id);
  const list = $('assetList');
  let filter = '';

  function drawingBounds(drawing) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const stroke of drawing.strokes || []) for (const point of strokePathPoints(stroke)) {
      minX = Math.min(minX, point[0]); maxX = Math.max(maxX, point[0]);
      minY = Math.min(minY, point[1]); maxY = Math.max(maxY, point[1]);
    }
    if (!Number.isFinite(minX)) return { minX: 0, minY: 0, width: 1, height: 1 };
    return { minX, minY, width: Math.max(1, maxX - minX), height: Math.max(1, maxY - minY) };
  }

  function preview(canvas, drawing) {
    const ctx = canvas.getContext('2d');
    const bounds = drawingBounds(drawing), inset = 8;
    ctx.fillStyle = '#252525'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    const scale = Math.min((canvas.width - inset * 2) / bounds.width, (canvas.height - inset * 2) / bounds.height);
    ctx.save();
    ctx.translate((canvas.width - bounds.width * scale) / 2 - bounds.minX * scale,
      (canvas.height - bounds.height * scale) / 2 - bounds.minY * scale);
    ctx.scale(scale, scale);
    for (const stroke of drawing.strokes || []) drawStroke(ctx, stroke);
    ctx.restore();
  }

  function render() {
    if (!state.project) return;
    list.replaceChildren();
    const drawings = state.project.drawings || {};
    const entries = Object.entries(drawings).filter(([id, drawing]) => `${drawing.name || id} ${id}`.toLowerCase().includes(filter));
    if (!entries.length) {
      const empty = document.createElement('p');
      empty.className = 'asset-empty';
      empty.textContent = filter
        ? `No drawings match "${filter}".`
        : 'No drawing assets yet. Draw on a frame and save it here, or import drawing JSON.';
      list.append(empty);
      return;
    }
    for (const [id, drawing] of entries) {
      const card = document.createElement('article');
      card.className = 'asset-card';
      const thumb = document.createElement('canvas');
      thumb.width = 120; thumb.height = 76; thumb.className = 'asset-thumb';
      preview(thumb, drawing);
      const info = document.createElement('div');
      info.className = 'asset-info';
      const title = document.createElement('strong');
      title.textContent = drawing.name || id;
      const meta = document.createElement('small');
      meta.textContent = `${drawing.strokes?.length || 0} stroke${drawing.strokes?.length === 1 ? '' : 's'}`;
      info.append(title, meta);
      const add = document.createElement('button');
      add.className = 'asset-place';
      add.textContent = 'Add to frame';
      add.title = 'Place an independent copy on the selected layer at the current frame';
      add.onclick = () => placeDrawing(id);
      const actions = document.createElement('div');
      actions.className = 'asset-actions';
      const download = document.createElement('button');
      download.textContent = 'JSON';
      download.title = 'Download this drawing asset as JSON';
      download.onclick = () => {
        const blob = new Blob([JSON.stringify(drawing, null, 2)], { type: 'application/json' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${(drawing.name || id).replace(/[^a-z0-9_-]+/gi, '_')}.json`;
        link.click();
        URL.revokeObjectURL(link.href);
      };
      const inUse = state.project.scenes.some(scene => scene.layers.some(layer => layer.exposures?.some(exposure => exposure.drawing === id)));
      const remove = document.createElement('button');
      remove.textContent = '×';
      remove.title = inUse ? 'Remove this drawing from its exposures before deleting it' : 'Delete unused asset';
      remove.disabled = inUse;
      remove.onclick = () => {
        if (!inUse && confirm(`Delete unused asset "${drawing.name || id}"?`)) {
          execute(setValue(['drawings', id], undefined, 'Delete drawing asset'));
        }
      };
      actions.append(download, remove);
      card.append(thumb, info, add, actions);
      list.append(card);
    }
  }

  function uniqueId(prefix = 'asset') {
    let number = 1;
    while (Object.prototype.hasOwnProperty.call(state.project.drawings, `${prefix}_${number}`)) number++;
    return `${prefix}_${number}`;
  }

  function placeDrawing(sourceId) {
    const layer = getLayer();
    if (!layer) { toast('Select a layer first', 'err'); return; }
    if (layer.locked || layer.visible === false) { toast(layer.locked ? 'Unlock this layer first' : 'Show this layer first', 'err'); return; }
    const source = state.project.drawings[sourceId];
    if (!validDrawing(source)) { toast('This drawing asset is invalid', 'err'); return; }
    const id = uniqueId('asset');
    const drawing = JSON.parse(JSON.stringify(source));
    drawing.id = id;
    const frame = state.frame, exposures = (layer.exposures || []).flatMap(exposure => {
      const end = exposure.start + exposure.length;
      if (frame < exposure.start || frame >= end) return [exposure];
      return [
        ...(exposure.start < frame ? [{ ...exposure, length: frame - exposure.start }] : []),
        ...(frame + 1 < end ? [{ ...exposure, start: frame + 1, length: end - frame - 1 }] : []),
      ];
    });
    exposures.push({ start: frame, length: 1, drawing: id });
    exposures.sort((a, b) => a.start - b.start);
    const scene = getScene(), si = sceneIndex(), li = scene.layers.indexOf(layer);
    execute(batch([
      setValue(['drawings', id], drawing, 'Place drawing asset'),
      setValue(['scenes', si, 'layers', li, 'exposures'], exposures, 'Place drawing asset'),
    ], 'Place drawing asset'));
    toast(`Added ${source.name || 'drawing'} to frame ${frame + 1}`, 'ok');
  }

  function captureCurrent() {
    const layer = getLayer();
    const exposure = layer?.exposures?.find(item => state.frame >= item.start && state.frame < item.start + item.length);
    const source = exposure && state.project.drawings[exposure.drawing];
    if (!source) { toast('There is no drawing on the current frame to save', 'err'); return; }
    const name = prompt('Asset name', `${source.name || 'Drawing'} Asset`);
    if (name === null) return;
    const id = uniqueId('asset');
    const drawing = JSON.parse(JSON.stringify(source));
    drawing.id = id; drawing.name = name.trim() || `${source.name || 'Drawing'} Asset`;
    execute(setValue(['drawings', id], drawing, 'Save drawing asset'));
  }

  async function importFile(file) {
    if (!file) return;
    if (file.size > MAX_ASSET_FILE_BYTES) { toast('Drawing JSON must be 10 MB or smaller', 'err'); return; }
    try {
      const payload = JSON.parse(await file.text());
      const drawings = payload.format === 'kae' && payload.drawings && typeof payload.drawings === 'object'
        ? Object.values(payload.drawings)
        : [payload.drawing || payload];
      if (!drawings.length || drawings.some(drawing => !validDrawing(drawing))) {
        throw new Error('Expected a drawing with a strokes array of points');
      }
      const ids = new Set(Object.keys(state.project.drawings));
      let number = 1;
      const commands = drawings.map(source => {
        while (ids.has(`asset_${number}`)) number++;
        const id = `asset_${number++}`;
        ids.add(id);
        const drawing = JSON.parse(JSON.stringify(source));
        drawing.id = id;
        drawing.name = String(source.name || file.name.replace(/\.json$/i, ''));
        return setValue(['drawings', id], drawing, 'Import drawing asset');
      });
      execute(batch(commands, 'Import drawing assets'));
      toast(`Imported ${commands.length} drawing asset${commands.length === 1 ? '' : 's'}`, 'ok');
    } catch (error) {
      toast(error?.message || 'Could not import drawing JSON', 'err', 6000);
    }
  }

  $('assetImport').onclick = () => $('assetFile').click();
  $('assetCapture').onclick = captureCurrent;
  $('assetSearch').oninput = event => { filter = event.target.value.trim().toLowerCase(); render(); };
  $('assetFile').onchange = async event => {
    const file = event.target.files?.[0];
    if (file) await importFile(file);
    event.target.value = '';
  };
  bus.on('project:changed', render);
  bus.on('state', patch => { if ('project' in patch) render(); });
  bus.on('selection', () => { if (!getLayer()) render(); });
  render();
  return { render };
}
