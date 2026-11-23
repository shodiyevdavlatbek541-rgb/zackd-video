"""Quick look at the BodyParts3D skin scan: front + side workbench renders and slice stats."""
import bpy, sys, json
from mathutils import Vector
SRC, OUT = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=SRC + '/FJ2810.obj', forward_axis='Y', up_axis='Z')
o = bpy.context.selected_objects[0]
for v in o.data.vertices: v.co = v.co / 1000
o.data.update()
S = bpy.context.scene; S.render.engine = 'BLENDER_WORKBENCH'
S.render.resolution_x, S.render.resolution_y = 500, 900
cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; cd.ortho_scale = 1.9
c = bpy.data.objects.new('c', cd); S.collection.objects.link(c); S.camera = c
for name, loc, rot in (('front', (0, -5, .82), (1.5708, 0, 0)), ('side', (5, 0, .82), (1.5708, 0, 1.5708))):
    c.location = loc; c.rotation_euler = rot
    S.render.filepath = f'{OUT}/scan_{name}.png'; bpy.ops.render.render(write_still=True)
# horizontal slices: x-extent clusters at several heights
vs = [v.co.copy() for v in o.data.vertices]
rep = {}
for z in [i / 100 for i in range(5, 170, 5)]:
    xs = sorted(round(v.x, 3) for v in vs if abs(v.z - z) < .004)
    clus, cur = [], [xs[0]] if xs else []
    for x in xs[1:]:
        if x - cur[-1] > .02: clus.append((cur[0], cur[-1])); cur = [x]
        else: cur.append(x)
    if cur: clus.append((cur[0], cur[-1]))
    rep[z] = clus
json.dump({str(k): v for k, v in rep.items()}, open(OUT + '/scan_slices.json', 'w'), indent=0)
print('##SCAN', len(vs), flush=True)
