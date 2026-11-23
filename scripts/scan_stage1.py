import sys, bpy
exec(compile(open(sys.argv[sys.argv.index('--') + 1] + '/scripts/scan_cast.py', encoding='utf8').read(), 'scan_cast', 'exec'))
skin0.hide_set(False); skin0.hide_render = False
mt = bpy.data.materials.new('j'); mt.diffuse_color = (1, .1, .1, 1)
for n, (h, t, p) in SKEL.items():
    for q, r in ((h, .008), ((h + t) / 2, .004)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=q, segments=8, ring_count=6); bpy.context.object.data.materials.append(mt)
S.render.engine = 'BLENDER_WORKBENCH'; S.display.shading.color_type = 'MATERIAL'; S.display.shading.show_xray = True; S.display.shading.xray_alpha = .45
S.render.resolution_x, S.render.resolution_y = 600, 1000
cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'
c = bpy.data.objects.new('c', cd); S.collection.objects.link(c); S.camera = c
for name, loc, rot, sc, z in (('front', (0, -5, .88), (1.5708, 0, 0), 1.85, 0), ('side', (5, 0, .88), (1.5708, 0, 1.5708), 1.85, 0),
                              ('hand', (.3, -5, .8), (1.5708, 0, 0), .4, 0), ('face', (0, -5, 1.55), (1.5708, 0, 0), .3, 0)):
    c.location = loc; c.rotation_euler = rot; cd.ortho_scale = sc
    S.render.filepath = ROOT + f'/chk/rig_{name}.png'; bpy.ops.render.render(write_still=True)
log('stage1 done')
