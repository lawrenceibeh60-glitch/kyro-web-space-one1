// KAE compositor graph: ordered, saved post-processing nodes.
import { state } from '../core/state_manager.js';
import { execute, setValue } from '../core/command_manager.js';
import { flattenLayerTree } from '../scene/scene_hierarchy.js';

const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
export const COMPOSITOR_NODE_TYPES = Object.freeze({
  render_layers: { label: 'Render Layers', defaults: {} },
  color_correct: { label: 'Color Correct', defaults: { brightness: 0, contrast: 0, saturation: 100 } },
  levels: { label: 'Levels', defaults: { brightness: 0, contrast: 0 } },
  vignette: { label: 'Vignette', defaults: { strength: 0.35, radius: 0.7 } },
  alpha_over: { label: 'Alpha Over', defaults: { overlay_layer_id: '', opacity: 1 } },
  alpha_mask: { label: 'Alpha Mask / Matte', defaults: { mask_layer_id: '', invert: false } },
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
  const sorted = layers.filter(layer => layer && layer.canvas && !excludedIds.has(layer.id)).slice();
  if (direction === 'near_to_far' || direction === 'far_to_near') sorted.sort((a, b) =>
    direction === 'near_to_far' ? (Number(a.depth) || 0) - (Number(b.depth) || 0) : (Number(b.depth) || 0) - (Number(a.depth) || 0));
  for (const layer of sorted) drawLayerImage(ctx, layer, width, height);
  return sorted.map(layer => layer.id);
}

function makeCanvas(documentRef, width, height) {
  const canvas = documentRef.createElement('canvas');
  canvas.width = width; canvas.height = height;
  return canvas;
}
function copyCanvasInto(targetCtx, source, width, height, composite = 'copy') {
  targetCtx.save();
  targetCtx.setTransform(1, 0, 0, 1, 0, 0);
  targetCtx.globalAlpha = 1;
  targetCtx.globalCompositeOperation = composite;
  targetCtx.filter = 'none';
  targetCtx.clearRect(0, 0, width, height);
  if (source) targetCtx.drawImage(source, 0, 0, width, height);
  targetCtx.restore();
}
function topologicalCompositorOrder(nodes, links) {
  const orderIndex = new Map(nodes.map((node, index) => [node.id, index]));
  const incoming = new Map(nodes.map(node => [node.id, 0]));
  const outgoing = new Map(nodes.map(node => [node.id, []]));
  for (const link of links || []) {
    if (!incoming.has(link.from) || !incoming.has(link.to)) continue;
    outgoing.get(link.from).push(link.to);
    incoming.set(link.to, incoming.get(link.to) + 1);
  }
  const queue = nodes.filter(node => incoming.get(node.id) === 0).map(node => node.id);
  const result = [];
  while (queue.length) {
    queue.sort((a, b) => orderIndex.get(a) - orderIndex.get(b));
    const id = queue.shift();
    result.push(nodes[orderIndex.get(id)]);
    for (const next of outgoing.get(id) || []) {
      incoming.set(next, incoming.get(next) - 1);
      if (incoming.get(next) === 0) queue.push(next);
    }
  }
  return result.length === nodes.length ? result : nodes;
}

/** Evaluate image sockets as a DAG. Each node writes an isolated surface, so branches can be reused. */
export function applyCompositorGraph(ctx, graph, width, height, options = {}) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const links = Array.isArray(graph?.links) ? graph.links : [];
  const trace = [];
  const documentRef = ctx?.canvas?.ownerDocument;
  if (!documentRef?.createElement || !nodes.length) return trace;
  const layers = Array.isArray(options.layers) ? options.layers : [];
  const layerById = new Map(layers.map(layer => [layer.id, layer]));
  const base = makeCanvas(documentRef, width, height);
  base.getContext('2d')?.drawImage(ctx.canvas, 0, 0, width, height);
  const outputs = new Map();
  const order = topologicalCompositorOrder(nodes, links);
  const getInputLink = (node, socket) => links.find(link => link.to === node.id && Number(link.to_socket ?? link.input ?? 0) === socket);
  const getInputCanvas = (node, socket, fallback) => {
    const link = getInputLink(node, socket);
    return link ? outputs.get(link.from) || fallback : fallback;
  };
  let lastOutput = base;
  for (const node of order) {
    const params = node.params || {};
    const input0 = getInputCanvas(node, 0, lastOutput || base);
    const input1Link = getInputLink(node, 1);
    const input1 = input1Link ? outputs.get(input1Link.from) : null;
    const output = makeCanvas(documentRef, width, height);
    const outCtx = output.getContext('2d');
    if (!outCtx) continue;
    if (node.enabled === false) {
      copyCanvasInto(outCtx, input0 || base, width, height);
    } else if (node.type === 'render_layers') {
      copyCanvasInto(outCtx, base, width, height);
    } else if (node.type === 'z_depth') {
      rebuildLayerStack(outCtx, layers, width, height, options.background,
        params.direction || 'far_to_near', new Set());
    } else {
      copyCanvasInto(outCtx, input0 || base, width, height);
      if (node.type === 'color_correct') {
        const brightness = clamp(Number(params.brightness) || 0, -100, 100);
        const contrast = clamp(Number(params.contrast) || 0, -100, 100);
        const saturation = clamp(Number(params.saturation == null ? 100 : params.saturation), 0, 300);
        compositeFilter(outCtx, width, height, 'brightness(' + (100 + brightness) + '%) contrast(' + (100 + contrast) + '%) saturate(' + saturation + '%)');
      } else if (node.type === 'levels') {
        const brightness = clamp(Number(params.brightness) || 0, -100, 100);
        const contrast = clamp(Number(params.contrast) || 0, -100, 100);
        compositeFilter(outCtx, width, height, 'brightness(' + (100 + brightness) + '%) contrast(' + (100 + contrast) + '%)');
      } else if (node.type === 'vignette') {
        vignette(outCtx, width, height, params);
      } else if (node.type === 'alpha_over') {
        const layer = layerById.get(String(params.overlay_layer_id || ''));
        const overlay = input1 || layer?.canvas || null;
        if (overlay) {
          outCtx.save(); outCtx.globalAlpha = clamp(Number(params.opacity ?? 1), 0, 1);
          outCtx.globalCompositeOperation = 'source-over';
          outCtx.drawImage(overlay, 0, 0, width, height); outCtx.restore();
        }
      } else if (node.type === 'alpha_mask') {
        const layer = layerById.get(String(params.mask_layer_id || ''));
        const matte = input1 || layer?.canvas || null;
        if (matte) {
          outCtx.save(); outCtx.globalAlpha = 1;
          outCtx.globalCompositeOperation = params.invert ? 'destination-out' : 'destination-in';
          outCtx.drawImage(matte, 0, 0, width, height); outCtx.restore();
        }
      }
    }
    outputs.set(node.id, output);
    lastOutput = output;
    trace.push(node.type);
  }
  const outputNode = order.find(node => node.type === 'output' && node.enabled !== false);
  const finalCanvas = outputNode
    ? getInputCanvas(outputNode, 0, outputs.get(outputNode.id) || lastOutput || base)
    : lastOutput || base;
  copyCanvasInto(ctx, finalCanvas, width, height);
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
        if (key === 'direction' || key === 'overlay_layer_id' || key === 'mask_layer_id') {
          input = document.createElement('select');
          const choices = key === 'direction' ? [['far_to_near', 'Far to near'], ['near_to_far', 'Near to far']] : [['', 'Select layer'], ...flattenLayerTree(((state.project && state.project.scenes || []).find(scene => scene.id === state.sceneId)?.layers || []), [], []).map(({ layer }) => [layer.id, layer.name || layer.id])];
          for (const choice of choices) { const option = document.createElement('option'); option.value = choice[0]; option.textContent = choice[1]; input.append(option); }
          input.value = params[key] == null ? fallback : params[key];
        } else if (key === 'invert') {
          input = document.createElement('input'); input.type = 'checkbox'; input.checked = !!params[key];
        } else {
          input = document.createElement('input'); input.type = 'number'; input.step = 'any'; input.value = params[key] == null ? fallback : params[key];
          input.min = key === 'saturation' || key === 'strength' || key === 'opacity' ? '0' : '-100';
          input.max = key === 'saturation' ? '300' : key === 'strength' || key === 'opacity' ? '1' : key === 'radius' ? '1' : '100';
        }
        input.onchange = () => {
          const value = input.tagName === 'SELECT' ? input.value : input.type === 'checkbox' ? input.checked : Number(input.value);
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
