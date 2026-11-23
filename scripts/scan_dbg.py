import bpy
from mathutils import Vector as V
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    me = o.data
    zs = [v.co.z for v in me.vertices]
    c = sum((v.co for v in me.vertices), V()) / max(1, len(me.vertices))
    # average normal . (v - centre axis) -> outward if positive
    out = 0
    for v in list(me.vertices)[::max(1, len(me.vertices) // 400)]:
        r = v.co - V((0, -.06, v.co.z)); r.z = 0
        out += 1 if v.normal.dot(r) > 0 else -1
    print('##OBJ', o.name, len(me.vertices), round(min(zs), 3), round(max(zs), 3), 'outward', out, [m.name for m in me.materials][:3],
          [md.type for md in o.modifiers])
