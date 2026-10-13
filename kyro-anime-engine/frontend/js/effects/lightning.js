export function drawLightning(ctx, effect, width, height, random) {
  const intensity = effect.intensity ?? 0.5;
  const color = /^#[0-9a-f]{6}$/i.test(effect.color || '') ? effect.color : '#ffffff';
  const x = width * (0.2 + random() * 0.6);
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2 + intensity * 5;
  ctx.globalAlpha = 0.55 + intensity * 0.45;
  ctx.shadowColor = color;
  ctx.shadowBlur = 6 + intensity * 24;
  ctx.beginPath();
  ctx.moveTo(x, 0);
  for (let step = 1; step <= 12; step++) {
    ctx.lineTo(x + (random() - 0.5) * width * 0.09, height * step / 12);
  }
  ctx.stroke();
  ctx.restore();
}
