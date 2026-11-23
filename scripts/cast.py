"""Original cast for the stroke case, generated with MPFB (MakeHuman CC0 assets)."""
import bpy, sys, importlib, math, traceback
from mathutils import Vector

ROOT = sys.argv[sys.argv.index('--') + 1]
PK = 'bl_ext.blender_org.mpfb.services.'
HS = importlib.import_module(PK + 'humanservice').HumanService
FS = importlib.import_module(PK + 'faceservice').FaceService
TS = importlib.import_module(PK + 'targetservice').TargetService

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
S = bpy.context.scene

TEAL, NAVY, RED = (.015, .30, .33), (.012, .022, .06), (.75, .04, .025)
# look: (upper colour, lower colour, split height 0..1 of garment, options)
CAST = {
 'patient': dict(g=1, age=.78, w=.64, m=.4, h=.5, skin='old_caucasian_male', hair='short04', hc=(.36, .34, .32), brow='eyebrow012',
                 suit='male_casualsuit01', shoe='shoes01', look=((.34, .13, .07), (.05, .05, .06), .585, '')),
 'wife':    dict(g=0, age=.74, w=.66, m=.4, h=.45, skin='old_caucasian_female', hair='braid01', hc=(.12, .09, .075), brow='eyebrow010',
                 suit='female_elegantsuit01', shoe='shoes03', look=((.45, .05, .12), (.04, .03, .05), .43, '')),
 'son':     dict(g=1, age=.56, w=.52, m=.55, h=.58, skin='middleage_caucasian_male', hair='short02', hc=(.03, .022, .018), brow='eyebrow001',
                 suit='male_casualsuit02', shoe='shoes04', look=((.06, .20, .10), (.03, .06, .14), .575, 'flat')),
 'daughter':dict(g=0, age=.5, w=.45, m=.4, h=.55, skin='young_caucasian_female', hair='long01', hc=(.07, .035, .02), brow='eyebrow009',
                 suit='female_casualsuit01', shoe='shoes05', look=((.85, .50, .12), (.03, .06, .16), .60, 'flat')),
 'doc':     dict(g=1, age=.63, w=.5, m=.55, h=.62, skin='middleage_caucasian_male', hair='short04', hc=(.025, .02, .018), brow='eyebrow012',
                 suit='male_elegantsuit01', shoe='shoes03', look=((.86, .88, .88), TEAL, .42, 'coat')),
 'doc2':    dict(g=0, age=.54, w=.45, m=.45, h=.56, skin='young_caucasian_female', hair='long01', hc=(.02, .012, .009), brow='eyebrow009',
                 suit='female_casualsuit01', shoe='shoes05', look=(TEAL, TEAL, .5, 'flat')),
 'medic1':  dict(g=1, age=.54, w=.55, m=.65, h=.6, skin='young_caucasian_male', hair='short02', hc=(.05, .03, .02), brow='eyebrow002',
                 suit='male_casualsuit05', shoe='shoes03', look=(RED, NAVY, .565, 'stripes')),
 'medic2':  dict(g=1, age=.58, w=.5, m=.6, h=.55, skin='middleage_asian_male', hair='short04', hc=(.015, .012, .01), brow='eyebrow003',
                 suit='male_casualsuit05', shoe='shoes03', look=(RED, NAVY, .565, 'stripes')),
}

def recolour(obj, upper, lower, split, opt, gain=2.6):
    """Tint the garment, keeping the folds of its own diffuse map."""
    for i, slot in enumerate(obj.material_slots):
        if not slot.material: continue
        m = slot.material = slot.material.copy()
        t = m.node_tree; N, L = t.nodes, t.links
        b = next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
        if not b: continue
        bc = b.inputs['Base Color']
        src = bc.links[0].from_socket if bc.links else None
        tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ')
        L.new(tc.outputs['Generated'], sep.inputs[0])
        rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.interpolation = 'CONSTANT'
        e = rp.color_ramp.elements; e[0].color = (*lower, 1); e[1].position = split; e[1].color = (*upper, 1)
        if opt == 'stripes':
            for p, c in ((.10, (.8, .85, .7)), (.13, lower), (.62, (.95, .85, .15)), (.645, (.8, .85, .8)), (.67, upper), (.80, (.95, .85, .15)), (.83, upper)):
                x = e.new(p); x.color = (*c, 1)
        L.new(sep.outputs['Z'], rp.inputs[0])
        col = rp.outputs['Color']
        if opt == 'coat':       # shirt/tie opening down the middle of the chest
            ax = N.new('ShaderNodeMath'); ax.operation = 'SUBTRACT'; L.new(sep.outputs['X'], ax.inputs[0]); ax.inputs[1].default_value = .5
            ab = N.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; L.new(ax.outputs[0], ab.inputs[0])
            lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; L.new(ab.outputs[0], lt.inputs[0]); lt.inputs[1].default_value = .045
            gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; L.new(sep.outputs['Z'], gt.inputs[0]); gt.inputs[1].default_value = .74
            fr = N.new('ShaderNodeMath'); fr.operation = 'GREATER_THAN'; fr.inputs[1].default_value = .5
            sb = N.new('ShaderNodeMath'); sb.operation = 'SUBTRACT'; sb.inputs[0].default_value = 1; L.new(sep.outputs['Y'], sb.inputs[1])
            L.new(sb.outputs[0], fr.inputs[0])
            m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L.new(lt.outputs[0], m1.inputs[0]); L.new(gt.outputs[0], m1.inputs[1])
            m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; L.new(m1.outputs[0], m2.inputs[0]); L.new(fr.outputs[0], m2.inputs[1])
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(m2.outputs[0], mx.inputs[0]); L.new(col, mx.inputs[6]); mx.inputs[7].default_value = (*TEAL, 1)
            col = mx.outputs[2]
        if src and opt != 'flat':
            bw = N.new('ShaderNodeRGBToBW'); L.new(src, bw.inputs[0])
            mr = N.new('ShaderNodeMapRange'); L.new(bw.outputs[0], mr.inputs[0])
            mr.inputs[1].default_value = 0; mr.inputs[2].default_value = .22
            mr.inputs[3].default_value = .5; mr.inputs[4].default_value = 1.05
            mu = N.new('ShaderNodeVectorMath'); mu.operation = 'SCALE'; L.new(col, mu.inputs[0]); L.new(mr.outputs[0], mu.inputs['Scale'])
            col = mu.outputs[0]
        L.new(col, bc)
        b.inputs['Roughness'].default_value = .8

def hair_tint(obj, c):
    for slot in obj.material_slots:
        if not slot.material: continue
        m = slot.material = slot.material.copy(); t = m.node_tree
        b = next((n for n in t.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not b: continue
        bc = b.inputs['Base Color']
        if bc.links:
            src = bc.links[0].from_socket
            bw = t.nodes.new('ShaderNodeRGBToBW'); t.links.new(src, bw.inputs[0])
            mr = t.nodes.new('ShaderNodeMapRange'); t.links.new(bw.outputs[0], mr.inputs[0])
            mr.inputs[2].default_value = .12; mr.inputs[3].default_value = .35; mr.inputs[4].default_value = 1.7
            mu = t.nodes.new('ShaderNodeVectorMath'); mu.operation = 'SCALE'
            mu.inputs[0].default_value = c; t.links.new(mr.outputs[0], mu.inputs['Scale']); t.links.new(mu.outputs[0], bc)
        else:
            bc.default_value = (*c, 1)
        b.inputs['Roughness'].default_value = .5
        m.surface_render_method = 'DITHERED'

def tint_mul(t, b, c):
    bc = b.inputs['Base Color']
    if not bc.links: return
    mu = t.nodes.new('ShaderNodeVectorMath'); mu.operation = 'MULTIPLY'
    t.links.new(bc.links[0].from_socket, mu.inputs[0]); mu.inputs[1].default_value = c
    t.links.new(mu.outputs[0], bc)

def moustache(body, arm, col):
    import random
    rr = random.Random(5); kb = body.data.shape_keys.key_blocks
    mix = [v.co.copy() for v in body.data.vertices]
    base = kb['Basis'].data
    skip = set(fk.name for fk in kb if fk.name[:1].islower() and '-' not in fk.name and '$' not in fk.name)
    for k in kb:
        if k.name != 'Basis' and k.value:
            for i, d in enumerate(k.data): mix[i] = mix[i] + (d.co - base[i].co) * k.value
    def top(name):
        k = kb[name]
        return max(range(13380), key=lambda i: (k.data[i].co - base[i].co).length)
    cl, cr = mix[top('mouthSmileLeft')], mix[top('mouthSmileRight')]
    mid = (cl + cr) / 2; half = abs(cl.x - cr.x) / 2
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
    ids = [i for i in range(13380) if abs(mix[i].x - mid.x) < half * 1.06 and mix[i].y < mid.y + .006
           and .007 - .009 * (abs(mix[i].x - mid.x) / half) ** 2 < mix[i].z - mid.z < .0155 - .012 * (abs(mix[i].x - mid.x) / half) ** 2]
    print('##MOUTH', cl[:], cr[:], 'moustache roots', len(ids), flush=True)
    if not ids: return
    V, F, src = [], [], []
    for i in ids:
        for _ in range(30):
            p = mix[i] + Vector((rr.gauss(0, .0022), -.0012 - rr.random() * .0015, rr.gauss(0, .0016)))
            side = 1 if p.x > mid.x else -1
            q = p + Vector((side * rr.uniform(.001, .004), -.001, -rr.uniform(.003, .006)))
            n = len(V); V += [p - Vector((.00035, 0, 0)), p + Vector((.00035, 0, 0)), q]; F.append((n, n + 1, n + 2)); src += [i] * 3
    me = bpy.data.meshes.new('moustache'); me.from_pydata(V, [], F)
    o = bpy.data.objects.new('patient.moustache', me); col.objects.link(o); o.parent = arm
    o['part'] = 'moustache'; o['who'] = 'patient'
    g = o.vertex_groups.new(name='head'); g.add(list(range(len(V))), 1, 'REPLACE')
    o.modifiers.new('arm', 'ARMATURE').object = arm
    m = bpy.data.materials.new('moustache'); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'); b.inputs['Base Color'].default_value = (.20, .17, .145, 1)
    me.materials.append(m)
    o.shape_key_add(name='Basis')
    for k in kb:
        if k.name not in skip: continue
        ds = [k.data[i].co - base[i].co for i in src]
        if max(d.length for d in ds) < 1e-4: continue
        nk = o.shape_key_add(name=k.name, from_mix=False); nk.value = 0
        for j, d in enumerate(ds): nk.data[j].co = V[j] + d

def make(name, d):
    info = HS._create_default_human_info_dict()
    ph = TS.get_default_macro_info_dict()
    ph.update(gender=float(d['g']), age=d['age'], muscle=d['m'], weight=d['w'], height=d['h'], proportions=.65,
              race=dict(asian=.3, caucasian=.7, african=0.0))
    s = d['skin']
    info.update(name=name, phenotype=ph, rig='game_engine', eyes='high-poly/high-poly.mhclo',
                eyebrows=f"{d['brow']}/{d['brow']}.mhclo", eyelashes='eyelashes01/eyelashes01.mhclo',
                teeth='teeth_base/teeth_base.mhclo', tongue='tongue01/tongue01.mhclo',
                hair=f"{d['hair']}/{d['hair']}.mhclo",
                clothes=[f"{d['suit']}/{d['suit']}.mhclo", f"{d['shoe']}/{d['shoe']}.mhclo"],
                skin_mhmat=f'{s}/{s}.mhmat', skin_material_type='MAKESKIN', eyes_material_type='MAKESKIN')
    st = HS.get_default_deserialization_settings(); st['subdiv_levels'] = 1
    before = set(bpy.data.objects)
    body = HS.deserialize_from_dict(info, st)
    FS.load_targets(body, load_microsoft_visemes=False, load_meta_visemes=False, load_arkit_faceunits=True)
    FS.interpolate_targets(body)
    new = [o for o in bpy.data.objects if o not in before]
    col = bpy.data.collections.new('C_' + name); S.collection.children.link(col)
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o); n = o.name.lower(); o['who'] = name
        if o.type == 'ARMATURE':
            o.name = name
            continue
        if d['suit'] in n:
            o['part'] = 'suit'; recolour(o, *d['look'])
        elif d['hair'] in n:
            o['part'] = 'hair'; hair_tint(o, d['hc'])
        elif 'eyebrow' in n:
            o['part'] = 'brow'
            if name == 'patient': hair_tint(o, (.22, .19, .16))
        elif 'high-poly' in n:
            o['part'] = 'eyes'
            for slot in o.material_slots:
                t = slot.material.node_tree
                for q in t.nodes:
                    if q.type == 'BSDF_PRINCIPLED': tint_mul(t, q, (.62, .72, .72)); q.inputs['Roughness'].default_value = .12
        elif o == body: o['part'] = 'body'
        else: o['part'] = n.split('.')[-1]
        for md in o.modifiers:
            if md.type == 'SUBSURF':
                md.levels = 0
                md.render_levels = 1 if (o == body or o.get('part') in ('brow',)) else 0
    for slot in body.material_slots:
        if slot.material and slot.material.node_tree:
            for n in slot.material.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Roughness'].default_value = .47
                    tint_mul(slot.material.node_tree, n, (1.0, .80, .66) if name not in ('wife', 'daughter', 'doc2') else (1.0, .80, .68))
    for o in new:
        if o.get('part') == 'teeth_base':
            for slot in o.material_slots:
                t = slot.material.node_tree
                for n in t.nodes:
                    if n.type == 'BSDF_PRINCIPLED': tint_mul(t, n, (1.0, .9, .72))
    if name == 'patient': moustache(body, next(o for o in new if o.type == 'ARMATURE'), col)
    k = body.data.shape_keys.key_blocks
    print('##CAST', name, [(o.name, o.type) for o in new], 'keys', len(k), flush=True)
    return next(o for o in new if o.type == 'ARMATURE')

arms = {}
for nm, d in CAST.items():
    try:
        arms[nm] = make(nm, d)
    except Exception:
        print('##FAIL', nm, traceback.format_exc(), flush=True)
bpy.ops.wm.save_as_mainfile(filepath=ROOT + '/cast.blend')
import json
json.dump({n: {b.name: [list(b.head_local), list(b.tail_local), b.parent.name if b.parent else None] for b in a.data.bones} for n, a in arms.items()},
          open(ROOT + '/bones.json', 'w'))

# ---------- contact sheet: line-up + faces + expression test
def look(o, t): o.rotation_euler = (Vector(t) - o.location).to_track_quat('-Z', 'Y').to_euler()
for i, (nm, a) in enumerate(arms.items()):
    a.location.x = (i - (len(arms) - 1) / 2) * .78
w = bpy.data.worlds.new('w'); w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[0].default_value = (.18, .42, .62, 1); bg.inputs[1].default_value = .8
S.world = w
ld = bpy.data.lights.new('s', 'SUN'); ld.energy = 2.6; ld.angle = .3
l = bpy.data.objects.new('s', ld); S.collection.objects.link(l); l.rotation_euler = (math.radians(55), 0, math.radians(25))
cd = bpy.data.cameras.new('c'); c = bpy.data.objects.new('c', cd); S.collection.objects.link(c); S.camera = c
r = S.render; r.engine = 'BLENDER_EEVEE'; S.eevee.taa_render_samples = 16
r.image_settings.file_format = 'PNG'
def shot(path, loc, tgt, lens, res):
    c.location = loc; look(c, tgt); cd.lens = lens; r.resolution_x, r.resolution_y = res; r.resolution_percentage = 100
    r.filepath = f'{ROOT}/chk/{path}.png'; bpy.ops.render.render(write_still=True)
shot('cast_line', (0, -9.5, 1.3), (0, 0, .9), 50, (1600, 520))
bpy.context.view_layer.update()
def head(a): return a.matrix_world @ a.pose.bones['head'].head
for i, (nm, a) in enumerate(arms.items()):
    h = head(a) + Vector((0, 0, .07))
    shot(f'face_{i}', h + Vector((.16, -1.05, .02)), h, 85, (360, 440))
if 'patient' in arms:
    a = arms['patient']; E = dict(mouthFrownRight=1, eyeSquintRight=.3, mouthLowerDownRight=.6, mouthLeft=.5, browInnerUp=.9,
                                  mouthStretchLeft=.3, jawOpen=.25, eyeWideLeft=.4)
    for o in bpy.data.objects:
        if o.get('who') == 'patient' and o.type == 'MESH' and o.data.shape_keys:
            for k, v in E.items():
                q = o.data.shape_keys.key_blocks.get(k)
                if q: q.value = v
    h = head(a) + Vector((0, 0, .07))
    shot('face_8', h + Vector((0, -1.05, 0)), h, 85, (360, 440))
    shot('face_9', h + Vector((0, -.8, 0)), h + Vector((0, 0, -.05)), 100, (360, 440))
print('##CAST DONE', flush=True)
