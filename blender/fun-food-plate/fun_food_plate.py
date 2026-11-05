"""Fun Food Plate: a top-down plate where each food is first scribbled in crayon,
then pops into a real 3D food.

Run headless:
    blender -b -P fun_food_plate.py -- --out /path/to/frames/ [--still FRAME] [--res 720] [--samples 32]

Writes PNG frames (or a single still) plus events.json (frame numbers of every
scribble and pop) for the soundtrack script.
"""
import bpy, bmesh, math, random, sys, json, os
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return type(default)(argv[argv.index(name) + 1]) if name in argv else default
OUT = arg("--out", "/tmp/fun_food_frames/")
STILL = arg("--still", -1)
RES = arg("--res", 720)
SAMPLES = arg("--samples", 32)

random.seed(7)
FPS = 30

# ---------------------------------------------------------------- reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS

def link(obj, parent=None):
    if obj.name not in scene.collection.objects:
        scene.collection.objects.link(obj)
    if parent:
        obj.parent = parent
    return obj

def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True

def subsurf(obj, lv=2):
    m = obj.modifiers.new("sub", "SUBSURF"); m.levels = lv; m.render_levels = lv
    return m

def active(obj):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

# ---------------------------------------------------------------- materials
def mat(name, color, rough=0.5, spec=0.5, sss=0.0, trans=0.0, coat=0.0, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = spec
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.3, 0.12, 0.06)
        b.inputs["Subsurface Scale"].default_value = 0.05
    if trans:
        b.inputs["Transmission Weight"].default_value = trans
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    return m

def mottle(m, c2, scale=8.0, amount=1.0, bump=0.0, bump_scale=60.0, voronoi=False):
    """Mix the base colour with c2 through a noise texture, optionally bump."""
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]
    c1 = tuple(b.inputs["Base Color"].default_value)
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = c1
    ramp.color_ramp.elements[1].position = 0.35 + 0.4 / max(amount, 0.01)
    ramp.color_ramp.elements[1].color = (*c2, 1)
    L.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], b.inputs["Base Color"])
    if bump:
        if voronoi:
            tex = N.new("ShaderNodeTexVoronoi"); tex.feature = "DISTANCE_TO_EDGE"
            tex.inputs["Scale"].default_value = bump_scale
            out = tex.outputs["Distance"]
        else:
            tex = N.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = bump_scale
            tex.inputs["Detail"].default_value = 8
            out = tex.outputs["Fac"]
        L.new(tc.outputs["Object"], tex.inputs["Vector"])
        bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.01
        L.new(out, bp.inputs["Height"])
        L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def crayon_mat(name, color):
    """Flat crayon colour, broken up by grain so it reads as wax on paper."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    N.remove(N["Principled BSDF"])
    out = N["Material Output"]
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = 1.0
    tr = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader")
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 260
    nz.inputs["Detail"].default_value = 4
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.4; ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    L.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], mix.inputs["Fac"])
    L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    m.blend_method = "BLEND"
    return m

# ---------------------------------------------------------------- mesh helpers
def lathe(name, profile, segs=96):
    """Revolve (r, z) profile points round the z axis."""
    bm = bmesh.new(); rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segs),
                                        r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            if len(a) == 1:
                bm.faces.new((a[0], b[i], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[i], b[0], a[j]))
            else:
                bm.faces.new((a[i], b[i], b[j], a[j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); link(ob); smooth(ob)
    return ob

def cylinder(name, r, h, loc, m, parent=None, verts=48, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
    ob = bpy.context.object; ob.name = name; ob.data.materials.append(m)
    if bevel:
        bv = ob.modifiers.new("bev", "BEVEL"); bv.width = bevel; bv.segments = 3
        bv.limit_method = "ANGLE"
        smooth(ob); ob.data.shade_auto_smooth() if hasattr(ob.data, "shade_auto_smooth") else None
    if parent:
        ob.parent = parent
    return ob

def sphere(name, r, loc, scale, m, parent=None, seg=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=r, location=loc)
    ob = bpy.context.object; ob.name = name; ob.scale = scale
    ob.data.materials.append(m); smooth(ob)
    if parent:
        ob.parent = parent
    return ob

def poly_curve(name, pts, depth, m, parent=None, cyclic=False):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = depth; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, (x, y, z) in zip(sp.points, pts):
        p.co = (x, y, z, 1)
    sp.use_cyclic_u = cyclic
    ob = bpy.data.objects.new(name, cu); link(ob, parent); cu.materials.append(m)
    return ob

def smooth_noise(n_terms=4, amp=1.0):
    ph = [(random.uniform(0, 6.28), random.randint(2, 7)) for _ in range(n_terms)]
    return lambda t: amp * sum(math.sin(k * t + p) / k for p, k in ph)

def group(name, x, y, rot=0.0):
    e = bpy.data.objects.new(name, None); link(e)
    e.location = (x, y, 0); e.rotation_euler = (0, 0, math.radians(rot))
    return e

TOP = 0.045  # height of the plate's flat top

# ---------------------------------------------------------------- set & lights
bg_mat = mat("tablecloth", (0.55, 0.6, 0.8), rough=0.9, spec=0.2)
mottle(bg_mat, (0.62, 0.66, 0.85), scale=1.2, amount=0.6, bump=0.04, bump_scale=300)
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
bpy.context.object.data.materials.append(bg_mat)

plate_mat = mat("ceramic", (0.93, 0.93, 0.91), rough=0.18, spec=0.6, coat=0.4)
plate = lathe("plate", [(0, TOP), (0.98, TOP), (1.06, 0.06), (1.2, 0.12), (1.33, 0.155),
                         (1.37, 0.15), (1.38, 0.135), (1.34, 0.12), (1.18, 0.06),
                         (0.9, 0.012), (0.88, 0.0), (0.6, 0.0), (0.58, 0.01), (0, 0.01)])
plate.data.materials.append(plate_mat); subsurf(plate, 2)

world = bpy.data.worlds.new("world"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.72, 0.76, 0.9, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55

sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 3.2; sun.angle = math.radians(14)
sun.color = (1.0, 0.97, 0.92)
so = bpy.data.objects.new("sun", sun); link(so)
so.rotation_euler = Euler((math.radians(32), math.radians(-18), math.radians(-30)))

fill = bpy.data.lights.new("fill", "AREA"); fill.energy = 120; fill.size = 6
fo = bpy.data.objects.new("fill", fill); link(fo); fo.location = (-3, 3, 6)
fo.rotation_euler = (math.radians(-30), math.radians(-30), 0)

cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"; cam.ortho_scale = 4.95
co = bpy.data.objects.new("cam", cam); link(co); co.location = (0, -0.35, 10)
scene.camera = co

# ---------------------------------------------------------------- foods
foods = []  # (group empty, footprint ellipses, outline colour, fill colour)

def add_food(g, prints, outline, fill):
    foods.append(dict(g=g, prints=prints, outline=outline, fill=fill))

# 1. Sprinkle donut ------------------------------------------------------
def make_donut():
    g = group("donut", -0.4, 0.42, 10)
    R, r = 0.27, 0.125
    dough = mottle(mat("dough", (0.78, 0.47, 0.2), rough=0.6, sss=0.15),
                   (0.55, 0.28, 0.1), scale=6, amount=0.8, bump=0.25, bump_scale=40)
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=72,
                                     minor_segments=36, location=(0, 0, TOP + r * 0.8))
    d = bpy.context.object; d.scale.z = 0.8; d.data.materials.append(dough); smooth(d); d.parent = g
    # icing: the top of a slightly fatter torus, cut with a wavy drip line
    icing = mat("icing", (1.0, 0.36, 0.62), rough=0.22, spec=0.6, sss=0.1, coat=0.6)
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r * 1.06, major_segments=144,
                                     minor_segments=48, location=(0, 0, 0))
    ic = bpy.context.object
    wave = smooth_noise(5, 0.025)
    bm = bmesh.new(); bm.from_mesh(ic.data)
    kill = [v for v in bm.verts if v.co.z < -0.02 + wave(math.atan2(v.co.y, v.co.x))
            + 0.012 * math.sin(11 * math.atan2(v.co.y, v.co.x))]
    bmesh.ops.delete(bm, geom=kill, context="VERTS"); bm.to_mesh(ic.data); bm.free()
    ic.location = (0, 0, TOP + r * 0.8); ic.scale.z = 0.8
    ic.data.materials.append(icing); smooth(ic)
    s = ic.modifiers.new("thick", "SOLIDIFY"); s.thickness = 0.012; s.offset = 1
    subsurf(ic, 1); ic.parent = g
    # sprinkles
    cols = [(1, 0.85, 0.1), (0.2, 0.55, 1), (0.25, 0.85, 0.4), (1, 1, 1), (0.6, 0.3, 0.95), (1, 0.45, 0.1)]
    smats = [mat(f"sprinkle{i}", c, rough=0.35, coat=0.3) for i, c in enumerate(cols)]
    for i in range(75):
        phi = random.uniform(0, 2 * math.pi); psi = random.uniform(math.radians(35), math.radians(145))
        rr = r * 1.06 + 0.018
        x = (R + rr * math.cos(psi)) * math.cos(phi); y = (R + rr * math.cos(psi)) * math.sin(phi)
        z = TOP + r * 0.8 + rr * math.sin(psi) * 0.8
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.011, depth=0.05, location=(x, y, z))
        sp = bpy.context.object
        sp.rotation_euler = (math.radians(90), 0, random.uniform(0, math.pi))
        bv = sp.modifiers.new("b", "BEVEL"); bv.width = 0.008; bv.segments = 3
        sp.data.materials.append(smats[i % len(smats)]); smooth(sp); sp.parent = g
    add_food(g, [(-0.4, 0.42, 0.42, 0.40, 10)], (0.55, 0.25, 0.1), (1.0, 0.45, 0.65))

# 2. Sushi rolls ---------------------------------------------------------
def make_sushi():
    g = group("sushi", 0.38, 0.48)
    nori = mottle(mat("nori", (0.03, 0.07, 0.04), rough=0.55, spec=0.4),
                  (0.08, 0.14, 0.06), scale=30, amount=0.7, bump=0.3, bump_scale=80)
    rice = mottle(mat("rice", (0.97, 0.96, 0.92), rough=0.35, sss=0.3),
                  (0.86, 0.85, 0.8), scale=60, amount=0.6, bump=0.9, bump_scale=48, voronoi=True)
    salmon = mat("salmon", (1.0, 0.38, 0.15), rough=0.25, sss=0.4, coat=0.3)
    nt = salmon.node_tree  # fat stripes
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 18
    wv.inputs["Distortion"].default_value = 3
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = (1.0, 0.38, 0.15, 1); rp.color_ramp.elements[0].position = 0.7
    rp.color_ramp.elements[1].color = (1.0, 0.8, 0.68, 1); rp.color_ramp.elements[1].position = 0.85
    nt.links.new(wv.outputs["Fac"], rp.inputs["Fac"])
    nt.links.new(rp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    cucumber = mat("cucumber", (0.45, 0.8, 0.3), rough=0.3, sss=0.3)
    avocado = mat("avocado", (0.75, 0.85, 0.35), rough=0.45)
    roe = mat("roe", (1.0, 0.3, 0.02), rough=0.08, trans=0.4, coat=1.0)
    rolls = [(-0.16, 0.14), (0.17, -0.06), (-0.18, -0.2)]
    for i, (x, y) in enumerate(rolls):
        h = 0.15
        cylinder("nori", 0.17, h, (x, y, TOP + h / 2), nori, g, 64, bevel=0.006)
        cylinder("rice", 0.158, h + 0.012, (x, y, TOP + h / 2 + 0.006), rice, g, 64, bevel=0.02)
        ang = random.uniform(0, 6.28)
        cylinder("salmon", 0.055, h + 0.022, (x + 0.02 * math.cos(ang), y + 0.02 * math.sin(ang), TOP + h / 2 + 0.01),
                 salmon, g, 32, bevel=0.01).rotation_euler.z = ang
        cylinder("cuke", 0.03, h + 0.02, (x + 0.06 * math.cos(ang + 2.2), y + 0.06 * math.sin(ang + 2.2), TOP + h / 2 + 0.01),
                 cucumber, g, 24, bevel=0.008)
        cylinder("avo", 0.032, h + 0.02, (x + 0.06 * math.cos(ang - 2.0), y + 0.06 * math.sin(ang - 2.0), TOP + h / 2 + 0.01),
                 avocado, g, 24, bevel=0.008)
        if i == 0:  # roe on top of one roll
            for k in range(28):
                a = random.uniform(0, 6.28); rr = 0.14 * math.sqrt(random.random())
                sphere("roe", 0.014, (x + rr * math.cos(a), y + rr * math.sin(a), TOP + h + 0.022), (1, 1, 1), roe, g, 12, 8)
    wasabi = mottle(mat("wasabi", (0.55, 0.75, 0.2), rough=0.6), (0.4, 0.6, 0.1), 20, 0.8, 0.4, 50)
    w = sphere("wasabi", 0.07, (0.2, 0.24, TOP + 0.02), (1.1, 0.9, 0.55), wasabi, g)
    dp = w.modifiers.new("d", "DISPLACE"); tx = bpy.data.textures.new("wn", "CLOUDS"); tx.noise_scale = 0.3
    dp.texture = tx; dp.strength = 0.03; subsurf(w, 1)
    add_food(g, [(0.38 + x, 0.48 + y, 0.2, 0.19, 0) for x, y in rolls] + [(0.58, 0.72, 0.08, 0.07, 0)],
             (0.1, 0.25, 0.15), (1.0, 0.5, 0.2))

# 3. Pizza slice ---------------------------------------------------------
def make_pizza():
    ang = -22
    g = group("pizza", 0.06, -0.05, ang)
    L, half = 0.74, math.radians(23)
    cheese = mottle(mat("cheese", (1.0, 0.72, 0.18), rough=0.3, sss=0.2, coat=0.3),
                    (0.95, 0.5, 0.08), scale=9, amount=0.5, bump=0.4, bump_scale=25)
    sauce = mat("sauce", (0.75, 0.12, 0.04), rough=0.4)
    crust = mottle(mat("crust", (0.85, 0.55, 0.22), rough=0.6), (0.6, 0.32, 0.1), 7, 0.7, 0.3, 30)
    def wedge(name, rad, h, z, m):
        bm = bmesh.new(); vs = [bm.verts.new((0.04, 0, 0))]
        for i in range(25):
            a = -half + 2 * half * i / 24
            vs.append(bm.verts.new((rad * math.cos(a), rad * math.sin(a), 0)))
        f = bm.faces.new(vs)
        ext = bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(bm, vec=(0, 0, h), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); link(ob, g); ob.location.z = z; me.materials.append(m)
        bv = ob.modifiers.new("b", "BEVEL"); bv.width = 0.012; bv.segments = 3; smooth(ob)
        return ob
    wedge("base", L, 0.03, TOP, crust)
    wedge("sauce", L - 0.03, 0.006, TOP + 0.03, sauce)
    ch = wedge("cheese", L - 0.06, 0.012, TOP + 0.034, cheese)
    # melty cheese edge
    dp = ch.modifiers.new("d", "DISPLACE"); tx = bpy.data.textures.new("cn", "CLOUDS"); tx.noise_scale = 0.08
    dp.texture = tx; dp.strength = 0.008
    pts = [(L * math.cos(-half - 0.03 + (2 * half + 0.06) * i / 30), L * math.sin(-half - 0.03 + (2 * half + 0.06) * i / 30), TOP + 0.045)
           for i in range(31)]
    poly_curve("crust_rim", pts, 0.05, crust, g).scale = (1, 1, 0.8)
    pep = mottle(mat("pepperoni", (0.7, 0.1, 0.06), rough=0.3, coat=0.5), (0.45, 0.04, 0.03), 25, 0.5, 0.3, 40)
    for (d, a) in [(0.2, 0.02), (0.38, -0.2), (0.4, 0.2), (0.55, 0.0)]:
        aa = a * half / 0.23 * 0.9
        cylinder("pep", 0.055, 0.014, (d * math.cos(aa), d * math.sin(aa), TOP + 0.05), pep, g, 32, bevel=0.006)
    basil = mat("basil", (0.15, 0.5, 0.12), rough=0.3, sss=0.2)
    for (d, a, rot) in [(0.3, -0.1, 30), (0.5, 0.15, -40)]:
        b = sphere("basil", 0.04, (d * math.cos(a), d * math.sin(a), TOP + 0.052), (1.6, 0.8, 0.12), basil, g)
        b.rotation_euler.z = math.radians(rot)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    cx, cy = 0.06 + 0.4 * ca, -0.05 + 0.4 * sa
    add_food(g, [(cx, cy, 0.4, 0.22, ang)], (0.65, 0.35, 0.05), (1.0, 0.75, 0.15))

# 4. Smiley fried egg ----------------------------------------------------
def make_egg():
    g = group("egg", -0.45, -0.3, 0)
    white = mat("eggwhite", (0.98, 0.97, 0.94), rough=0.15, sss=0.3, coat=0.5)
    nz = smooth_noise(5, 0.09)
    bm = bmesh.new(); vs = []
    for i in range(96):
        a = 2 * math.pi * i / 96; rr = 0.31 * (1 + nz(a))
        vs.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), 0)))
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, 0, 0.025), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
    me = bpy.data.meshes.new("eggwhite"); bm.to_mesh(me); bm.free()
    ew = bpy.data.objects.new("eggwhite", me); link(ew, g); ew.location.z = TOP; me.materials.append(white)
    bv = ew.modifiers.new("b", "BEVEL"); bv.width = 0.012; bv.segments = 4; smooth(ew)
    crisp = mottle(mat("crisp", (0.85, 0.6, 0.3), rough=0.5), (0.95, 0.85, 0.65), 14, 0.5, 0.4, 40)
    edge = [(0.31 * (1 + nz(a)) * math.cos(a), 0.31 * (1 + nz(a)) * math.sin(a), TOP + 0.014)
            for a in [2 * math.pi * i / 96 for i in range(96)]]
    poly_curve("crisp", edge, 0.016, crisp, g, cyclic=True)
    yolk = mat("yolk", (1.0, 0.55, 0.03), rough=0.08, sss=0.4, coat=1.0)
    sphere("yolk", 0.115, (0.0, 0.03, TOP + 0.03), (1, 1, 0.6), yolk, g, 48, 24)
    ketchup = mat("ketchup", (0.75, 0.04, 0.03), rough=0.1, coat=1.0)
    smile = [(0.17 * math.cos(a), -0.02 + 0.13 * math.sin(a), TOP + 0.035)
             for a in [math.radians(200 + 140 * i / 20) for i in range(21)]]
    poly_curve("smile", smile, 0.02, ketchup, g)
    for x in (-0.15, 0.15):
        sphere("eye", 0.03, (x, 0.13, TOP + 0.033), (1, 1, 0.5), ketchup, g)
    add_food(g, [(-0.45, -0.3, 0.34, 0.33, 0)], (0.9, 0.6, 0.1), (1.0, 0.8, 0.2))

# 5. Strawberries --------------------------------------------------------
def make_strawberry(name, x, y, rot, size):
    g = group(name, x, y, rot)
    red = mottle(mat("berry", (0.85, 0.04, 0.07), rough=0.2, sss=0.25, coat=0.6),
                 (0.55, 0.02, 0.04), scale=6, amount=0.7, bump=0.25, bump_scale=35)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, radius=1)
    b = bpy.context.object; b.name = name
    for v in b.data.vertices:
        t = max(0.0, min(1.0, (v.co.x + 1) / 2))
        k = 0.42 + 0.7 * t ** 0.8
        v.co.y *= k; v.co.z *= k
    b.scale = (size, size * 0.85, size * 0.75); b.location = (0, 0, TOP + size * 0.6)
    b.data.materials.append(red); smooth(b); b.parent = g
    bpy.context.view_layer.update()
    seed = mat("seed", (1.0, 0.85, 0.3), rough=0.3)
    vs = [v for v in b.data.vertices if v.co.z > -0.1 and -0.9 < v.co.x < 0.85]
    random.shuffle(vs)
    for v in vs[:55]:
        p = Vector((v.co.x * size, v.co.y * size * 0.85, v.co.z * size * 0.75 + TOP + size * 0.6))
        n = v.normal
        sd = sphere("seed", 0.008, p + n * 0.004, (1, 0.6, 0.6), seed, g, 8, 6)
    leaf = mottle(mat("leaf", (0.15, 0.55, 0.15), rough=0.4, sss=0.2), (0.05, 0.35, 0.05), 20, 0.7)
    for i in range(7):
        a = 2 * math.pi * i / 7
        lf = sphere("leaf", 1, (size * 1.0, 0.13 * size * math.cos(a), TOP + size * 0.6 + 0.13 * size * math.sin(a)),
                    (size * 0.12, size * 0.45, size * 0.06), leaf, g, 16, 8)
        lf.rotation_euler = (a - math.pi / 2, 0, 0)
    cylinder("stem", 0.012, 0.08, (size * 1.08, 0, TOP + size * 0.9), leaf, g, 8).rotation_euler.y = math.radians(55)
    return g

def make_strawberries():
    g1 = make_strawberry("berry1", 0.55, -0.66, 145, 0.18)
    g2 = make_strawberry("berry2", 0.22, -0.92, 100, 0.16)
    g = group("berries", 0, 0)
    for c in (g1, g2):
        c.parent = g
    add_food(g, [(0.54, -0.65, 0.21, 0.15, 145), (0.22, -0.9, 0.19, 0.14, 100)], (0.7, 0.05, 0.1), (1.0, 0.2, 0.25))

# 6. Macarons ------------------------------------------------------------
def make_macaron(name, x, y, col, rot=0, tilt=0):
    g = group(name, x, y, rot)
    shell = mottle(mat("shell", col, rough=0.55, sss=0.1), tuple(min(1, c * 1.1 + 0.05) for c in col),
                   8, 0.6, 0.2, 40)
    feet = mottle(mat("feet", tuple(c * 0.92 for c in col), rough=0.9), (1, 1, 1), 30, 0.4, 1.0, 120)
    cream = mat("cream", (0.98, 0.93, 0.85), rough=0.5, sss=0.2)
    r = 0.15; base = TOP + 0.0
    sphere("bottom", r, (0, 0, base + 0.03), (1, 1, 0.22), shell, g, 48, 24)
    bpy.ops.mesh.primitive_torus_add(major_radius=r * 0.93, minor_radius=0.016, location=(0, 0, base + 0.045))
    t = bpy.context.object; t.data.materials.append(feet); t.parent = g; smooth(t)
    cylinder("cream", r * 0.88, 0.035, (0, 0, base + 0.07), cream, g, 48, bevel=0.012)
    bpy.ops.mesh.primitive_torus_add(major_radius=r * 0.93, minor_radius=0.017, location=(0, 0, base + 0.095))
    t = bpy.context.object; t.data.materials.append(feet); t.parent = g; smooth(t)
    sphere("top", r, (0, 0, base + 0.105), (1, 1, 0.35), shell, g, 48, 24)
    if tilt:
        inner = group(name + "_tip", 0, 0); inner.parent = g
        for c in list(g.children):
            if c is not inner:
                c.parent = inner
        inner.rotation_euler.x = math.radians(tilt); inner.location.z = r * 0.95 - 0.06
    return g

def make_macarons():
    gs = [make_macaron("mac1", -0.02, -0.58, (0.4, 0.85, 0.65), 15, 90),
          make_macaron("mac2", -0.2, -0.88, (0.7, 0.5, 0.95), 0),
          make_macaron("mac3", 0.2, -0.42, (1.0, 0.75, 0.25), -20, 90)]
    g = group("macarons", 0, 0)
    for c in gs:
        c.parent = g
    add_food(g, [(-0.02, -0.58, 0.19, 0.14, 15), (-0.2, -0.88, 0.18, 0.18, 0), (0.2, -0.42, 0.19, 0.14, -20)],
             (0.4, 0.3, 0.7), (0.6, 0.9, 0.75))

# 7. Gummy bears ---------------------------------------------------------
def make_bear(name, x, y, rot, col):
    g = group(name, x, y, rot)
    mb = bpy.data.metaballs.new(name); mb.resolution = 0.012; mb.render_resolution = 0.006
    parts = [((0, 0, 0), 0.08, (0.9, 1.1, 0.7)), ((0, 0.115, 0), 0.066, (1.0, 0.9, 0.75)),
             ((-0.048, 0.165, 0), 0.026, (1, 1, 0.8)), ((0.048, 0.165, 0), 0.026, (1, 1, 0.8)),
             ((-0.068, 0.04, 0), 0.028, (1.1, 0.85, 0.8)), ((0.068, 0.04, 0), 0.028, (1.1, 0.85, 0.8)),
             ((-0.048, -0.085, 0), 0.034, (1, 1.1, 0.8)), ((0.048, -0.085, 0), 0.034, (1, 1.1, 0.8))]
    for co, r, sc in parts:
        e = mb.elements.new(); e.co = co; e.radius = r * 1.45; e.type = "ELLIPSOID"
        e.size_x, e.size_y, e.size_z = sc
    ob = bpy.data.objects.new(name + "_mb", mb); link(ob, g); ob.location.z = TOP + 0.07
    ob.scale = (1.55, 1.55, 1.4)
    gm = mat("gummy_" + name, col, rough=0.12, sss=0.6, trans=0.55, coat=0.8)
    mb.materials.append(gm)
    return g

def make_gummies():
    gs = [make_bear("bear_red", -0.88, 0.04, 18, (1.0, 0.08, 0.05)),
          make_bear("bear_green", -0.6, -0.8, -35, (0.3, 0.9, 0.1)),
          make_bear("bear_yellow", -0.03, 0.12, 70, (1.0, 0.75, 0.0))]
    g = group("gummies", 0, 0)
    for c in gs:
        c.parent = g
    add_food(g, [(-0.88, 0.04, 0.17, 0.24, 18), (-0.6, -0.8, 0.17, 0.24, -35), (-0.03, 0.12, 0.17, 0.24, 70)],
             (0.85, 0.1, 0.3), (1.0, 0.65, 0.1))

for maker in (make_donut, make_sushi, make_pizza, make_egg, make_strawberries, make_macarons, make_gummies):
    maker()

# ---------------------------------------------------------------- crayon scribbles
ZS = 0.6  # scribbles float above the food so nothing hides them

def outline_pts(cx, cy, rx, ry, rot):
    nz = smooth_noise(4, 0.06); pts = []
    start = random.uniform(0, 6.28); turns = 1.12
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for i in range(90):
        a = start + 2 * math.pi * turns * i / 89
        k = 1 + nz(a) + 0.05 * i / 89
        x, y = rx * k * math.cos(a), ry * k * math.sin(a)
        pts.append((cx + c * x - s * y, cy + s * x + c * y, ZS))
    return pts

def hatch_pts(cx, cy, rx, ry, rot):
    """Zig-zag fill like a kid colouring in, clipped to the ellipse."""
    ang = math.radians(rot + random.uniform(25, 50)); pts = []
    c0, s0 = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    step = 0.038
    rmax = max(rx, ry) * 0.86
    n = int(2 * rmax / step)
    for i in range(n + 1):
        v = -rmax + i * step
        # the chord of the ellipse along direction ang at offset v
        ca, sa = math.cos(ang - math.radians(rot)), math.sin(ang - math.radians(rot))
        # param line: p = v*(-sa, ca) + u*(ca, sa); solve ellipse (x/rx)^2+(y/ry)^2 = 0.82^2
        A = (ca / rx) ** 2 + (sa / ry) ** 2
        B = 2 * v * (-sa * ca / rx ** 2 + ca * sa / ry ** 2)
        C = (v * sa / rx) ** 2 + (v * ca / ry) ** 2 - 0.8 ** 2
        disc = B * B - 4 * A * C
        if disc <= 0:
            continue
        u1, u2 = (-B - math.sqrt(disc)) / (2 * A), (-B + math.sqrt(disc)) / (2 * A)
        if i % 2:
            u1, u2 = u2, u1
        for u in (u1, u2):
            x = -v * sa + u * ca + random.uniform(-0.012, 0.012)
            y = v * ca + u * sa + random.uniform(-0.012, 0.012)
            pts.append((cx + c0 * x - s0 * y, cy + s0 * x + c0 * y, ZS - 0.01))
    return pts

def key_hide(ob, frame, hidden):
    ob.hide_render = hidden; ob.keyframe_insert("hide_render", frame=frame)
    ob.hide_viewport = hidden; ob.keyframe_insert("hide_viewport", frame=frame)

def draw_on(ob, f0, f1):
    cu = ob.data
    cu.bevel_factor_mapping_end = "SPLINE"
    cu.bevel_factor_end = 0.0; cu.keyframe_insert("bevel_factor_end", frame=f0)
    cu.bevel_factor_end = 1.0; cu.keyframe_insert("bevel_factor_end", frame=f1)
    for fc in cu.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "SINE"; kp.easing = "EASE_IN_OUT"

def pop(g, f):
    keys = [(f - 1, 0.0), (f, 0.35), (f + 3, 1.16), (f + 6, 0.94), (f + 9, 1.03), (f + 12, 1.0)]
    for fr, s in keys:
        g.scale = (max(s, 1e-4),) * 3; g.keyframe_insert("scale", frame=fr)

events = []
frame = 14
for food in foods:
    g = food["g"]
    out_m = crayon_mat("crayon_line", food["outline"])
    fill_m = crayon_mat("crayon_fill", food["fill"])
    strokes = []; t = frame
    for (cx, cy, rx, ry, rot) in food["prints"]:
        o = poly_curve("scribble_outline", outline_pts(cx, cy, rx, ry, rot), 0.016, out_m)
        h = poly_curve("scribble_fill", hatch_pts(cx, cy, rx, ry, rot), 0.021, fill_m)
        draw_on(o, t, t + 7); draw_on(h, t + 6, t + 14)
        events.append(dict(type="scribble", start=t, end=t + 14))
        strokes += [(o, t), (h, t + 6)]
        t += 5 if len(food["prints"]) > 2 else 7
    end = t - (5 if len(food["prints"]) > 2 else 7) + 14
    pop_f = end + 4
    for ob, st in strokes:
        key_hide(ob, 0, True); key_hide(ob, st, False); key_hide(ob, pop_f, True)
    pop(g, pop_f)
    events.append(dict(type="pop", frame=pop_f))
    frame = pop_f + 5

HOLD = 50
end_full = frame + HOLD
# loop back to the empty plate, like the original clip
for food in foods:
    g = food["g"]
    g.scale = (1, 1, 1); g.keyframe_insert("scale", frame=end_full)
    g.scale = (1e-4,) * 3; g.keyframe_insert("scale", frame=end_full + 1)
events.append(dict(type="clear", frame=end_full + 1))
scene.frame_start = 1
scene.frame_end = end_full + 18

# ---------------------------------------------------------------- render
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6; scene.cycles.transmission_bounces = 6
scene.cycles.transparent_max_bounces = 8
scene.render.resolution_x = RES
scene.render.resolution_y = int(RES * 16 / 9)
scene.render.film_transparent = False
scene.view_settings.view_transform = "Standard"
scene.view_settings.exposure = -0.35
scene.render.image_settings.file_format = "PNG"
scene.render.use_persistent_data = True
scene.render.threads_mode = "AUTO"

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "events.json"), "w") as f:
    json.dump(dict(fps=FPS, frames=scene.frame_end, events=events), f)

if STILL == 9999:
    STILL = end_full - 1
if STILL >= 0:
    scene.frame_set(STILL)
    scene.render.filepath = os.path.join(OUT, f"still_{STILL:04d}.png")
    bpy.ops.render.render(write_still=True)
else:
    scene.render.filepath = os.path.join(OUT, "f_")
    bpy.ops.render.render(animation=True)
print("FRAMES", scene.frame_end)
