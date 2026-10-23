// KAE compositor graph: ordered, saved post-processing nodes.
import { state } from '../core/state_manager.js';
import { execute, setValue } from '../core/command_manager.js';

const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
export const COMPOSITOR_NODE_TYPES = Object.freeze({
  render_layers: { label: 'Render Layers', defaults: {} },
  color_correct: { label: 'Color Correct', defaults: { brightness: 0, contrast: 0, saturation: 100 } },
  levels: { label: 'Levels', defaults: { brightness: 0, contrast: 0 } },
  vignette: { label: 'Vignette', defaults: { strength: 0.35, radius: 0.7 } },
  alpha_over: { label: 'Alpha Over', defaults: { overlay_layer_id: '', opacity: 1 } },
  z_depth: { label: 'Z-Depth Sort', defaults: { direction: 'far_to_near' } },
  output: { label: 'Composite Output', defaults: {} },
});
function compositeFilter(ctx, width, height, filter) {
  if (!ctx?.canvas?.ownerDocument?.createElement || width < 1 || height < 1) return;
  const source = ctx.canvas.ownerDocument.createElement('canvas');
  source.width = width; source.height = height;
  const copy = source.getContext('2d');
  if (!copy) return;
  copy.drawImage(ctx.canvas, 0, 0, width, height);
  ctx.save(); ctx.globalCompositeOperation = 'copy'; ctx.filter = filter;
  ctx.drawImage(source, 0, 0, width, height); ctx.restore();
}
function vignette(ctx, width, height, params) {
  if (!ctx?.createRadialGradient || width < 1 || height < 1) return;
  const strength = clamp(Number(params.strength) || 0, 0, 1);
  if (!strength) return;
  const radius = clamp(Number(params.radius) || .7, .1, 1);
  const gradient = ctx.createRadialGradient(width / 2, height / 2, Math.min(width, height) * radius * .25, width / 2, height / 2, Math.max(width, height) * .72);
  gradient.addColorStop(0, 'rgba(0,0,0,0)');
  gradient.addColorStop(radius, 'rgba(0,0,0,0)');
  gradient.addColorStop(1, `rgba(0,0,0,${strength})`);
  ctx.save(); ctx.fillStyle = gradient; ctx.fillRect(0, 0, width, height); ctx.restore();
}
function drawLayerImage(ctx, layer, width, height, opacity = 1) {
  if (!layer || !layer.canvas) return;
  ctx.save();
  ctx.globalAlpha = clamp(Number(opacity), 0, 1);
  const blends = { normal: 'source-over', multiply: 'multiply', screen: 'screen', overlay: 'overlay', add: 'lighter' };
  ctx.globalCompositeOperation = blends[layer.blend] || 'source-over';
  ctx.drawImage(layer.canvas, 0, 0, width, height);
  ctx.restore();
}

function rebuildLayerStack(ctx, layers, width, height, background, direction, excludedIds) {
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'copy'; ctx.clearRect(0, 0, width, height);
  if (background && background !== 'transparent') { ctx.fillStyle = background; ctx.fillRect(0, 0, width, height); }
  ctx.restore();
  const sorted = layers.filter(layer => layer && layer.canvas && !excludedIds.has(layer.id)).slice().sort((a, b) =>
    direction === 'near_to_far' ? (Number(a.depth) || 0) - (Number(b.depth) || 0) : (Number(b.depth) || 0) - (Number(a.depth) || 0));
  for (const layer of sorted) drawLayerImage(ctx, layer, width, height);
  return sorted.map(layer => layer.id);
}

/** Apply post-processing and optional layer-aware compositor nodes. */
export function applyCompositorGraph(ctx, graph, width, height, options = {}) {
  const nodes = Array.isArray(graph && graph.nodes) ? graph.nodes : [];
  const trace = [];
  const layers = Array.isArray(options.layers) ? options.layers : [];
  const byId = new Map(layers.map(layer => [layer.id, layer]));
  const enabled = nodes.filter(node => node && node.enabled !== false);
  const depthNode = enabled.find(node => node.type === 'z_depth');
  const alphaNodes = enabled.filter(node => node.type === 'alpha_over');
  if ((depthNode || alphaNodes.length) && layers.length) {
    const excluded = new Set(alphaNodes.map(node => node.params && node.params.overlay_layer_id).filter(Boolean));
    rebuildLayerStack(ctx, layers, width, height, options.background, depthNode && depthNode.params && depthNode.params.direction || 'far_to_near', excluded);
  }
  for (const node of enabled) {
    const p = node.params || {};
    if (node.type === 'color_correct') {
      const brightness = clamp(Number(p.brightness) || 0, -100, 100);
      const contrast = clamp(Number(p.contrast) || 0, -100, 100);
      const saturation = clamp(Number(p.saturation == null ? 100 : p.saturation), 0, 300);
      compositeFilter(ctx, width, height, 'brightness(' + (100 + brightness) + '%) contrast(' + (100 + contrast) + '%) saturate(' + saturation + '%)');
    } else if (node.type === 'levels') {
      const brightness = clamp(Number(p.brightness) || 0, -100, 100);
      const contrast = clamp(Number(p.contrast) || 0, -100, 100);
      compositeFilter(ctx, width, height, 'brightness(' + (100 + brightness) + '%) contrast(' + (100 + contrast) + '%)');
    } else if (node.type === 'vignette') {
      vignette(ctx, width, height, p);
    } else if (node.type === 'alpha_over') {
      const layer = byId.get(String(p.overlay_layer_id || ''));
      if (layer) drawLayerImage(ctx, layer, width, height, p.opacity == null ? 1 : p.opacity);
    }
    trace.push(node.type);
  }
  return trace;
}

const makeNodeId = () => 'comp_' + Math.random().toString(36).slice(2, 11);
const graphFromNodes = nodes => ({ nodes, links: nodes.slice(0, -1).map((node, index) => ({ from: node.id, to: nodes[index + 1].id })) });
const defaultCompositorGraph = () => graphFromNodes([
  { id: 'render_layers', type: 'render_layers', enabled: true, params: {} },
  { id: 'output', type: 'output', enabled: true, params: {} },
]);
export function initCompositorStudio() {
  const list = document.getElementById('compositorNodeList');
  const typeSelect = document.getElementById('compositorNodeType');
  const addButton = document.getElementById('compositorAddNode');
  if (!list || !typeSelect || !addButton) return;
  const current = () => state.project?.compositor_graph || null;
  const commitGraph = (graph, label) => { execute(setValue(['compositor_graph'], graph, label)); render(); };
  const render = () => {
    list.replaceChildren();
    const graph = current();
    if (!graph?.nodes?.length) {
      const empty = document.createElement('p'); empty.className = 'hint'; empty.textContent = 'No compositor graph yet. Add a node to create Render Layers → Output.'; list.append(empty); return;
    }
    graph.nodes.forEach((node, index) => {
      const meta = COMPOSITOR_NODE_TYPES[node.type];
      if (!meta) return;
      const card = document.createElement('article'); card.className = 'compositor-node' + (node.enabled === false ? ' disabled' : '');
      const head = document.createElement('div'); head.className = 'compositor-node-head';
      const title = document.createElement('strong'); title.textContent = meta.label; head.append(title);
      const toggle = document.createElement('button'); toggle.type = 'button'; toggle.textContent = node.enabled === false ? 'Enable' : 'On'; toggle.title = 'Toggle compositor node'; toggle.onclick = () => { const nodes = graph.nodes.map(n => n.id === node.id ? { ...n, enabled: n.enabled === false } : { ...n }); commitGraph(graphFromNodes(nodes), 'Toggle compositor node'); }; head.append(toggle);
      if (!['render_layers', 'output'].includes(node.type)) {
        const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×'; remove.title = 'Remove node'; remove.onclick = () => { const nodes = graph.nodes.filter(n => n.id !== node.id).map(n => ({ ...n })); commitGraph(graphFromNodes(nodes), 'Remove compositor node'); }; head.append(remove);
      }
      card.append(head);
      const params = node.params || {};
      for (const [key, fallback] of Object.entries(meta.defaults)) {
        const label = document.createElement('label'); label.className = 'compositor-param'; label.textContent = key.replaceAll('_', ' ');
        let input;
        if (key === 'direction' || key === 'overlay_layer_id') {
          input = document.createElement('select');
          const choices = key === 'direction' ? [['far_to_near', 'Far to near'], ['near_to_far', 'Near to far']] : [['', 'Select layer'], ...((state.project && state.project.scenes || []).find(scene => scene.id === state.sceneId)?.layers || []).map(layer => [layer.id, layer.name || layer.id])];
          for (const choice of choices) { const option = document.createElement('option'); option.value = choice[0]; option.textContent = choice[1]; input.append(option); }
          input.value = params[key] == null ? fallback : params[key];
        } else {
          input = document.createElement('input'); input.type = 'number'; input.step = 'any'; input.value = params[key] == null ? fallback : params[key];
          input.min = key === 'saturation' || key === 'strength' || key === 'opacity' ? '0' : '-100';
          input.max = key === 'saturation' ? '300' : key === 'strength' || key === 'opacity' ? '1' : key === 'radius' ? '1' : '100';
        }
        input.onchange = () => {
          const value = input.tagName === 'SELECT' ? input.value : Number(input.value);
          if (typeof value === 'number' && !Number.isFinite(value)) return;
          const nodes = graph.nodes.map(n => n.id === node.id ? { ...n, params: { ...(n.params || {}), [key]: value } } : { ...n });
          commitGraph(graphFromNodes(nodes), 'Edit compositor parameter');
        };
        label.append(input); card.append(label);
      }
      if (!['render_layers', 'output'].includes(node.type)) {
        const order = document.createElement('div'); order.className = 'compositor-order';
        for (const [textLabel, delta] of [['↑', -1], ['↓', 1]]) {
          const button = document.createElement('button'); button.type = 'button'; button.textContent = textLabel; button.title = delta < 0 ? 'Move node up' : 'Move node down'; button.disabled = (index + delta <= 0 || index + delta >= graph.nodes.length - 1);
          button.onclick = () => { const nodes = graph.nodes.map(n => ({ ...n })); const target = index + delta; [nodes[index], nodes[target]] = [nodes[target], nodes[index]]; commitGraph(graphFromNodes(nodes), 'Reorder compositor node'); };
          order.append(button);
        }
        card.append(order);
      }
      list.append(card);
    });
    const footer = document.createElement('p'); footer.className = 'hint'; footer.textContent = 'Top-to-bottom order is evaluated after scene effects. Node parameters are saved in the project.'; list.append(footer);
  };
  addButton.onclick = () => {
    const type = typeSelect.value, meta = COMPOSITOR_NODE_TYPES[type];
    if (!meta || type === 'render_layers' || type === 'output') return;
    const graph = current() || defaultCompositorGraph();
    if (graph.nodes.length >= 128) return;
    const nodes = graph.nodes.map(n => ({ ...n, params: { ...(n.params || {}) } }));
    const outputIndex = nodes.findIndex(n => n.type === 'output');
    nodes.splice(outputIndex < 0 ? nodes.length : outputIndex, 0, { id: makeNodeId(), type, enabled: true, params: { ...meta.defaults } });
    commitGraph(graphFromNodes(nodes), 'Add compositor node');
  };
  render();
}
