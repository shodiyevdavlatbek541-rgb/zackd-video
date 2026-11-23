"""Realism pass applied to every shot after it is built: ray-traced light, skin SSS + pores,
cloth weave + folds, hair sheen, surface micro-variation, filmic colour, motion blur."""
import bpy


def _bsdf(m):
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m and m.use_nodes else None


def _bump(m, b, scale, strength, dist=.002, kind='noise', coord='Object', detail=2.0):
    """Chain a procedural bump in front of whatever already drives the normal."""
    N, L = m.node_tree.nodes, m.node_tree.links
    tc = N.new('ShaderNodeTexCoord')
    if kind == 'wave':
        t = N.new('ShaderNodeTexWave'); t.wave_type = 'BANDS'; t.bands_direction = 'DIAGONAL'
        t.inputs['Distortion'].default_value = .6
    else:
        t = N.new('ShaderNodeTexNoise'); t.inputs['Detail'].default_value = detail
    t.inputs['Scale'].default_value = scale
    L.new(tc.outputs[coord], t.inputs['Vector'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = strength; bp.inputs['Distance'].default_value = dist
    L.new(t.outputs[0] if kind == 'wave' else t.outputs['Fac'], bp.inputs['Height'])
    nin = b.inputs['Normal']
    if nin.links:
        L.new(nin.links[0].from_socket, bp.inputs['Normal'])
    L.new(bp.outputs['Normal'], nin)
    return t


def _rough_var(m, b, lo, hi, scale=3.0):
    N, L = m.node_tree.nodes, m.node_tree.links
    r = b.inputs['Roughness']
    if r.links: return
    tc = N.new('ShaderNodeTexCoord'); t = N.new('ShaderNodeTexNoise'); t.inputs['Scale'].default_value = scale
    L.new(tc.outputs['Object'], t.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange'); mr.inputs[3].default_value = lo; mr.inputs[4].default_value = hi
    mr.inputs[1].default_value = .3; mr.inputs[2].default_value = .7
    L.new(t.outputs['Fac'], mr.inputs[0]); L.new(mr.outputs[0], r)


def apply(S, heavy=True):
    e = S.eevee
    for k, v in dict(use_raytracing=True, ray_tracing_method='SCREEN', use_fast_gi=True,
                     fast_gi_method='GLOBAL_ILLUMINATION', fast_gi_distance=1.5, fast_gi_resolution='2',
                     shadow_ray_count=2, shadow_step_count=6, use_shadows=True,
                     taa_render_samples=32 if heavy else 18).items():
        try: setattr(e, k, v)
        except Exception as x: print('##REAL skip', k, x, flush=True)
    try:
        e.ray_tracing_options.resolution_scale = '2'
        e.ray_tracing_options.use_denoise = True
    except Exception as x: print('##REAL skip rt opts', x, flush=True)
    vs = S.view_settings
    try:
        vs.view_transform = 'AgX'; vs.look = 'AgX - Medium High Contrast'
    except Exception:
        try: vs.look = 'Medium High Contrast'
        except Exception as x: print('##REAL skip look', x, flush=True)
    vs.exposure = .05
    S.render.use_motion_blur = True
    try: S.render.motion_blur_shutter = .45; e.motion_blur_steps = 1
    except Exception: pass

    for o in S.objects:                       # every lamp casts a soft shadow
        if o.type == 'LIGHT':
            o.data.use_shadow = True
            if o.data.type in ('POINT', 'SPOT'): o.data.shadow_soft_size = max(o.data.shadow_soft_size, .15)

    who_parts = {}
    for o in S.objects:
        if o.type == 'MESH':
            for s in o.material_slots:
                if s.material: who_parts.setdefault(s.material.name, set()).add(o.get('part') or ('char' if o.get('who') else 'set'))
    done = 0
    for m in bpy.data.materials:
        if m.name not in who_parts or m.get('_real'): continue
        b = _bsdf(m)
        if not b: continue
        m['_real'] = 1; parts = who_parts[m.name]
        if 'body' in parts:
            b.inputs['Subsurface Weight'].default_value = .22
            b.inputs['Subsurface Radius'].default_value = (1.0, .35, .2)
            b.inputs['Subsurface Scale'].default_value = .012
            b.inputs['Roughness'].default_value = .44
            b.inputs['Specular IOR Level'].default_value = .42
            for n in m.node_tree.nodes:      # earlier tint was too orange
                if n.type == 'VECT_MATH' and n.operation == 'MULTIPLY' and not n.inputs[1].links:
                    c = n.inputs[1].default_value
                    n.inputs[1].default_value = (1.0, min(1, c[1] + .1), min(1, c[2] + .13))
            _bump(m, b, 2200, .09, .0008)
            _bump(m, b, 160, .05, .002, detail=5)
        elif 'suit' in parts:
            b.inputs['Sheen Weight'].default_value = .45; b.inputs['Sheen Roughness'].default_value = .45
            b.inputs['Roughness'].default_value = .86
            _bump(m, b, 900, .12, .0006, 'wave')      # weave
            _bump(m, b, 7, .35, .02, detail=3)        # soft folds
        elif 'hair' in parts or 'moustache' in parts or 'brow' in parts:
            b.inputs['Roughness'].default_value = .36
            b.inputs['Coat Weight'].default_value = .15
            try: b.inputs['Anisotropic'].default_value = .5
            except Exception: pass
            _bump(m, b, 400, .25, .001, 'wave', 'UV')
        elif parts & {'eyes', 'teeth_base', 'tongue01', 'eyelashes01'} or 'char' in parts:
            continue
        else:                                  # props and sets: no perfectly clean CG surfaces
            if b.inputs['Emission Strength'].default_value > 0 or b.inputs['Alpha'].default_value < 1: continue
            if b.inputs['Metallic'].default_value > .5:
                _rough_var(m, b, .18, .42, 4)
            else:
                rr = b.inputs['Roughness'].default_value
                _rough_var(m, b, max(.05, rr - .15), min(1, rr + .12), 2.5)
                _bump(m, b, 260, .04, .001)
        done += 1
    print('##REAL materials', done, flush=True)
