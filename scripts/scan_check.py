"""Look at the scan cast: line-up, faces, expressions and a bent pose. usage: blender -b CAST.blend -P scan_check.py -- ROOT tag"""
import bpy, sys, math
from mathutils import Vector as V, Quaternion
ROOT, TAG = sys.argv[sys.argv.index('--') + 1:][:2]
sys.path.insert(0, ROOT + '/scripts')
S = bpy.context.scene
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
for i, a in enumerate(arms): a.location.x = (i - (len(arms) - 1) / 2) * .8
w = bpy.data.worlds.new('w'); w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[0].default_value = (.05, .06, .08, 1); bg.inputs[1].default_value = 1
S.world = w
def lamp(kind, loc, e, col, size):
    d = bpy.data.lights.new('l', kind); d.energy = e; d.color = col
    if kind == 'AREA': d.size = size
    o = bpy.data.objects.new('l', d); S.collection.objects.link(o); o.location = loc
    o.rotation_euler = (V((0, 0, 1.3)) - V(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
lamp('AREA', (2.5, -3.0, 2.6), 380, (1, .85, .7), 1.5); lamp('AREA', (-3, -2.5, 1.6), 60, (.6, .75, 1), 3); lamp('AREA', (-1.5, 3, 2.5), 500, (.6, .8, 1), 1.2)
cd = bpy.data.cameras.new('c'); c = bpy.data.objects.new('c', cd); S.collection.objects.link(c); S.camera = c; cd.dof.use_dof = True
r = S.render; r.engine = 'BLENDER_EEVEE'; r.image_settings.file_format = 'PNG'
import realism; realism.apply(S)
def shot(path, loc, tgt, lens, res, f=2.8):
    c.location = loc; c.rotation_euler = (V(tgt) - V(loc)).to_track_quat('-Z', 'Y').to_euler(); cd.lens = lens
    cd.dof.focus_distance = (V(tgt) - V(loc)).length; cd.dof.aperture_fstop = f
    r.resolution_x, r.resolution_y = res; r.resolution_percentage = 100
    r.filepath = f'{ROOT}/chk/{path}.png'; bpy.ops.render.render(write_still=True)
def keys(a, d):
    for o in bpy.data.objects:
        if o.get('who') == a.name and o.type == 'MESH' and o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks[1:]: kb.value = d.get(kb.name, 0)
n = len(arms)
shot(f'{TAG}_line', (0, -2.2 - n * .9, 1.0), (0, 0, .9), 35, (1600 if n > 2 else 900, 900), 8)
for a in arms:
    hd = a.matrix_world @ a.data.bones['head'].head_local + V((0, -.05, .08))
    shot(f'{TAG}_face_{a.name}', hd + V((.05, -.42, .02)), hd, 50, (720, 900))
    keys(a, dict(mouthSmileLeft=.8, mouthSmileRight=.8, cheekSquintLeft=.5, cheekSquintRight=.5, eyeSquintLeft=.3, eyeSquintRight=.3))
    shot(f'{TAG}_smile_{a.name}', hd + V((0, -.42, .0)), hd, 50, (540, 600))
    keys(a, dict(jawOpen=.7, browInnerUp=1, browOuterUpLeft=.8, browOuterUpRight=.8, eyeWideLeft=1, eyeWideRight=1))
    shot(f'{TAG}_shock_{a.name}', hd + V((0, -.42, .0)), hd, 50, (540, 600))
    keys(a, dict(mouthFrownRight=1, mouthLowerDownRight=.55, mouthLeft=.7, palsyRight=1, eyeBlinkRight=.25, browInnerUp=.8, jawOpen=.1))
    shot(f'{TAG}_droop_{a.name}', hd + V((0, -.42, .0)), hd, 50, (540, 600))
    keys(a, dict(eyeBlinkLeft=1, eyeBlinkRight=1))
    shot(f'{TAG}_blink_{a.name}', hd + V((0, -.30, .0)), hd, 50, (540, 400))
    keys(a, {})
# bend test: arms up and forward, knee bent, head turned, fist
for a in arms:
    pb = a.pose.bones
    for b in pb: b.rotation_mode = 'XYZ'
    pb['upperarm_l'].rotation_euler = (math.radians(-60), 0, math.radians(-30))
    pb['lowerarm_l'].rotation_euler = (math.radians(-70), 0, 0)
    pb['upperarm_r'].rotation_euler = (math.radians(40), 0, 0)
    pb['thigh_l'].rotation_euler = (math.radians(-50), 0, 0); pb['calf_l'].rotation_euler = (math.radians(70), 0, 0)
    pb['spine_02'].rotation_euler = (math.radians(15), 0, 0); pb['head'].rotation_euler = (0, 0, math.radians(30))
    for f in ('index', 'middle', 'ring', 'pinky'):
        for j in (1, 2, 3): pb[f'{f}_0{j}_r'].rotation_euler = (math.radians(60), 0, 0)
shot(f'{TAG}_pose', (2.2, -2.6 - n * .5, 1.2), (0, 0, .9), 35, (1200 if n > 2 else 800, 900), 8)
print('##CHECK DONE', flush=True)
