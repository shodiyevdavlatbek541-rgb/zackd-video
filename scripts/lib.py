"""Small animation toolkit: materials, modelling helpers, FK/IK poser, faces, camera."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Quaternion, noise

FPS = 30
V = Vector
RX = lambda d: Quaternion((1, 0, 0), math.radians(d))
RY = lambda d: Quaternion((0, 1, 0), math.radians(d))
RZ = lambda d: Quaternion((0, 0, 1), math.radians(d))
FONT = {'b': 'C:/Windows/Fonts/seguibl.ttf', 'r': 'C:/Windows/Fonts/segoeuib.ttf', 's': 'C:/Windows/Fonts/georgiab.ttf'}

def ss(a, b, x):
    t = min(1, max(0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def lerp(a, b, t): return a + (b - a) * t

def track(keys, t):
    """Eased interpolation through [(t, value)]; value is a number or Vector."""
    if t <= keys[0][0]: return keys[0][1]
    for (a, x), (b, y) in zip(keys, keys[1:]):
        if t <= b: return lerp(x, y, ss(a, b, t))
    return keys[-1][1]

# ---------- materials
_M = {}
def mat(col, rough=.6, emit=0, metal=0, alpha=1, coat=0):
    key = (tuple(col), rough, emit, metal, alpha, coat)
    if key in _M: return _M[key]
    m = bpy.data.materials.new('m%d' % len(_M)); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    for k, v in (('Base Color', (*col, 1)), ('Roughness', rough), ('Metallic', metal), ('Alpha', alpha), ('Coat Weight', coat)):
        b.inputs[k].default_value = v
    if emit:
        b.inputs['Emission Color'].default_value = (*col, 1); b.inputs['Emission Strength'].default_value = emit
    if alpha < 1: m.surface_render_method = 'BLENDED'
    _M[key] = m
    return m

def pattern(kind, stops, scale=(5, 5, 5), rough=.6, bump=0, coord='Object', coat=0):
    m = bpy.data.materials.new(kind); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = scale
    L.new(tc.outputs[coord], mp.inputs[0])
    if kind == 'noise':
        t = N.new('ShaderNodeTexNoise'); t.inputs['Scale'].default_value = 1; t.inputs['Detail'].default_value = 4
        L.new(mp.outputs[0], t.inputs[0]); out = t.outputs[0]
    elif kind == 'voronoi':
        t = N.new('ShaderNodeTexVoronoi'); t.inputs['Scale'].default_value = 1; t.distance = 'MANHATTAN'
        L.new(mp.outputs[0], t.inputs[0]); out = t.outputs['Distance']
    elif kind == 'wave':
        t = N.new('ShaderNodeTexWave'); t.inputs['Scale'].default_value = 1; t.inputs['Distortion'].default_value = 4
        L.new(mp.outputs[0], t.inputs[0]); out = t.outputs['Fac']
    r = N.new('ShaderNodeValToRGB'); e = r.color_ramp.elements
    while len(e) < len(stops): e.new(.5)
    for el, (p, c) in zip(e, stops): el.position = p; el.color = (*c, 1)
    L.new(out, r.inputs[0]); L.new(r.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough; b.inputs['Coat Weight'].default_value = coat
    if bump:
        bn = N.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = bump; bn.inputs['Distance'].default_value = .02
        L.new(out, bn.inputs['Height']); L.new(bn.outputs[0], b.inputs['Normal'])
    return m

# ---------- modelling
def link(o, parent=None):
    bpy.context.scene.collection.objects.link(o)
    if parent: o.parent = parent
    return o

def empty(loc=(0, 0, 0), parent=None):
    o = link(bpy.data.objects.new('E', None), parent); o.location = loc
    return o

def mesh(vs, fs, m=None, parent=None, smooth=False, name='mesh'):
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs)
    if m: me.materials.append(m)
    for p in me.polygons: p.use_smooth = smooth
    return link(bpy.data.objects.new(name, me), parent)

def box(loc, dim, m, parent=None, bevel=0, rot=(0, 0, 0)):
    x, y, z = [d / 2 for d in dim]
    o = mesh([(a, b, c) for a in (-x, x) for b in (-y, y) for c in (-z, z)],
             [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)], m, parent)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    if bevel:
        md = o.modifiers.new('b', 'BEVEL'); md.width = bevel; md.segments = 3
        for p in o.data.polygons: p.use_smooth = True
    return o

def lathe(profile, m, loc=(0, 0, 0), parent=None, n=32, rot=(0, 0, 0), smooth=True):
    vs = [(r * math.cos(i * math.tau / n), r * math.sin(i * math.tau / n), z) for r, z in profile for i in range(n)]
    fs = [(j * n + i, j * n + (i + 1) % n, (j + 1) * n + (i + 1) % n, (j + 1) * n + i)
          for j in range(len(profile) - 1) for i in range(n)]
    o = mesh(vs, fs, m, parent, smooth); o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    return o

def cyl(loc, r, h, m, parent=None, rot=(0, 0, 0), n=20):
    return lathe([(1e-4, -h / 2), (r, -h / 2), (r, -h / 2), (r, h / 2), (r, h / 2), (1e-4, h / 2)], m, loc, parent, n, rot)

def ball(loc, r, m, parent=None, scale=(1, 1, 1)):
    o = lathe([(max(1e-4, r * math.sin(i * math.pi / 12)), -r * math.cos(i * math.pi / 12)) for i in range(13)], m, loc, parent, 20)
    o.scale = scale
    return o

def pipe(points, r, m, parent=None):
    cu = bpy.data.curves.new('pipe', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(points) - 1)
    for p, q in zip(sp.points, points): p.co = (*q, 1)
    cu.materials.append(m)
    return link(bpy.data.objects.new('pipe', cu), parent)

def text(body, loc, size, m, parent=None, rot=(90, 0, 0), font='b', extrude=.006, align='CENTER'):
    cu = bpy.data.curves.new('text', 'FONT'); cu.body = body; cu.size = size; cu.extrude = extrude
    cu.align_x = align; cu.align_y = 'CENTER'; cu.font = bpy.data.fonts.load(FONT[font], check_existing=True)
    cu.materials.append(m)
    o = link(bpy.data.objects.new('text', cu), parent); o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    return o

def engraved(body, loc, dim, size, face, groove, rotz=0, parent=None):
    """A slab with the words really cut into it."""
    root = empty(loc, parent); root.rotation_euler.z = math.radians(rotz)
    w, d, h = dim
    slab = box((0, 0, 0), dim, face, root)
    slab.data.materials.append(groove)
    t = text(body, (0, 0, 0), size, groove, None, (90, 0, 0), 's', .022)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(t.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    me.transform(Matrix.Translation((0, -d / 2, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    me.materials.clear(); me.materials.append(face); me.materials.append(groove)
    for p in me.polygons: p.material_index = 1
    bpy.data.objects.remove(t)
    cut = link(bpy.data.objects.new('cutter', me), root); cut.hide_render = True
    md = slab.modifiers.new('engrave', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = cut
    return root

def light(kind, loc, energy, col=(1, 1, 1), tgt=None, size=1, shadow=False):
    d = bpy.data.lights.new('L', kind); d.energy = energy; d.color = col; d.use_shadow = shadow
    if kind == 'AREA': d.size = size
    elif kind == 'SUN': d.angle = .2
    else: d.shadow_soft_size = size
    o = link(bpy.data.objects.new('L', d)); o.location = loc
    if tgt is not None: o.rotation_euler = (V(tgt) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o

def world(col, strength=1):
    w = bpy.data.worlds.new('W'); w.use_nodes = True
    b = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    b.inputs[0].default_value = (*col, 1); b.inputs[1].default_value = strength
    bpy.context.scene.world = w

def snowfall(lo, hi, count, t0, t1, seed=4, r=.014):
    rr = random.Random(seed); src = ball((0, 0, -50), r, mat((.9, .95, 1), .5, .8)); src.hide_render = True
    f0, f1 = int(t0 * FPS) - 1, int(t1 * FPS) + 1
    for _ in range(count):
        o = link(bpy.data.objects.new('flake', src.data))
        o.scale = [rr.uniform(.5, 1.2)] * 3; o.visible_shadow = False
        p = V([rr.uniform(a, b) for a, b in zip(lo, hi)]); fall = (f1 - f0) / FPS * rr.uniform(.45, .75)
        o.location = p + V((0, 0, fall / 2)); o.keyframe_insert('location', frame=f0)
        o.location = p + V((rr.uniform(-.2, .4), 0, -fall / 2)); o.keyframe_insert('location', frame=f1)

# ---------- characters
FINGERS = ('index', 'middle', 'ring', 'pinky')
EMO = {
    'calm': {},
    'happy': dict(mouthSmileLeft=.65, mouthSmileRight=.65, cheekSquintLeft=.4, cheekSquintRight=.4, eyeSquintLeft=.25, eyeSquintRight=.25),
    'focus': dict(browDownLeft=.45, browDownRight=.45, eyeSquintLeft=.15, eyeSquintRight=.15, mouthPressLeft=.4, mouthPressRight=.4),
    'worry': dict(browInnerUp=1, eyeWideLeft=.3, eyeWideRight=.3, mouthFrownLeft=.65, mouthFrownRight=.65, jawOpen=.08),
    'shock': dict(browInnerUp=.9, browOuterUpLeft=.8, browOuterUpRight=.8, eyeWideLeft=1, eyeWideRight=1, jawOpen=.55, mouthStretchLeft=.25, mouthStretchRight=.25),
    'ask':   dict(browOuterUpLeft=1, browInnerUp=.35, browDownRight=.35, eyeWideLeft=.2, mouthPressRight=.3),
    # right central palsy: lower face sags on the right, the left side pulls, forehead still works
    'droop': dict(mouthFrownRight=1, mouthLowerDownRight=.55, mouthLeft=.7, mouthStretchLeft=.35, mouthSmileLeft=.2, jawOpen=.10,
                  eyeBlinkRight=.22, browInnerUp=1, eyeWideLeft=.45, jawLeft=.15, palsyRight=1),
    'dazed': dict(browInnerUp=.6, eyeBlinkLeft=.2, eyeBlinkRight=.35, mouthFrownRight=.7, mouthLeft=.35, jawOpen=.12, palsyRight=.7),
}
def emo(*names, **extra):
    d = {}
    for n in names: d.update(EMO[n])
    d.update(extra)
    return d

class Actor:
    def __init__(s, name, detail=False):
        s.arm = bpy.data.objects[name]; s.name = name
        s.arm.animation_data_clear(); s.arm.rotation_mode = 'XYZ'
        s.parts = [o for o in bpy.data.objects if o.get('who') == name and o.type == 'MESH']
        for o in s.parts:
            for md in o.modifiers:
                if md.type == 'SUBSURF':
                    md.render_levels = 1 if (detail and o.get('part') in ('body', 'brow')) else 0
        bs = s.arm.data.bones
        s.order = []
        def walk(b):
            s.order.append(b.name)
            for c in b.children: walk(c)
        for b in bs:
            if not b.parent: walk(b)
        s.par = {b.name: b.parent.name if b.parent else None for b in bs}
        s.h0 = {b.name: b.head_local.copy() for b in bs}
        s.t0 = {b.name: b.tail_local.copy() for b in bs}
        s.r0 = {b.name: b.matrix_local.to_quaternion() for b in bs}
        s.k = (s.h0['head'].z) / 1.546           # size relative to the patient
        s.fr = {}
        for sd in 'lr':
            h = s.h0['hand_' + sd]; f = (s.h0['middle_01_' + sd] - h).normalized()
            w = s.h0['index_01_' + sd] - s.h0['pinky_01_' + sd]
            n = f.cross(w) if sd == 'l' else w.cross(f)
            s.fr[sd] = (f, (n - f * n.dot(f)).normalized())
        for pb in s.arm.pose.bones: pb.rotation_mode = 'QUATERNION'
        s.faces = []

    def solve(s, p, root):
        inv = root.inverted(); loc = lambda v: inv @ V(v); dr = lambda v: (inv.to_3x3() @ V(v)).normalized()
        Q, H = {}, {}; bq = p.get('body', Quaternion()); aim = {}
        bends = p.get('bend', (0, 0, 0)); look = p.get('head', (0, 0, 0))
        curl = p.get('curl', {})
        for b in s.order:
            q0 = s.par[b]
            if not q0:
                Q[b] = Quaternion(); H[b] = s.h0[b].copy(); continue
            qp = Q[q0]; H[b] = H[q0] + qp @ (s.h0[b] - s.h0[q0]); q = qp
            if b == 'pelvis':
                q = bq
                if 'hip' in p: H[b] = loc(p['hip'])
            elif b in ('spine_01', 'spine_02', 'spine_03'):
                q = qp @ RX(bends[0] / 3) @ RY(bends[1] / 3) @ RZ(bends[2] / 3)
            elif b == 'neck_01':
                q = qp @ RX(look[0] * .35) @ RY(look[1] * .35) @ RZ(look[2] * .35)
            elif b == 'head':
                q = qp @ RX(look[0] * .65) @ RY(look[1] * .65) @ RZ(look[2] * .65)
            elif b[:-2] in ('upperarm', 'thigh'):
                sd = b[-1]; arm = b.startswith('upper'); spec = p.get(('hand_' if arm else 'foot_') + sd)
                mid = ('lowerarm_' if arm else 'calf_') + sd; end = ('hand_' if arm else 'foot_') + sd
                S0 = H[b]
                if spec:
                    T, pole = loc(spec[0]), dr(spec[1])
                else:
                    # relaxed: arm hangs, leg stands straight
                    T = S0 + qp @ (V((.07 if sd == 'l' else -.07, -.06, -.49)) * s.k if arm else (s.h0[end] - s.h0[b]) * .998)
                    pole = qp @ V((0, 1 if arm else -1, 0))
                L1 = (s.h0[mid] - s.h0[b]).length; L2 = (s.h0[end] - s.h0[mid]).length
                d = T - S0; D = min(L1 + L2 - .002, max(abs(L1 - L2) + .01, d.length)); u = d.normalized()
                a = (L1 * L1 - L2 * L2 + D * D) / (2 * D); h = math.sqrt(max(0, L1 * L1 - a * a))
                n = pole - u * pole.dot(u)
                n = n.normalized() if n.length > 1e-4 else u.orthogonal().normalized()
                E = S0 + u * a + n * h
                aim[b] = (E - S0).normalized(); aim[mid] = (S0 + u * D - E).normalized()
                q = (qp @ (s.h0[mid] - s.h0[b]).normalized()).rotation_difference(aim[b]) @ qp
            elif b in aim:
                sd = b[-1]; end = ('hand_' if b.startswith('lower') else 'foot_') + sd
                q = (qp @ (s.h0[end] - s.h0[b]).normalized()).rotation_difference(aim[b]) @ qp
            elif b.startswith('hand_'):
                sd = b[-1]; o = p.get('palm_' + sd)
                if o:
                    f0, n0 = s.fr[sd]; f = dr(o[0]); n = dr(o[1]); n = (n - f * n.dot(f)).normalized()
                    A = Matrix((f0, n0, f0.cross(n0))).transposed(); B = Matrix((f, n, f.cross(n))).transposed()
                    q = (B @ A.transposed()).to_quaternion()
            elif b.startswith('foot_'):
                q = p.get('sole', bq)
            elif b.split('_')[0] in FINGERS + ('thumb',):
                nm, i, sd = b.split('_'); c = curl.get(sd, .25); f = (s.t0[b] - s.h0[b]).normalized()
                ax = f.cross(s.fr[sd][1])
                if ax.length > 1e-3:
                    ang = c * ((22, 30, 30) if nm == 'thumb' else (62, 78, 55))[int(i) - 1]
                    q = qp @ Quaternion(ax.normalized(), math.radians(ang))
            Q[b] = q.normalized()
        return Q, H

    def pose(s, f, p):
        pos = V(p.get('at', (0, 0, 0))); yaw = math.radians(p.get('yaw', 0))
        root = Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, 'Z')
        s.arm.location = pos; s.arm.rotation_euler = (0, 0, yaw)
        s.arm.keyframe_insert('location', frame=f); s.arm.keyframe_insert('rotation_euler', frame=f)
        Q, H = s.solve(p, root); W = {}
        for b in s.order:
            pb = s.arm.pose.bones[b]
            W[b] = Matrix.Translation(H[b]) @ (Q[b] @ s.r0[b]).to_matrix().to_4x4()
            rest = Matrix.Translation(s.h0[b]) @ s.r0[b].to_matrix().to_4x4(); q0 = s.par[b]
            if q0:
                rp = Matrix.Translation(s.h0[q0]) @ s.r0[q0].to_matrix().to_4x4()
                basis = (rp.inverted() @ rest).inverted() @ W[q0].inverted() @ W[b]
            else:
                basis = rest.inverted() @ W[b]
            q = basis.to_quaternion(); last = pb.get('_q')
            if last and q.dot(Quaternion(last)) < 0: q = -q
            pb['_q'] = tuple(q)
            pb.rotation_quaternion = q; pb.keyframe_insert('rotation_quaternion', frame=f)
            if b == 'pelvis':
                pb.location = basis.to_translation(); pb.keyframe_insert('location', frame=f)
        return root, Q, H

    def perform(s, fn, f0, f1, step=1):
        out = {}
        fs = list(range(f0, f1, step))
        if fs[-1] != f1 - 1: fs.append(f1 - 1)
        for f in fs: out[f] = s.pose(f, fn(f / FPS))
        return out

    def face(s, keys, t0, t1, blink=3.1, talk=None):
        """keys: [(time, {shape: value})]; adds blinking, eye darts and optional talking."""
        names = {'eyeBlinkLeft', 'eyeBlinkRight'}
        for _, d in keys: names.update(d)
        if talk: names.update(('jawOpen', 'mouthFunnel', 'mouthStretchLeft', 'mouthPucker'))
        blocks = []
        for o in s.parts:
            sk = o.data.shape_keys
            if not sk: continue
            for n in names:
                kb = sk.key_blocks.get(n)
                if kb: blocks.append((n, kb))
        off = (sum(map(ord, s.name)) % 10) * .23
        for f in range(int(t0 * FPS), int(t1 * FPS) + 1):
            t = f / FPS; val = {n: track([(a, d.get(n, 0)) for a, d in keys], t) for n in names}
            p = (t + off) % blink; b = max(0, 1 - abs(p - .12) / .10)
            for n in ('eyeBlinkLeft', 'eyeBlinkRight'): val[n] = max(val[n], b)
            if talk and talk[0] <= t <= talk[1]:
                env = ss(talk[0], talk[0] + .2, t) * (1 - ss(talk[1] - .2, talk[1], t))
                val['jawOpen'] += env * (.12 + .28 * abs(math.sin(t * 9.3)) * (.6 + .4 * math.sin(t * 3.1) ** 2))
                val['mouthFunnel'] += env * .45 * max(0, math.sin(t * 5.2))
                val['mouthPucker'] += env * .3 * max(0, math.sin(t * 4.1 + 2))
                val['mouthStretchLeft'] += env * .3 * max(0, math.sin(t * 6.4 + 1))
            for n, kb in blocks:
                kb.value = min(1, val[n]); kb.keyframe_insert('value', frame=f)

    def stick(s, o, offset):
        """Rigidly attach an object to the head, offset in rest space."""
        c = o.constraints.new('CHILD_OF'); c.target = s.arm; c.subtarget = 'head'
        o.location = s.h0['head'] + V(offset)
        c.inverse_matrix = s.arm.data.bones['head'].matrix_local.inverted()
        return o

def camera(keys, f0, f1, shake=.006):
    """keys: (t, pos, target, lens, fstop[, roll_deg]). Several calls in one shot = hard cuts (timeline markers)."""
    S = bpy.context.scene
    cd = bpy.data.cameras.new('Cam'); cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 36; cd.clip_start = .02; cd.clip_end = 120
    cd.dof.use_dof = True
    o = link(bpy.data.objects.new('Cam', cd)); S.camera = o
    mk = S.timeline_markers.new('cut%d' % f0, frame=f0); mk.camera = o
    prev = None
    for f in range(f0, f1):
        t = f / FPS
        p = track([(k[0], V(k[1])) for k in keys], t) + noise.noise_vector(V((t * 1.4, 3, 8))) * shake
        g = track([(k[0], V(k[2])) for k in keys], t)
        cd.lens = track([(k[0], k[3]) for k in keys], t); cd.dof.aperture_fstop = track([(k[0], k[4]) for k in keys], t)
        roll = track([(k[0], k[5] if len(k) > 5 else 0) for k in keys], t) + 1.2 * noise.noise(V((t * .9, 7, 1))) * (shake > .005)
        cd.dof.focus_distance = (g - p).length
        q = (g - p).to_track_quat('-Z', 'Y') @ Quaternion((0, 0, 1), math.radians(roll))
        e = q.to_euler('XYZ', prev) if prev else q.to_euler()
        prev = e.copy()
        o.location = p; o.rotation_euler = e
        for ob, k in ((o, 'location'), (o, 'rotation_euler'), (cd, 'lens'), (cd.dof, 'aperture_fstop'), (cd.dof, 'focus_distance')):
            ob.keyframe_insert(k, frame=f)
    return o

def crash(t0, t1, far, near, end, tgt0, tgt1, lens, fstop=2.8, roll=(0, 0), snap=.16):
    """ZackD push: 0.15 s hard move with motion blur, then an almost-still drift."""
    return [(t0, far, tgt0, lens[0], fstop, roll[0]), (t0 + snap, near, tgt1, lens[1], fstop, roll[1]),
            (t1, end, tgt1, lens[1] + (lens[2] if len(lens) > 2 else 2), fstop, roll[1] * 1.1)]

# ---------- downloaded CC0 assets (Poly Haven)
import os
DL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets_dl')
_ASSET = {}
def asset(name, loc, rotz=0, back=None):
    """Instance a Poly Haven glTF model. back: world direction its backrest should face (auto-oriented)."""
    if name not in _ASSET:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(DL, name, name + '_1k.gltf'))
        objs = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in objs if o.type == 'MESH']
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
        lo = V([min(p[i] for p in pts) for i in range(3)]); hi = V([max(p[i] for p in pts) for i in range(3)])
        c = (lo + hi) / 2; top = [p for p in pts if p.z > lo.z + .75 * (hi.z - lo.z)]
        tc = sum(top, V()) / len(top) - c; tc.z = 0
        col = bpy.data.collections.new('A_' + name)
        for o in objs:
            for uc in list(o.users_collection): uc.objects.unlink(o)
            col.objects.link(o)
            if o.parent is None: o.location -= V((c.x, c.y, lo.z))
        _ASSET[name] = (col, math.atan2(tc.y, tc.x) if tc.length > .02 else None, hi - lo)
        print('##ASSET', name, tuple(round(x, 3) for x in hi - lo), 'back', _ASSET[name][1], flush=True)
    col, ang, size = _ASSET[name]
    e = bpy.data.objects.new(name, None); e.instance_type = 'COLLECTION'; e.instance_collection = col
    bpy.context.scene.collection.objects.link(e); e.location = loc
    e.rotation_euler.z = (math.atan2(back[1], back[0]) - ang) if (back is not None and ang is not None) else math.radians(rotz)
    return e

def hdri_world(file, light_col, light_str, cam_str=1.0, rotz=0):
    """Camera sees the photographed environment; the scene keeps its own designed lighting."""
    w = bpy.data.worlds.new('W'); w.use_nodes = True; N, L = w.node_tree.nodes, w.node_tree.links
    out = next(n for n in N if n.type == 'OUTPUT_WORLD'); bg = next(n for n in N if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (*light_col, 1); bg.inputs[1].default_value = light_str
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value[2] = math.radians(rotz)
    env = N.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(DL, file), check_existing=True)
    L.new(tc.outputs['Generated'], mp.inputs[0]); L.new(mp.outputs[0], env.inputs[0])
    b2 = N.new('ShaderNodeBackground'); L.new(env.outputs[0], b2.inputs[0]); b2.inputs[1].default_value = cam_str
    lp = N.new('ShaderNodeLightPath'); mx = N.new('ShaderNodeMixShader')
    L.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); L.new(bg.outputs[0], mx.inputs[1]); L.new(b2.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], out.inputs['Surface'])
    bpy.context.scene.world = w
