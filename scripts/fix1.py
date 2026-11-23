import sys
R=sys.argv[1]
def patch(fn, pairs):
    p=f'{R}/scripts/{fn}'; s=open(p,encoding='utf8').read()
    for a,b in pairs:
        if s.count(a)!=1: print('MISS',fn,s.count(a),a[:70]); continue
        s=s.replace(a,b)
    open(p,'w',encoding='utf8').write(s)
patch('cast.py',[
 ("half * 1.25","half * 1.06"),
 (".007 - .006",".007 - .009"),
 ("< .021 - .009 *","< .0155 - .012 *"),
 ("(.16, .14, .12, 1)","(.20, .17, .145, 1)"),
 ("for _ in range(26):","for _ in range(30):"),
 ("q = p + Vector((side * rr.uniform(.001, .005), -.0015, -rr.uniform(.004, .009)))","q = p + Vector((side * rr.uniform(.001, .004), -.001, -rr.uniform(.003, .006)))"),
 ("n = len(V); V += [p - Vector((.0005, 0, 0)), p + Vector((.0005, 0, 0)), q]","n = len(V); V += [p - Vector((.00035, 0, 0)), p + Vector((.00035, 0, 0)), q]"),
 ("hair='ponytail01', hc=(.03, .018, .012)","hair='long01', hc=(.02, .012, .009)"),
 ("        elif o == body: o['part'] = 'body'","""        elif 'high-poly' in n:
            o['part'] = 'eyes'
            for slot in o.material_slots:
                t = slot.material.node_tree
                for q in t.nodes:
                    if q.type == 'BSDF_PRINCIPLED': tint_mul(t, q, (.62, .72, .72)); q.inputs['Roughness'].default_value = .12
        elif o == body: o['part'] = 'body'"""),
])
patch('sets.py',[
 ("def gurney(parent=None, recline=38","def gurney(parent=None, recline=47"),
 ("x = (i / nx - .5) * .72; y = -1.0 + j / ny * 1.0","x = (i / nx - .5) * .74; y = -1.06 + j / ny * 1.03"),
 ("body = math.exp(-(x / .22) ** 4); up = ss(-.45, -.05, y)","body = math.exp(-(x / .24) ** 4); up = ss(-.85, -.30, y)"),
 ("z = .80 + lerp(.13 * legs, .20 * body, up) + .07 * math.exp(-((y + .9) / .09) ** 2) * legs",
  "z = .80 + lerp(.16 * legs, (.215 + .04 * legs) * body, up) + .16 * math.exp(-((y + .92) / .10) ** 2) * legs"),
 ("(0, -.05, TABLE_Z - .025), (.95, 1.15, .05)","(0, -.05, TABLE_Z - .025), (.82, 1.15, .05)"),
 ("for x in (-.4, .4):\n        for y in (-.53, .43)","for x in (-.35, .35):\n        for y in (-.53, .43)"),
 ("((0, .86, 0), (-.82, .1, 90), (.82, .1, -90), (.82, -.5, -90))","((0, .86, 0), (-.70, .22, 90), (.70, .22, -90))"),
 ("((-.28, .05), (.28, .12), (.28, -.42))","((-.24, .10), (.25, .22), (.25, -.25))"),
 ("(.12, .15, z))","(.07, .12, z))"),
])
patch('shots.py',[
 ("bend=(24 + br, 0, 0), head=head","bend=(34 + br, 0, 0), head=head"),
 ("hand_l=(w(at, yaw, (.27, -.16, .99)), left(yaw)), hand_r=(w(at, yaw, (-.27, -.16, .98)), -left(yaw))","hand_l=(w(at, yaw, (.27, -.22, 1.02)), left(yaw)), hand_r=(w(at, yaw, (-.27, -.22, 1.01)), -left(yaw))"),
 ("hd = [10, 7 * ss(8.5, 9.4, t), 3 * math.sin(t * 1.6)]","hd = [16, 7 * ss(8.5, 9.4, t), 3 * math.sin(t * 1.6)]"),
 ("(V((.27, -.16, .99)).lerp(V((.30, -.22, 1.50)), up)","(V((.27, -.22, 1.02)).lerp(V((.30, -.30, 1.52)), up)"),
 ("(V((-.28, -.16, .97)).lerp(V((-.30, -.24, 1.36)), tr)","(V((-.28, -.22, 1.00)).lerp(V((-.30, -.30, 1.38)), tr)"),
 ("(V((.27, -.16, .99)).lerp(V((.25, -.20","(V((.27, -.22, 1.02)).lerp(V((.25, -.28"),
 ("hd = [10 + 5 * math.sin","hd = [16 + 5 * math.sin"),
 ("hd = [track([(10.2, 8), (10.8, 14), (11.6, 18)], t)","hd = [track([(10.2, 14), (10.8, 20), (11.6, 24)], t)"),
 ("camera([(T0, head + V((.10, -1.35, .12)), head + V((0, 0, -.06)), 60, 3.5), (T1, head + V((-.10, -.74, .05)), head + V((0, 0, -.03)), 66, 3.2)]",
  "camera([(T0, head + facing * 1.25 + V((.16, 0, .06)), head + V((0, 0, -.05)), 58, 3.5), (T1, head + facing * .70 + V((-.06, 0, .03)), head + V((0, 0, -.025)), 64, 3.2)]"),
 ("camera([(T0, (.25, -2.15, 1.78), (0, .15, 1.20), 42, 4), (T1, (0, -1.80, 1.62), (0, .15, 1.24), 45, 4)]",
  "camera([(T0, (.20, -1.95, 1.98), (0, .10, 1.22), 42, 4), (T1, (0, -1.62, 1.86), (0, .10, 1.26), 45, 4)]"),
 ("camera([(T0, head + V((-.50, -1.30, .16)), head + V((.10, .03, -.08)), 50, 3.5), (13.5, head + V((-.18, -.95, .07)), head + V((.02, 0, -.05)), 58, 3.2),\n                (T1, head + V((.05, -.72, .03)), head + V((0, 0, -.05)), 64, 3.2)]",
  "camera([(T0, head + facing * 1.30 + V((-.45, 0, .02)), head + V((.14, .03, 0)), 42, 3.5), (13.5, head + facing * .95 + V((-.20, 0, .02)), head + V((.05, 0, -.03)), 52, 3.2),\n                (T1, head + facing * .68, head + V((0, 0, -.04)), 62, 3.2)]"),
 ("sip)\n        hr = hr.lerp","sip)\n        hr = hr.lerp") if False else ("lerp(V((-.15, .66, 1.12)), sip)","lerp(V((-.17, .62, 1.00)), sip)"),
 ("(('wife', (-.80, .12, 0), 90, 1), ('son', (.80, .12, 0), -90, 2), ('daughter', (.80, -.50, 0), -90, 3))","(('wife', (-.70, .22, 0), 90, 1), ('son', (.70, .22, 0), -90, 2))"),
 ("    if SHOT == '2a':\n        camera([(T0, (.12, -2.45, 1.62), (0, .7, 1.28), 38, 4), (T1, (-.05, -1.75, 1.45), (-.05, .75, 1.20), 43, 3.5)]",
"""    a = actor('daughter'); at = (.50, 1.22, 0)
    def girl(t):
        k = ss(6.8, 7.2, t); h = {}
        for sd, x in (('l', .12), ('r', -.12)):
            h['hand_' + sd] = (w(at, -15, (x, -.30, 1.02)).lerp(w(at, -15, (x * .7, -.17, 1.36)), k), DOWN + left(-15) * (1 if sd == 'l' else -1))
        return stand(a, at, -15, t, (14, 0, -18), 8, h, 2)
    a.perform(girl, F0, F1)
    a.face([(3.3, emo('happy')), (6.55, emo('happy')), (6.95, emo('shock'))], T0, T1)
    if SHOT == '2a':
        camera([(T0, (.15, -2.15, 1.58), (0, .55, 1.28), 28, 4.5), (T1, (-.05, -1.60, 1.42), (-.04, .62, 1.18), 32, 4)]"""),
 ("people = [('doc', .36, .15, 0, 'ask'), ('doc2', -.36, .22, 5, 'ask')","people = [('doc', .27, .15, 0, 'ask'), ('doc2', -.27, .22, 5, 'ask')"),
 ("a.face([(T0, emo('focus') if isdoc else emo(e)), (T0 + .5, emo(e))], T0, T1, talk=(15.4, 17.5) if nm == 'doc' else None)","a.face([(T0, emo('focus') if isdoc else emo(e)), (T0 + .5, emo(e))], T0, T1)"),
 ("camera([(T0, m + V((.25, -2.1, .02)), m + V((0, 0, -.17)), 44, 2.8), (T1, m + V((.05, -1.65, 0)), m + V((0, 0, -.13)), 46, 2.8)]",
  "camera([(T0, m + V((.2, -2.5, .02)), m + V((0, 0, -.17)), 39, 2.8), (T1, m + V((.03, -2.05, 0)), m + V((0, 0, -.13)), 41, 2.8)]"),
 ("camera([(T0, (3.5, -7.3, 2.15), (-.55, .2, 1.75), 36, 4), (T1, (2.6, -5.9, 1.85), (-.3, .6, 1.7), 37, 4)]",
  "camera([(T0, (4.1, -6.6, 2.7), (-.75, -.1, 1.75), 33, 4), (T1, (3.2, -5.2, 2.3), (-.35, .4, 1.65), 35, 4)]"),
])
