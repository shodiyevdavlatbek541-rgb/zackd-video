import sys
p=sys.argv[1]; s=open(p,encoding='utf8').read()
def r(a,b,n=1):
    global s
    assert s.count(a)==n,(a,s.count(a))
    s=s.replace(a,b)
r("skin='old_caucasian_male', hair='short02', hc=(.42, .40, .37), brow='eyebrow006'","skin='old_caucasian_male', hair='short04', hc=(.36, .34, .32), brow='eyebrow012'")
r("look=((.34, .13, .07), (.05, .05, .06), .50, '')","look=((.34, .13, .07), (.05, .05, .06), .585, '')")
r("hair='bob01', hc=(.16, .09, .06), brow='eyebrow010'","hair='bob02', hc=(.17, .11, .08), brow='eyebrow010'")
r("look=((.45, .05, .12), (.04, .03, .05), .38, '')","look=((.45, .05, .12), (.04, .03, .05), .43, '')")
r("look=((.06, .20, .10), (.03, .06, .14), .50, '')","look=((.06, .20, .10), (.03, .06, .14), .575, 'flat')")
r("hair='ponytail01', hc=(.07, .035, .02)","hair='long01', hc=(.07, .035, .02)")
r("look=((.85, .50, .12), (.03, .06, .16), .52, '')","look=((.85, .50, .12), (.03, .06, .16), .60, 'flat')")
r("hair='bob01', hc=(.02, .014, .01), brow='eyebrow011'","hair='ponytail01', hc=(.03, .018, .012), brow='eyebrow009'")
r("look=(TEAL, TEAL, .5, '')","look=(TEAL, TEAL, .5, 'flat')")
r("hair='short03', hc=(.05, .03, .02)","hair='short02', hc=(.05, .03, .02)")
r("look=(RED, NAVY, .49, 'stripes')","look=(RED, NAVY, .565, 'stripes')",2)
r("brow='eyebrow004'","brow='eyebrow012'")
r("(.10, (.8, .85, .7)), (.13, lower), (.60, (.95, .85, .15)), (.635, (.8, .85, .8)), (.66, upper)","(.10, (.8, .85, .7)), (.13, lower), (.62, (.95, .85, .15)), (.645, (.8, .85, .8)), (.67, upper)")
r("        if src:\n            bw","        if src and opt != 'flat':\n            bw")
r("                if n.type == 'BSDF_PRINCIPLED': n.inputs['Roughness'].default_value = .5",
"""                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Roughness'].default_value = .47
                    tint_mul(slot.material.node_tree, n, (1.0, .80, .66) if name not in ('wife', 'daughter', 'doc2') else (1.0, .84, .74))
    for o in new:
        if o.get('part') == 'teeth_base':
            for slot in o.material_slots:
                t = slot.material.node_tree
                for n in t.nodes:
                    if n.type == 'BSDF_PRINCIPLED': tint_mul(t, n, (1.0, .9, .72))
    if name == 'patient': moustache(body, next(o for o in new if o.type == 'ARMATURE'), col)""")
r("def make(name, d):",
"""def tint_mul(t, b, c):
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
    ids = [i for i in range(13380) if abs(mix[i].x - mid.x) < half * 1.25 and mix[i].y < mid.y + .006
           and .007 - .006 * (abs(mix[i].x - mid.x) / half) ** 2 < mix[i].z - mid.z < .021 - .009 * (abs(mix[i].x - mid.x) / half) ** 2]
    print('##MOUTH', cl[:], cr[:], 'moustache roots', len(ids), flush=True)
    if not ids: return
    V, F, src = [], [], []
    for i in ids:
        for _ in range(26):
            p = mix[i] + Vector((rr.gauss(0, .0022), -.0012 - rr.random() * .0015, rr.gauss(0, .0016)))
            side = 1 if p.x > mid.x else -1
            q = p + Vector((side * rr.uniform(.001, .005), -.0015, -rr.uniform(.004, .009)))
            n = len(V); V += [p - Vector((.0005, 0, 0)), p + Vector((.0005, 0, 0)), q]; F.append((n, n + 1, n + 2)); src += [i] * 3
    me = bpy.data.meshes.new('moustache'); me.from_pydata(V, [], F)
    o = bpy.data.objects.new('patient.moustache', me); col.objects.link(o); o.parent = arm
    o['part'] = 'moustache'; o['who'] = 'patient'
    g = o.vertex_groups.new(name='head'); g.add(list(range(len(V))), 1, 'REPLACE')
    o.modifiers.new('arm', 'ARMATURE').object = arm
    m = bpy.data.materials.new('moustache'); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'); b.inputs['Base Color'].default_value = (.16, .14, .12, 1)
    me.materials.append(m)
    o.shape_key_add(name='Basis')
    for k in kb:
        if k.name not in skip: continue
        ds = [k.data[i].co - base[i].co for i in src]
        if max(d.length for d in ds) < 1e-4: continue
        nk = o.shape_key_add(name=k.name, from_mix=False); nk.value = 0
        for j, d in enumerate(ds): nk.data[j].co = V[j] + d

def make(name, d):""")
r("bpy.ops.wm.save_as_mainfile(filepath=ROOT + '/cast.blend')",
"""bpy.ops.wm.save_as_mainfile(filepath=ROOT + '/cast.blend')
import json
json.dump({n: {b.name: [list(b.head_local), list(b.tail_local), b.parent.name if b.parent else None] for b in a.data.bones} for n, a in arms.items()},
          open(ROOT + '/bones.json', 'w'))""")
open(p,'w',encoding='utf8').write(s)
