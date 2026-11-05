"""Fun Food Plate (dessert): a top-down plate where each food is first scribbled in crayon,
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
FSTART = arg("--fstart", -1)
FEND = arg("--fend", -1)

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

def group(name, x, y, rot=0.0, s=1.0):
    e = bpy.data.objects.new(name, None); link(e); e["base"] = s
    e.location = (x, y, 0); e.rotation_euler = (0, 0, math.radians(rot))
    return e

TOP = 0.045  # height of the plate's flat top

# ---------------------------------------------------------------- set & lights
bg_mat = mat("tablecloth", (0.55, 0.6, 0.8), rough=0.9, spec=0.2)
mottle(bg_mat, (0.62, 0.66, 0.85), scale=1.2, amount=0.6, bump=0.04, bump_scale=300)
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
bpy.context.object.data.materials.append(bg_mat)

plate_mat = mat("ceramic", (0.93, 0.93, 0.91), rough=0.18, spec=0.6, coat=0.4)
plate = lathe("plate", [(0, TOP), (1.1, TOP), (1.17, 0.065), (1.28, 0.125), (1.37, 0.155),
                         (1.41, 0.15), (1.42, 0.135), (1.38, 0.12), (1.22, 0.06),
                         (0.95, 0.012), (0.93, 0.0), (0.6, 0.0), (0.58, 0.01), (0, 0.01)])
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

cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"; cam.ortho_scale = 5.15
co = bpy.data.objects.new("cam", cam); link(co); co.location = (0, -0.35, 10)
scene.camera = co

# ---------------------------------------------------------------- foods
foods = []  # (group empty, footprint ellipses, outline colour, fill colour)

def add_food(g, prints, outline, fill):
    foods.append(dict(g=g, prints=prints, outline=outline, fill=fill))

# 1. Sprinkle donut ------------------------------------------------------
def make_donut():
    g = group("donut", -0.42, 0.5, 10, 1.3)
    R, r = 0.27, 0.125
    dough = mat("dough", (0.78, 0.47, 0.2), rough=0.65, sss=0.2)
    N = dough.node_tree.nodes; Lk = dough.node_tree.links
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ")
    ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"
    dv = N.new("ShaderNodeMath"); dv.operation = "DIVIDE"; dv.inputs[1].default_value = r
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 25
    ad = N.new("ShaderNodeMath"); ad.operation = "MULTIPLY_ADD"; ad.inputs[1].default_value = 0.25
    Lk.new(tc.outputs["Object"], sep.inputs[0]); Lk.new(sep.outputs["Z"], ab.inputs[0])
    Lk.new(ab.outputs[0], dv.inputs[0]); Lk.new(tc.outputs["Object"], nz.inputs["Vector"])
    Lk.new(nz.outputs["Fac"], ad.inputs[0]); Lk.new(dv.outputs[0], ad.inputs[2])
    rp = N.new("ShaderNodeValToRGB"); el = rp.color_ramp.elements
    el[0].position = 0.25; el[0].color = (0.96, 0.84, 0.6, 1)
    el[1].position = 0.55; el[1].color = (0.7, 0.4, 0.14, 1)
    el.new(0.85).color = (0.55, 0.28, 0.08, 1)
    Lk.new(ad.outputs[0], rp.inputs[0]); Lk.new(rp.outputs[0], N["Principled BSDF"].inputs["Base Color"])
    bt = N.new("ShaderNodeTexNoise"); bt.inputs["Scale"].default_value = 60; bt.inputs["Detail"].default_value = 10
    Lk.new(tc.outputs["Object"], bt.inputs["Vector"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.3; bp.inputs["Distance"].default_value = 0.01
    Lk.new(bt.outputs["Fac"], bp.inputs["Height"]); Lk.new(bp.outputs["Normal"], N["Principled BSDF"].inputs["Normal"])
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=72,
                                     minor_segments=36, location=(0, 0, TOP + r * 0.8))
    d = bpy.context.object; d.scale.z = 0.8; d.data.materials.append(dough); smooth(d); d.parent = g
    # icing: the top of a slightly fatter torus, cut with a wavy drip line
    icing = mottle(mat("icing", (0.97, 0.52, 0.66), rough=0.16, spec=0.6, sss=0.3, coat=0.5), (0.99, 0.62, 0.74), 5, 0.4, 0.08, 30)
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
    s = ic.modifiers.new("thick", "SOLIDIFY"); s.thickness = 0.018; s.offset = 1
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
    add_food(g, [(-0.42, 0.5, 0.54, 0.52, 10)], (0.55, 0.25, 0.1), (1.0, 0.45, 0.65))

# shared: a polar-grid slab with per-vertex height and colour -------------
from mathutils import noise as mnoise

def fbm(x, y, z=0.0, oct=4):
    v, a, f = 0.0, 0.5, 1.0
    for _ in range(oct):
        v += a * mnoise.noise(Vector((x * f, y * f, z * f))); a *= 0.5; f *= 2.0
    return v

def polar_slab(name, parent, a0, a1, rmax, zfn, colfn, n_r=40, n_a=96, closed=False, apex=0.0):
    """Top surface over angle a0..a1 and radius apex..rmax(a); zfn(t, a, x, y) -> height,
    colfn(t, a, x, y) -> rgb. t is 0 at the centre/apex and 1 at the rim."""
    bm = bmesh.new()
    na = n_a if closed else n_a + 1
    centre = bm.verts.new((0, 0, zfn(0, 0, 0, 0)))
    rings = []
    for i in range(1, n_r + 1):
        t = i / n_r; ring = []
        for j in range(na):
            a = a0 + (a1 - a0) * j / n_a
            r = apex + (rmax(a) - apex) * t
            x, y = r * math.cos(a), r * math.sin(a)
            ring.append(bm.verts.new((x, y, zfn(t, a, x, y))))
        rings.append(ring)
    segs = range(na) if closed else range(na - 1)
    for j in segs:
        k = (j + 1) % na
        bm.faces.new((centre, rings[0][j], rings[0][k]))
        for i in range(n_r - 1):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][k], rings[i][k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    col = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    for v in me.vertices:
        x, y = v.co.x, v.co.y; a = math.atan2(y, x); r = math.hypot(x, y)
        t = 0 if r < 1e-6 else min(1.0, (r - apex) / max(1e-6, rmax(a) - apex))
        c = colfn(t, a, x, y); col.data[v.index].color = (*c, 1)
    ob = bpy.data.objects.new(name, me); link(ob, parent); smooth(ob)
    so = ob.modifiers.new("solid", "SOLIDIFY"); so.thickness = 0.008; so.offset = -1
    return ob

def vcol_mat(name, rough=0.4, sss=0.1, coat=0.0, bump=0.0, bump_scale=60):
    m = mat(name, (1, 1, 1), rough=rough, sss=sss, coat=coat)
    N = m.node_tree.nodes; L = m.node_tree.links
    ca = N.new("ShaderNodeVertexColor"); ca.layer_name = "Col"
    L.new(ca.outputs["Color"], N["Principled BSDF"].inputs["Base Color"])
    if sss:
        L.new(ca.outputs["Color"], N["Principled BSDF"].inputs["Subsurface Radius"])
    if bump:
        tc = N.new("ShaderNodeTexCoord"); tx = N.new("ShaderNodeTexNoise")
        tx.inputs["Scale"].default_value = bump_scale; tx.inputs["Detail"].default_value = 8
        L.new(tc.outputs["Object"], tx.inputs["Vector"])
        bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.01
        L.new(tx.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], N["Principled BSDF"].inputs["Normal"])
    return m

def lerp(c1, c2, f):
    f = max(0.0, min(1.0, f)); return tuple(a + (b - a) * f for a, b in zip(c1, c2))

def sstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)

# 3. Vanilla ice cream scoop with chocolate drizzle and a cherry ----------
def make_icecream():
    g = group("icecream", 0.52, 0.56, 0)
    R0 = 0.34
    vanilla = mat("vanilla", (1.0, 0.95, 0.84), rough=0.55, sss=0.3)
    vanilla.node_tree.nodes["Principled BSDF"].inputs["Subsurface Radius"].default_value = (1, 0.9, 0.7)
    vanilla.node_tree.nodes["Principled BSDF"].inputs["Subsurface Scale"].default_value = 0.015
    mottle(vanilla, (0.96, 0.88, 0.72), scale=14, amount=1.0, bump=0.6, bump_scale=30)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=R0, location=(0, 0, 0))
    sc = bpy.context.object; sc.name = "scoop"; sc.parent = g
    for v in sc.data.vertices:  # scooped ridges + lumps
        a = math.atan2(v.co.y, v.co.x); k = 1 + 0.1 * fbm(v.co.x * 7, v.co.y * 7, v.co.z * 7) \
            + 0.035 * math.sin(6 * a + v.co.z * 18) + 0.06 * max(0.0, -v.co.z / R0 - 0.2)
        v.co *= k
    sc.scale = (1, 1, 0.9); sc.location.z = TOP + R0 * 0.6
    sc.data.materials.append(vanilla); smooth(sc)
    # melted puddle round the foot
    nz = smooth_noise(6, 0.08)
    pud = polar_slab("puddle", g, 0, 2 * math.pi, lambda a: 0.4 * (1 + nz(a)),
                     lambda t, a, x, y: 0.012 * (1 - sstep(0.7, 1.0, t)),
                     lambda t, a, x, y: (0.97, 0.92, 0.78), n_r=16, n_a=96, closed=True)
    pud.location.z = TOP; pud.data.materials.append(vcol_mat("melt", rough=0.12, sss=0.3, coat=0.6))
    # chocolate drizzle zig-zags over the dome
    choc = mat("drizzle", (0.16, 0.06, 0.025), rough=0.12, spec=0.6, coat=1.0)
    pts = []
    for i in range(140):
        t = i / 139; x = -0.27 + 0.54 * t; y = 0.2 * math.sin(t * math.pi * 6.5 + 0.3 * math.sin(t * 17)) * (1 - abs(2 * t - 1) * 0.35) + 0.015 * math.sin(t * 41)
        d2 = min(0.98, (x * x + y * y) / (R0 * R0))
        pts.append((x * R0 / 0.3, y * R0 / 0.3, TOP + R0 * 0.6 + 0.9 * R0 * 1.06 * math.sqrt(1 - d2) + 0.01))
    poly_curve("drizzle", pts, 0.014, choc, g)
    cherry = mat("cherry", (0.45, 0.01, 0.03), rough=0.08, sss=0.2, coat=1.0)
    sphere("cherry", 0.08, (0.02, 0.02, TOP + R0 * 1.55 + 0.06), (1, 1, 0.92), cherry, g, 48, 24)
    stem = mat("stem", (0.35, 0.4, 0.12), rough=0.5)
    poly_curve("stem", [(0.02, 0.02, TOP + R0 * 1.55 + 0.13), (0.06, 0.06, TOP + R0 * 1.55 + 0.18),
                        (0.13, 0.08, TOP + R0 * 1.55 + 0.2)], 0.008, stem, g)
    add_food(g, [(0.52, 0.56, 0.42, 0.41, 0)], (0.6, 0.45, 0.25), (1.0, 0.9, 0.6))

# 4. Chocolate-chip cookies --------------------------------------------------
def make_cookie(name, x, y, rot, rad):
    g = group(name, x, y, rot)
    nz = smooth_noise(6, 0.05)
    rmax = lambda a: rad * (1 + nz(a))
    def zfn(t, a, px, py):
        return (0.012 + 0.03 * (1 - t * t) + 0.008 * fbm(px * 14, py * 14)) * (1 - sstep(0.88, 1.0, t) * 0.6)
    def colfn(t, a, px, py):
        c = lerp((0.86, 0.62, 0.32), (0.78, 0.52, 0.24), 0.5 + fbm(px * 20, py * 20))
        c = lerp(c, (0.62, 0.36, 0.14), sstep(0.7, 1.0, t))          # browner edge
        c = lerp(c, (0.93, 0.78, 0.5), sstep(0.25, 0.45, fbm(px * 35 + 4, py * 35)) * 0.6)  # sugar cracks
        return c
    ck = polar_slab(name, g, 0, 2 * math.pi, rmax, zfn, colfn, n_r=30, n_a=96, closed=True)
    ck.location.z = TOP; ck.data.materials.append(vcol_mat("cookie", rough=0.75, sss=0.1, bump=0.6, bump_scale=45))
    subsurf(ck, 1)
    chip = mat("chip", (0.12, 0.05, 0.02), rough=0.3, coat=0.4)
    for k in range(16):
        a = random.uniform(0, 6.28); rr = rad * 0.8 * math.sqrt(random.random())
        t = rr / rad; z = TOP + (0.012 + 0.03 * (1 - t * t))
        c = sphere("chip", random.uniform(0.022, 0.034), (rr * math.cos(a), rr * math.sin(a), z),
                   (1.2, 1, 0.6), chip, g, 16, 10)
        c.rotation_euler.z = random.uniform(0, 3)
    return g

def make_cookies():
    gs = [make_cookie("cookie1", 0.68, -0.1, 0, 0.27), make_cookie("cookie2", 0.34, -0.46, 40, 0.25)]
    g = group("cookies", 0, 0)
    for c in gs:
        c.parent = g
    add_food(g, [(0.68, -0.1, 0.31, 0.3, 0), (0.34, -0.46, 0.29, 0.28, 0)], (0.45, 0.25, 0.1), (0.85, 0.6, 0.3))

# 3. Pizza slice (pepperoni) ---------------------------------------------
def make_pizza():
    ang = -12
    g = group("pizza", 0.12, -0.05, ang, 1.25)
    L, half = 0.76, math.radians(23)
    edge_n = smooth_noise(5, 0.015)
    rmax = lambda a: L + edge_n(a * 20)
    CRUST = 0.84
    def zfn(t, a, x, y):
        side = 1 - abs(a) / half           # 0 at the cut sides
        cut = sstep(0.0, 0.06, side)       # cheese thins to the cut edge
        z = 0.012 + 0.024 * cut + 0.006 * fbm(x * 9, y * 9)
        bub = max(0.0, fbm(x * 14 + 3, y * 14) - 0.15) * 0.05
        z += bub * cut * (1 - sstep(CRUST - 0.04, CRUST, t))
        if t > CRUST - 0.05:               # puffy cornicione
            u = (t - (CRUST - 0.05)) / (1 - CRUST + 0.05)
            z = max(z, 0.012 + 0.07 * math.sin(math.pi * min(1, u * 0.95)) ** 0.7 * (1 + 0.25 * fbm(x * 12, y * 12)))
        return z
    def colfn(t, a, x, y):
        side = 1 - abs(a) / half
        cheese = (1.0, 0.83, 0.45)
        brown = (0.72, 0.42, 0.14)
        n = fbm(x * 14 + 3, y * 14)
        c = lerp(cheese, (1.0, 0.92, 0.65), 0.5 + 0.8 * fbm(x * 30, y * 30))
        c = lerp(c, brown, sstep(0.18, 0.4, n))                 # browned blisters
        c = lerp(c, (0.8, 0.18, 0.05), (1 - sstep(0.02, 0.07, side)) * 0.9)   # sauce at the cut
        if t > CRUST - 0.06:
            u = sstep(CRUST - 0.06, CRUST, t)
            crust = lerp((0.86, 0.6, 0.3), (0.55, 0.3, 0.12), 0.5 + fbm(x * 18, y * 18))
            crust = lerp(crust, (0.25, 0.12, 0.05), sstep(0.3, 0.5, fbm(x * 25 + 7, y * 25)))  # char
            c = lerp(lerp(c, (0.8, 0.2, 0.06), (1 - u) * 0.6), crust, u)
        return c
    pm = vcol_mat("pizza", rough=0.38, sss=0.15, coat=0.35, bump=0.25, bump_scale=70)
    pz = polar_slab("pizza", g, -half, half, rmax, zfn, colfn, n_r=70, n_a=90, apex=0.0)
    pz.location.z = TOP; pz.data.materials.append(pm); subsurf(pz, 1)
    pep_m = vcol_mat("pepperoni", rough=0.22, sss=0.05, coat=0.7, bump=0.2, bump_scale=90)
    for (d, a, r) in [(0.22, 0.03, 0.052), (0.38, -0.19, 0.056), (0.42, 0.2, 0.055), (0.6, -0.03, 0.058), (0.56, 0.32, 0.05)]:
        aa = a * half / 0.23 * 0.85
        cx, cy = d * math.cos(aa), d * math.sin(aa)
        rn = smooth_noise(3, 0.04)
        pp = polar_slab("pep", g, 0, 2 * math.pi, lambda q, r=r, rn=rn: r * (1 + rn(q)),
                        lambda t, q, x, y: 0.004 + 0.012 * t ** 2.5,       # cupped edges
                        lambda t, q, x, y: lerp(lerp((0.62, 0.08, 0.05), (0.75, 0.16, 0.08), 0.5 + fbm(x * 60, y * 60)),
                                                (0.3, 0.05, 0.03), sstep(0.75, 1.0, t)),
                        n_r=12, n_a=48, closed=True)
        z_here = TOP + 0.036 + 0.01
        pp.location = (cx, cy, z_here); pp.data.materials.append(pep_m)
    herb = mat("oregano", (0.18, 0.28, 0.08), rough=0.7)
    for k in range(40):
        u = random.uniform(0.1, 0.8); a = random.uniform(-half * 0.85, half * 0.85)
        sphere("herb", 0.006, (u * L * math.cos(a), u * L * math.sin(a), TOP + 0.05), (1.6, 1, 0.4), herb, g, 8, 6)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    cx, cy = 0.12 + 0.5 * ca, -0.05 + 0.5 * sa
    add_food(g, [(cx, cy, 0.52, 0.28, ang)], (0.65, 0.35, 0.05), (1.0, 0.75, 0.15))

# 4. Fried egg -----------------------------------------------------------
def make_egg():
    g = group("egg", -0.58, -0.45, 20, 1.2)
    nz = smooth_noise(6, 0.1)
    rmax = lambda a: 0.32 * (1 + nz(a))
    def zfn(t, a, x, y):
        thick = 0.006 + 0.02 * (1 - sstep(0.3, 0.75, t)) + 0.004 * fbm(x * 12, y * 12)
        bub = max(0.0, fbm(x * 20 + 5, y * 20) - 0.25) * 0.03 * (1 - sstep(0.6, 0.9, t))
        return (thick + bub) * (1 - sstep(0.9, 1.0, t) * 0.7)
    def colfn(t, a, x, y):
        c = lerp((0.98, 0.97, 0.94), (0.93, 0.92, 0.88), 0.5 + fbm(x * 25, y * 25))
        lace = sstep(0.8, 1.0, t) * (0.6 + 0.6 * fbm(x * 30 + 1, y * 30))
        return lerp(c, (0.78, 0.52, 0.22), lace)
    em = vcol_mat("eggwhite", rough=0.12, sss=0.35, coat=0.6, bump=0.1, bump_scale=40)
    ew = polar_slab("eggwhite", g, 0, 2 * math.pi, rmax, zfn, colfn, n_r=40, n_a=128, closed=True)
    ew.location.z = TOP; ew.data.materials.append(em); subsurf(ew, 1)
    yolk = mat("yolk", (1.0, 0.5, 0.02), rough=0.06, sss=0.5, coat=1.0)
    yolk.node_tree.nodes["Principled BSDF"].inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.05)
    y = sphere("yolk", 0.105, (0.03, 0.02, TOP + 0.022), (1, 0.95, 0.55), yolk, g, 64, 32)
    pepper = mat("pepper", (0.05, 0.04, 0.03), rough=0.8)
    for k in range(26):
        a = random.uniform(0, 6.28); rr = random.uniform(0.02, 0.24)
        sphere("pep", random.uniform(0.004, 0.007), (rr * math.cos(a), rr * math.sin(a), TOP + 0.03 + (0.04 if rr < 0.1 else 0)),
               (1.3, 1, 0.5), pepper, g, 6, 4)
    add_food(g, [(-0.58, -0.45, 0.42, 0.41, 0)], (0.9, 0.6, 0.1), (1.0, 0.8, 0.2))

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
    g1 = make_strawberry("berry1", -0.15, -0.9, 10, 0.21)
    g2 = make_strawberry("berry2", 0.32, -0.86, 160, 0.21)
    g = group("berries", 0, 0)
    for c in (g1, g2):
        c.parent = g
    add_food(g, [(-0.15, -0.9, 0.26, 0.18, 10), (0.32, -0.86, 0.26, 0.18, 160)], (0.7, 0.05, 0.1), (1.0, 0.2, 0.25))

# 6. Macarons ------------------------------------------------------------
def make_macaron(name, x, y, col, rot=0, tilt=0):
    g = group(name, x, y, rot)
    shell = mottle(mat("shell", col, rough=0.55, sss=0.1), tuple(min(1, c * 1.1 + 0.05) for c in col),
                   8, 0.6, 0.2, 40)
    feet = mottle(mat("feet", tuple(c * 0.92 for c in col), rough=0.9), (1, 1, 1), 30, 0.4, 1.0, 120)
    cream = mat("cream", (0.98, 0.93, 0.85), rough=0.5, sss=0.2)
    r = 0.19; base = TOP + 0.0
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
    gs = [make_macaron("mac1", -0.62, -0.22, (0.4, 0.85, 0.65), 70, 90),
          make_macaron("mac2", -0.3, -0.5, (0.7, 0.5, 0.95), 0),
          make_macaron("mac3", -0.62, -0.68, (1.0, 0.75, 0.25), -20, 90)]
    g = group("macarons", 0, 0)
    for c in gs:
        c.parent = g
    add_food(g, [(-0.62, -0.22, 0.23, 0.16, 70), (-0.3, -0.5, 0.22, 0.22, 0), (-0.62, -0.68, 0.23, 0.16, -20)],
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
    ob.scale = (1.9, 1.9, 1.6)
    gm = mat("gummy_" + name, col, rough=0.12, sss=0.6, trans=0.55, coat=0.8)
    mb.materials.append(gm)
    return g

def make_gummies():
    gs = [make_bear("bear_red", 0.9, 0.25, 90, (1.0, 0.08, 0.05)),
          make_bear("bear_green", -1.0, 0.12, -10, (0.3, 0.9, 0.1)),
          make_bear("bear_yellow", 0.1, 0.0, 20, (1.0, 0.75, 0.0))]
    g = group("gummies", 0, 0)
    for c in gs:
        c.parent = g
    add_food(g, [(0.9, 0.25, 0.2, 0.29, 90), (-1.0, 0.12, 0.2, 0.29, -10), (0.1, 0.0, 0.2, 0.29, 20)],
             (0.85, 0.1, 0.3), (1.0, 0.65, 0.1))

# 0. Chocolate sauce swoosh (plated first, food sits on it) -----------------
def make_sauce():
    g = group("sauce", 0, 0)
    choc = mat("chocolate", (0.16, 0.06, 0.025), rough=0.12, spec=0.6, coat=1.0)
    wob = smooth_noise(3, 0.03)
    cu = bpy.data.curves.new("sauce", "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = 1.0; cu.bevel_resolution = 6; cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); n = 90; sp.points.add(n - 1)
    for i, pt in enumerate(sp.points):
        t = i / (n - 1); a = math.radians(165 + 160 * t)
        rr = 1.04 + wob(a * 3)
        pt.co = (rr * math.cos(a), rr * math.sin(a), 0, 1)
        pt.radius = 0.12 * math.sin(math.pi * (0.04 + 0.92 * t)) ** 0.6 * (1 + 0.15 * math.sin(9 * t))
    ob = bpy.data.objects.new("sauce", cu); link(ob, g); cu.materials.append(choc)
    ob.scale.z = 0.22; ob.location.z = TOP + 0.002
    drops = []
    for (x, y, r) in [(1.0, -0.22, 0.05), (1.03, -0.07, 0.037)]:
        d = sphere("drop", r, (x, y, TOP), (1, 1, 0.3), choc, g, 32, 16)
        drops.append(d)
    add_food(g, [(-0.95, -0.42, 0.22, 0.11, -65), (-0.5, -0.92, 0.22, 0.11, -30), (0.25, -1.02, 0.22, 0.11, 10), (0.85, -0.6, 0.2, 0.11, 55)],
             (0.3, 0.15, 0.05), (0.45, 0.22, 0.1))
    foods[-1]["pour"] = (ob, drops)

for maker in (make_sauce, make_donut, make_icecream, make_cookies, make_macarons, make_strawberries, make_gummies):
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
        g.scale = (max(s * g.get("base", 1.0), 1e-4),) * 3; g.keyframe_insert("scale", frame=fr)

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
        for c in (o, h):  # drawn on the "glass", so no shadows on the plate
            c.visible_shadow = False; c.visible_diffuse = False; c.visible_glossy = False
        draw_on(o, t, t + 7); draw_on(h, t + 6, t + 14)
        events.append(dict(type="scribble", start=t, end=t + 14))
        strokes += [(o, t), (h, t + 6)]
        t += 5 if len(food["prints"]) > 2 else 7
    end = t - (5 if len(food["prints"]) > 2 else 7) + 14
    pop_f = end + 4
    for ob, st in strokes:
        key_hide(ob, 0, True); key_hide(ob, st, False); key_hide(ob, pop_f, True)
    if food.get("pour"):  # sauce pours along its path, drops plop in after
        ob, drops = food["pour"]
        cu = ob.data; cu.bevel_factor_mapping_end = "SPLINE"
        cu.bevel_factor_end = 0.0; cu.keyframe_insert("bevel_factor_end", frame=pop_f - 1)
        cu.bevel_factor_end = 1.0; cu.keyframe_insert("bevel_factor_end", frame=pop_f + 9)
        key_hide(ob, 0, True); key_hide(ob, pop_f - 1, False)
        for k, d in enumerate(drops):
            f = pop_f + 9 + 2 * k
            for fr, sc in [(f - 1, 0.0), (f, 0.5), (f + 2, 1.2), (f + 4, 1.0)]:
                d.scale = (max(sc, 1e-4), max(sc, 1e-4), max(sc, 1e-4) * 0.3); d.keyframe_insert("scale", frame=fr)
    else:
        pop(g, pop_f)
    events.append(dict(type="pop", frame=pop_f))
    frame = pop_f + 5

HOLD = 50
end_full = frame + HOLD
# loop back to the empty plate, like the original clip
for food in foods:
    g = food["g"]
    g.scale = (g.get("base", 1.0),) * 3; g.keyframe_insert("scale", frame=end_full)
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
    if FSTART > 0:
        scene.frame_start = FSTART
    if FEND > 0:
        scene.frame_end = FEND
    scene.render.filepath = os.path.join(OUT, "f_")
    bpy.ops.render.render(animation=True)
print("FRAMES", scene.frame_end)
