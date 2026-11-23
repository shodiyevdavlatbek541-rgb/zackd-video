"""Cast built from the BodyParts3D skin scan (CC BY-SA 2.1 JP): own skeleton (same bone names as before),
own weights, procedural face shapes, strand hair, cloth shells. No MPFB/MakeHuman.
usage: blender -b -P scan_cast.py -- ROOT [names,comma] [check]"""
import bpy, bmesh, math, random, json, sys, os, time
from mathutils import Vector as V, Matrix, Quaternion, noise
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

A = sys.argv[sys.argv.index('--') + 1:]
ROOT = A[0]; ONLY = A[1].split(',') if len(A) > 1 and A[1] != 'all' else None; CHECK = 'check' in A
SCAN = ROOT + '/scan'
T0 = time.time()
def log(*a): print('##', round(time.time() - T0, 1), *a, flush=True)
def sm(a, b, x):
    t = min(1, max(0, (x - a) / (b - a))) if b != a else float(x >= a)
    return t * t * (3 - 2 * t)
def gs(x, w): return math.exp(-(x / w) ** 2)

bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene
ZOFF = .0781112

# ---------------------------------------------------------------- load the scan
parts = json.load(open(SCAN + '/parts.json'))
def load(code):
    bpy.ops.wm.obj_import(filepath=f'{SCAN}/{code}.obj', forward_axis='Y', up_axis='Z')
    o = bpy.context.selected_objects[0]
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    for v in bm.verts: v.co = V((v.co.x / 1000, v.co.y / 1000, v.co.z / 1000 + ZOFF))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free(); o.data.materials.clear()
    for p in o.data.polygons: p.use_smooth = True
    return o
BASE = {}
for k, v in parts.items():
    n = v['name'].lower(); o = load(k)
    g = 'tooth_lo' if ('tooth' in n and 'lower' in n) else 'tooth_up' if 'tooth' in n else v['g']
    if g in ('sclera', 'iris', 'cornea'): g += '_l' if n.startswith('left') else '_r'
    BASE.setdefault(g, []).append(o)
def join(objs):
    if len(objs) == 1: return objs[0]
    for o in objs: o.hide_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); return objs[0]
for g in list(BASE): BASE[g] = join(BASE[g])
for o in BASE.values(): o.hide_render = True; o.hide_set(True)
skin0 = BASE['skin']
log('loaded', {g: len(o.data.vertices) for g, o in BASE.items()})

def pts(o): return [v.co.copy() for v in o.data.vertices]
def centroid(ps): return sum(ps, V()) / len(ps)
def bvh(o): return BVHTree.FromPolygons([v.co for v in o.data.vertices], [p.vertices[:] for p in o.data.polygons])

# ---------------------------------------------------------------- landmarks
SV = pts(skin0); H = max(p.z for p in SV)
def slab(z, tol=.005, P=SV): return [p for p in P if abs(p.z - z) < tol]
def clusters(ps, gap=.014):
    ps = sorted(ps, key=lambda p: p.x); out = [[ps[0]]] if ps else []
    for p in ps[1:]:
        if p.x - out[-1][-1].x > gap: out.append([p])
        else: out[-1].append(p)
    return out

L = {}
lip = pts(BASE['lip'])
L['cl'] = max(lip, key=lambda p: p.x); L['cr'] = min(lip, key=lambda p: p.x)
mz = (L['cl'].z + L['cr'].z) / 2
L['m'] = V((0, min(p.y for p in lip if abs(p.x) < .01), mz))
for s, sd in ((1, 'l'), (-1, 'r')):
    sc = pts(BASE['sclera_' + sd]); L['eye_' + sd] = centroid(sc)
    L['er_' + sd] = (max(p.z for p in sc) - min(p.z for p in sc)) / 2
br = pts(BASE['brow'])
for s, sd in ((1, 'l'), (-1, 'r')):
    b = [p for p in br if p.x * s > 0]
    L['brow_' + sd] = centroid(b); L['browin_' + sd] = min(b, key=lambda p: abs(p.x)); L['browout_' + sd] = max(b, key=lambda p: abs(p.x))
ear = pts(BASE['ear']); L['ear'] = V((0, centroid(ear).y, centroid(ear).z))
L['pivot'] = L['ear'] + V((0, -.012, -.01))
face = [p for p in SV if abs(p.x) < .006 and L['m'].z < p.z < L['eye_l'].z]
L['nose'] = min(face, key=lambda p: p.y)
ch = [p for p in SV if abs(p.x) < .008 and p.z < L['m'].z and p.y < L['m'].y + .035 and p.z > L['m'].z - .09]
L['chin'] = min(ch, key=lambda p: p.z)
log('face', {k: tuple(round(x, 3) for x in v) if isinstance(v, V) else round(v, 4) for k, v in L.items()})

J = {}   # joints
for s, sd in ((1, 'l'), (-1, 'r')):
    def leg(z):
        q = [p for p in slab(z) if .015 < p.x * s < (.17 if z > .6 else .26)]
        return centroid(q)
    hip = leg(.80); J['hip_' + sd] = V((hip.x * .86, hip.y + .01, .515 * H))
    kn = leg(.29 * H); J['knee_' + sd] = V((kn.x, kn.y - .005, .29 * H))
    an = leg(.095); J['ankle_' + sd] = V((an.x, an.y + .012, .075))
    foot = [p for p in SV if p.z < .06 and .02 < p.x * s < .2]
    toe = min(foot, key=lambda p: p.y); heel = max(foot, key=lambda p: p.y)
    ball = heel + (toe - heel) * .72; J['ball_' + sd] = V((ball.x, ball.y, .022)); J['toe_' + sd] = V((toe.x, toe.y + .01, .018))
    # arm centre line from the outermost free cluster of each slice
    arm = {}
    for i in range(140):
        z = 1.30 - i * .005
        cs = [c for c in clusters(slab(z, .0035)) if centroid(c).x * s > 0]
        if len(cs) < 2: continue
        c = max(cs, key=lambda c: centroid(c).x * s)
        if min(abs(p.x) for p in c) < .12: continue
        arm[round(z, 3)] = c
    zs = sorted(arm)
    HP = [p for p in SV if p.x * s > .2 and p.z < 1.0]
    tip = min(p.z for p in HP); hl = .175 * H / 1.72
    wz = tip + hl
    J['wrist_' + sd] = centroid([p for p in HP if abs(p.z - wz) < .004])
    shz = .81 * H; top = slab(shz, .006); xm = max(p.x * s for p in top)
    sh = [p for p in top if p.x * s > xm - .06]
    J['shoulder_' + sd] = V((s * (xm - .048), centroid(sh).y + .004, shz))
    ez = J['shoulder_' + sd].z - (J['shoulder_' + sd].z - wz) * .56
    ek = min(zs, key=lambda z: abs(z - ez)); J['elbow_' + sd] = centroid(arm[ek]) + V((0, .008, 0))
    J['palm_' + sd] = centroid([p for p in HP if abs(p.z - (tip + hl * .62)) < .004])
    J['knuckle_z_' + sd] = tip + hl * .50
    fc = [centroid(c) for c in clusters([p for p in HP if abs(p.z - (tip + hl * .22)) < .003], .003)]
    J['fingers_' + sd] = sorted(fc, key=lambda p: -p.x * s)
    J['tip_' + sd] = tip
    log('arm', sd, 'wrist', round(wz, 3), 'tip', round(tip, 3), 'finger clusters', len(fc))

def back_y(z):
    q = [p for p in slab(z) if abs(p.x) < .03]
    return max(p.y for p in q), min(p.y for p in q)
for nm, z, d in (('pelvis', .535 * H, .075), ('sp1', .585 * H, .06), ('sp2', .63 * H, .055), ('sp3', .68 * H, .055),
                 ('sp3t', .76 * H, .06), ('neck', .835 * H, .05), ('head', .885 * H, 0)):
    b, f = back_y(z); J[nm] = V((0, b - d if d else (b + f) / 2 + .01, z))
J['top'] = V((0, J['head'].y, H))
J['clav_l'] = V((.022, back_y(.82 * H)[1] + .035, .82 * H)); J['clav_r'] = J['clav_l'] * V((-1, 1, 1)) if False else V((-.022, J['clav_l'].y, J['clav_l'].z))
log('joints', {k: tuple(round(x, 3) for x in v) for k, v in J.items() if isinstance(v, V)})

FL = {'index': (.044, .026, .020), 'middle': (.047, .029, .021), 'ring': (.044, .027, .020), 'pinky': (.035, .021, .018), 'thumb': (.040, .032, .027)}
def skeleton():
    B = {}   # name: (head, tail, parent)
    B['Root'] = (V((0, 0, 0)), V((0, .03, 0)), None)
    B['pelvis'] = (J['pelvis'], J['sp1'], 'Root'); B['spine_01'] = (J['sp1'], J['sp2'], 'pelvis')
    B['spine_02'] = (J['sp2'], J['sp3'], 'spine_01'); B['spine_03'] = (J['sp3'], J['sp3t'], 'spine_02')
    B['neck_01'] = (J['neck'], J['head'], 'spine_03'); B['head'] = (J['head'], J['top'], 'neck_01')
    for s, sd in ((1, 'l'), (-1, 'r')):
        B['clavicle_' + sd] = (J['clav_' + sd], J['shoulder_' + sd], 'spine_03')
        B['upperarm_' + sd] = (J['shoulder_' + sd], J['elbow_' + sd], 'clavicle_' + sd)
        B['lowerarm_' + sd] = (J['elbow_' + sd], J['wrist_' + sd], 'upperarm_' + sd)
        w = J['wrist_' + sd]; pm = J['palm_' + sd]; down = (pm - w).normalized()
        B['hand_' + sd] = (w, w + down * .03, 'lowerarm_' + sd)
        kz = J['knuckle_z_' + sd]
        cs = clusters([p for p in SV if abs(p.z - (kz + .012)) < .003 and p.x * s > .2], .006)
        palm = max(cs, key=len); pc = centroid(palm)
        lat = max(palm, key=lambda p: p.x * s); med = min(palm, key=lambda p: p.x * s)
        for i, f in enumerate(('index', 'middle', 'ring', 'pinky')):
            t = .13 + i * .245; k = lat + (med - lat) * t; k = V((k.x, pc.y, kz))
            band = [p for p in SV if p.x * s > .2 and abs(p.z - (kz - .045)) < .003 and abs(p.x - k.x) < .008]
            d = (centroid(band) - k).normalized() if band else down
            p0 = k
            for j, ln in enumerate(FL[f]):
                p1 = p0 + d * ln; B[f'{f}_0{j + 1}_{sd}'] = (p0, p1, 'hand_' + sd if j == 0 else f'{f}_0{j}_{sd}'); p0 = p1
        p0 = w + V((s * .022, -.018, -.022)); d = V((s * .45, -.55, -.7)).normalized()
        for j, ln in enumerate(FL['thumb']):
            p1 = p0 + d * ln; B[f'thumb_0{j + 1}_{sd}'] = (p0, p1, 'hand_' + sd if j == 0 else f'thumb_0{j}_{sd}'); p0 = p1
        B['thigh_' + sd] = (J['hip_' + sd], J['knee_' + sd], 'pelvis')
        B['calf_' + sd] = (J['knee_' + sd], J['ankle_' + sd], 'thigh_' + sd)
        B['foot_' + sd] = (J['ankle_' + sd], J['ball_' + sd], 'calf_' + sd)
        B['ball_' + sd] = (J['ball_' + sd], J['toe_' + sd], 'foot_' + sd)
    return B
SKEL = skeleton()

# ---------------------------------------------------------------- base mesh: ears joined, face densified, mouth opened
skin0 = join([skin0, BASE.pop('ear')]); BASE['skin'] = skin0; skin0.hide_set(True)
bm = bmesh.new(); bm.from_mesh(skin0.data)
ed = [e for e in bm.edges if all(v.co.y < -.105 and v.co.z > 1.46 and abs(v.co.x) < .075 for v in e.verts) and e.calc_length() > .0028]
bmesh.ops.subdivide_edges(bm, edges=ed, cuts=1, use_grid_fill=True)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
bnd = [e for e in bm.edges if e.is_boundary and ((e.verts[0].co + e.verts[1].co) / 2 - L['m']).length < .035]
log('mouth boundary edges before cut', len(bnd))
if len(bnd) < 10:   # sealed lips: split the skin along the lip line (no gap at rest, the jaw can open it)
    def onl(v): return abs(v.co.z - L['m'].z) < .0016 and abs(v.co.x) < L['cl'].x - .0015 and v.co.y < L['m'].y + .016
    cut = [e for e in bm.edges if onl(e.verts[0]) and onl(e.verts[1]) and abs(e.verts[0].co.z - e.verts[1].co.z) < .0012]
    bmesh.ops.split_edges(bm, edges=cut); log('mouth split edges', len(cut))
bm.to_mesh(skin0.data); bm.free()
for p in skin0.data.polygons: p.use_smooth = True
tipg = min((v for v in skin0.data.vertices if abs(v.co.x) < .04 and .70 < v.co.z < .86), key=lambda v: v.co.y).co.copy()
refy = min(v.co.y for v in skin0.data.vertices if abs(v.co.x) < .03 and abs(v.co.z - .93) < .006)
for v in skin0.data.vertices:
    d = (v.co - tipg).length
    if d < .09 and v.co.y < refy + .01 and abs(v.co.x) < .07:
        w = sm(.09, .03, d); v.co.y = v.co.y + (max(v.co.y, refy + .012) - v.co.y) * w
SV = pts(skin0); NV = len(SV)
ADJ = [[] for _ in range(NV)]
for e in skin0.data.edges:
    a, b = e.vertices; ADJ[a].append(b); ADJ[b].append(a)
log('base skin', NV)

# ---------------------------------------------------------------- weights (base topology, reused by every character)
def segd(p, a, b):
    ab = b - a; t = max(0, min(1, (p - a).dot(ab) / ab.length_squared)); return (p - a - ab * t).length, t
BONES = [n for n in SKEL if n != 'Root']
def region_of(n):
    if n in ('head', 'neck_01'): return 'head'
    if n.startswith('clavicle') or n in ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'Root'): return 'torso'
    if n.startswith(('thigh', 'calf', 'foot', 'ball')): return 'leg_' + n[-1]
    return 'arm_' + n[-1]
def head_side(p):   # above the plane under the jaw and the base of the skull
    return p.z > L['chin'].z - .012 + (p.y - L['chin'].y) * .55 and abs(p.x) < .11 and p.z > J['neck'].z + .03
def nearest(p, cands):
    best = None
    for n in cands:
        h, t, _ = SKEL[n]; d, _ = segd(p, h, t)
        if n.split('_')[0] in ('index', 'middle', 'ring', 'pinky', 'thumb'): d *= .9
        if best is None or d < best[0]: best = (d, n)
    return best[1]
# body-part labels by walking over the skin from unambiguous seeds (a hand resting near the thigh stays an arm)
import heapq
def seed_label(p):
    if head_side(p): return 'head'
    best = {}
    for n in BONES:
        if n == 'head': continue
        h, t, _ = SKEL[n]; d, _ = segd(p, h, t); r = region_of(n)
        if r not in best or d < best[r]: best[r] = d
    rs = sorted(best.items(), key=lambda x: x[1])
    return rs[0][0] if rs[1][1] > 2.2 * rs[0][1] + .01 else None
LAB = [seed_label(p) for p in SV]
dist = [0.0 if l else 1e9 for l in LAB]
heap = [(0.0, i) for i in range(NV) if LAB[i]]; heapq.heapify(heap)
while heap:
    d, i = heapq.heappop(heap)
    if d > dist[i]: continue
    for j in ADJ[i]:
        nd = d + (SV[i] - SV[j]).length
        if nd < dist[j]: dist[j] = nd; LAB[j] = LAB[i]; heapq.heappush(heap, (nd, j))
LAB = [l or 'torso' for l in LAB]
log('labels', {r: LAB.count(r) for r in set(LAB)})
CAND = {'head': ['head', 'neck_01'],
        'torso': ['pelvis', 'spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r', 'neck_01', 'upperarm_l', 'upperarm_r', 'thigh_l', 'thigh_r']}
for sd in 'lr':
    CAND['arm_' + sd] = [b for b in BONES if region_of(b) == 'arm_' + sd] + ['clavicle_' + sd, 'spine_03']
    CAND['leg_' + sd] = [b for b in BONES if region_of(b) == 'leg_' + sd] + ['pelvis']
def weigh(P, labs, sigma=.011):
    out = []
    for p, lab in zip(P, labs):
        if lab == 'head' and head_side(p):
            out.append({'head': 1.0}); continue
        ds = []
        for n in CAND[lab]:
            h, t, _ = SKEL[n]; d, _ = segd(p, h, t)
            if n.split('_')[0] in ('index', 'middle', 'ring', 'pinky', 'thumb'): d *= .9
            ds.append((d, n))
        ds.sort(); d0 = ds[0][0]; sg = .0045 if ds[0][1].split('_')[0] in ('index', 'middle', 'ring', 'pinky', 'thumb') else sigma
        w = {n: math.exp(-(d - d0) / sg) for d, n in ds[:3]}
        s_ = sum(w.values()); out.append({n: x / s_ for n, x in w.items() if x / s_ > .02})
    return out
W = weigh(SV, LAB)
for it in range(3):
    W2 = []
    for i in range(NV):
        acc = dict(W[i])
        for j in ADJ[i]:
            for n, x in W[j].items(): acc[n] = acc.get(n, 0) + x
        s_ = sum(acc.values()); W2.append({n: x / s_ for n, x in acc.items() if x / s_ > .015})
    W = W2
DOM = [max(w, key=w.get) for w in W]
log('weights done')

REG = list(LAB)

# ---------------------------------------------------------------- per-character shape
def deform(p, reg, P):
    """Body/face variation as smooth displacement fields (same function moves skin, clothes source and bones)."""
    q = p.copy(); fem = P.get('fem', 0); g = P.get('girth', 1.0); z = p.z
    s = 1 if p.x >= 0 else -1
    if reg == 'torso' or reg == 'head' and z < J['neck'].z + .02:
        fx = 1 + (g - 1) * (gs(z - .60 * H, .12) + .5) - fem * .09 * sm(.74 * H, .80 * H, z) + fem * .07 * gs(z - .53 * H, .06) - fem * .07 * gs(z - .62 * H, .04)
        fy = 1 + (g - 1) * (gs(z - .60 * H, .12) + .4)
        q.x *= fx; q.y = (q.y + .05) * fy - .05
        if p.y < -.06:
            q.y -= P.get('belly', 0) * gs(z - .585 * H, .075) * gs(p.x, .13)
            q.y -= fem * .032 * (gs(p.x - .085, .045) + gs(p.x + .085, .045)) * gs(z - .72 * H, .045)
    elif reg.startswith('arm'):
        q.x -= s * fem * .021; q.x += s * (g - 1) * .08
    elif reg.startswith('leg'):
        q.x += s * (fem * .012 + (g - 1) * .04) * sm(.25 * H, .5 * H, z)
        c = SKEL['thigh_' + reg[-1]][1] if z < .5 * H else SKEL['thigh_' + reg[-1]][0]
        k = 1 + (g - 1) * .6 + fem * .04 * sm(.3 * H, .5 * H, z)
        q.x = c.x + (q.x - c.x) * k; q.y = c.y + (q.y - c.y) * k
    if reg == 'head' or p.z > J['neck'].z + .03:
        nb = L['nose'] + V((0, .022, -.012)); dn = (p - nb).length
        if p.y < L['eye_l'].y + .02 and dn < .05:
            f = gs(dn, .03) * (P.get('nose', 1) - 1)
            q += (p - nb) * f
        if p.z < L['m'].z + .01 and p.y < L['ear'].y:
            jw = (P.get('jaw', 1) - 1) * sm(L['m'].z + .01, L['chin'].z, p.z)
            q.x += p.x * jw; q.y -= P.get('chin', 0) * gs(p.x, .03) * sm(L['m'].z, L['chin'].z, p.z)
        if p.y < L['ear'].y and abs(p.z - L['brow_l'].z - .006) < .03:
            q.y += P.get('brow', 0) * gs(p.z - L['brow_l'].z - .006, .012) * (gs(abs(p.x) - .035, .03))
        if fem:
            dl = (p - L['m']).length
            if dl < .03 and p.y < L['m'].y + .015: q.y -= .0025 * gs(dl, .012); q.z = L['m'].z + (q.z - L['m'].z) * (1 + .25 * gs(dl, .015))
        age = P.get('age', 0)
        if age and p.y < L['ear'].y and p.z < L['m'].z + .02:
            q.z -= age * .005 * gs(abs(p.x) - .045, .018) * gs(p.z - L['m'].z + .02, .03)
        E = L['eye_l']; wf = sm(J['neck'].z, J['neck'].z + .06, p.z)
        q.x += p.x * (P.get('fw', 1) - 1) * wf
        if p.z < E.z: q.z += (p.z - E.z) * (P.get('flen', 1) - 1) * wf
        if p.y < L['ear'].y:
            q.y -= P.get('cheek', 0) * gs(abs(p.x) - .045, .018) * gs(p.z - (E.z - .035), .022)
            q.y -= P.get('lips', 0) * gs((p - L['m']).length, .012)
            q.z += P.get('browz', 0) * gs(p.z - L['brow_l'].z, .015) * gs(abs(p.x) - .035, .03)
    hs = P.get('h', 1.0)
    return V((q.x * hs, q.y * hs, q.z * hs))

def define(me, P):
    d = P.get('define', .8)
    for v in me.vertices:
        X, Y, Z = v.co
        if Y > -.12 or Z < 1.47 or Z > 1.66: continue
        h = 0
        for s in (1, -1):
            E = L['eye_' + ('l' if s > 0 else 'r')]
            h -= .0035 * gs(X - E.x, .02) * gs(Z - E.z - .004, .016) * (1 - gs(Z - E.z, .009))      # socket shadow above/below the eye
            h += .0025 * gs(X - s * .052, .014) * gs(Z - (E.z - .03), .012)                          # cheekbone
            h -= .0022 * gs(math.hypot(X - s * (.022 + (L['nose'].z - Z) * .35), 0), .004) * gs(Z - (L['m'].z + .018), .02)  # nasolabial
        v.co.y -= h * d
def wrinkles(me, P):
    """Age lines from the first test (BodyParts3D head), converted to metres."""
    if not P.get('age'): return
    a = P['age']
    def seg(x, z, p0, p1):
        dx, dz = p1[0] - p0[0], p1[1] - p0[1]
        t = min(1, max(0, ((x - p0[0]) * dx + (z - p0[1]) * dz) / (dx * dx + dz * dz)))
        return math.hypot(x - p0[0] - t * dx, z - p0[1] - t * dz)
    for v in me.vertices:
        X, Y, Z = v.co
        if Y > -.13 or Z < 1.46: continue
        x, z = X * 10, (Z - 1.62811) * 10; h = 0; j = noise.noise(V((x * 6, z * 3, 1)))
        for i, zz in enumerate((.06, .15, .24, .32)):
            h -= .011 * gs(z - zz - .018 * j - .012 * math.cos(x * 8 + i), .014) * sm(.48, .22, abs(x))
        for sd in (1, -1):
            for dz in (-.07, 0, .07):
                h -= .009 * gs(seg(x, z, (sd * .46, -.32 + dz * .3), (sd * .59, -.32 + dz)), .011)
            h -= .010 * gs(seg(x, z, (sd * .17, -.45), (sd * .38, -.43)), .015)
            h += .009 * gs(seg(x, z, (sd * .19, -.41), (sd * .37, -.40)), .025)
            h -= .012 * gs(seg(x, z, (sd * .20, -.69), (sd * .31, -.91)), .025)
        v.co.y -= h * a / 10

# ---------------------------------------------------------------- shaders (ported from the first test, metres)
class G:
    def __init__(s, name, blended=False):
        s.m = bpy.data.materials.new(name); s.m.use_nodes = True; s.m['_real'] = 1
        s.m.surface_render_method = 'BLENDED' if blended else 'DITHERED'
        s.t = s.m.node_tree; s.b = next(n for n in s.t.nodes if n.type == 'BSDF_PRINCIPLED')
        s.pos = s.n('Attribute', attribute_name='rest').outputs['Vector']   # stays put while the armature moves the mesh
    def n(s, typ, **kw):
        n = s.t.nodes.new('ShaderNode' + typ)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def put(s, sock, v):
        if isinstance(v, bpy.types.NodeSocket): s.t.links.new(v, sock)
        else: sock.default_value = v
    def set(s, **kw):
        for k, v in kw.items(): s.put(s.b.inputs[k.replace('_', ' ')], v)
    def math(s, op, a, b=None):
        n = s.n('Math', operation=op)
        for i, v in enumerate((a, b)):
            if v is not None: s.put(n.inputs[i], v)
        return n.outputs[0]
    def noise(s, scale, detail=3, vec=None):
        n = s.n('TexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
        s.put(n.inputs['Vector'], vec if vec else s.pos); return n.outputs[0]
    def vor(s, scale):
        n = s.n('TexVoronoi'); n.inputs['Scale'].default_value = scale; s.put(n.inputs['Vector'], s.pos); return n.outputs['Distance']
    def wave(s, scale, dist=2, vec=None):
        n = s.n('TexWave'); n.inputs['Scale'].default_value = scale; n.inputs['Distortion'].default_value = dist
        s.put(n.inputs['Vector'], vec if vec else s.pos); return n.outputs['Fac']
    def ramp(s, v, stops):
        n = s.n('ValToRGB'); e = n.color_ramp.elements
        while len(e) < len(stops): e.new(.5)
        for el, (p, c) in zip(e, stops): el.position = p; el.color = (*c, 1)
        s.put(n.inputs[0], v); return n.outputs[0]
    def step(s, v, a, b):
        n = s.n('MapRange', interpolation_type='SMOOTHSTEP')
        for i, x in enumerate((v, a, b)): s.put(n.inputs[i], x)
        return n.outputs[0]
    def mix(s, f, a, b, mode='MIX'):
        n = s.n('Mix', data_type='RGBA', blend_type=mode); s.put(n.inputs[0], f)
        for i, v in ((6, a), (7, b)): s.put(n.inputs[i], (*v, 1) if isinstance(v, tuple) else v)
        return n.outputs[2]
    def attr(s, name): return s.n('Attribute', attribute_name=name).outputs['Fac']
    def bump(s, h, strength=.2, d=.001):
        n = s.n('Bump'); n.inputs['Strength'].default_value = strength; n.inputs['Distance'].default_value = d
        s.put(n.inputs['Height'], h); s.put(s.b.inputs['Normal'], n.outputs[0])

def tone(c, k): return tuple(min(1, x * k) for x in c)
def skin_mat(P):
    g = G('skin_' + P['name']); t = P.get('tone', 1.0); old = P.get('age', 0)
    c = g.ramp(g.noise(50, 5), [(.3, tone((.30, .135, .08), t)), (.5, tone((.42, .22, .14), t)), (.72, tone((.50, .29, .19), t))])
    c = g.mix(g.math('MULTIPLY', g.step(g.noise(170, 2), .64, .72), .25 * old + .02), c, tone((.24, .10, .05), t))   # spots / freckles
    c = g.mix(g.math('MULTIPLY', g.step(g.noise(450, 3), .5, .75), .07), c, tone((.46, .11, .08), t))            # blotches
    c = g.mix(g.math('MULTIPLY', g.attr('cheek'), .35), c, tone((.55, .17, .12), t))                               # flushed cheeks / nose
    c = g.mix(g.math('MULTIPLY', g.attr('beard'), P.get('stubble', 0)), c, tone((.20, .14, .12), t * .9))         # shaved beard shadow
    c = g.mix(g.math('MULTIPLY', g.attr('lip'), .5), c, P.get('lipc', tone((.36, .13, .10), t)))
    c = g.mix(g.math('MULTIPLY', g.attr('mouth'), 1.0), c, (.05, .008, .008))
    g.set(Base_Color=c, Roughness=.47, Subsurface_Weight=.25, Subsurface_Scale=.009, Subsurface_Radius=(1, .35, .2), Specular_IOR_Level=.45)
    g.bump(g.math('ADD', g.vor(380), g.math('MULTIPLY', g.noise(900), .5)), .26, .0008)
    return g.m
def cloth_mat(name, col, var=.18, weave=900, rough=.85, sheen=.12, stripes=None, coat_front=False, flowers=False):
    g = G('cloth_' + name)
    c = g.ramp(g.noise(9, 4), [(.3, tone(col, 1 - var)), (.7, tone(col, 1 + var * .6))])
    if flowers:
        c = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, g.step(g.vor(55), .05, .14)), .9), c, (.85, .78, .55))
        c = g.mix(g.math('MULTIPLY', g.step(g.noise(70, 2), .6, .66), .8), c, (.70, .08, .10))
    if stripes:
        zc = g.n('SeparateXYZ'); g.put(zc.inputs[0], g.pos); z = zc.outputs['Z']
        for z0, w, sc in stripes:
            band = g.math('MULTIPLY', g.step(z, z0 - w, z0 - w + .002), g.math('SUBTRACT', 1.0, g.step(z, z0 + w - .002, z0 + w)))
            c = g.mix(band, c, sc)
    g.set(Base_Color=c, Roughness=rough, Sheen_Weight=sheen, Sheen_Roughness=.45)
    g.bump(g.math('ADD', g.wave(weave, 1), g.math('MULTIPLY', g.noise(14, 3), 6.0)), .22, .0012)
    return g.m
def hair_mat(name, root, tip, grey=0):
    g = G('hair_' + name); n = g.noise(190, 3)
    c = g.ramp(n, [(.36, tone(root, .6)), (.52, root), (.7, tip)])
    if grey: c = g.mix(g.math('MULTIPLY', g.step(g.noise(420, 2), .5, .62), grey), c, (.58, .56, .53))
    g.set(Base_Color=c, Roughness=.5, Sheen_Weight=.25)
    return g.m
def flat(name, col, rough=.4, **kw):
    g = G(name); g.set(Base_Color=(*col, 1), Roughness=rough, **kw); return g.m

# ---------------------------------------------------------------- helpers to make objects
COL = None
def new_obj(name, me, who, part):
    o = bpy.data.objects.new(name, me); COL.objects.link(o); o['who'] = who; o['part'] = part
    for p in me.polygons: p.use_smooth = True
    return o
def set_rest(o):
    a = o.data.attributes.get('rest') or o.data.attributes.new('rest', 'FLOAT_VECTOR', 'POINT')
    a.data.foreach_set('vector', [c for v in o.data.vertices for c in v.co])
def bind(o, arm, weights=None, bone=None):
    if bone:
        g = o.vertex_groups.new(name=bone); g.add(list(range(len(o.data.vertices))), 1, 'REPLACE')
    else:
        groups = {}
        for i, w in enumerate(weights):
            for n, x in w.items(): groups.setdefault(n, []).append((i, x))
        for n, lst in groups.items():
            g = o.vertex_groups.new(name=n)
            for i, x in lst: g.add([i], x, 'REPLACE')
    md = o.modifiers.new('arm', 'ARMATURE'); md.object = arm; o.parent = arm
def bt(i, bone):
    h, t, _ = SKEL[bone]; return segd(SV[i], h, t)[1]
WAIST = J['sp1'].z + .01
def region(kind, opt=None):
    out = set()
    for i, n in enumerate(DOM):
        b = n.rsplit('_', 1)[0] if n[-2:] in ('_l', '_r') else n; z = SV[i].z; ok = False
        if kind == 'top':
            nl = J['neck'].z + (.012 if opt == 'collar' else -.012) - (.035 if SV[i].y < -.09 and opt != 'collar' else 0) * gs(SV[i].x, .05)
            ok = (b in ('spine_01', 'spine_02', 'spine_03', 'clavicle', 'neck_01') or (b == 'pelvis' and z > WAIST - .085)) and z < nl
            if b == 'upperarm': ok = opt != 'short' or bt(i, n) < .55
            if b == 'lowerarm': ok = opt != 'short' and bt(i, n) < .94
        elif kind == 'pants':
            ok = b == 'thigh' or (b == 'calf' and bt(i, n) < .93) or (b == 'pelvis' and z <= WAIST + .03)
        elif kind == 'shoes':
            ok = b in ('foot', 'ball') or (b == 'calf' and bt(i, n) >= .9)
        elif kind == 'scarf':
            p = SV[i]; top = L['brow_l'].z + .022; zc = (top + L['chin'].z) / 2
            inface = p.y < L['ear'].y - .015 and (p.x / .064) ** 2 + ((p.z - zc) / ((top - L['chin'].z) / 2 + .004)) ** 2 < 1
            ok = (b == 'head' or (b == 'neck_01' and z > J['neck'].z + .02)) and not inface and z > L['chin'].z - .03
        if ok: out.add(i)
    return out

DRAPE = [None]
def shell(name, who, arm, PD, sel, off, smooth, mat, fold=.004, thick=.002, cut=None):
    """Garment = the body's own surface in that region, relaxed, pushed out, folded and thickened."""
    me0 = skin0.data; bm = bmesh.new(); idx = {}; src = []
    for poly in me0.polygons:
        vs = poly.vertices
        if not all(v in sel for v in vs): continue
        if cut and cut(SV[vs[0]]): continue
        for v in vs:
            if v not in idx: idx[v] = bm.verts.new(PD[v]); src.append(v)
        try: bm.faces.new([idx[v] for v in vs])
        except ValueError: pass
    bm.verts.ensure_lookup_table()
    bnd = [v for v in bm.verts if v.is_boundary]
    tree = DRAPE[0]
    for rnd in range(3):
        for _ in range(smooth): bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        for _ in range(16): bmesh.ops.smooth_vert(bm, verts=bnd, factor=.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        for v, s_ in zip(bm.verts, src):
            q, n_, _, _ = tree.find_nearest(v.co)
            if q is None: continue
            r = SV[s_]
            f = 0 if v.is_boundary else fold * (noise.noise(V((r.x * 9, r.y * 9, r.z * 3))) + .5 * noise.noise(r * 31))
            tgt = off + max(0, f) * (rnd == 2); d = (v.co - q).dot(n_)
            if d < tgt: v.co += n_ * (tgt - d)
    bm.normal_update()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = new_obj(f'{who}.{name}', me, who, 'suit'); me.materials.append(mat)
    a = me.attributes.new('rest', 'FLOAT_VECTOR', 'POINT'); a.data.foreach_set('vector', [c for s_ in src for c in SV[s_]])
    sd = o.modifiers.new('thick', 'SOLIDIFY'); sd.thickness = thick; sd.offset = 1
    bind(o, arm, [W[s_] for s_ in src])
    o.modifiers.move(len(o.modifiers) - 1, 0)
    return o

def skirt(name, who, arm, P, PD, z0, z1, mat, flare=.05, open_front=False, n=56):
    """Tube garment (dress / coat hem) around hips and legs."""
    hs = P.get('h', 1); bm = bmesh.new(); rings = []; rows = 26
    for r in range(rows):
        u = r / (rows - 1); z = z0 + (z1 - z0) * u
        q = [PD[i] / hs for i in range(NV) if abs(SV[i].z - z) < .006 and REG[i] in ('torso', 'leg_l', 'leg_r')]
        cy = (max(p.y for p in q) + min(p.y for p in q)) / 2; rx = max(abs(p.x) for p in q) + .012 + flare * u
        ry = (max(p.y for p in q) - min(p.y for p in q)) / 2 + .015 + flare * .7 * u
        ring = []
        for k in range(n):
            a = 2 * math.pi * (k + .5) / n
            ring.append(bm.verts.new(V((rx * math.sin(a), cy - ry * math.cos(a), z)) * hs))
        rings.append(ring)
    for r in range(rows - 1):
        for k in range(n):
            if open_front and k == n - 1: continue          # gap at the front centre (k=n-1 -> 0 wraps there)
            a, b = rings[r][k], rings[r][(k + 1) % n]; c, d = rings[r + 1][(k + 1) % n], rings[r + 1][k]
            bm.faces.new((a, b, c, d))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = new_obj(f'{who}.{name}', me, who, 'suit'); me.materials.append(mat); set_rest(o)
    ws = []
    for v in me.vertices:
        u = (z0 * hs - v.co.z) / ((z0 - z1) * hs); side = 'l' if v.co.x > 0 else 'r'; lat = min(1, abs(v.co.x) / (.12 * hs))
        k = sm(0, 1, u) * .75 * (.3 + .7 * lat)
        ws.append({'pelvis': 1 - k, 'thigh_' + side: k})
    sd = o.modifiers.new('thick', 'SOLIDIFY'); sd.thickness = .002; sd.offset = 1
    bind(o, arm, ws); o.modifiers.move(len(o.modifiers) - 1, 0)
    return o

def tris(me, keep=lambda p: True, P=None):
    me.calc_loop_triangles(); out = []
    for t in me.loop_triangles:
        cs = [P[i] if P else me.vertices[i].co.copy() for i in t.vertices]
        if all(keep(c) for c in cs):
            nr = (cs[1] - cs[0]).cross(cs[2] - cs[0])
            if nr.length > 1e-12: out.append((*cs, nr.normalized()))
    return out

def strands(src_tris, name, who, arm, mat, count, length, width, comb, segs=4, surf=None, stick=99, seed=1, lift=.0012):
    """Hair as many thin tubes. comb(p, n) gives the growth direction; surf keeps them on/outside the head."""
    rr = random.Random(seed)
    cv = bpy.data.curves.new(name, 'CURVE'); cv.dimensions = '3D'; cv.bevel_depth = width; cv.bevel_resolution = 0; cv.resolution_u = 1
    areas = [((b - a).cross(c - a)).length + 1e-12 for a, b, c, nr in src_tris]
    for a, b, c, nr in rr.choices(src_tris, weights=areas, k=count):
        u, v = rr.random(), rr.random()
        if u + v > 1: u, v = 1 - u, 1 - v
        p = a + (b - a) * u + (c - a) * v; n = nr.copy(); L_ = length * rr.uniform(.65, 1.3); out = [p + n * lift * .5]
        for i in range(segs):
            d = comb(p, n)
            if i < stick: d = d - n * d.dot(n)
            d = d.normalized() + noise.noise_vector(p * 40 + V((seed, 0, 0))) * .35
            p = p + d.normalized() * L_ / segs
            if surf:
                q = surf.find_nearest(p)
                if q[0] is not None:
                    if i < stick: p, n = q[0] + q[1] * lift * (1 + i * .5), q[1]
                    elif (p - q[0]).dot(q[1]) < .006: p = q[0] + q[1] * .006
            out.append(p.copy())
        sp = cv.splines.new('POLY'); sp.points.add(len(out) - 1)
        for i, q in enumerate(out):
            sp.points[i].co = (*q, 1); sp.points[i].radius = 1 - .75 * i / len(out)
    cv.materials.append(mat)
    tmp = bpy.data.objects.new(name, cv); S.collection.objects.link(tmp); bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cv)
    o = new_obj(f'{who}.{name}', me, who, name); me.materials.clear(); me.materials.append(mat); set_rest(o)
    bind(o, arm, bone='head')
    return o

# ---------------------------------------------------------------- face shapes (ARKit names the animation code already uses)
def face_fields(LC, hs):
    pv = LC['pivot']; m = LC['m']; ch = LC['chin']; k = hs
    def rotx(p, a, c):
        r = p - c; ca, sa = math.cos(a), math.sin(a)
        return c + V((r.x, r.y * ca - r.z * sa, r.y * sa + r.z * ca))
    def jaw_w(p, kind):
        if kind == 2: return 1.0
        if kind == 1: return 0.0
        if kind == 3: return sm(m.z + .004 * k, m.z - .012 * k, p.z)
        wv = sm(m.z + .0015 * k, m.z - .006 * k, p.z)
        wl = 1 - sm(.042 * k, .075 * k, abs(p.x))
        wy = sm(pv.y + .015 * k, pv.y - .02 * k, p.y)
        wn = sm(-.04 * k, -.008 * k, (p.z - ch.z) + (p.y - ch.y) * -.7)
        return wv * wl * wy * wn
    def front(p, c, d=.02): return 1.0 if p.y < c.y + d * k else 0.0
    def G3(p, c, r): return math.exp(-((p - c).length / (r * k)) ** 2)
    F = {}
    F['jawOpen'] = lambda p, kd: rotx(p, math.radians(19) * jaw_w(p, kd), pv) - p
    F['jawLeft'] = lambda p, kd: V((.006 * k * jaw_w(p, kd), 0, 0))
    for s, sd, Sd in ((1, 'l', 'Left'), (-1, 'r', 'Right')):
        c = LC['c' + sd]; E = LC['eye_' + sd]; r = LC['er_' + sd]
        F['mouthSmile' + Sd] = (lambda c, s: lambda p, kd: (V((s * .007, .005, .010)) * k * G3(p, c, .018) + V((0, -.003, .003)) * k * G3(p, c + V((s * .014, .0, .022)) * 1, .02)) * front(p, c) if kd == 0 else V())(c, s)
        F['mouthFrown' + Sd] = (lambda c, s: lambda p, kd: V((s * .0015, .0, -.0075)) * k * G3(p, c, .016) * front(p, c) if kd == 0 else V())(c, s)
        F['mouthStretch' + Sd] = (lambda c, s: lambda p, kd: V((s * .007, .002, -.002)) * k * G3(p, c, .017) * front(p, c) if kd == 0 else V())(c, s)
        F['cheekSquint' + Sd] = (lambda E, s: lambda p, kd: V((0, -.001, .004)) * k * G3(p, E + V((s * .006, -.004, -.026)) * 1, .016) if kd == 0 else V())(E, s)
        def lid(p, kd, E=E, r=r, amt=-.78):
            if kd != 0 or p.y > E.y - r * .25: return V()
            dx, dz = p.x - E.x, p.z - E.z
            if dz < -.001 * k: return V()
            w = gs(dx, .017 * k) * (1.0 if dz < .006 * k else gs(dz - .006 * k, .009 * k))
            q = p + V((0, 0, amt * r * w))
            d = q - E
            if d.length < r + .0014 * k: q = E + d.normalized() * (r + .0014 * k)
            return q - p
        F['eyeBlink' + Sd] = lid
        F['eyeWide' + Sd] = (lambda E, r: lambda p, kd: lid(p, kd, E, r, .22))(E, r)
        def low(p, kd, E=E, r=r):
            if kd != 0 or p.y > E.y - r * .25: return V()
            dx, dz = p.x - E.x, p.z - E.z
            if dz > .001 * k: return V()
            return V((0, -.0006, .0032)) * k * gs(dx, .016 * k) * gs(dz + .006 * k, .008 * k)
        F['eyeSquint' + Sd] = (lambda low, lid: lambda p, kd: low(p, kd) + lid(p, kd) * .18)(low, lid)
        F['browDown' + Sd] = (lambda b, s: lambda p, kd: V((-s * .002, -.001, -.0055)) * k * G3(p, b, .024) if kd == 0 else V())(LC['brow_' + sd], s)
        F['browOuterUp' + Sd] = (lambda b: lambda p, kd: V((0, 0, .0075)) * k * G3(p, b, .02) if kd == 0 else V())(LC['browout_' + sd])
    F['browInnerUp'] = lambda p, kd: (V((0, 0, .0075)) * k * (G3(p, LC['browin_l'], .018) + G3(p, LC['browin_r'], .018))) if kd == 0 else V()
    gm = lambda p: math.exp(-(((p.x - m.x) / (.032 * k)) ** 2 + ((p.z - m.z) / (.018 * k)) ** 2)) * (1.0 if p.y < m.y + .022 * k else 0.0)
    F['mouthLeft'] = lambda p, kd: V((.007 * k * gm(p), 0, 0)) if kd == 0 else V()
    F['mouthPucker'] = lambda p, kd: V((-(p.x - m.x) * .35, -.006 * k, 0)) * gm(p) if kd == 0 else V()
    F['mouthFunnel'] = lambda p, kd: (V((-(p.x - m.x) * .2, -.004 * k, (.002 if p.z > m.z else -.003) * k)) * gm(p)) if kd == 0 else V()
    F['mouthPressLeft'] = F['mouthPressRight'] = lambda p, kd: V((0, 0, (-.0012 if p.z > m.z else .0012) * k)) * gm(p) if kd == 0 else V()
    cr = LC['cr']
    F['mouthLowerDownRight'] = lambda p, kd: V((0, 0, -.005 * k)) * G3(p, V((cr.x * .5, m.y, m.z - .007 * k)), .014) * (1.0 if p.z < m.z else 0) if kd == 0 else V()
    def palsy(p, kd):
        if kd != 0 or p.y > m.y + .075 * k: return V()
        dx, dz = p.x - cr.x, p.z - cr.z
        c = math.exp(-(dx / (.021 * k)) ** 2 - (dz / (.019 * k)) ** 2)
        j = math.exp(-((dx + .014 * k) / (.022 * k)) ** 2 - ((dz - .014 * k) / (.026 * k)) ** 2)
        return V((.004 * c, .001 * c, -.0125 * c - .004 * j)) * k
    F['palsyRight'] = palsy
    return F

def add_keys(o, F, kinds=None, box=None):
    me = o.data; base = [v.co.copy() for v in me.vertices]
    if not me.shape_keys: o.shape_key_add(name='Basis')
    for name, f in F.items():
        flat_ = []; mx = 0
        for i, p in enumerate(base):
            d = f(p, kinds[i] if kinds else 0) if (box is None or box(p)) else V()
            mx = max(mx, d.length); q = p + d; flat_ += (q.x, q.y, q.z)
        if mx < 1e-5: continue
        kb = o.shape_key_add(name=name, from_mix=False); kb.data.foreach_set('co', flat_); kb.value = 0

# ---------------------------------------------------------------- the cast
U = (.38, .15, .07)
CAST = {
 'patient':  dict(h=.99, girth=1.05, belly=.02, age=2.0, nose=1.16, jaw=1.0, fw=1.02, flen=1.03, cheek=-.002, chin=.002, brow=-.002, tone=.92, stubble=.35,
                  hair=('back', (.06, .055, .05), (.27, .25, .23), .35), brows=(.12, .10, .085), moustache=True, iris=(.14, .07, .03),
                  wear=[('top', 'collar', (.20, .075, .035), .006), ('pants', None, (.025, .025, .03), .009), ('shoes', None, (.03, .02, .015), .006)]),
 'wife':     dict(h=.93, fem=1, girth=1.08, belly=.015, age=1.3, nose=1.08, jaw=.95, fw=1.06, flen=.95, cheek=.004, lips=.001, tone=1.02, lipc=(.36, .10, .09),
                  scarf=(.06, .10, .32), brows=(.14, .10, .08), iris=(.10, .05, .02),
                  wear=[('top', None, (.45, .05, .12), .007), ('skirt', 'ankle', (.10, .05, .09), 0), ('shoes', None, (.05, .03, .02), .006)]),
 'son':      dict(h=1.02, girth=1.0, nose=1.1, jaw=1.08, chin=.003, fw=.96, flen=1.06, cheek=-.002, browz=.002, tone=.98, stubble=.45,
                  hair=('side', (.03, .022, .018), (.07, .05, .04), 0), brows=(.04, .03, .025), iris=(.08, .04, .02),
                  wear=[('top', None, (.06, .20, .10), .010), ('pants', None, (.03, .06, .14), .010), ('shoes', None, (.30, .25, .20), .006)]),
 'daughter': dict(h=.95, fem=1, girth=.94, nose=.92, jaw=.90, fw=.95, flen=.95, lips=.0025, cheek=.002, tone=1.04, lipc=(.40, .11, .10),
                  hair=('long', (.06, .03, .016), (.14, .07, .035), 0), brows=(.06, .035, .02), iris=(.10, .05, .02),
                  wear=[('top', None, (.85, .50, .12), .008), ('pants', None, (.03, .06, .16), .009), ('shoes', None, (.8, .8, .78), .006)]),
 'doc':      dict(h=1.01, girth=.98, nose=1.22, jaw=1.04, brow=-.003, fw=.94, flen=1.08, cheek=-.003, tone=1.0, stubble=.3,
                  hair=('side', (.025, .02, .017), (.06, .045, .035), .15), brows=(.04, .03, .025), iris=(.07, .035, .015),
                  wear=[('top', 'short', (.015, .30, .33), .006), ('coat', None, (.86, .88, .88), .018), ('pants', None, (.015, .30, .33), .009),
                        ('shoes', None, (.85, .86, .86), .006)]),
 'doc2':     dict(h=.96, fem=1, girth=.95, nose=.95, jaw=.92, fw=1.0, flen=.97, lips=.002, browz=.002, tone=1.03, lipc=(.38, .11, .10),
                  hair=('bun', (.03, .016, .01), (.08, .045, .025), 0), brows=(.04, .025, .015), iris=(.06, .03, .012),
                  wear=[('top', 'short', (.015, .30, .33), .007), ('pants', None, (.015, .30, .33), .009), ('shoes', None, (.85, .86, .86), .006)]),
 'medic1':   dict(h=1.01, girth=1.02, nose=1.14, jaw=1.14, chin=.004, fw=1.04, flen=1.0, cheek=.002, brow=-.003, tone=.97, stubble=.5,
                  hair=('short', (.04, .025, .018), (.08, .05, .035), 0), brows=(.05, .035, .025), iris=(.09, .045, .02),
                  wear=[('top', 'collar', (.75, .04, .025), .012, 'jacket'), ('pants', None, (.012, .022, .06), .010, 'legstripe'),
                        ('shoes', None, (.02, .02, .02), .008)]),
 'medic2':   dict(h=.98, girth=1.08, belly=.012, nose=1.28, jaw=1.1, fw=1.1, flen=.94, cheek=.005, lips=.0015, age=.5, tone=.94, stubble=.6,
                  hair=('short', (.02, .016, .012), (.05, .035, .025), 0), brows=(.03, .022, .018), iris=(.05, .025, .01),
                  wear=[('top', 'collar', (.75, .04, .025), .012, 'jacket'), ('pants', None, (.012, .022, .06), .010, 'legstripe'),
                        ('shoes', None, (.02, .02, .02), .008)]),
}

def comb_for(style, LC, hs):
    top = LC['eye_l'].z + .06 * hs
    if style == 'back':
        return lambda p, n: V((p.x * 2.5, 1.0, -.35)) if p.z > top else V((p.x * .5, .5, -1))
    if style in ('side', 'short'):
        part = .025 * hs
        return lambda p, n: (V((-1 if p.x < part else .4, .5, -.4)) if p.z > top else V((math.copysign(.2, p.x), .4, -1)))
    if style in ('long', 'bun'):
        return lambda p, n: V((math.copysign(.6, p.x) if style == 'long' else p.x * 3, .9 if style == 'bun' else .25, -1 if style == 'long' else -.2))
    return lambda p, n: V((0, 0, -1))

def build(name, P):
    global COL
    P = dict(P, name=name); hs = P.get('h', 1)
    COL = bpy.data.collections.new('C_' + name); S.collection.children.link(COL)
    # deformed copies of every point (skin, parts, joints, landmarks)
    PD = [deform(p, REG[i], P) for i, p in enumerate(SV)]
    LC = {k: (deform(v, 'head', P) if isinstance(v, V) else v * hs) for k, v in L.items()}
    # armature
    ad = bpy.data.armatures.new(name); arm = bpy.data.objects.new(name, ad); COL.objects.link(arm); arm['who'] = name
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    reg_b = lambda n: region_of(n) if not n.startswith('clavicle') else 'torso'
    for n, (h, t, par) in SKEL.items():
        eb = ad.edit_bones.new(n); r = reg_b(n) if n != 'Root' else 'torso'
        eb.head = deform(h, r, P) if n != 'Root' else h * hs; eb.tail = deform(t, r, P) if n != 'Root' else t * hs
        if par: eb.parent = ad.edit_bones[par]
    bpy.ops.object.mode_set(mode='OBJECT')
    # body skin: wrinkles on the base shape, then the character's proportions
    me = skin0.data.copy(); me.name = name + '_skin'
    wrinkles(me, P); define(me, P)
    for i, v in enumerate(me.vertices): v.co = deform(v.co, REG[i], P)
    body = new_obj(name + '.body', me, name, 'body')
    # attributes for the shader (computed on the base face)
    lipT = BVHTree.FromPolygons([v.co for v in BASE['lip'].data.vertices], [p.vertices[:] for p in BASE['lip'].data.polygons])
    att = {k: me.attributes.new(k, 'FLOAT', 'POINT') for k in ('lip', 'beard', 'cheek', 'mouth')}
    for i, p in enumerate(SV):
        if p.z < 1.44 or p.y > -.08: continue
        if abs(p.x) < .045 and abs(p.z - L['m'].z) < .022:
            hit = lipT.find_nearest(p)
            if hit[0]: att['lip'].data[i].value = 1 - sm(.0012, .0045, hit[3])
        bz = (L['chin'].z - .02 < p.z < L['m'].z + .022 and abs(p.x) < .07 and p.y < L['ear'].y - .01) and not (abs(p.x) < .03 and abs(p.z - L['m'].z) < .008)
        if bz: att['beard'].data[i].value = sm(L['m'].z + .022, L['m'].z + .005, p.z) if abs(p.x) > .03 else 1.0
        att['cheek'].data[i].value = .7 * (gs((p - (L['eye_l'] + V((.012, -.01, -.035)))).length, .02) + gs((p - (L['eye_r'] + V((-.012, -.01, -.035)))).length, .02)) \
            + .5 * gs((p - L['nose']).length, .012)
        if p.y > L['m'].y + .013 and abs(p.x) < L['cl'].x - .002 and abs(p.z - L['m'].z) < .005: att['mouth'].data[i].value = 1
    # garments
    bmS = bmesh.new(); vS = [bmS.verts.new(p) for p in PD]
    for poly in skin0.data.polygons:
        try: bmS.faces.new([vS[i] for i in poly.vertices])
        except ValueError: pass
    for _ in range(30): bmesh.ops.smooth_vert(bmS, verts=bmS.verts, factor=.7, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmS.normal_update(); DRAPE[0] = BVHTree.FromBMesh(bmS); bmS.free()
    covered = set(); outfit = []
    for w in P['wear']:
        kind, opt, col, off = w[:4]; tag = w[4] if len(w) > 4 else ''
        if kind == 'skirt':
            m = cloth_mat(name + '_skirt', col, .15, 700)
            outfit.append(skirt('skirt', name, arm, P, PD, WAIST + .02, (.085 if opt == 'ankle' else .40) * H, m, .07)); continue
        if kind == 'coat':
            m = cloth_mat(name + '_coat', col, .05, 1100, .7, .1)
            sel = region('top')
            outfit.append(shell('coat', name, arm, PD, sel, off, 6, m, .006, .0025, cut=lambda p: abs(p.x) < .012 and p.y < -.09 and p.z < J['neck'].z - .01))
            outfit.append(skirt('coathem', name, arm, P, PD, WAIST - .07, .40 * H, m, .06, open_front=True)); continue
        stripes = None
        if tag == 'jacket': stripes = [(1.06 * hs, .012, (.78, .80, .72)), (1.085 * hs, .010, (.95, .82, .12)), (1.20 * hs, .012, (.78, .80, .72))]
        if tag == 'legstripe': stripes = [(.30 * hs, .012, (.78, .80, .72)), (.33 * hs, .009, (.95, .82, .12))]
        m = cloth_mat(f'{name}_{kind}', col, .14, 900 if kind != 'shoes' else 300, .85 if kind != 'shoes' else .35, .12 if kind != 'shoes' else 0, stripes)
        sel = region(kind, opt); covered |= sel
        sm_ = {'top': 8, 'pants': 8, 'shoes': 10}[kind]
        outfit.append(shell(kind, name, arm, PD, sel, off, sm_, m, .0035 if kind != 'shoes' else .001))
    if any(w[0] == 'skirt' for w in P['wear']):
        covered |= {i for i in range(NV) if REG[i] in ('leg_l', 'leg_r') and SV[i].z > .12 or (DOM[i] == 'pelvis' and SV[i].z < WAIST)}
    if any(w[0] == 'coat' for w in P['wear']): covered |= region('top')
    # remove hidden skin (no poke-through, lighter scenes)
    for _ in range(3):
        edge = {i for i in covered if any(j not in covered for j in ADJ[i])}
        covered -= edge
    keep = [i for i in range(NV) if i not in covered]
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in covered], context='VERTS'); bm.to_mesh(me); bm.free()
    Wk = [W[i] for i in keep]; Pk = [SV[i] for i in keep]
    a = me.attributes.new('rest', 'FLOAT_VECTOR', 'POINT'); a.data.foreach_set('vector', [c for p in Pk for c in p])
    me.materials.append(skin_mat(P))
    # teeth and mouth interior join the body (the jaw shape moves the lower teeth)
    extra = []
    for g_, kd, mat in (('tooth_up', 1, flat('teeth', (.80, .74, .62), .25)), ('tooth_lo', 2, None)):
        tm = BASE[g_].data.copy()
        for v in tm.vertices: v.co = deform(v.co, 'head', P)
        to = bpy.data.objects.new('t', tm); COL.objects.link(to); tm.materials.append(bpy.data.materials['teeth'] if mat is None else mat)
        extra.append((to, kd, len(tm.vertices)))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=20, ring_count=12, location=LC['m'] + V((0, .047, -.004)) * hs)
    bag = bpy.context.object; bag.scale = V((.022, .026, .015)) * hs; bpy.ops.object.transform_apply(scale=True)
    for c_ in list(bag.users_collection): c_.objects.unlink(bag)
    COL.objects.link(bag); bag.data.materials.append(flat('mouth', (.09, .015, .015), .6)); extra.append((bag, 3, len(bag.data.vertices)))
    kinds = [0] * len(me.vertices); wts = list(Wk)
    for o_, kd, nv in extra:
        kinds += [kd] * nv; wts += [{'head': 1.0}] * nv
        ra = o_.data.attributes.new('rest', 'FLOAT_VECTOR', 'POINT'); ra.data.foreach_set('vector', [c for v in o_.data.vertices for c in v.co])
    bpy.ops.object.select_all(action='DESELECT')
    for o_, _, _ in extra: o_.select_set(True)
    body.select_set(True); bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
    fbox = lambda p: p.z > LC['chin'].z - .06 * hs and p.y < LC['ear'].y + .02 * hs
    F = face_fields(LC, hs)
    add_keys(body, F, kinds, fbox)
    bind(body, arm, wts)
    # eyes (static in the head)
    for sd in 'lr':
        gS = G('sclera_' + sd); gS.set(Roughness=.15, Base_Color=gS.ramp(gS.noise(140, 5), [(.4, (.62, .56, .50)), (.75, (.55, .32, .27))]))
        gI = G('iris_' + sd); ic_ = P['iris']; gI.set(Roughness=.2, Base_Color=gI.ramp(gI.noise(550, 3), [(.3, tone(ic_, .25)), (.7, tone(ic_, 1.2))]))
        for part, mat in (('sclera', gS.m), ('iris', gI.m), ('cornea', None)):
            em = BASE[f'{part}_{sd}'].data.copy()
            for v in em.vertices: v.co = deform(v.co, 'head', P)
            eo = new_obj(f'{name}.{part}_{sd}', em, name, 'eyes')
            if mat is None:
                mat = flat('cornea', (0, 0, 0), .02, Alpha=.12); mat.surface_render_method = 'BLENDED'
            em.materials.append(mat); set_rest(eo); bind(eo, arm, bone='head')
        ic = centroid(pts(BASE['iris_' + sd])); iy = min(p.y for p in pts(BASE['iris_' + sd]))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=16, ring_count=8, location=deform(V((ic.x, iy + .0012, ic.z)), 'head', P))
        pu = bpy.context.object; pu.scale = V((.0026, .0008, .0026)) * hs; bpy.ops.object.transform_apply(scale=True)
        for c_ in list(pu.users_collection): c_.objects.unlink(pu)
        COL.objects.link(pu); pu['who'] = name; pu['part'] = 'eyes'; pu.data.materials.append(flat('pupil', (0, 0, 0), .05)); set_rest(pu); bind(pu, arm, bone='head')
    # hair, brows, lashes, moustache (strands follow the same face shapes)
    hairM = BASE['hair'].data
    HP = [deform(v.co, 'head', P) for v in hairM.vertices]
    headT = BVHTree.FromPolygons([PD[i] for i in range(NV)], [p.vertices[:] for p in skin0.data.polygons])
    hz = P.get('hair')
    if hz:
        style, root, tip, grey = hz
        hm = hair_mat(name, root, tip, grey)
        T = tris(hairM, P=HP)
        cfg = {'back': (9000, .045, 4, 99), 'side': (9000, .05, 4, 99), 'short': (9000, .028, 3, 99), 'long': (7000, .34, 9, 3), 'bun': (8000, .06, 4, 99)}[style]
        strands(T, 'hair', name, arm, hm, cfg[0], cfg[1] * hs, .00028 * hs, comb_for(style, LC, hs), cfg[2], headT, cfg[3], seed=len(name))
        if style == 'bun':
            bc = LC['eye_l'] * V((0, 1, 1)) + V((0, .16, .05)) * hs
            bpy.ops.mesh.primitive_uv_sphere_add(radius=.042 * hs, segments=24, ring_count=12, location=bc)
            bo = bpy.context.object
            for c_ in list(bo.users_collection): c_.objects.unlink(bo)
            COL.objects.link(bo); bo['who'] = name; bo['part'] = 'hair'; bo.scale = (1, .8, .85)
            bo.data.materials.append(hm); set_rest(bo); bind(bo, arm, bone='head')
    if P.get('scarf'):
        m = cloth_mat(name + '_scarf', P['scarf'], .5, 800, .8, .3, flowers=True)
        sc = shell('scarf', name, arm, PD, region('scarf'), .014 * hs, 8, m, .003)
        for g_ in list(sc.vertex_groups): sc.vertex_groups.remove(g_)
        sc.modifiers.remove(sc.modifiers['arm']); bind(sc, arm, bone='head')
    bm_ = hair_mat(name + '_brow', P['brows'], tone(P['brows'], 1.6))
    BP = [deform(v.co, 'head', P) for v in BASE['brow'].data.vertices]
    for g_, colr in (('brow', tone(P['brows'], .7)), ('hair', tone(hz[1], .8) if hz else None)):
        if colr is None or (g_ == 'hair' and P.get('scarf')): continue
        bm2 = BASE[g_].data.copy(); cen = LC['eye_l'] * V((0, 1, 1)) + V((0, .07, 0))
        for v in bm2.vertices:
            q = deform(v.co, 'head', P); v.co = q - (q - cen).normalized() * (.0004 if g_ == 'brow' else .0008)
        bo2 = new_obj(f'{name}.{g_}_base', bm2, name, 'brow' if g_ == 'brow' else 'hair')
        bm2.materials.append(flat(f'{g_}base_{name}', colr, .7)); set_rest(bo2); bind(bo2, arm, bone='head')
        if g_ == 'brow': add_keys(bo2, F)
    br = strands(tris(BASE['brow'].data, P=BP), 'brow', name, arm, bm_, 1300, .007 * hs, .00016 * hs,
                 lambda p, n: V((math.copysign(1, p.x), 0, .35)), 2, headT, seed=3)
    add_keys(br, F)
    # eyelashes along the upper lid opening
    for sd in 'lr':
        E = LC['eye_' + sd]; r = LC['er_' + sd]
        lt = [t for t in tris(skin0.data, P=PD) if all((q - E).length < r + .006 * hs and q.z > E.z + r * .15 and q.y < E.y - r * .3 for q in t[:3])]
        if lt:
            la = strands(lt, 'lash_' + sd, name, arm, flat('lash', (.01, .008, .006), .5), 70, .007 * hs, .00007 * hs,
                         lambda p, n: V((0, -1, .7)), 2, None, 0, seed=5)
            add_keys(la, {k: F[k] for k in F if k.startswith(('eyeBlink', 'eyeWide', 'eyeSquint'))})
    if P.get('moustache'):
        mt = [t for t in tris(skin0.data, P=PD) if all(abs(q.x) < LC['cl'].x + .004 * hs and LC['m'].z + .0035 * hs < q.z < LC['nose'].z - .012 * hs
                                                       and q.y < LC['m'].y + .02 * hs for q in t[:3])]
        mm = hair_mat(name + '_moust', (.06, .05, .045), (.30, .28, .26), .5)
        mo = strands(mt, 'moustache', name, arm, mm, 800, .011 * hs, .00018 * hs,
                     lambda p, n: V((math.copysign(.45, p.x), -.35, -1)), 3, headT, 1, seed=7)
        add_keys(mo, F)
    log('built', name, 'body verts', len(body.data.vertices), 'objects', len(COL.objects))
    return arm

ARMS = {}
for nm, P in CAST.items():
    if ONLY and nm not in ONLY: continue
    ARMS[nm] = build(nm, P)
for o in list(BASE.values()): bpy.data.objects.remove(o)
out = ROOT + ('/cast_scan_test.blend' if ONLY else '/cast.blend')
bpy.ops.wm.save_as_mainfile(filepath=out)
json.dump({n: {b.name: [list(b.head_local), list(b.tail_local), b.parent.name if b.parent else None] for b in a.data.bones} for n, a in ARMS.items()},
          open(ROOT + ('/bones_test.json' if ONLY else '/bones.json'), 'w'))
log('saved', out)
