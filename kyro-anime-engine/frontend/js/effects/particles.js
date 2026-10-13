export function drawParticles(ctx, effect, width, height, frame, random) {
  const intensity = effect.intensity ?? 0.5;
  const color = /^#[0-9a-f]{6}$/i.test(effect.color || '') ? effect.color : '#ffffff';
  const speed = effect.speed ?? 1;
  const count = effect.count ?? 36;
  ctx.save();
  ctx.fillStyle = color;
  ctx.globalAlpha = Math.min(1, 0.25 + intensity * 0.75);
  for (let index = 0; index < count; index++) {
    const x0 = random() * width;
    const y0 = random() * height;
    const x = (x0 + Math.sin((frame + index) * 0.08) * 14 + width) % width;
    const y = (y0 + frame * speed * 2.2 + height) % height;
    const radius = 1 + random() * (1 + intensity * 3);
    ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}
