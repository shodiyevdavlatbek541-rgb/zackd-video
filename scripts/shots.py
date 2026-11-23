"""One shot = one build. usage: blender -b cast.blend -P shots.py -- ROOT SHOT MODE [times]
MODE: still (half-res PNG at given seconds) | anim (JPEG frames with global numbering)"""
import bpy, sys, math, time
A = sys.argv[sys.argv.index('--') + 1:]
ROOT, SHOT, MODE = A[:3]
sys.path.insert(0, ROOT + '/scripts')
from lib import *
import sets

S = bpy.context.scene
# cut points come from the measured pauses of the voice-over
SHOTS = {'1a': (0, 53), '1b': (53, 100), '2a': (100, 172), '2b': (172, 213), '2c': (213, 234), '3a': (234, 303),
         '3b': (303, 359), '4': (359, 455), '5a': (455, 494), '5b': (494, 533), '6': (533, 780)}
F0, F1 = SHOTS[SHOT]; T0, T1 = F0 / FPS, F1 / FPS
UP = V((0, 0, 1)); DOWN = -UP; X = V((1, 0, 0)); Y = V((0, 1, 0))
CAST = []
def actor(name, detail=False):
    a = Actor(name, detail); CAST.append(a); return a
def fwd(yaw): return RZ(yaw) @ V((0, -1, 0))
def left(yaw): return RZ(yaw) @ V((1, 0, 0))
def w(at, yaw, p): return V(at) + RZ(yaw) @ V(p)

def stand(a, at, yaw, t, head=(0, 0, 0), lean=0, hands=None, phase=0):
    k = a.k; br = math.sin(t * 2.2 + phase)
    d = dict(at=at, yaw=yaw, hip=w(at, yaw, (.012 * math.sin(t * .9 + phase), -.004, .905 * k)), bend=(lean + br * .7, 0, 0),
             head=(head[0] + br * .6, head[1], head[2] + 1.5 * math.sin(t * 1.1 + phase)),
             foot_l=(w(at, yaw, (.13 * k, 0, .07 * k)), fwd(yaw)), foot_r=(w(at, yaw, (-.13 * k, .02, .07 * k)), fwd(yaw)), sole=Quaternion())
    d.update(hands or {})
    return d

def walk(a, start, speed, yaw, t, hands=None, head=(0, 0, 0), phase=0, lean=7):
    k = a.k; dist = speed * (t - T0); at = V(start) + fwd(yaw) * dist
    C = 1.15 * k; p = dist / C + phase
    d = dict(at=at, yaw=yaw, hip=w(at, yaw, (0, 0, (.878 + .016 * math.cos(p * 4 * math.pi)) * k)),
             bend=(lean, 0, 5 * math.sin(p * math.tau)), head=(head[0] - lean * .5, head[1], head[2]), sole=Quaternion())
    for sd, off, x in (('l', 0, .115), ('r', .5, -.115)):
        q = (p + off) % 1
        if q < .5: rel = C / 4 - C * q; z = 0
        else:
            s = (q - .5) * 2; rel = -C / 4 + C / 2 * ss(0, 1, s); z = .10 * math.sin(math.pi * s)
        d['foot_' + sd] = (w(at, yaw, (x * k, -rel, (.07 + z) * k)), fwd(yaw))
        swing = -math.cos((p + off) * math.tau) * .16
        d['hand_' + sd] = (w(at, yaw, (2.3 * x * k, -.06 + swing, .86 * k)), -fwd(yaw))
    d.update(hands or {})
    return d

def recline(a, at, yaw, t, head=(8, 0, 0), over=None):
    """Half-sitting on the gurney; `at` is the gurney origin."""
    br = math.sin(t * 2.4)
    d = dict(at=at, yaw=yaw, hip=w(at, yaw, (0, 0, .875)), body=RX(-76), bend=(34 + br, 0, 0), head=head, sole=RX(-70),
             foot_l=(w(at, yaw, (.11, -.86, .84)), UP), foot_r=(w(at, yaw, (-.11, -.86, .84)), UP),
             hand_l=(w(at, yaw, (.27, -.22, 1.02)), left(yaw)), hand_r=(w(at, yaw, (-.27, -.22, 1.01)), -left(yaw)),
             palm_l=(fwd(yaw), DOWN), palm_r=(fwd(yaw), DOWN), curl={'l': .3, 'r': .35})
    d.update(over or {})
    return d

def sit(a, seat, yaw, t, head=(0, 0, 0), lean=6, hands=None, phase=0):
    k = a.k; br = math.sin(t * 2.1 + phase)
    d = dict(at=seat, yaw=yaw, hip=w(seat, yaw, (0, 0, .535)), body=RX(0), bend=(lean + br, 0, 0),
             head=(head[0], head[1], head[2] + 2 * math.sin(t * 1.3 + phase)), sole=Quaternion(),
             foot_l=(w(seat, yaw, (.13, -.43 * k, .075)), fwd(yaw) + UP * .6), foot_r=(w(seat, yaw, (-.13, -.43 * k, .075)), fwd(yaw) + UP * .6),
             hand_l=(w(seat, yaw, (.17, -.36, .80)), left(yaw) + DOWN), hand_r=(w(seat, yaw, (-.17, -.36, .80)), -left(yaw) + DOWN),
             palm_l=(fwd(yaw), DOWN), palm_r=(fwd(yaw), DOWN))
    d.update(hands or {})
    return d

def with_mask(p):
    p.stick(sets.mask(p), (0, -.105, .026))

def fr_(res, t):
    f = min(max(res), max(min(res), int(round(t * FPS))))
    if f not in res: f = min(res, key=lambda x: abs(x - f))
    return res[f]
def hp(res, t):
    root, Q, H = fr_(res, t); return root @ (H['head'] + Q['head'] @ V((0, -.07, .045)))
def hf(res, t):
    root, Q, H = fr_(res, t); return (root.to_3x3() @ (Q['head'] @ V((0, -1, 0)))).normalized()
def bp(res, t, bone):
    root, Q, H = fr_(res, t); return root @ H[bone]
def face_keys(res, t0, t1, dist, side=0, up=0, lens=22, fstop=2.8, roll=0, far=1.9, step=.1, look=(0, 0, 0)):
    """Camera in front of a moving face; first key far away so the shot starts with a crash push."""
    keys = []; n = max(2, int((t1 - t0) / step) + 1)
    for j in range(n + 1):
        t = t0 + (t1 - t0) * j / n if j else t0
        if j == 1: t = min(t1, t0 + .16)
        h = hp(res, t); fc = hf(res, t); sd = fc.cross(UP).normalized()
        d = dist * (far if j == 0 else 1 - .08 * j / n)
        keys.append((t, h + fc * d + sd * side + UP * up, h + V(look), lens - (3 if j == 0 else 0), fstop, roll))
    return keys

# ---------- 1. the ambulance crew brings the patient in
def arrival():
    sets.hospital(T0, T1)
    spd = 1.05; y0 = -2.75 if SHOT == '1a' else -1.75
    gy = lambda t: y0 + spd * (t - T0)
    root = empty(); g = sets.gurney(root); g.rotation_euler.z = math.pi      # feet first into the door
    for f in range(F0, F1):
        root.location = (0, gy(f / FPS), 0); root.keyframe_insert('location', frame=f)
    P = actor('patient', SHOT == '1b'); with_mask(P)
    resP = P.perform(lambda t: recline(P, (0, gy(t), 0), 180, t, (6, 6, 10 * math.sin(t * 2))), F0, F1)
    P.face([(T0, emo('dazed', eyeBlinkLeft=.45, eyeBlinkRight=.6))], T0, T1)
    for nm, side, dy, ph in (('medic1', 1, .30, 0), ('medic2', -1, -.45, .5)):
        a = actor(nm)
        def fn(t, a=a, side=side, dy=dy, ph=ph):
            y = gy(t); x = side * .70
            near = (side * .36, y + dy + .28, .89); far = (side * .62, y + dy + .05, .84)
            inner, outer = ('l', 'r') if side > 0 else ('r', 'l')
            h = {'hand_' + inner: (near, (side, -.5, -.5)), 'palm_' + inner: (Y, DOWN),
                 'curl': {inner: .8, outer: .3}}
            return walk(a, (x, y0 + dy, 0), spd, 180, t, h, (2, 0, side * (20 if a.name == 'medic1' else 8)), ph, 9)
        a.perform(fn, F0, F1); a.face([(T0, emo('focus', jawOpen=.15))], T0, T1, talk=(T0, T1) if nm == 'medic1' else None)
    for nm, x, dy, ph in (('wife', .42, -1.75, .2), ('son', -.4, -1.95, .7)):
        a = actor(nm)
        a.perform(lambda t, a=a, x=x, dy=dy, ph=ph: walk(a, (x, y0 + dy, 0), spd, 180, t, None, (4, 0, 0), ph), F0, F1)
        a.face([(T0, emo('worry'))], T0, T1)
    DR = {}
    for nm, x, ph in (('doc', 1.12, 0), ('doc2', -1.12, 1.5)):
        a = actor(nm); sets.stethoscope(a); yaw = math.degrees(math.atan2(-x, 1.6))
        def fn(t, a=a, x=x, yaw=yaw, ph=ph):
            k = ss(T0 + .1, T0 + .8, t); at = V((x, 1.75 - .25 * k, 0)); s = 1 if x > 0 else -1
            sd = 'r' if x > 0 else 'l'
            h = {'hand_' + sd: (w(at, yaw, ((-.24 if sd == 'r' else .24), lerp(-.1, -.42, k), lerp(.85, 1.18, k) * a.k)), DOWN + (-left(yaw) if sd == 'r' else left(yaw))),
                 'palm_' + sd: (fwd(yaw), UP)}
            return stand(a, at, yaw, t, (12, 0, 0), 5, h, ph)
        DR[nm] = a.perform(fn, F0, F1); a.face([(T0, emo('focus', browOuterUpLeft=.3))], T0, T1, talk=(T0, T1) if nm == 'doc' else None)
    if SHOT == '1a':
        c1 = 29     # "62 yoshli" | "erkakni"
        camera(crash(T0, c1 / FPS, (4.8, -8.2, .45), (3.7, -6.7, .40), (3.45, -6.3, .40), (-1.0, -1.4, 1.75), (-1.0, -1.7, 1.55), (16, 19, 1), 4, (14, 11)), F0, c1, .012)
        camera(face_keys(resP, c1 / FPS, T1, .42, .12, .30, 20, 2.8, -10, 2.2), c1, F1, .008)
    else:
        c2 = 82     # "tez yordam reanimatsiyaga" | "olib keldi"
        ks = []
        for j in range(6):
            t = T0 + (c2 / FPS - T0) * j / 5; g = gy(t)
            ks.append((t, (1.05 - .1 * j / 5, g - 2.0 + (.5 if j == 0 else 0), .26), (0, g + .9, .95), 17 if j else 15, 4, -9))
        ks[1] = (T0 + .15, ks[1][1], ks[1][2], 17, 4, -9)
        camera(ks, F0, c2, .02)
        t2 = c2 / FPS; d = hp(DR['doc'], t2 + .2); fc = hf(DR['doc'], t2 + .2)
        camera([(t2, (.9, gy(t2) - 1.5, .55), (0, gy(t2) + .9, 1.0), 18, 4, -8), (t2 + .13, d + fc * .45 + V((0, 0, -.04)), d, 22, 2.8, 6),
                (T1, d + fc * .38 + V((0, 0, -.04)), d, 24, 2.8, 7)], c2, F1, .008)

# ---------- 2. tea with the family
def tea():
    sets.home(T0, T1)
    P = actor('patient', SHOT != '2a'); seat = (0, .86, 0)
    REL, HIT = 6.36, 6.79
    def pat(t):
        sip = track([(3.3, 0), (3.95, 0), (4.4, 1), (4.95, 1), (5.4, 0)], t); slack = ss(6.15, 6.55, t); gone = ss(6.4, 6.95, t)
        hr = V((-.27, .44, .92)).lerp(V((-.17, .62, 1.00)), sip)
        hr = hr.lerp(V((-.36, .50, .90)), ss(5.55, 6.1, t)).lerp(V((-.36, .78, .50)), gone)
        hr += V((1, 0, 1)) * .006 * math.sin(t * 55) * ss(5.8, 6.1, t) * (1 - gone)
        f = V((.45, -.8, .05)).lerp(V((.9, .05, .2)), sip).lerp(V((-.1, -.55, -.8)), slack)
        n = V((.55, .25, .75)).lerp(V((.2, .3, .9)), sip).lerp(V((1, .1, -.1)), slack)
        return sit(P, seat, 0, t, (4 + 8 * sip + 9 * gone, -8 * gone, 8 * (1 - slack) * math.sin(t * 1.7)), 8,
                   dict(hand_r=(hr, (-1, .2, -.8)), palm_r=(f, n), curl={'r': lerp(.48, .12, slack), 'l': .3},
                        bend=(8 + 5 * gone, -10 * gone, 0)))
    res = P.perform(pat, F0, F1)
    P.face([(3.3, emo('happy')), (5.6, emo('happy')), (6.1, emo('worry', mouthFrownRight=.9)), (6.7, emo('droop', mouthLeft=.3)), (7.8, emo('droop'))],
           T0, T1, talk=(3.3, 4.0))
    cup = empty(); cup.rotation_mode = 'QUATERNION'
    sets.piyola((0, 0, 0), cup); tea_top = cyl((0, 0, .047), .050, .003, mat((.33, .11, .01), .05), cup)
    def held(t):
        p = pat(min(t, REL)); root = Matrix.Translation(V(p['at']))
        Q, H = P.solve(p, root); f0, n0 = P.fr['r']; h = H['hand_r']; q = Q['hand_r']
        pos = root @ (h + q @ (f0 * .085 + n0 * .035))
        sip = track([(3.3, 0), (3.95, 0), (4.4, 1), (4.95, 1), (5.4, 0)], t)
        return pos - UP * .02, RY(32 * sip) @ RX(-8 * sip)
    p0, _ = held(REL); p1 = V((-.54, .80, .03))
    for f in range(F0, F1):
        t = f / FPS
        if t <= REL: p, q = held(t); q = q @ RY(-25 * ss(6.1, REL, t))
        else:
            u = min(1, (t - REL) / (HIT - REL)); p = V((lerp(p0.x, p1.x, u), lerp(p0.y, p1.y, u), lerp(p0.z, p1.z, u * u))); q = RY(-25 - 120 * u) @ RX(50 * u)
        cup.location = p; cup.rotation_quaternion = q
        cup.keyframe_insert('location', frame=f); cup.keyframe_insert('rotation_quaternion', frame=f)
        for o in cup.children:
            o.hide_render = t >= HIT; o.keyframe_insert('hide_render', frame=f)
    # shards and spilt tea
    import random
    rr = random.Random(3); ch = sets.china(); bits = []
    prof = sets.BOWL[1:7]; n = 9
    for i in range(n):
        for j in range(2):
            rs = prof[j * 2 + 1:j * 2 + 4]; a0 = (i + rr.uniform(0, .3)) * math.tau / n; a1 = a0 + math.tau / n * rr.uniform(.6, 1)
            vs = [(r * math.cos(a), r * math.sin(a), z) for r, z in rs for a in (a0, (a0 + a1) / 2 + rr.uniform(-.1, .1), a1)]
            o = mesh(vs, [(k * 3 + m, k * 3 + m + 1, k * 3 + m + 4, k * 3 + m + 3) for k in range(len(rs) - 1) for m in range(2)], ch)
            o.modifiers.new('s', 'SOLIDIFY').thickness = .004
            am = (a0 + a1) / 2; bits.append((o, V((math.cos(am), math.sin(am), 0)) * rr.uniform(.35, .95), rr.uniform(.6, 1.3), rr.uniform(200, 600)))
    for i in range(34):
        a = rr.random() * math.tau; o = ball((0, 0, 0), rr.uniform(.004, .009), mat((.40, .14, .02), .1))
        bits.append((o, V((math.cos(a), math.sin(a), 0)) * rr.uniform(.2, .8), rr.uniform(.6, 1.6), 0))
    puddle = lathe([(1e-4, .0), (.05, .002), (.10, -.001)], mat((.16, .045, .008), .03, 0, 0, 1, .6), (p1.x, p1.y, .028), None, 24)
    for f in range(F0, F1):
        u = f / FPS - HIT
        for o, vel, vz, spin in bits:
            air = min(max(u, 0), vz / 4.9); o.hide_render = u < 0
            o.location = V((p1.x, p1.y, .026)) + vel * air * 1.3 + UP * max(0, vz * air - 4.9 * air * air)
            o.rotation_euler = (math.radians(spin * air), math.radians(spin * .4 * air), 0)
            o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f); o.keyframe_insert('hide_render', frame=f)
        s = max(.01, 1.7 * ss(0, .5, u)); puddle.scale = (s, s * .7, 1); puddle.keyframe_insert('scale', frame=f)
        puddle.hide_render = u < 0; puddle.keyframe_insert('hide_render', frame=f)
    TR = {}
    for nm, seat_, yaw, ph in (('wife', (-.70, .22, 0), 90, 1), ('son', (.70, .22, 0), -90, 2)):
        a = actor(nm, SHOT == '2c' and nm == 'wife'); s = 1 if yaw > 0 else -1
        def fn(t, a=a, seat_=seat_, yaw=yaw, ph=ph, s=s):
            k = ss(6.8, 7.2, t); h = None
            if k > 0:
                h = {}
                for sd, x in (('l', .13), ('r', -.13)):
                    tgt = w(seat_, yaw, (x, -.36, .80)).lerp(w(seat_, yaw, (x * .8, -.30, 1.10 * a.k)), k)
                    h['hand_' + sd] = (tgt, DOWN + left(yaw) * (1 if sd == 'l' else -1))
                    h['palm_' + sd] = (UP * k + fwd(yaw) * (1.01 - k), fwd(yaw) * k + DOWN * (1.01 - k))
            return sit(a, seat_, yaw, t, (3 + 8 * k, 0, s * (25 + 8 * k)), 5 + 12 * k, h, ph)
        TR[nm] = a.perform(fn, F0, F1)
        a.face([(3.3, emo('happy')), (6.55, emo('happy')), (6.95, emo('shock'))], T0, T1, talk=(4.0, 5.5) if nm == 'son' else None)
    a = actor('daughter'); at = (.50, 1.22, 0)
    def girl(t):
        k = ss(6.8, 7.2, t); h = {}
        for sd, x in (('l', .12), ('r', -.12)):
            h['hand_' + sd] = (w(at, -15, (x, -.30, 1.02)).lerp(w(at, -15, (x * .7, -.17, 1.36)), k), DOWN + left(-15) * (1 if sd == 'l' else -1))
        return stand(a, at, -15, t, (14, 0, -18), 8, h, 2)
    a.perform(girl, F0, F1)
    a.face([(3.3, emo('happy')), (6.55, emo('happy')), (6.95, emo('shock'))], T0, T1)
    if SHOT == '2a':
        c1 = 139    # "Bir soat oldin choy ichib" | "o'tirgan ekan"
        camera(crash(T0, c1 / FPS, (.55, -2.95, .9), (.32, -2.15, .98), (.27, -1.98, 1.0), (0, .6, 1.1), (0, .6, 1.12), (16, 20, 1), 4.5, (7, 5)), F0, c1, .008)
        camera(face_keys(res, c1 / FPS, T1, .40, -.12, -.05, 21, 3.2, -5, 2.0, look=(0, 0, -.03)), c1, F1, .006)
    elif SHOT == '2b':
        c1 = 187    # "birdan qo'lidagi" | "piyola tushib"
        hk = []
        for j in range(5):
            t = T0 + (c1 / FPS - T0) * j / 4; hd_ = bp(res, t, 'hand_r')
            hk.append((t, hd_ + V((-.24, -.20, .09)) * (1.8 if j == 0 else 1), hd_, 28, 2.8, 8))
        hk[1] = (T0 + .15, hk[1][1], hk[1][2], 28, 2.8, 8)
        camera(hk, F0, c1, .006)
        t1_ = c1 / FPS; h0 = bp(res, t1_, 'hand_r')
        camera([(t1_, h0 + V((-.32, -.26, .06)), h0, 24, 3.5, 8), (REL + .03, h0 + V((-.30, -.25, .02)), h0 + V((0, 0, -.03)), 24, 3.5, 9),
                (HIT - .02, V((p1.x - .42, p1.y - .33, .11)), V((p1.x, p1.y, .07)), 17, 5, 16), (T1, V((p1.x - .38, p1.y - .29, .10)), V((p1.x, p1.y, .05)), 17, 5, 18)], c1, F1, .006)
    else:
        camera(face_keys(TR['wife'], T0, T1, .42, .08, .0, 22, 2.8, -9, 2.1), F0, F1, .008)

# ---------- 3-4. the symptoms, inside the resuscitation bay
def exam():
    sets.bay(T0, T1); sets.gurney()
    P = actor('patient', True); at = (0, 0, 0)
    def pat(t):
        h = {}; hd = [10, 0, 0]
        if SHOT == '3a':
            hd = [16, 7 * ss(8.5, 9.4, t), 3 * math.sin(t * 1.6)]
        if SHOT == '3b':
            up = ss(10.15, 10.85, t)
            tr = track([(10.15, 0), (10.55, .28), (10.75, .12), (11.0, .30), (11.3, 0)], t) + .02 * math.sin(t * 40) * ss(10.4, 10.6, t) * (1 - ss(11.0, 11.3, t))
            h = dict(hand_l=(V((.27, -.22, 1.02)).lerp(V((.30, -.30, 1.52)), up), X + DOWN),
                     palm_l=(V((0, -1, 0)).lerp(V((0, -.5, .9)), up), DOWN.lerp(V((0, -1, -.2)), up)),
                     hand_r=(V((-.28, -.22, 1.00)).lerp(V((-.30, -.30, 1.38)), tr), -X + DOWN),
                     palm_r=(V((0, -1, -.15 - tr)), DOWN), curl={'l': lerp(.3, .03, up), 'r': .55})
            hd = [track([(10.2, 14), (10.8, 20), (11.6, 24)], t), 4, track([(10.2, 0), (10.7, -22), (11.8, -25)], t)]
        if SHOT == '4':
            hd = [16 + 5 * math.sin(t * 3.3) * ss(12, 12.4, t), 6 * math.sin(t * 1.5), 14 * math.sin(t * 1.2)]
            g = ss(12.2, 12.8, t)
            h = dict(hand_l=(V((.27, -.22, 1.02)).lerp(V((.25, -.28, 1.22 + .05 * math.sin(t * 5))), g), X + DOWN),
                     palm_l=(V((-.2, -1, .4)), V((-.4, 0, 1))), curl={'l': .25 + .15 * math.sin(t * 5), 'r': .5})
        return recline(P, at, 0, t, hd, h)
    res = P.perform(pat, F0, F1)
    root, Q, H = res[(F0 + F1) // 2] if (F0 + F1) // 2 in res else res[F0]
    head = root @ (H['head'] + Q['head'] @ V((0, -.07, .045)))
    facing = (Q['head'] @ V((0, -1, 0))).normalized()
    print('##HEAD', SHOT, head[:], facing[:], flush=True)
    if SHOT == '3a':
        P.face([(7.8, emo('worry', mouthFrownLeft=.1, mouthFrownRight=.1)), (8.25, emo('worry', mouthFrownLeft=.1, mouthFrownRight=.2)),
                (8.95, emo('droop')), (10.1, emo('droop', mouthFrownRight=1, browInnerUp=1, mouthLeft=.85))], T0, T1)
    elif SHOT == '3b':
        P.face([(10.1, emo('droop')), (10.8, emo('droop', eyeSquintLeft=.6, browInnerUp=.6, mouthPressLeft=.5)), (11.7, emo('droop', browInnerUp=1))], T0, T1)
    else:
        P.face([(11.9, emo('droop')), (13.0, emo('droop', browDownLeft=.4)), (14.0, emo('droop', browInnerUp=1, eyeWideLeft=.7))], T0, T1, talk=(12.05, 14.85))
    ER = {}
    for nm, x, y, yaw in (('doc', -.78, .22, 80), ('wife', .72, .45, -75)):
        a = actor(nm, SHOT == '4')
        if nm == 'doc': sets.stethoscope(a)
        def fn(t, a=a, x=x, y=y, yaw=yaw):
            h = None
            if a.name == 'wife':
                h = dict(hand_l=(w((x, y, 0), yaw, (.03, -.24, 1.22 * a.k)), left(yaw) + DOWN),
                         hand_r=(w((x, y, 0), yaw, (-.02, -.25, 1.19 * a.k)), -left(yaw) + DOWN),
                         palm_l=(UP, -left(yaw)), palm_r=(UP, left(yaw)), curl={'l': .55, 'r': .55})
            elif SHOT == '3b':
                k = ss(10.1, 10.6, t)
                h = dict(hand_l=(w((x, y, 0), yaw, (.22, -.12 - .3 * k, .9 + .42 * k)), left(yaw) + DOWN), palm_l=(fwd(yaw), UP))
            return stand(a, (x, y, 0), yaw, t, (22, 0, 0), 12, h, x)
        ER[nm] = a.perform(fn, F0, F1)
        a.face([(T0, emo('worry') if nm == 'wife' else emo('focus'))], T0, T1)
    if SHOT == '3a':
        c1 = 268    # "Yuzining o'ng tomoni" | "qiyshayib qolgan"
        camera(face_keys(res, T0, c1 / FPS, .38, .03, .02, 21, 3.2, 3, 2.6, look=(0, 0, -.02)), F0, c1, .005)
        camera(face_keys(res, c1 / FPS, T1, .40, -.24, -.10, 21, 3.2, 15, 1.8, look=(0, 0, -.02)), c1, F1, .006)
    elif SHOT == '3b':
        c1 = 321    # "o'ng qo'lini" | "ko'tara olmayapti"
        hr_ = bp(res, T0, 'hand_r')
        camera([(T0, hr_ + V((-.42, -.50, .2)), hr_, 26, 2.8, -6), (T0 + .15, hr_ + V((-.24, -.30, .13)), hr_, 28, 2.8, -6),
                (c1 / FPS, hr_ + V((-.22, -.28, .12)), hr_, 29, 2.8, -7)], F0, c1, .006)
        camera(crash(c1 / FPS, T1, (.55, -1.75, 1.8), (.32, -1.18, 1.64), (.30, -1.1, 1.62), (0, -.05, 1.3), (0, -.05, 1.32), (17, 20, 1), 4, (-7, -6)), c1, F1, .008)
    else:
        c1, c2 = 392, 412   # "Gapirmoqchi bo'ladi," | "lekin so'zlari" | "tushunarsiz chiqyapti."
        camera(face_keys(res, T0, c1 / FPS, .30, .04, -.05, 21, 2.8, 0, 2.0, look=(0, 0, -.06)), F0, c1, .005)
        wh = hp(ER['wife'], c1 / FPS); wf = hf(ER['wife'], c1 / FPS); sd_ = wf.cross(UP).normalized()
        camera([(c1 / FPS, wh - wf * .5 + sd_ * .22 + UP * .1, head, 22, 3.5, 6), (c1 / FPS + .15, wh - wf * .32 + sd_ * .16 + UP * .06, head, 26, 3.5, 7),
                (c2 / FPS, wh - wf * .30 + sd_ * .15 + UP * .06, head, 27, 3.5, 8)], c1, c2, .008)
        camera(face_keys(res, c2 / FPS, T1, .34, -.05, .0, 21, 2.8, -4, 1.7), c2, F1, .006)

# ---------- 5-6. the question, in front of the same door
def question():
    sets.hospital(T0, T1)
    g = sets.gurney(); g.location = (0, .95, 0); g.rotation_euler.z = math.radians(90)      # head towards -X
    P = actor('patient'); with_mask(P)
    P.perform(lambda t: recline(P, (0, .95, 0), 90, t, (6, 0, 20)), F0, F1, 2)
    P.face([(T0, emo('dazed'))], T0, T1)
    people = [('doc', .27, .15, 0, 'ask'), ('doc2', -.27, .22, 5, 'ask'), ('medic1', -1.10, 1.15, 25, 'focus'), ('medic2', 1.12, .95, -25, 'focus'),
              ('wife', -.72, 1.62, 8, 'worry'), ('son', .72, 1.7, -5, 'worry')]
    info = {}
    for i, (nm, x, y, yaw, e) in enumerate(people):
        a = actor(nm, SHOT != '6' and nm in ('doc', 'doc2'))
        isdoc = nm in ('doc', 'doc2')
        if isdoc: sets.stethoscope(a)
        def fn(t, a=a, x=x, y=y, yaw=yaw, isdoc=isdoc, i=i):
            h, hd = None, (4, 0, 0)
            if isdoc:
                turn = ss(15.15, 15.8, t); hd = (-3 + 2 * ss(16.6, 17.2, t), (5 if a.name == 'doc' else -5) * ss(16.4, 17.1, t), lerp(45 if x < 0 else -45, 0, turn))
                if a.name == 'doc':
                    h = dict(hand_l=(w((x, y, 0), yaw, (-.13, -.24, 1.12 * a.k)), X + DOWN), hand_r=(w((x, y, 0), yaw, (.14, -.27, 1.10 * a.k)), -X + DOWN),
                             palm_l=(-X, Y), palm_r=(X, Y), curl={'l': .5, 'r': .5})
            return stand(a, (x, y, 0), yaw, t, hd, 3, h, i)
        res = a.perform(fn, F0, F1, 2)
        a.face([(T0, emo('focus') if isdoc else emo(e)), (T0 + .5, emo(e))], T0, T1)
        root, Q, H = res[F0]
        info[nm] = root @ (H['head'] + V((0, -.08, .07)))
    d, d2 = info['doc'], info['doc2']; m = (d + d2) / 2
    if SHOT == '5a':
        camera(crash(T0, T1, m + V((.30, -2.2, -.70)), m + V((.14, -1.25, -.56)), m + V((.12, -1.15, -.53)), m + V((0, 0, -.10)), m + V((0, 0, -.12)), (16, 20, 1), 2.8, (10, 8)), F0, F1, .008)
    elif SHOT == '5b':
        camera(crash(T0, T1, d + V((-.06, -1.05, .0)), d + V((-.02, -.38, .0)), d + V((-.02, -.33, .0)), d + V((0, 0, -.02)), d + V((0, 0, -.02)), (21, 24, 1), 2.8, (0, -4)), F0, F1, .004)
    else:
        camera([(T0, (.2, -3.2, 1.75), (0, .9, 1.6), 36, 5), (18.6, (.1, -4.5, 1.9), (0, .9, 1.95), 32, 5), (T1, (-.1, -4.9, 2.0), (0, .9, 2.0), 32, 5)], F0, F1)

t_build = time.time()
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'): bpy.data.objects.remove(o)
{'1': arrival, '2': tea, '3': exam, '4': exam, '5': question, '6': question}[SHOT[0]]()
used = {a.name for a in CAST}
for o in list(bpy.data.objects):
    if o.get('who') and o['who'] not in used: bpy.data.objects.remove(o)
    elif o.type == 'ARMATURE' and o.name not in used: bpy.data.objects.remove(o)
for o in bpy.data.objects:
    if o.get('part') in ('eyelashes01', 'brow', 'moustache', 'teeth_base', 'tongue01'): o.visible_shadow = False

r = S.render; r.engine = 'BLENDER_EEVEE'; r.resolution_x, r.resolution_y, r.fps = 1080, 1920, FPS
e = S.eevee
for k, v in dict(taa_render_samples=20, use_raytracing=False, use_fast_gi=False, use_shadows=True, shadow_ray_count=1, shadow_step_count=4).items():
    setattr(e, k, v)
S.view_settings.view_transform = 'Khronos PBR Neutral'
S.view_settings.exposure = .1
import realism; realism.apply(S, heavy=(SHOT != '6'))
r.use_persistent_data = True
S.frame_start, S.frame_end = F0, F1 - 1
print('##BUILT', SHOT, round(time.time() - t_build, 1), flush=True)
if MODE == 'still':
    r.resolution_percentage = 50; r.image_settings.file_format = 'PNG'
    for i, t in enumerate(float(x) for x in A[3].split(',')):
        c = time.time(); S.frame_set(min(F1 - 1, max(F0, int(t * FPS))))
        r.filepath = f'{ROOT}/chk/s_{SHOT}_{i}.png'; bpy.ops.render.render(write_still=True)
        print('##STILL', SHOT, t, round(time.time() - c, 1), flush=True)
else:
    r.image_settings.file_format = 'JPEG'; r.image_settings.quality = 96
    r.resolution_percentage = 100; r.use_overwrite = False
    if SHOT == '6':
        # this shot sits under a heavy blur: half resolution, every second frame
        r.resolution_percentage = 50; S.frame_step = 2; e.taa_render_samples = 14
    r.filepath = f'{ROOT}/frames/f_'
    c = time.time(); bpy.ops.render.render(animation=True)
    print('##RENDERED', SHOT, round(time.time() - c, 1), flush=True)
