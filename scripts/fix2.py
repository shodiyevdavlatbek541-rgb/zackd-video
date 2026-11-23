import sys
R=sys.argv[1]
def patch(fn, pairs):
    p=f'{R}/scripts/{fn}'; s=open(p,encoding='utf8').read()
    for a,b in pairs:
        if s.count(a)!=1: print('MISS',fn,s.count(a),a[:70]); continue
        s=s.replace(a,b)
    open(p,'w',encoding='utf8').write(s)
patch('cast.py',[
 ("hair='short01', hc=(.025, .02, .018)","hair='short04', hc=(.025, .02, .018)"),
 ("hair='short04', hc=(.03, .022, .018)","hair='short02', hc=(.03, .022, .018)"),
 ("    mid = (cl + cr) / 2; half = abs(cl.x - cr.x) / 2\n",
"""    mid = (cl + cr) / 2; half = abs(cl.x - cr.x) / 2
    # stronger one-sided sag than the stock face units can give
    pk = body.shape_key_add(name='palsyRight', from_mix=False); pk.value = 0
    for i in range(13380):
        p = mix[i]
        if p.y > mid.y + .075: continue
        dx, dz = p.x - cr.x, p.z - cr.z
        c = math.exp(-(dx / .021) ** 2 - (dz / .019) ** 2)
        j = math.exp(-((dx + .014) / .022) ** 2 - ((dz - .014) / .026) ** 2)
        pk.data[i].co = base[i].co + Vector((.004 * c, .001 * c, -.0125 * c - .004 * j))
    kb = body.data.shape_keys.key_blocks; base = kb['Basis'].data; skip.add('palsyRight')
"""),
])
patch('lib.py',[("eyeBlinkRight=.22, browInnerUp=1, eyeWideLeft=.45, jawLeft=.15)","eyeBlinkRight=.22, browInnerUp=1, eyeWideLeft=.45, jawLeft=.15, palsyRight=1)"),
 ("mouthFrownRight=.7, mouthLeft=.35, jawOpen=.12)","mouthFrownRight=.7, mouthLeft=.35, jawOpen=.12, palsyRight=.7)")])
patch('sets.py',[
 ("(0, 2.54, 3.95), (3.1, .14, .66)","(0, 2.54, 4.22), (3.1, .14, .66)"),
 ("light('AREA', (0, 2.0, 4.55), 25, (1, .75, .45), (0, 2.5, 3.95), 2)","light('AREA', (0, 1.7, 4.9), 28, (1, .75, .45), (0, 2.5, 4.2), 2)"),
 ("snowfall((-6, -8, .3), (6, .9, 5), 420","snowfall((-6, -3.3, .3), (6, .9, 5), 380"),
 ("mat((.6, .75, .9), .8, .15) if j % 2","mat((.6, .75, .9), .8, .55) if j % 2"),
 ("engraved('Doxtir Davlat', (0, 1.44, 2.12), (1.5, .09, .36), .23","engraved('Doxtir Davlat', (0, 1.44, 1.92), (1.3, .09, .26), .185"),
 ("box((0, 1.42, 1.80), (1.5, .02, .20)","box((0, 1.42, 1.67), (1.3, .02, .17)"),
 ("text('REANIMATSIYA', (0, 1.40, 1.80), .15","text('REANIMATSIYA', (0, 1.40, 1.67), .13"),
])
patch('shots.py',[
 ("camera([(T0, (4.1, -6.6, 2.7), (-.75, -.1, 1.75), 33, 4), (T1, (3.2, -5.2, 2.3), (-.35, .4, 1.65), 35, 4)]",
  "camera([(T0, (4.3, -7.3, 2.8), (-2.3, -2.2, 1.45), 32, 4), (1.1, (3.8, -6.2, 2.5), (-.45, .1, 1.8), 32, 4), (T1, (3.4, -5.6, 2.3), (-.15, .5, 1.85), 33, 4)]"),
 ("p1 = V((p0.x - .10, p0.y - .12, .025))","p1 = V((-.54, .80, .03))"),
 ("camera([(5.72, (-1.0, -.75, 1.40), (-.2, .62, 1.03), 48, 3.2), (6.3, (-1.02, -.68, 1.30), (p0.x, p0.y, p0.z + .04), 52, 3.2),\n                (HIT, (-1.0, -.62, .72), (p1.x, p1.y, .08), 46, 4), (T1, (-.96, -.58, .62), (p1.x, p1.y, .05), 48, 4)]",
  "camera([(5.72, (-1.28, .92, 1.38), (-.20, .60, 1.02), 34, 3.5), (6.3, (-1.27, .93, 1.26), (p0.x, p0.y, p0.z), 38, 3.5),\n                (HIT, (-1.22, 1.05, .66), (p1.x, p1.y, .12), 38, 5), (T1, (-1.18, 1.05, .58), (p1.x, p1.y, .07), 41, 5)]"),
 ("camera([(T0, (.42, -.62, 1.38), (-.16, .62, 1.14), 40, 3.5), (T1, (.30, -.40, 1.33), (-.16, .62, 1.14), 43, 3.5)]",
  "camera([(T0, (.12, -1.45, 1.55), (0, .70, 1.17), 31, 4.5), (T1, (.06, -1.12, 1.48), (0, .70, 1.17), 33, 4.5)]"),
 ("(0, .10, 1.22), 42, 4), (T1, (0, -1.62, 1.86), (0, .10, 1.26), 45, 4)","(0, .12, 1.28), 38, 4), (T1, (0, -1.62, 1.86), (0, .12, 1.31), 41, 4)"),
 ("('medic1', -1.25, 1.05, 25, 'focus'), ('medic2', 1.3, .85, -25, 'focus'),","('medic1', -1.10, 1.15, 25, 'focus'), ('medic2', 1.12, .95, -25, 'focus'),"),
 ("('wife', -.45, 1.65, 8, 'worry'), ('son', .5, 1.7, -5, 'worry')","('wife', -.72, 1.62, 8, 'worry'), ('son', .72, 1.7, -5, 'worry')"),
 ("hd = (2 + 3 * ss(16.6, 17.2, t)","hd = (-3 + 2 * ss(16.6, 17.2, t)"),
 ("camera([(T0, (.2, -3.1, 1.75), (0, .9, 1.6), 38, 5), (18.6, (.1, -4.2, 1.85), (0, .9, 1.85), 36, 5), (T1, (-.1, -4.7, 1.95), (0, .9, 1.9), 36, 5)]",
  "camera([(T0, (.2, -3.2, 1.75), (0, .9, 1.6), 36, 5), (18.6, (.1, -4.5, 1.9), (0, .9, 1.95), 32, 5), (T1, (-.1, -4.9, 2.0), (0, .9, 2.0), 32, 5)]"),
])
