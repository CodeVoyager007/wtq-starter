"""Build demo.mp4 from timeline.json: renders slides, frames raw recordings, scores music, enforces limits.

Usage (from video/):  python3 tools/assemble.py [timeline.json]
Needs: a static server on :8765 serving video/ (python3 -m http.server 8765), node + playwright, ffmpeg.
"""
import hashlib, json, os, subprocess, sys, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
B = 'build'; SEG = f'{B}/seg'; os.makedirs(SEG, exist_ok=True)
URL = 'http://localhost:8765'
FPS = 30; MAX_SEC = 180
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
tl = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'timeline.json'))

def sh(*cmd): subprocess.run(cmd, check=True)
def ff(*a): sh('ffmpeg', '-y', '-loglevel', 'error', *a)
def dur(f): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]))
def data_hash():
    h = hashlib.md5()
    for d in ('slides', 'intro', 'assets/panels'):
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            if os.path.isfile(p): h.update(open(p, 'rb').read())
    for f in sorted(os.listdir('slides/data')): h.update(open(f'slides/data/{f}', 'rb').read())
    return h.hexdigest()[:10]
H = data_hash()

def render_page(path, key):
    out = f'{SEG}/{key}_{H}.mp4'
    if os.path.exists(out): return out
    frames = f'{B}/frames_{key}'; sh('rm', '-rf', frames)
    sh('node', 'tools/render_frames.mjs', f'{URL}/{path}', frames, str(FPS))
    ff('-framerate', str(FPS), '-i', f'{frames}/f%05d.jpg', '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p', out)
    return out

def clip(s, idx):
    src = s['file']; key = f'clip{idx}'
    q = urllib.parse.urlencode({'num': s.get('num', ''), 'cap': s.get('cap', '')})
    fr = f'{B}/frame_{idx}_{H}'
    if not os.path.exists(f'{fr}/f00000.png'):
        sh('node', 'tools/render_frames.mjs', f'{URL}/slides/frame.html?{q}', fr, str(FPS), 'png')
    if not os.path.exists(src):  # placeholder so the cut can be previewed
        src = f'{SEG}/placeholder_{idx}.mp4'
        txt = f"SCREEN RECORDING GOES HERE  ·  {s['file']}"
        ff('-f', 'lavfi', '-i', f'color=c=0x0f0d0b:s=1536x864:d={s.get("placeholder_sec", 6)}:r={FPS}',
           '-vf', f"drawtext=fontfile={FONT}:text='{txt}':fontcolor=0x8a7f74:fontsize=44:x=(w-tw)/2:y=(h-th)/2",
           '-pix_fmt', 'yuv420p', src)
    spd = float(s.get('speed', 1)); trim = []
    if 'from' in s: trim += ['-ss', str(s['from'])]
    if 'to' in s: trim += ['-to', str(s['to'])]
    out = f'{SEG}/{key}.mp4'
    ff(*trim, '-i', src, '-loop', '1', '-i', f'{fr}/f00000.png', '-filter_complex',
       f'[0:v]setpts=PTS/{spd},fps={FPS},scale=1536:864:force_original_aspect_ratio=decrease,pad=1536:864:(ow-iw)/2:(oh-ih)/2:color=0x0f0d0b[v];'
       f'color=c=black:s=1920x1080:r={FPS}[bg];[bg][v]overlay=192:100:shortest=1[b];[b][1:v]overlay=0:0:shortest=1,format=yuv420p',
       '-an', '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', out)
    return out

parts, starts, t = [], [], 0.0
for i, s in enumerate(tl['segments']):
    ty = s['type']
    if ty == 'intro': f = render_page('intro/intro.html', 'intro')
    elif ty == 'chapter': f = render_page(f"slides/chapter.html?i={s['i']}", f"chapter{s['i']}")
    elif ty == 'slide': f = render_page(f"slides/{s['page']}", s['page'].split('.')[0])
    elif ty == 'outro': f = render_page('slides/outro.html', 'outro')
    elif ty == 'clip': f = clip(s, i)
    d = dur(f); parts.append(f); starts.append((ty, t, d)); t += d
    print(f'{t - d:7.2f}s  +{d:5.2f}s  {ty:8} {s.get("file", s.get("page", ""))}')
total = t
print(f'TOTAL {total:.1f}s')
if total > MAX_SEC: sys.exit(f'ERROR: {total:.1f}s is over the 3 minute limit. Trim clips (from/to) or raise speed.')

with open(f'{B}/concat.txt', 'w') as fh: fh.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
ff('-f', 'concat', '-safe', '0', '-i', f'{B}/concat.txt', '-c', 'copy', f'{B}/video_only.mp4')

intro_end = next((st + d for ty, st, d in starts if ty == 'intro'), 0)
cues = {'duration': total, 'drop': intro_end,
        'hits': [st for ty, st, d in starts if ty == 'chapter' and st > intro_end + 0.1],
        'outro': next((st for ty, st, d in starts if ty == 'outro'), total - 4)}
json.dump(cues, open(f'{B}/cues.json', 'w'))
sh('python3', 'tools/music.py', f'{B}/cues.json', f'{B}/music.wav')
sh('python3', 'tools/intro_audio.py', f'{B}/intro_sfx.wav')
ff('-i', f'{B}/music.wav', '-i', f'{B}/intro_sfx.wav', '-filter_complex',
   '[0:a]volume=0.7[m];[1:a]volume=0.9,apad[s];[m][s]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.8:level=0[a]',
   '-map', '[a]', f'{B}/mix.wav')

# Two-pass encode to a size target so the ZIP stays under 15 MB
target_mb = float(tl.get('target_mb', 8)); akbps = 96
vkbps = max(300, int(target_mb * 8000 * 0.95 / total - akbps))
os.makedirs('out', exist_ok=True); out = 'out/demo.mp4'
enc = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{vkbps}k', '-pix_fmt', 'yuv420p', '-passlogfile', f'{B}/x264']
ins = ['-i', f'{B}/video_only.mp4', '-i', f'{B}/mix.wav', '-map', '0:v', '-map', '1:a']
ff(*ins, *enc, '-pass', '1', '-an', '-f', 'mp4', '/dev/null')
ff(*ins, *enc, '-pass', '2', '-c:a', 'aac', '-b:a', f'{akbps}k', '-shortest', '-movflags', '+faststart', out)
size = os.path.getsize(out) / 1e6
print(f'DONE {out}: {dur(out):.1f}s, {size:.2f} MB (video {vkbps} kbps)')
