import { evaluateCamera } from '../animation/camera_evaluator.js';

export function applyCameraShake(camera, effects, frame) {
  const shake = effects.filter(effect => effect.type === 'camera_shake');
  if (!shake.length) return camera;
  const evaluated = evaluateCamera(camera, frame);
  const x = shake.reduce((sum, effect) =>
    sum + Math.sin(frame * (effect.speed ?? 1) * 0.7) * (effect.intensity ?? 0.5) * 18, 0);
  const y = shake.reduce((sum, effect) =>
    sum + Math.cos(frame * (effect.speed ?? 1) * 0.93) * (effect.intensity ?? 0.5) * 14, 0);
  return {
    transform: {
      x: evaluated.x + x, y: evaluated.y + y,
      rotation: evaluated.rotation, scale_x: evaluated.zoom,
    },
  };
}
