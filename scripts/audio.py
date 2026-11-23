"""Original music + synthesised SFX. The voice is added sample-for-sample, untouched."""
import sys, subprocess, wave
import numpy as np

ROOT, VOICE = sys.argv[1:3]
SR, DUR = 48000, 26.0
N = int(SR * DUR)
rng = np.random.default_rng(62)
music, sfx = np.zeros((N, 2)), np.zeros((N, 2))
TAU = 2 * np.pi

def T(d): return np.arange(int(d * SR)) / SR
def band(x, lo, hi):
    f = np.fft.rfftfreq(len(x), 1 / SR); X = np.fft.rfft(x)
    g = 1 / np.sqrt(1 + (f / hi) ** 8)
    if lo > 0: g = g * (1 - 1 / np.sqrt(1 + (f / lo) ** 8))
    return np.fft.irfft(X * g, len(x))
def noise(d, lo=20, hi=12000):
    x = band(rng.standard_normal(int(d * SR)), lo, hi)
    return x / (np.abs(x).max() + 1e-9)
def fade(x, a=.01, b=.05):
    a = min(int(a * SR), len(x) // 2); b = min(int(b * SR), len(x) // 2); x = x.copy()
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x
def put(bus, x, t, g=1., pan=0.):
    i = max(0, int(t * SR)); x = x[:N - i]
    bus[i:i + len(x), 0] += x * g * min(1, 1 - pan); bus[i:i + len(x), 1] += x * g * min(1, 1 + pan)

def pluck(f, d=1.2):
    t = T(d); return fade(sum(a * np.sin(TAU * f * h * t) * np.exp(-t * (3 + h * 1.8)) for h, a in ((1, 1), (2, .4), (3, .18), (4, .08))), .004, .1)
def pad(notes, d):
    t = T(d); return fade(sum(np.sin(TAU * f * k * t + .6 * np.sin(TAU * .3 * t)) * a for f in notes for k, a in ((1, .3), (1.004, .25), (2, .06))), .3, .4)
def kick():
    t = T(.35); return np.sin(TAU * (45 * t + 70 * (1 - np.exp(-t * 22)) / 22)) * np.exp(-t * 11)
def hat(): return noise(.05, 6000, 14000) * np.exp(-T(.05) * 70)
def whoosh(d=.5):
    t = T(d); return noise(d, 300, 4500) * np.exp(-((t - d * .55) / (d * .22)) ** 2)
def thud(f=55, k=7):
    t = T(.8); return (np.sin(TAU * f * t * (1 + .3 * np.exp(-t * 9))) + .3 * noise(.8, 40, 500)) * np.exp(-t * k)
def ding(f):
    t = T(1.4); return fade((np.sin(TAU * f * t) + .3 * np.sin(TAU * f * 2.76 * t) * np.exp(-t * 5)) * np.exp(-t * 3.2), .003, .2)
def clink(f, d=.35):
    t = T(d); return fade(sum(np.sin(TAU * f * r * t) * np.exp(-t * k) for r, k in ((1, 18), (1.51, 24), (2.33, 35))) / 3, .001, .02)

# ---------- music: tense - warm - drop - tense - quiz
note = lambda m: 440 * 2 ** ((m - 69) / 12)
Am, F, C, G, Dm, E = (57, 60, 64), (53, 57, 60), (60, 64, 67), (55, 59, 62), (50, 53, 57), (52, 56, 59)
for a, b, ch in ((0, 1.7, Am), (1.7, 3.34, F), (3.34, 4.6, C), (4.6, 5.9, G), (6.79, 7.8, Dm), (7.8, 9.0, Am), (9.0, 10.1, F), (10.1, 11.95, Dm),
                 (11.95, 13.5, F), (13.5, 15.15, E), (15.15, 17.75, E), (17.75, 19.75, Am), (19.75, 21.75, F), (21.75, 23.75, Dm), (23.75, 26.0, E)):
    warm = 3.3 < a < 5.9
    put(music, pad([note(m) for m in ch], b - a + .3), a, .16)
    put(music, pad([note(ch[0] - 12)], b - a + .2), a, .25)
    seq = [ch[0], ch[1], ch[2], ch[1]]; step = .315 if warm else .21; i, t = 0, a
    while t < b - .05:
        put(music, pluck(note(seq[i % 4] + 12), .9), t, .20 if warm else .13, .35 if i % 2 else -.35); i += 1; t += step
for a, b in ((0, 3.3), (7.8, 15.1), (15.15, 17.6), (17.75, 25.6)):
    for i, t in enumerate(np.arange(a, b, .315)):
        if i % 2 == 0: put(music, kick(), t, .55)
        put(music, hat(), t + .157, .07, .2)

# ---------- SFX
E_ = []                                   # event log for the sync check
def ev(name, x, t, g, pan=0.): put(sfx, x, t, g, pan); E_.append((name, t))
# 1 arrival
t = T(3.5); phase = np.cumsum(700 + 260 * np.sin(TAU * .55 * t)) / SR
siren = band(np.tanh(2 * np.sin(TAU * phase)), 400, 1800) * np.clip(1 - t / 3.5, 0, 1) ** 1.5
ev('siren', fade(siren, .05, .3), 0, .17, -.4)
ev('wind', fade(noise(3.4, 150, 900), .1, .4), 0, .06)
ev('wheels', fade(noise(3.2, 90, 1400) * (.35 + .65 * (np.sin(TAU * 7 * T(3.2)) > .7)), .05, .2), .05, .12, .2)
for i, t0 in enumerate(np.arange(.10, 3.3, .275)):
    ev('step', noise(.12, 120, 2200) * np.exp(-T(.12) * 40), t0, .16, .3 if i % 2 else -.3)
ev('door', fade(noise(.8, 1500, 7000) * np.exp(-((T(.8) - .35) / .22) ** 2)), 1.6, .12)
for c in (1.767, 3.333, 5.733, 7.80, 10.10, 11.967, 15.167, 16.467, 17.767):
    ev('cut', whoosh(.42), c - .23, .20 if c in (3.333, 7.80, 11.967, 15.167, 17.767) else .10)
# 2 home
ev('room', fade(noise(4.4, 100, 600), .3, .3), 3.34, .025)
for t0 in np.sort(rng.uniform(3.4, 7.6, 26)):
    ev('fire', noise(.03, 1200, 6000) * np.exp(-T(.03) * 160), float(t0), .05)
ev('cup', clink(2300), 3.62, .22, -.3); ev('cup', clink(2650), 4.15, .14, .3)
ev('sip', fade(noise(.32, 900, 3500) * (.5 + .5 * np.sin(TAU * 23 * T(.32))), .06, .08), 4.65, .10)
t = T(.40); ev('fall', fade(np.sin(TAU * (1100 * t - 900 * t * t)), .05, .05), 6.36, .09)
ev('smash', noise(.45, 1500, 14000) * np.exp(-T(.45) * 16), 6.79, .60)
ev('smash', thud(90, 18), 6.79, .35)
for _ in range(22):
    d = float(rng.exponential(.11)); ev('shard', clink(float(rng.uniform(2000, 6000)), .22), 6.79 + min(d, .7), float(rng.uniform(.10, .3)), float(rng.uniform(-.6, .6)))
ev('gasp', fade(noise(.42, 700, 2600), .22, .12), 7.0, .16, .3)
# 3 symptoms
for t0 in np.arange(7.95, 15.1, .72):
    ev('monitor', fade(np.sin(TAU * 980 * T(.10)), .005, .02), float(t0), .075, .4)
t = T(.9); ev('droop', fade(np.sin(TAU * (420 * t - 150 * t * t)) * (1 - t / .9), .05, .1), 8.4, .10)
ev('cloth', fade(noise(.6, 600, 3500), .2, .3), 10.2, .07)
ev('hand', thud(70, 14), 11.28, .55)

def mumble(d, seed):
    """Wordless slurred babble: glottal pulses through moving formants."""
    r = np.random.default_rng(seed); n = int(d * SR); out = np.zeros(n); i = 0
    while i < n - 2000:
        L = int(r.uniform(.13, .27) * SR); L = min(L, n - i); t = np.arange(L) / SR
        f0 = r.uniform(88, 118) * (1 + .12 * np.sin(TAU * r.uniform(2, 4) * t)); ph = np.cumsum(f0) / SR
        a, b = r.uniform(260, 620), r.uniform(700, 1500); s = np.zeros(L)
        for h in range(1, 22):
            f = 103 * h
            g = np.exp(-((f - a) / 120) ** 2) + .45 * np.exp(-((f - b) / 170) ** 2) + .04
            s += g * np.sin(TAU * h * ph)
        out[i:i + L] += s * np.sin(np.pi * np.arange(L) / L) ** .7
        i += int(L * r.uniform(.75, 1.05))
    out = band(out, 120, 1700)
    return fade(out / np.abs(out).max(), .03, .06)
ev('mumble', mumble(.42, 1), 11.70, .42)
ev('mumble', mumble(2.7, 2), 12.12, .10)
ev('mumble', mumble(.46, 3), 14.72, .50)
# 4 question + quiz
t = T(2.5); ev('riser', fade(noise(2.5, 500, 5000) * (t / 2.5) ** 3, .1, .02), 15.25, .17)
ev('impact', thud(48, 4.5), 17.767, .8)
for i, t0 in enumerate((18.0, 18.3, 18.6, 18.9)):
    ev('option', ding(note(76 + [0, 3, 7, 10][i])), t0, .24, [-.3, -.1, .1, .3][i])
ev('cta', ding(note(88)), 19.35, .16)
for i, t0 in enumerate(np.arange(19.75, 25.6, .5)):
    ev('tick', fade(np.sin(TAU * (1500 if i % 2 else 1900) * T(.05)) * np.exp(-T(.05) * 80), .001, .005), float(t0), .20 if t0 < 24 else .30)
ev('end', ding(note(81)), 25.2, .22)

# ---------- mix
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', VOICE, '-vn', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
raw = np.frombuffer(pcm, np.float32).reshape(-1, 2).astype(float)[:N]
voice = np.zeros((N, 2)); voice[:len(raw)] = raw
level = np.sqrt(np.convolve(voice.mean(1) ** 2, np.ones(4800) / 4800, 'same'))
talk = np.convolve((level > .035).astype(float), np.ones(9600) / 9600, 'same').clip(0, 1)
music /= np.abs(music).max()
music *= (.22 * (1 - talk) + .075 * talk)[:, None]
music[:int(.2 * SR)] *= np.linspace(0, 1, int(.2 * SR))[:, None]
music[-int(.7 * SR):] *= np.linspace(1, 0, int(.7 * SR))[:, None]
sfx *= (.80 * (1 - talk) + .42 * talk)[:, None]
bed = music + sfx
hot = np.abs(voice + bed).max(1)
over = np.where(hot > .80, np.maximum(0, (.80 - np.abs(voice).max(1)).clip(0) / (np.abs(bed).max(1) + 1e-9)), 1.).clip(0, 1)
over = np.lib.stride_tricks.sliding_window_view(np.pad(over, 120, mode='edge'), 241).min(1)
bed *= np.convolve(over, np.ones(120) / 120, 'same')[:, None]         # only the bed is ever turned down
mix = (voice + bed).clip(-.99, .99)
def save(name, x):
    w = wave.open(f'{ROOT}/{name}', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x.clip(-1, 1) * 32767).astype('<i2').tobytes()); w.close()
save('mix.wav', mix); save('bed.wav', bed); save('music.wav', music); save('sfx.wav', sfx); save('voice.wav', voice)
m = talk > .9
db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
print('voice over bed during speech: %.1f dB' % (db(voice[m]) - db(bed[m])))
print('voice over music during speech: %.1f dB' % (db(voice[m]) - db(music[m])))
print('peak %.2f dB' % (20 * np.log10(np.abs(mix).max())), '| sfx events', len(E_), '| types', len({n for n, _ in E_}))
