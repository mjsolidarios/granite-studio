"""
Procedural headstone granite - GS06_RustRed      (v2, refined against the photos)
==========================================================================
Dataset 6th  (SE269550 - shouldered upright, granite lantern/vase)
Stone: Paradiso "rust" variety - the reddest of the six.
Observed:
  * Rust/red-brown matrix (sRGB ~81,69,62); ~94 % of pixels lean red.
  * Leucosome nearly absent; long steep streaks (~60-70 deg) of rust and black.
  * Fully polished faces; sides polished too.
Calibration (albedo of a ~25-30 cm patch vs. the photo, same area):
  photo : mean sRGB 82 69 62, std 27.1, p5-p95 27-116, reddish px 94%
  shader: mean sRGB 84 71 65, std 24.3, p5-p95 31-113, reddish px 93%

USAGE (Blender 4.0+, tested on 5.2 LTS; Cycles or EEVEE)
  1. Scripting workspace > Open this file > Run Script.
  2. Selected meshes get "GS06_RustRed_Polished"; the other finishes are created
     alongside for side / edge faces.

SEED CONTROL (three levels, they add together)
  * Material  : "Granite" group node > Seed  (live; or SEED below; or set_seed(42))
  * Per object: Object Properties > Custom Properties > granite_seed
                (or set_object_seed(obj, 7) / randomize_selected_seeds())
  * Automatic : "Object Random Seed" = 1 adds Object Info > Random, so copies
                differ without any setup. Set 0 for identical copies.
  "Seed Variation" (0..1) lets the seed also nudge warp strength and the
  amount of rose / grey patches, not just move the pattern.

MAPPING: Object coordinates in metres, front face in the X/Z plane (Blender
"front" view). Apply scale (Ctrl+A) so grain size is consistent.
"""

SEED = 6             # <- change me, or use the node input

PRESET = {'id': 'GS06_RustRed',
 'seed': 6,
 'scale': 9.0,
 'flow_angle': 65.0,
 'angle_jitter': 8.0,
 'stretch': 0.35,
 'warp': 1.2,
 'fold': 0.35,
 'crinkle': 0.5,
 'band_scale': 2.0,
 'band_distortion': 9.0,
 'band_weight': 0.05,
 'rose': 0.8,
 'leuco': 0.25,
 'melano': 0.4,
 'biotite': 0.75,
 'speckle': 0.2,
 'lamination': 0.35,
 'lam_scale': 12.0,
 'grain_scale': 75.0,
 'saturation': 0.75,
 'polish_rough': 0.06,
 'tone_var': 0.28,
 'honed_mix': 0.55,
 'honed_gain': 1.2,
 'honed_rough': 0.55,
 'colors': {'matrix': [(0.0, (0.0058, 0.0029, 0.0023)),
                       (0.12, (0.0313, 0.0191, 0.0148)),
                       (0.32, (0.0647, 0.0438, 0.0355)),
                       (0.78, (0.1138, 0.0814, 0.0671)),
                       (0.95, (0.2103, 0.1682, 0.1402))],
            'rose': [(0.0, (0.0235, 0.011, 0.007)),
                     (0.12, (0.1294, 0.0682, 0.0447)),
                     (0.6, (0.1961, 0.1111, 0.0758)),
                     (0.9, (0.309, 0.1913, 0.1398))],
            'leuco': [(0.0, (0.0061, 0.0043, 0.0037)),
                      (0.22, (0.1115, 0.0991, 0.0929)),
                      (0.55, (0.2169, 0.1952, 0.1807)),
                      (0.85, (0.3161, 0.2908, 0.2655))],
            'biotite': (0.006, 0.0035, 0.0025),
            'honed_dark': (0.1, 0.09, 0.085),
            'honed_light': (0.24, 0.22, 0.21)},
 'finishes': {'Polished': {'honed': 0.0, 'bump': 0.03}, 'Honed': {'honed': 1.0, 'bump': 0.15}}}

# =============================================================================
#  CORE  (identical in every dataset script - only the PRESET block differs)
# =============================================================================
import bpy


def _lin(rgb):
    """Accept (r,g,b) linear floats -> RGBA tuple."""
    return (rgb[0], rgb[1], rgb[2], 1.0)


# ---------------------------------------------------------------- helpers ---
def _iface_new(ng, name, in_out, stype, default=None, mn=None, mx=None):
    """Create a group socket (Blender 4.0+ interface API, 3.x fallback)."""
    if hasattr(ng, "interface"):
        s = ng.interface.new_socket(name=name, in_out=in_out, socket_type=stype)
    else:  # Blender 3.x
        coll = ng.inputs if in_out == "INPUT" else ng.outputs
        s = coll.new(stype, name)
    if default is not None and hasattr(s, "default_value"):
        s.default_value = default
    if mn is not None and hasattr(s, "min_value"):
        s.min_value = mn
    if mx is not None and hasattr(s, "max_value"):
        s.max_value = mx
    return s


def _inp(node, name, idx=None):
    """Find an *enabled* input socket by name (handles duplicate names)."""
    for nm in (name, _ALIASES.get(name)):
        for s in node.inputs:
            if s.name == nm and s.enabled:
                return s
    if idx is not None:
        return node.inputs[idx]
    raise KeyError(f"{node.bl_idname} has no input '{name}'")


_ALIASES = {"Fac": "Factor", "Factor": "Fac"}   # Blender 5.x renamed Fac -> Factor


def _out(node, name):
    for nm in (name, _ALIASES.get(name)):
        for s in node.outputs:
            if s.name == nm and s.enabled:
                return s
    raise KeyError(f"{node.bl_idname} has no output '{name}'")


class _G:
    """Tiny node-graph builder to keep the network readable."""

    def __init__(self, tree):
        self.t = tree
        self.n = tree.nodes
        self.l = tree.links
        self.x = 0

    def node(self, kind, x=None, y=0, **props):
        nd = self.n.new(kind)
        nd.location = (self.x if x is None else x, y)
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.l.new(a, b)

    def set(self, sock, val):
        """Link if val is a socket, otherwise assign default."""
        if isinstance(val, bpy.types.NodeSocket):
            self.link(val, sock)
        else:
            sock.default_value = val

    # --- math shortcuts -----------------------------------------------------
    def math(self, op, a, b=0.0, x=0, y=0, clamp=False):
        m = self.node("ShaderNodeMath", x, y, operation=op, use_clamp=clamp)
        self.set(m.inputs[0], a)
        self.set(m.inputs[1], b)
        return m.outputs[0]

    def madd(self, a, b, c, x=0, y=0):
        """a * b + c"""
        m = self.node("ShaderNodeMath", x, y, operation="MULTIPLY_ADD")
        self.set(m.inputs[0], a)
        self.set(m.inputs[1], b)
        self.set(m.inputs[2], c)
        return m.outputs[0]

    def vmath(self, op, a, b=(0, 0, 0), x=0, y=0):
        m = self.node("ShaderNodeVectorMath", x, y, operation=op)
        self.set(m.inputs[0], a)
        self.set(m.inputs[1], b)
        return _out(m, "Value") if op in {"DOT_PRODUCT", "LENGTH", "DISTANCE"} else m.outputs[0]

    def maprange(self, v, fmin, fmax, tmin=0.0, tmax=1.0, x=0, y=0, interp="SMOOTHSTEP"):
        m = self.node("ShaderNodeMapRange", x, y, interpolation_type=interp, clamp=True)
        if hasattr(m, "data_type"):
            m.data_type = "FLOAT"
        self.set(m.inputs[0], v)
        self.set(m.inputs[1], fmin)
        self.set(m.inputs[2], fmax)
        self.set(m.inputs[3], tmin)
        self.set(m.inputs[4], tmax)
        return _out(m, "Result")

    def mix(self, fac, a, b, blend="MIX", x=0, y=0):
        m = self.node("ShaderNodeMix", x, y, data_type="RGBA", blend_type=blend, clamp_result=True)
        self.set(m.inputs[0], fac)
        self.set(m.inputs[6], a)
        self.set(m.inputs[7], b)
        return m.outputs[2]

    def mixf(self, fac, a, b, x=0, y=0):
        m = self.node("ShaderNodeMix", x, y, data_type="FLOAT", clamp_factor=True)
        self.set(m.inputs[0], fac)
        self.set(m.inputs[2], a)
        self.set(m.inputs[3], b)
        return m.outputs[0]

    def noise(self, vec, scale, detail, rough, distortion=0.0, x=0, y=0, lac=2.0):
        nd = self.node("ShaderNodeTexNoise", x, y)
        nd.noise_dimensions = "3D"
        if hasattr(nd, "normalize"):
            nd.normalize = True
        self.set(_inp(nd, "Vector"), vec)
        self.set(_inp(nd, "Scale"), scale)
        self.set(_inp(nd, "Detail"), detail)
        self.set(_inp(nd, "Roughness"), rough)
        self.set(_inp(nd, "Distortion"), distortion)
        try:
            self.set(_inp(nd, "Lacunarity"), lac)
        except KeyError:
            pass
        return nd

    def ramp(self, src, stops, interp="LINEAR", x=0, y=0):
        """stops = [(pos, (r,g,b)), ...]"""
        r = self.node("ShaderNodeValToRGB", x, y)
        cr = r.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]
        cr.elements[0].color = _lin(stops[0][1])
        for pos, col in stops[1:]:
            e = cr.elements.new(pos)
            e.color = _lin(col)
        self.set(r.inputs[0], src)
        return r.outputs[0]



    def wave(self, vec, scale, distortion, detail, dscale=1.4, drough=0.6, x=0, y=0):
        w = self.node("ShaderNodeTexWave", x, y, wave_type="BANDS",
                      bands_direction="Z", wave_profile="SIN")
        self.set(_inp(w, "Vector"), vec)
        self.set(_inp(w, "Scale"), scale)
        self.set(_inp(w, "Distortion"), distortion)
        self.set(_inp(w, "Detail"), detail)
        self.set(_inp(w, "Detail Scale"), dscale)
        self.set(_inp(w, "Detail Roughness"), drough)
        return _out(w, "Fac")

    def warp(self, p, scale, detail, rough, amount, x=0, y=0):
        """p + (noise(p).color - 0.5) * amount   (domain warp)"""
        n = self.noise(p, scale, detail, rough, x=x, y=y + 150)
        v = self.vmath("SUBTRACT", _out(n, "Color"), (0.5, 0.5, 0.5), x + 150, y + 150)
        v = self.vmath("SCALE", v, (0, 0, 0), x + 300, y + 150)
        self.set(_inp(v.node, "Scale"), amount)
        return self.vmath("ADD", p, v, x + 450, y), n

    def band(self, v, thr, width, x=0, y=0):
        """smoothstep(thr - width, thr + width, v)"""
        return self.maprange(v, self.math("SUBTRACT", thr, width, x - 150, y + 60),
                             self.math("ADD", thr, width, x - 150, y - 60), x=x, y=y)


# ------------------------------------------------------- the node group -----
#
#  Geology model (Paradiso / Himalayan-Blue migmatite gneiss)
#  ---------------------------------------------------------
#   matrix      fine dark crystals (biotite + plagioclase)          Voronoi grains
#   melanosome  broad, darker biotite-rich layers                  noise mask
#   rose        garnet / K-feldspar rich layers and lenses          wave + noise mask
#   leucosome   grey-white quartz-feldspar clouds, stretched        noise mask
#   speckle     discrete 1-4 mm biotite clots inside leucosome      Voronoi spots
#   schlieren   thin, broken black biotite streaks                  ridged noise
#   lamination  fine mm-scale foliation stripes that follow folds   high-freq wave
#  all sampled in one folded "flow space": rotate -> stretch -> 3-level domain warp
#
def build_granite_group(P):
    """Builds (or rebuilds) the node group 'GRANITE_<id>' from preset P."""
    gname = f"GRANITE_{P['id']}"
    old = bpy.data.node_groups.get(gname)
    if old:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new(gname, "ShaderNodeTree")
    g = _G(ng)

    # ---- interface ---------------------------------------------------------
    def fin(name, d, mn=None, mx=None):
        _iface_new(ng, name, "INPUT", "NodeSocketFloat", d, mn, mx)
    _iface_new(ng, "Vector", "INPUT", "NodeSocketVector")
    fin("Seed", float(P["seed"]), -1e6, 1e6)
    fin("Object Random Seed", 1.0, 0, 1)      # 1: each object differs automatically
    fin("Seed Variation", P.get("seed_variation", 0.35), 0, 1)  # how much the seed may
    #                                           also shift amounts/warp, not just position
    fin("Scale", P["scale"], 0.01, 1000)
    fin("Flow Angle", P["flow_angle"], -180, 180)
    fin("Flow Angle Jitter", P["angle_jitter"], 0, 90)
    fin("Stretch", P["stretch"], 0.02, 1)
    fin("Warp", P["warp"], 0, 6)
    fin("Fold", P["fold"], 0, 6)
    fin("Crinkle", P.get("crinkle", 0.4), 0, 4)
    fin("Undulation", P.get("undulation", 0.0), 0, 6)          # coherent wavy layering
    fin("Undulation Scale", P.get("undulation_scale", 2.5), 0.01, 50)
    fin("Band Scale", P["band_scale"], 0, 50)
    fin("Rose Amount", P["rose"], 0, 1)
    fin("Leucosome Amount", P["leuco"], 0, 1)
    fin("Melanosome Amount", P.get("melano", 0.4), 0, 1)
    fin("Biotite Streaks", P["biotite"], 0, 1)
    fin("Speckle Density", P.get("speckle", 0.35), 0, 1)
    fin("Lamination", P.get("lamination", 0.25), 0, 1)
    fin("Lamination Scale", P.get("lam_scale", 14.0), 0, 200)
    fin("Grain Scale", P["grain_scale"], 1, 500)
    fin("Light Veins", P.get("light_veins", 0.0), 0, 1)               # thin pale wavy lines
    fin("Mottle", P.get("mottle", 0.0), 0, 1)                    # lacy dark network (BHB)
    fin("Mottle Scale", P.get("mottle_scale", 0.15), 0.01, 2)
    fin("Mottle Threshold", P.get("mottle_thr", 0.5), 0, 1)
    fin("Brightness", P.get("brightness", 1.0), 0, 4)
    fin("Saturation", P.get("saturation", 1.0), 0, 3)
    fin("Polish Roughness", P["polish_rough"], 0, 1)
    fin("Finish (0 Polished, 1 Honed)", 0.0, 0, 1)
    fin("Rock Pitch", 0.0, 0, 1)
    _iface_new(ng, "Color", "OUTPUT", "NodeSocketColor")
    _iface_new(ng, "Roughness", "OUTPUT", "NodeSocketFloat")
    _iface_new(ng, "Height", "OUTPUT", "NodeSocketFloat")

    gi = g.node("NodeGroupInput", -3000, 0)
    go = g.node("NodeGroupOutput", 3600, 0)
    S = lambda n: _out(gi, n)
    FIN = S("Finish (0 Polished, 1 Honed)")

    # ---- 1. seed ------------------------------------------------------------
    #  seed = Seed + object custom property "granite_seed" + ObjectInfo.Random
    obj = g.node("ShaderNodeObjectInfo", -3000, -800)
    attr = g.node("ShaderNodeAttribute", -3000, -1000, attribute_type="OBJECT",
                  attribute_name="granite_seed")
    seed = g.math("ADD", S("Seed"), _out(attr, "Fac"), -2800, -900)
    rnd = g.math("MULTIPLY", g.math("MULTIPLY", _out(obj, "Random"), 9973.0, -2800, -750),
                 S("Object Random Seed"), -2650, -750)
    seed = g.math("ADD", seed, rnd, -2500, -850)

    def whitenoise(add, x, y):
        wn = g.node("ShaderNodeTexWhiteNoise", x, y)
        wn.noise_dimensions = "1D"
        g.link(g.math("ADD", seed, add, x - 150, y), _inp(wn, "W"))
        return wn

    wn = whitenoise(0.0, -2300, -700)
    offset = g.vmath("SCALE", _out(wn, "Color"), (0, 0, 0), -2150, -700)
    _inp(offset.node, "Scale").default_value = 1000.0
    wa = whitenoise(17.31, -2300, -900)
    jit = g.math("MULTIPLY", g.math("SUBTRACT", _out(wa, "Value"), 0.5, -2150, -900), 2.0, -2000, -900)
    ang = g.math("ADD", S("Flow Angle"), g.math("MULTIPLY", jit, S("Flow Angle Jitter"), -1850, -900), -1700, -900)
    ang = g.math("RADIANS", ang, 0, -1550, -900)
    # seed-driven variation of the look itself (scaled by Seed Variation)
    wv = whitenoise(41.7, -2300, -1100)
    sepv = g.node("ShaderNodeSeparateColor", -2150, -1100)
    g.link(_out(wv, "Color"), sepv.inputs[0])
    def var(i, k, x, y):     # (rand_i - 0.5) * k * SeedVariation
        return g.math("MULTIPLY", g.math("MULTIPLY", g.math("SUBTRACT", sepv.outputs[i], 0.5, x, y),
                                         k, x + 120, y), S("Seed Variation"), x + 240, y)
    v_warp = g.math("ADD", 1.0, var(0, 0.8, -2000, -1050), -1650, -1050)   # warp x(0.6..1.4)
    v_leu = var(1, 0.08, -2000, -1200)                                     # threshold shifts
    v_rose = var(2, 0.08, -2000, -1350)

    # ---- 2. flow space --------------------------------------------------------
    p = g.vmath("SCALE", S("Vector"), (0, 0, 0), -2600, 0)
    g.link(S("Scale"), _inp(p.node, "Scale"))
    rot = g.node("ShaderNodeVectorRotate", -1400, 0, rotation_type="Y_AXIS")
    g.link(p, _inp(rot, "Vector"))
    g.link(ang, _inp(rot, "Angle"))
    p_rot = _out(rot, "Vector")
    st = g.node("ShaderNodeCombineXYZ", -1400, -250)
    g.link(S("Stretch"), st.inputs[0])
    st.inputs[1].default_value = 1.0
    st.inputs[2].default_value = 1.0
    p = g.vmath("MULTIPLY", p_rot, _out(st, "Vector"), -1250, 0)
    p = g.vmath("ADD", p, offset, -1100, 0)
    p_flat = p
    # undulation: the whole layer stack bends up/down along the flow (depends on x,
    # barely on z) -> coherent waves as in Bahama-Blue type gneiss. 0 = off.
    sxyz = g.node("ShaderNodeSeparateXYZ", -1100, -300)
    g.link(p, sxyz.inputs[0])
    uv = g.node("ShaderNodeCombineXYZ", -950, -300)
    g.link(sxyz.outputs[0], uv.inputs[0])
    g.link(g.math("MULTIPLY", sxyz.outputs[2], 0.15, -1000, -400), uv.inputs[2])
    un = g.noise(_out(uv, "Vector"), S("Undulation Scale"), 2.0, 0.45, x=-800, y=-300)
    dz = g.math("MULTIPLY", g.math("SUBTRACT", _out(un, "Fac"), 0.5, -650, -300), S("Undulation"), -500, -300)
    dzv = g.node("ShaderNodeCombineXYZ", -350, -300)
    g.link(dz, dzv.inputs[2])
    p = g.vmath("ADD", p, _out(dzv, "Vector"), -250, -150)
    warp_amt = g.math("MULTIPLY", S("Warp"), v_warp, -1100, 300)
    p, _ = g.warp(p, 0.35, 2.0, 0.5, warp_amt, -950, 0)           # macro sweep
    p, nfold = g.warp(p, 1.3, 4.0, 0.55, S("Fold"), -450, 0)      # folds
    crk = g.math("MULTIPLY", S("Crinkle"), 0.15, 0, 300)
    p, _ = g.warp(p, 5.0, 3.0, 0.5, crk, 50, 0)                   # crinkly edges
    P_ = p

    # ---- 3. structural masks -----------------------------------------------
    # melanosome: broad darker biotite-rich layers
    nm = g.noise(P_, 0.7, 5.0, 0.6, x=700, y=900)
    mthr = g.math("SUBTRACT", 0.66, g.math("MULTIPLY", S("Melanosome Amount"), 0.20, 700, 1100), 850, 1100)
    mel = g.band(_out(nm, "Fac"), mthr, 0.05, x=1000, y=900)

    # lamination: fine foliation stripes following the folds (signed, -0.5..0.5)
    lam = g.wave(P_, S("Lamination Scale"), 3.5, 4.0, 2.0, 0.6, x=700, y=1300)
    lam = g.math("SUBTRACT", lam, 0.5, 900, 1300)
    lam = g.math("MULTIPLY", lam, S("Lamination"), 1050, 1300)

    # rose (garnet / K-feldspar): layered + cloudy
    bw = P.get("band_weight", 0.05)   # periodic layering is subtle in this stone
    rw = g.wave(P_, S("Band Scale"), P["band_distortion"], 6.0, 1.4, 0.62, x=700, y=600)
    rn = g.noise(P_, 1.6, 6.0, 0.62, distortion=0.25, x=700, y=400)
    rose_v = g.math("MULTIPLY", rw, bw, 900, 600)
    rose_v = g.madd(_out(rn, "Fac"), 1.0 - bw, rose_v, 1000, 500)
    rose_v = g.madd(lam, 0.04, rose_v, 1100, 500)
    rthr = g.math("SUBTRACT", 0.64, g.math("MULTIPLY", S("Rose Amount"), 0.22, 900, 750), 1050, 750)
    rthr = g.math("ADD", rthr, v_rose, 1150, 750)
    rose = g.band(rose_v, rthr, 0.05, x=1300, y=600)

    # leucosome: grey-white speckled clouds
    ln = g.noise(P_, 1.15, 5.0, 0.68, distortion=0.4, x=700, y=-300)
    lthr = g.math("SUBTRACT", 0.68, g.math("MULTIPLY", S("Leucosome Amount"), 0.18, 900, -450), 1050, -450)
    lthr = g.math("ADD", lthr, v_leu, 1150, -450)
    leu_v = g.madd(lam, 0.02, _out(ln, "Fac"), 1100, -300)
    leuco = g.band(leu_v, lthr, 0.055, x=1300, y=-300)

    inv_leu = g.math("SUBTRACT", 1.0, leuco, 1450, -150)
    rose = g.math("MULTIPLY", rose, g.math("SUBTRACT", 1.0, g.math("MULTIPLY", leuco, 0.8, 1450, 400), 1550, 400), 1650, 600)
    mel = g.math("MULTIPLY", mel, inv_leu, 1650, 900)

    # schlieren: thin broken black streaks
    bt = g.noise(P_, 3.2, 4.0, 0.55, x=700, y=-800)
    ridge = g.math("ABSOLUTE", g.math("SUBTRACT", _out(bt, "Fac"), 0.5, 900, -800), 0, 1050, -800)
    width = g.math("MULTIPLY", S("Biotite Streaks"), 0.035, 1050, -950)
    bio = g.maprange(ridge, 0.0, width, 1.0, 0.0, x=1200, y=-800)
    brk = g.noise(P_, 1.9, 2.0, 0.5, x=900, y=-1050)
    brk = g.maprange(_out(brk, "Fac"), 0.48, 0.62, x=1200, y=-1050)
    bio = g.math("MULTIPLY", g.math("MULTIPLY", bio, brk, 1350, -900), 0.9, 1500, -900)
    # light veins: thin pale sinuous lines along the layering (sparse ridges)
    lvn = g.noise(P_, P.get("light_vein_scale", 1.2), 3.0, 0.5, x=700, y=-1250)
    lvr = g.math("ABSOLUTE", g.math("SUBTRACT", _out(lvn, "Fac"), 0.5, 900, -1250), 0, 1050, -1250)
    lvw = g.math("MULTIPLY", S("Light Veins"), 0.03, 1050, -1350)
    lvein = g.maprange(lvr, 0.0, g.math("MAXIMUM", lvw, 1e-5, 1150, -1350), 1.0, 0.0, x=1200, y=-1250)
    lbrk = g.noise(P_, 0.8, 2.0, 0.5, x=900, y=-1400)
    lvein = g.math("MULTIPLY", lvein, g.maprange(_out(lbrk, "Fac"), 0.40, 0.55, x=1200, y=-1400), 1350, -1300)

    # ---- 4. crystals -----------------------------------------------------------
    stg = g.node("ShaderNodeCombineXYZ", 300, -1500)
    g.link(g.math("ADD", g.math("MULTIPLY", S("Stretch"), 0.2, 150, -1500), 0.8, 250, -1500), stg.inputs[0])
    stg.inputs[1].default_value = 1.0
    stg.inputs[2].default_value = 1.0
    gv = g.vmath("MULTIPLY", p_rot, _out(stg, "Vector"), 450, -1400)
    gv = g.vmath("ADD", gv, offset, 550, -1400)
    gv = g.vmath("SCALE", gv, (0, 0, 0), 650, -1400)
    g.link(S("Grain Scale"), _inp(gv.node, "Scale"))
    goff = g.vmath("SCALE", _out(nfold, "Color"), (0, 0, 0), 650, -1600)
    _inp(goff.node, "Scale").default_value = 3.0
    gv = g.vmath("ADD", gv, goff, 800, -1400)        # grains follow the folds a little

    vor = g.node("ShaderNodeTexVoronoi", 950, -1400, feature="F1", distance="EUCLIDEAN")
    vor.voronoi_dimensions = "3D"
    g.link(gv, _inp(vor, "Vector"))
    _inp(vor, "Scale").default_value = 1.0
    _inp(vor, "Randomness").default_value = 1.0
    sep = g.node("ShaderNodeSeparateColor", 1150, -1400)
    g.link(_out(vor, "Color"), sep.inputs[0])
    grain, grain2 = sep.outputs[0], sep.outputs[1]
    fine = g.noise(gv, 4.0, 2.0, 0.5, x=1150, y=-1650)
    # mottle: reticulated dark network of biotite between slate-blue feldspar
    # (isotropic, cm-scale, high-detail distorted noise thresholded at its median)
    mv = g.vmath("SCALE", gv, (0, 0, 0), 1150, -2300)
    g.link(S("Mottle Scale"), _inp(mv.node, "Scale"))
    mn = g.noise(mv, 1.0, 9.0, 0.68, distortion=P.get("mottle_distortion", 0.8), x=1300, y=-2300)
    mot = g.band(_out(mn, "Fac"), S("Mottle Threshold"), P.get("mottle_soft", 0.035), x=1500, y=-2300)
    # thin veins of the same network (ridges of a second, finer noise)
    mn2 = g.noise(mv, 1.7, 8.0, 0.65, distortion=P.get("mottle_distortion", 0.8) * 1.3, x=1300, y=-2550)
    vein = g.maprange(g.math("ABSOLUTE", g.math("SUBTRACT", _out(mn2, "Fac"), 0.5, 1450, -2550), 0, 1550, -2550),
                      0.0, max(P.get("vein_width", 0.0), 1e-5), 1.0, 0.0, x=1650, y=-2550)
    mot = g.math("MAXIMUM", mot, vein, 1750, -2400)
    # dark zones are clusters of dark crystals, not solid paint
    mot = g.math("MULTIPLY", mot, g.maprange(grain2, 0.0, max(P.get("mottle_porosity", 0.0), 1e-5), 0.0, 1.0, x=1750, y=-2600, interp="LINEAR"), 1850, -2400)
    mot = g.math("MULTIPLY", mot, S("Mottle"), 1950, -2300)

    # speckle: discrete round biotite clots (bigger than the crystals)
    sv = g.vmath("SCALE", gv, (0, 0, 0), 950, -1900)
    _inp(sv.node, "Scale").default_value = P.get("speckle_size", 0.45)
    vs = g.node("ShaderNodeTexVoronoi", 1100, -1900, feature="F1", distance="EUCLIDEAN")
    vs.voronoi_dimensions = "3D"
    g.link(sv, _inp(vs, "Vector"))
    _inp(vs, "Scale").default_value = 1.0
    _inp(vs, "Randomness").default_value = 1.0
    sps = g.node("ShaderNodeSeparateColor", 1300, -2000)
    g.link(_out(vs, "Color"), sps.inputs[0])
    keep = g.math("LESS_THAN", sps.outputs[0], S("Speckle Density"), 1450, -2000)
    rad = g.madd(sps.outputs[1], 0.22, 0.12, 1450, -2150)                # 0.12..0.34 cell
    dot = g.maprange(_out(vs, "Distance"), g.math("MULTIPLY", rad, 0.7, 1600, -2150), rad, 1.0, 0.0, x=1750, y=-1950)
    spk = g.math("MULTIPLY", dot, keep, 1900, -1950)
    spk = g.math("MULTIPLY", spk, g.madd(leuco, 0.75, 0.25, 1900, -2150), 2050, -1950)

    # ---- 5. colour -------------------------------------------------------------
    C = P["colors"]
    matrix_c = g.ramp(grain, C["matrix"], "CONSTANT", 1800, -200)
    rose_c = g.ramp(grain, C["rose"], "CONSTANT", 1800, 150)
    leuco_c = g.ramp(grain, C["leuco"], "CONSTANT", 1800, -550)
    blk = _lin(C["biotite"])

    col = g.mix(rose, matrix_c, rose_c, x=2100, y=0)
    col = g.mix(g.math("MULTIPLY", mel, P.get("melano_dark", 0.55), 2000, 300), col,
                (0.0, 0.0, 0.0, 1.0), x=2200, y=100)                     # darker layers
    col = g.mix(leuco, col, leuco_c, x=2300, y=-100)
    col = g.mix(spk, col, blk, x=2400, y=-200)
    col = g.mix(lvein, col, _lin(C.get("vein_light", C["leuco"][-1][1])), x=2450, y=-250)
    col = g.mix(bio, col, blk, x=2500, y=-200)
    mot = g.math("MULTIPLY", mot, g.math("SUBTRACT", 1.0, g.math("MULTIPLY", rose, P.get("mottle_in_layers", 0.5), 2350, -450), 2450, -450), 2500, -450)
    col = g.mix(mot, col, _lin(C.get("mottle", C["biotite"])), x=2550, y=-300)

    tn = g.noise(P_, 0.9, 3.0, 0.55, x=1800, y=-900)
    tone = g.maprange(_out(tn, "Fac"), 0.3, 0.7, 1.0 - P["tone_var"], 1.0 + P["tone_var"],
                      x=2000, y=-900, interp="LINEAR")
    lam_t = g.math("MULTIPLY", lam, g.math("SUBTRACT", 1.0, leuco, 2000, -1000), 2100, -1000)
    tone = g.madd(lam_t, 0.6, tone, 2150, -900)   # foliation shows in dark/rose layers
    hs = g.node("ShaderNodeHueSaturation", 2650, -200)
    g.link(col, _inp(hs, "Color"))
    sat = g.math("MULTIPLY", S("Saturation"),
                 g.math("SUBTRACT", 1.0, g.math("MULTIPLY", FIN, 0.55, 2300, -1100), 2400, -1100), 2500, -1100)
    g.link(sat, _inp(hs, "Saturation"))
    g.link(g.math("MULTIPLY", tone, S("Brightness"), 2300, -900), _inp(hs, "Value"))
    col = _out(hs, "Color")

    # honed: the matte surface scatters light, so light minerals brighten a lot
    # while biotite stays dark -> multiplicative lift (keeps the pattern), then a
    # thin cool/warm scatter veil.  rock-pitched: fractured crystals -> near white.
    honed_tint = g.mix(_out(fine, "Fac"), _lin(C["honed_dark"]), _lin(C["honed_light"]), x=2650, y=-450)
    rock_tint = g.mix(_out(fine, "Fac"), _lin(C.get("rock_dark", C["honed_dark"])),
                      _lin(C.get("rock_light", C["honed_light"])), x=2650, y=-600)
    gain = g.madd(FIN, P.get("honed_gain", 1.2), 1.0, 2650, -750)
    col_h = g.vmath("SCALE", col, (0, 0, 0), 2800, -300)
    g.link(gain, _inp(col_h.node, "Scale"))
    col_h = g.mix(g.math("MULTIPLY", FIN, P["honed_mix"] * 0.35, 2800, -750), col_h, honed_tint,
                  blend="SCREEN", x=2950, y=-300)
    col_r = g.mix(g.math("MULTIPLY", S("Rock Pitch"), 0.80, 2800, -850), col, rock_tint,
                  blend="SCREEN", x=2950, y=-500)
    rs = P.get("rock_speckle", 0.0)          # dark crystals left on flamed / split faces
    if rs > 0:
        # flamed / split face: every dark crystal is exposed as a discrete 2-4 mm
        # speck on a pale ground; pale crystals vary individually in brightness
        fv = g.vmath("SCALE", gv, (0, 0, 0), 2650, -1000)
        _inp(fv.node, "Scale").default_value = P.get("flame_speck_size", 0.25)
        fvo = g.node("ShaderNodeTexVoronoi", 2800, -1000, feature="F1", distance="EUCLIDEAN")
        fvo.voronoi_dimensions = "3D"
        g.link(fv, _inp(fvo, "Vector"))
        _inp(fvo, "Randomness").default_value = 1.0
        _inp(fvo, "Scale").default_value = 1.0
        fsep = g.node("ShaderNodeSeparateColor", 2950, -1000)
        g.link(_out(fvo, "Color"), fsep.inputs[0])
        fkeep = g.math("LESS_THAN", fsep.outputs[0], P.get("flame_speck_density", 0.45), 3050, -1000)
        frad = g.madd(fsep.outputs[1], 0.25, 0.2, 3050, -1100)
        fn_ = g.math("SUBTRACT", _out(g.noise(gv, 0.6, 2.0, 0.5, x=2800, y=-1200), "Fac"), 0.5, 2900, -1200)
        fdist = g.madd(fn_, P.get("flame_speck_ragged", 0.18), _out(fvo, "Distance"), 2950, -1200)   # ragged speck outlines
        fdot = g.maprange(fdist, g.math("MULTIPLY", frad, 0.75, 3100, -1150), frad, 1.0, 0.0, x=3200, y=-1050)
        fdot = g.math("MULTIPLY", fdot, fkeep, 3300, -1000)
        fdot = g.math("MAXIMUM", fdot, g.math("MULTIPLY", g.madd(bio, 0.5, spk, 3200, -850), 0.6, 3300, -850), 3400, -950)
        rock_tint2 = g.mix(grain, _lin(C.get("rock_dark", C["honed_dark"])),
                           _lin(C.get("rock_light", C["honed_light"])), x=3100, y=-650)
        col_r = g.mix(g.math("MULTIPLY", S("Rock Pitch"), 0.92, 3150, -750), col_r, rock_tint2, x=3200, y=-550)
        col_r = g.mix(g.math("MULTIPLY", fdot, rs, 3450, -800), col_r,
                      _lin(C.get("rock_speck", C["biotite"])), x=3500, y=-500)
    col = g.mix(S("Rock Pitch"), col_h, col_r, x=3600, y=-300)
    g.link(col, _inp(go, "Color"))

    # ---- 6. roughness ------------------------------------------------------
    r = g.madd(grain2, 0.05, S("Polish Roughness"), 2400, -1300)
    r = g.madd(leuco, 0.03, r, 2550, -1300)
    r = g.madd(spk, 0.04, r, 2700, -1300)               # biotite polishes worse
    r = g.mixf(FIN, r, P.get("honed_rough", 0.55), x=2850, y=-1300)
    r = g.mixf(S("Rock Pitch"), r, 0.85, x=3000, y=-1300)
    g.link(r, _inp(go, "Roughness"))

    # ---- 7. height ---------------------------------------------------------
    d = g.math("MULTIPLY", _out(vor, "Distance"), g.math("MAXIMUM", FIN, 0.15, 2400, -1600), 2550, -1600)
    rk = g.noise(p_flat, P.get("rock_noise_scale", 2.5), 10.0, 0.62, distortion=0.3, x=2400, y=-1800)
    rk2 = g.math("MULTIPLY", g.math("POWER", _out(rk, "Fac"), 1.6, 2550, -1800), S("Rock Pitch"), 2700, -1800)
    h = g.madd(rk2, 12.0, d, 2850, -1700)
    g.link(h, _inp(go, "Height"))
    return ng


# ------------------------------------------------------------ materials -----
def build_material(P, finish_name, finish):
    gname = f"GRANITE_{P['id']}"
    ng = bpy.data.node_groups.get(gname) or build_granite_group(P)
    mname = f"{P['id']}_{finish_name}"
    mat = bpy.data.materials.get(mname) or bpy.data.materials.new(mname)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    g = _G(nt)
    tc = g.node("ShaderNodeTexCoord", -900, 0)
    grp = g.node("ShaderNodeGroup", -650, 0)
    grp.node_tree = ng
    grp.label = "Granite  (Seed lives here)"
    grp.width = 260
    g.link(_out(tc, "Object"), grp.inputs["Vector"])
    grp.inputs["Seed"].default_value = float(P["seed"])
    grp.inputs["Finish (0 Polished, 1 Honed)"].default_value = finish.get("honed", 0.0)
    grp.inputs["Rock Pitch"].default_value = finish.get("rock", 0.0)

    bsdf = g.node("ShaderNodeBsdfPrincipled", -200, 0)
    g.link(_out(grp, "Color"), _inp(bsdf, "Base Color"))
    g.link(_out(grp, "Roughness"), _inp(bsdf, "Roughness"))
    _inp(bsdf, "IOR").default_value = 1.54
    try:
        _inp(bsdf, "Specular IOR Level").default_value = 0.5
    except KeyError:
        pass
    bump = g.node("ShaderNodeBump", -450, -350)
    _inp(bump, "Strength").default_value = finish.get("bump", 0.05)
    _inp(bump, "Distance").default_value = finish.get("bump_dist", 0.0005)
    g.link(_out(grp, "Height"), _inp(bump, "Height"))
    g.link(_out(bump, "Normal"), _inp(bsdf, "Normal"))
    out = g.node("ShaderNodeOutputMaterial", 150, 0)
    g.link(_out(bsdf, "BSDF"), _inp(out, "Surface"))
    if finish.get("displace", 0.0) > 0:
        disp = g.node("ShaderNodeDisplacement", -100, -400)
        g.link(_out(grp, "Height"), _inp(disp, "Height"))
        _inp(disp, "Scale").default_value = finish["displace"]
        _inp(disp, "Midlevel").default_value = 0.0
        g.link(_out(disp, "Displacement"), _inp(out, "Displacement"))
        try:
            mat.displacement_method = "BOTH"
        except AttributeError:
            pass
    mat["granite_preset"] = P["id"]
    return mat


def build_all(P, seed=None, assign_to_selected=True):
    """Build the node group + every finish material. Returns the materials."""
    if seed is not None:
        P = dict(P, seed=seed)
    old = bpy.data.node_groups.get(f"GRANITE_{P['id']}")
    if old:
        bpy.data.node_groups.remove(old)
    build_granite_group(P)
    mats = [build_material(P, name, fin) for name, fin in P["finishes"].items()]
    if assign_to_selected:
        for ob in bpy.context.selected_objects:
            if ob.type == "MESH":
                if ob.data.materials:
                    ob.data.materials[0] = mats[0]
                else:
                    ob.data.materials.append(mats[0])
    print(f"[granite] built {[m.name for m in mats]} (seed {P['seed']})")
    return mats


# ------------------------------------------------------------ seed tools ----
def set_seed(seed, preset_id=None):
    """Set the material-level Seed on every GRANITE material (or one preset)."""
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for nd in m.node_tree.nodes:
            if nd.type == "GROUP" and nd.node_tree and nd.node_tree.name.startswith("GRANITE_"):
                if preset_id is None or nd.node_tree.name == f"GRANITE_{preset_id}":
                    nd.inputs["Seed"].default_value = float(seed)


def set_object_seed(obj, seed):
    """Per-object seed: stored as obj['granite_seed'] (also editable/animatable in
    Object Properties > Custom Properties). Added on top of the material Seed."""
    obj["granite_seed"] = float(seed)
    obj.update_tag()


def randomize_selected_seeds(start=1, step=1):
    """Give every selected object its own deterministic seed (start, start+step...)."""
    for i, ob in enumerate(sorted(bpy.context.selected_objects, key=lambda o: o.name)):
        set_object_seed(ob, start + i * step)


# =============================================================================
if __name__ == "__main__":
    build_all(PRESET, seed=SEED, assign_to_selected=True)
