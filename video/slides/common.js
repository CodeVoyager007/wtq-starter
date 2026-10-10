// Shared timeline helpers. Each slide defines window.DUR and window.render(t).
const $ = id => document.getElementById(id);
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = x => 1 - Math.pow(1 - clamp(x), 3);
const easeIn = x => Math.pow(clamp(x), 3);
const easeIO = x => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const lerp = (a, b, x) => a + (b - a) * x;
const params = new URLSearchParams(location.search);
function grain(canvas, t) {
  const g = canvas.getContext('2d'); const img = g.createImageData(canvas.width, canvas.height);
  let s = Math.floor(t * 15) * 9973 + 1;
  for (let i = 0; i < img.data.length; i += 4) { s = (s * 48271) % 2147483647; const v = s & 255;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
  g.putImageData(img, 0, 0);
}
function loadImages(srcs) {
  return Promise.all(srcs.map(src => new Promise(r => { const i = new Image(); i.onload = i.onerror = r; i.src = src; })))
    .then(() => document.fonts.ready);
}
async function loadJSON(path) { return (await fetch(path)).json(); }
