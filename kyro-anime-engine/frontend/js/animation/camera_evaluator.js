import { evaluateTrack } from './interpolation.js';

export function evaluateCamera(camera, frame) {
  const transform = camera?.transform || {};
  const tracks = camera?.tracks || {};
  const value = (channel, fallback) => {
    const track = tracks[channel];
    const result = track?.length ? evaluateTrack(track, frame) : (transform[channel] ?? fallback);
    return Number.isFinite(result) ? result : fallback;
  };
  const zoom = Math.min(32, Math.max(0.05, value('scale_x', 1)));
  return {
    x: value('x', 0),
    y: value('y', 0),
    zoom,
    zoomY: Math.min(32, Math.max(0.05, value('scale_y', zoom))),

    rotation: value('rotation', 0),
  };
}

export function applyCameraTransform(ctx, width, height, camera, frame) {
  const { x, y, zoom, zoomY, rotation } = evaluateCamera(camera, frame);
  ctx.translate(width / 2 + x, height / 2 + y);
  ctx.rotate(rotation * Math.PI / 180);
  ctx.scale(zoom, zoomY);
  ctx.translate(-width / 2, -height / 2);
  return { x, y, zoom, zoomY };
}

export function applyCameraDepthTransform(ctx, width, height, camera, frame, depth = 1) {
  const { x, y, zoom, zoomY, rotation } = evaluateCamera(camera, frame);
  const influence = Math.min(2, Math.max(0, Number.isFinite(depth) ? depth : 1));
  const layerZoom = 1 + (zoom - 1) * influence;
  const layerZoomY = 1 + (zoomY - 1) * influence;
  ctx.translate(width / 2 + x * influence, height / 2 + y * influence);
  ctx.rotate(rotation * influence * Math.PI / 180);
  ctx.scale(layerZoom, layerZoomY);
  ctx.translate(-width / 2, -height / 2);
  return { x: x * influence, y: y * influence, zoom: layerZoom, zoomY: layerZoomY };
}
