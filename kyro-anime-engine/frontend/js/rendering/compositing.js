// KAE compositor graph: ordered, saved post-processing nodes.
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
export const COMPOSITOR_NODE_TYPES = Object.freeze({
  render_layers: { label: 'Render Layers', defaults: {} },
  color_correct: { label: 'Color Correct', defaults: { brightness: 0, contrast: 0, saturation: 100 } },
  levels: { label: 'Levels', defaults: { brightness: 0, contrast: 0 } },
  vignette: { label: 'Vignette', defaults: { strength: 0.35, radius: 0.7 } },
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
export function applyCompositorGraph(ctx, graph, width, height) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const trace = [];
  for (const node of nodes) {
    if (!node || node.enabled === false) continue;
    const p = node.params || {};
    if (node.type === 'color_correct') {
      const brightness = clamp(Number(p.brightness) || 0, -100, 100);
      const contrast = clamp(Number(p.contrast) || 0, -100, 100);
      const saturation = clamp(Number(p.saturation ?? 100), 0, 300);
      compositeFilter(ctx, width, height, `brightness(${100 + brightness}%) contrast(${100 + contrast}%) saturate(${saturation}%)`);
    } else if (node.type === 'levels') {
      const brightness = clamp(Number(p.brightness) || 0, -100, 100);
      const contrast = clamp(Number(p.contrast) || 0, -100, 100);
      compositeFilter(ctx, width, height, `brightness(${100 + brightness}%) contrast(${100 + contrast}%)`);
    } else if (node.type === 'vignette') {
      vignette(ctx, width, height, p);
    }
    trace.push(node.type);
  }
  return trace;
}
