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

// Floating embers: deterministic per t, drawn on a full-size canvas.
function embers(canvas, t, n = 70, alpha = 1) {
  const g = canvas.getContext('2d'); const W = canvas.width, H = canvas.height;
  g.clearRect(0, 0, W, H); g.globalCompositeOperation = 'lighter';
  let s = 12345; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < n; i++) {
    const x0 = r() * W, y0 = r() * H, sp = 30 + r() * 90, sz = 1 + r() * 3.2, ph = r() * 6.28, fl = 2 + r() * 4;
    const y = ((y0 - t * sp) % H + H) % H, x = x0 + Math.sin(t * 0.8 + ph) * 30;
    const a = alpha * (0.35 + 0.65 * Math.abs(Math.sin(t * fl + ph))) * Math.min(1, y / (H * 0.25));
    const gr = g.createRadialGradient(x, y, 0, x, y, sz * 5);
    gr.addColorStop(0, `rgba(255,190,110,${a})`); gr.addColorStop(0.35, `rgba(255,122,26,${a * 0.5})`); gr.addColorStop(1, 'rgba(255,80,20,0)');
    g.fillStyle = gr; g.beginPath(); g.arc(x, y, sz * 5, 0, 6.29); g.fill();
  }
  g.globalCompositeOperation = 'source-over';
}
// Diagonal light sweep: call with local time k in [0,1] to drive an element with class "sweep".
function sweep(el, k) {
  el.style.opacity = k > 0 && k < 1 ? 1 : 0;
  el.style.transform = `translateX(${lerp(-1400, 2600, easeIO(k))}px) skewX(-20deg)`;
}
// Slow cinematic ease (long tails) and a constant push-in used on every shot.
const easeS = x => { x = clamp(x); return x < .5 ? 16 * x ** 5 : 1 - Math.pow(-2 * x + 2, 5) / 2; };
const push = (el, t, dur, from = 1.0, to = 1.05) => { el.style.transform = `scale(${lerp(from, to, clamp(t / dur))})`; };
