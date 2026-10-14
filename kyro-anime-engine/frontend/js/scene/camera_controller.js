// Shared camera-editing operations for the viewport and future shot tools.
import { evaluateCamera } from '../animation/camera_evaluator.js';

const CHANNELS = new Set(['x', 'y', 'rotation', 'scale_x', 'scale_y']);
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export function writeCameraChannel(camera, channel, value, options = {}) {
  if (!CHANNELS.has(channel) || !Number.isFinite(value)) return camera;
  const frame = Number.isInteger(options.frame) && options.frame >= 0 ? options.frame : 0;
  const next = {
    ...(camera || {}),
    transform: { ...(camera?.transform || {}) },
    tracks: { ...(camera?.tracks || {}) },
  };
  const track = next.tracks[channel];
  if (options.autokey || (Array.isArray(track) && track.length > 0)) {
    const keys = Array.isArray(track) ? [...track] : [];
    const key = { t: frame, v: value, ease: options.ease || 'linear' };
    const index = keys.findIndex(item => item?.t === frame);
    if (index >= 0) keys[index] = key;
    else keys.push(key);
    keys.sort((a, b) => a.t - b.t);
    next.tracks[channel] = keys;
  } else {
    next.transform[channel] = value;
  }
  return next;
}

// Dolly around the pointer: the project-space point under the cursor stays fixed.
export function zoomCameraAtPoint(camera, localPoint, nextZoom, options = {}) {
  const frame = Number.isInteger(options.frame) && options.frame >= 0 ? options.frame : 0;
  const view = options.view || { zoom: 1, panX: 0, panY: 0 };
  const settings = options.settings || {};
  const width = settings.width, height = settings.height;
  if (
    !Number.isFinite(localPoint?.x) || !Number.isFinite(localPoint?.y)
    || !Number.isFinite(view.zoom) || view.zoom <= 0
    || !Number.isFinite(width) || !Number.isFinite(height)
  ) return camera;

  const zoom = clamp(nextZoom, 0.05, 32);
  const evaluated = evaluateCamera(camera, frame);
  const px = (localPoint.x - (view.panX || 0)) / view.zoom;
  const py = (localPoint.y - (view.panY || 0)) / view.zoom;
  const radians = evaluated.rotation * Math.PI / 180;
  const dx = px - width / 2 - evaluated.x;
  const dy = py - height / 2 - evaluated.y;
  const worldX = (dx * Math.cos(radians) + dy * Math.sin(radians)) / evaluated.zoom;
  const worldY = (-dx * Math.sin(radians) + dy * Math.cos(radians)) / evaluated.zoomY;
  const newDx = zoom * (worldX * Math.cos(radians) - worldY * Math.sin(radians));
  const newDy = zoom * (worldX * Math.sin(radians) + worldY * Math.cos(radians));
  const writeOptions = { frame, autokey: options.autokey === true, ease: options.ease || 'linear' };

  let next = writeCameraChannel(camera, 'x', clamp(px - width / 2 - newDx, -8192, 8192), writeOptions);
  next = writeCameraChannel(next, 'y', clamp(py - height / 2 - newDy, -8192, 8192), writeOptions);
  next = writeCameraChannel(next, 'scale_x', zoom, writeOptions);
  next = writeCameraChannel(next, 'scale_y', zoom, writeOptions);
  return next;
}
