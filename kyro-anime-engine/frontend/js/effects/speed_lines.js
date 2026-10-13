export function drawSpeedLines(ctx, effect, width, height, frame, random) {
  const intensity = effect.intensity ?? 0.5;
  const color = /^#[0-9a-f]{6}$/i.test(effect.color || '') ? effect.color : '#ffffff';
  const speed = effect.speed ?? 1;
  const count = effect.count ?? 36;
  const cx = width / 2, cy = height / 2;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.globalAlpha = Math.min(0.85, 0.15 + intensity * 0.65);
  ctx.lineWidth = 1 + intensity * 2;
  for (let index = 0; index < count; index++) {
    const angle = random() * Math.PI * 2 + frame * speed * 0.025;
    const radius = Math.max(width, height)
      * (0.34 + random() * 0.48)
      * (0.78 + Math.sin(frame * speed * 0.12 + index) * 0.22);
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;
    const length = 12 + random() * (20 + intensity * 100);
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - Math.cos(angle) * length, y - Math.sin(angle) * length);
    ctx.stroke();
  }
  ctx.restore();
}
