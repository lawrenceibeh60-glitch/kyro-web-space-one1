const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

function hsvToHex(hue, saturation, value) {
  const h = ((hue % 360) + 360) % 360;
  const c = value * saturation;
  const x = c * (1 - Math.abs((h / 60) % 2 - 1));
  const m = value - c;
  const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x]
    : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
  return '#' + [r, g, b].map(channel => Math.round((channel + m) * 255).toString(16).padStart(2, '0')).join('');
}

function hueToRgb(hue) {
  const h = ((hue % 360) + 360) % 360;
  const c = 1, x = 1 - Math.abs((h / 60) % 2 - 1);
  return h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x]
    : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
}

function hexToHsv(hex) {
  const value = hex.replace('#', '');
  const rgb = value.length === 3 ? [...value].map(part => parseInt(part + part, 16) / 255)
    : [0, 2, 4].map(index => parseInt(value.slice(index, index + 2), 16) / 255);
  const [r, g, b] = rgb, max = Math.max(...rgb), min = Math.min(...rgb), delta = max - min;
  const hue = delta === 0 ? 0 : max === r ? 60 * (((g - b) / delta) % 6)
    : max === g ? 60 * ((b - r) / delta + 2) : 60 * ((r - g) / delta + 4);
  return { hue: (hue + 360) % 360, saturation: max === 0 ? 0 : delta / max, value: max };
}

export function initColorPicker({ canvas, valueInput, colorInput, valueText, initialColor, onChange }) {
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const size = canvas.width, center = size / 2, radius = center - 2;
  let hue = 0, saturation = 1, value = 1, dragging = false;

  function paintWheel() {
    const image = ctx.createImageData(size, size);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const dx = x + 0.5 - center, dy = center - (y + 0.5);
      const distance = Math.hypot(dx, dy);
      if (distance > radius) continue;
      const pixel = (y * size + x) * 4;
      const hue = Math.atan2(dy, dx) * 180 / Math.PI;
      const saturation = clamp(distance / radius, 0, 1);
      const rgb = hueToRgb(hue);
      image.data[pixel] = Math.round(value * (1 - saturation + saturation * rgb[0]) * 255);
      image.data[pixel + 1] = Math.round(value * (1 - saturation + saturation * rgb[1]) * 255);
      image.data[pixel + 2] = Math.round(value * (1 - saturation + saturation * rgb[2]) * 255);
      image.data[pixel + 3] = 255;
    }
    ctx.putImageData(image, 0, 0);
    const angle = hue * Math.PI / 180;
    const point = radius * saturation;
    ctx.beginPath(); ctx.arc(center + Math.cos(angle) * point, center - Math.sin(angle) * point, 5, 0, Math.PI * 2);
    ctx.strokeStyle = '#171717'; ctx.lineWidth = 3; ctx.stroke();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.stroke();
  }

  function emitColor() {
    const hex = hsvToHex(hue, saturation, value);
    colorInput.value = hex;
    valueText.textContent = `${Math.round(value * 100)}%`;
    onChange(hex);
  }

  function chooseFromPointer(event) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = size / rect.width, scaleY = size / rect.height;
    const dx = (event.clientX - rect.left) * scaleX - center;
    const dy = center - (event.clientY - rect.top) * scaleY;
    hue = (Math.atan2(dy, dx) * 180 / Math.PI + 360) % 360;
    saturation = clamp(Math.hypot(dx, dy) / radius, 0, 1);
    paintWheel();
    emitColor();
  }

  const setColor = color => {
    if (!/^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i.test(color)) return;
    ({ hue, saturation, value } = hexToHsv(color));
    valueInput.value = Math.round(value * 100);
    paintWheel();
    colorInput.value = color.length === 4 ? '#' + [...color.slice(1)].map(c => c + c).join('') : color;
    valueText.textContent = `${Math.round(value * 100)}%`;
  };

  canvas.addEventListener('pointerdown', event => {
    dragging = true;
    canvas.setPointerCapture(event.pointerId);
    chooseFromPointer(event);
  });
  canvas.addEventListener('pointermove', event => { if (dragging) chooseFromPointer(event); });
  const stop = () => { dragging = false; };
  canvas.addEventListener('pointerup', stop);
  canvas.addEventListener('pointercancel', stop);
  valueInput.addEventListener('input', () => {
    value = Number(valueInput.value) / 100;
    paintWheel(); emitColor();
  });
  colorInput.addEventListener('input', () => { setColor(colorInput.value); onChange(colorInput.value); });
  setColor(initialColor);
  return { setColor };
}
