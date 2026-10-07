"""
Procedural headstone granite - GS05_HighContrast      (v4, macro microdetail)
==========================================================================
Dataset 5th  (SE269547 - flame / lantern niche, crescent & star)
Stone: Paradiso-type gneiss, highest contrast, slightly violet.
Observed:
  * Cool violet-charcoal matrix (blue channel >= red, sRGB ~69,66,68).
  * Strong contrast: dense black biotite swirls next to bright speckled patches.
  * Flow ~25 deg rising right, low coherence (lots of swirl).
  * Flame ribbons HONED: pale warm grey (sRGB ~130-220) - lighter than 2nd's.
Calibration (albedo of a ~25-30 cm patch vs. the photo, same area):
  photo : mean sRGB 69 66 68, std 33.9, p5-p95 11-125, reddish px 15%
  shader: mean sRGB 73 69 72, std 31.6, p5-p95 16-129, reddish px 16%

USAGE (Blender 4.0+, tested on 5.2 LTS; Cycles or EEVEE)
  1. Scripting workspace > Open this file > Run Script.
  2. Selected meshes get "GS05_HighContrast_Polished"; the other finishes are created
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

SEED = 5             # <- change me, or use the node input

PRESET = {'id': 'GS05_HighContrast',
 'seed': 5,
 'scale': 8.5,
 'flow_angle': 25.0,
 'angle_jitter': 12.0,
 'stretch': 0.26,
 'warp': 1.3,
 'fold': 0.8,
 'crinkle': 0.5,
 'band_scale': 2.8,
 'band_distortion': 6.0,
 'rose': 0.42,
 'leuco': 0.62,
 'melano': 0.6,
 'biotite': 0.75,
 'speckle': 0.7,
 'speckle_size': 0.3,
 'lamination': 0.25,
 'lam_scale': 14.0,
 'grain_scale': 75.0,
 'brightness': 0.92,
 'polish_rough': 0.07,
 'tone_var': 0.28,
 'honed_mix': 0.8,
 'honed_gain': 3.0,
 'honed_rough': 0.6,
 'colors': {'matrix': [(0.0, (0.002, 0.0018, 0.0023)),
                       (0.15, (0.0252, 0.0234, 0.027)),
                       (0.32, (0.0644, 0.0599, 0.0644)),
                       (0.78, (0.1319, 0.1279, 0.1385)),
                       (0.95, (0.2811, 0.2654, 0.2811))],
            'rose': [(0.0, (0.015, 0.009, 0.0105)),
                     (0.15, (0.0927, 0.0672, 0.0672)),
                     (0.6, (0.1406, 0.1048, 0.1023)),
                     (0.9, (0.2296, 0.1722, 0.1722))],
            'leuco': [(0.0, (0.0033, 0.0028, 0.0033)),
                      (0.22, (0.1263, 0.1329, 0.1529)),
                      (0.55, (0.2639, 0.2639, 0.2795)),
                      (0.85, (0.4122, 0.4122, 0.4259))],
            'biotite': (0.003, 0.0025, 0.0035),
            'honed_dark': (0.2, 0.19, 0.18),
            'honed_light': (0.42, 0.41, 0.39)},
 'finishes': {'Polished': {'honed': 0.0, 'bump': 0.03}, 'Honed': {'honed': 1.0, 'bump': 0.15}},
 'micro': {'kind': 'paradiso',
           'pluck': 0.6,
           'garnet': 0.35,
           'boundaries': 0.6,
           'scratches': 0.25,
           'waviness': 1.0},
 'grain_irregularity': 0.5,
 'grain_size_var': 0.35}

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
    fin("Grain Irregularity", P.get("grain_irregularity", 0.0), 0, 2)   # v4: wavy crystal outlines
    fin("Grain Size Variation", P.get("grain_size_var", 0.0), 0, 1)     # v4: share of 2x crystals
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
    _iface_new(ng, "Grain Cell", "OUTPUT", "NodeSocketColor")     # v4: crystal id for micro graphs
    _iface_new(ng, "Grain Edge", "OUTPUT", "NodeSocketFloat")     # v4: distance to crystal boundary
    _iface_new(ng, "Grain Dist", "OUTPUT", "NodeSocketFloat")     # v4: distance to crystal centre (zoning)

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

    # v4 crystals: irregular (warped) outlines + two crystal sizes (porphyroblasts),
    # so the macro view no longer shows uniform straight-edged Voronoi polygons.
    irr_n = g.noise(gv, 1.6, 3.0, 0.55, x=850, y=-1700)
    irr = g.vmath("SUBTRACT", _out(irr_n, "Color"), (0.5, 0.5, 0.5), 950, -1700)
    irr = g.vmath("SCALE", irr, (0, 0, 0), 1050, -1700)
    g.link(S("Grain Irregularity"), _inp(irr.node, "Scale"))
    gvc = g.vmath("ADD", gv, irr, 1150, -1600)

    def _vor(vec, feature, x, y):
        v = g.node("ShaderNodeTexVoronoi", x, y, feature=feature)
        if feature == "F1":
            v.distance = "EUCLIDEAN"
        v.voronoi_dimensions = "3D"
        g.link(vec, _inp(v, "Vector"))
        _inp(v, "Scale").default_value = 1.0
        _inp(v, "Randomness").default_value = 1.0
        return v
    gvb = g.vmath("SCALE", gvc, (0, 0, 0), 1250, -1500)
    _inp(gvb.node, "Scale").default_value = 0.5                      # 2x larger crystals
    vor = _vor(gvc, "F1", 1350, -1400)
    ved = _vor(gvc, "DISTANCE_TO_EDGE", 1350, -1250)
    vorb = _vor(gvb, "F1", 1350, -1550)
    vedb = _vor(gvb, "DISTANCE_TO_EDGE", 1350, -1700)
    szn = g.noise(gv, 0.11, 2.0, 0.5, x=1350, y=-1850)
    sthr = g.math("SUBTRACT", 1.0, g.math("MULTIPLY", S("Grain Size Variation"), 0.5, 1350, -1950), 1450, -1950)
    big = g.math("GREATER_THAN", _out(szn, "Fac"), sthr, 1500, -1850)
    cell = g.mix(big, _out(vor, "Color"), _out(vorb, "Color"), x=1550, y=-1400)
    edge = g.mixf(big, _out(ved, "Distance"), g.math("MULTIPLY", _out(vedb, "Distance"), 2.0, 1500, -1700), x=1600, y=-1600)
    seam = g.math("MULTIPLY", g.math("ABSOLUTE", g.math("SUBTRACT", _out(szn, "Fac"), sthr, 1550, -2000), 0, 1600, -2000), 40.0, 1650, -2000)
    edge = g.math("MINIMUM", edge, seam, 1700, -1700)                # the size switch is a boundary too
    sep = g.node("ShaderNodeSeparateColor", 1750, -1400)
    g.link(cell, sep.inputs[0])
    g.link(cell, _inp(go, "Grain Cell"))
    g.link(edge, _inp(go, "Grain Edge"))
    g.link(g.mixf(big, _out(vor, "Distance"), _out(vorb, "Distance"), x=1600, y=-1800), _inp(go, "Grain Dist"))
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
        if P.get("flame_speck_angular", 0):
            # v4: specks are whole, angular mineral grains (warped Voronoi cells, inset by a
            # thin pale rim) instead of round dots - reads correctly in macro shots
            fw = g.noise(fv, 1.3, 2.0, 0.5, x=2650, y=-1150)
            fvw = g.vmath("ADD", fv, g.vmath("SCALE", g.vmath("SUBTRACT", _out(fw, "Color"), (0.5, 0.5, 0.5), 2700, -1150), (0, 0, 0), 2750, -1150), 2800, -1100)
            _inp(fvw.node.inputs[1].links[0].from_node, "Scale").default_value = 0.45
            g.link(fvw, _inp(fvo, "Vector"))
            fve = g.node("ShaderNodeTexVoronoi", 2800, -1300, feature="DISTANCE_TO_EDGE"); fve.voronoi_dimensions = "3D"
            g.link(fvw, _inp(fve, "Vector")); _inp(fve, "Scale").default_value = 1.0
            # same mean coverage as the round dots it replaces: density * pi * r^2 (r ~ 0.33)
            fkeep = g.math("LESS_THAN", fsep.outputs[0], P.get("flame_speck_density", 0.45) * 0.34, 3050, -1000)
            fdot = g.math("MULTIPLY", g.maprange(_out(fve, "Distance"), 0.02, 0.07, x=3100, y=-1250), fkeep, 3300, -1000)
        else:
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
    tc = g.node("ShaderNodeTexCoord", -1300, 0)
    seedv = g.node("ShaderNodeValue", -1300, 250)
    seedv.label = "SEED"; seedv.name = "SEED"
    seedv.outputs[0].default_value = float(P["seed"])
    grp = g.node("ShaderNodeGroup", -1000, 0)
    grp.node_tree = ng
    grp.label = "Granite pattern (calibrated)"
    grp.width = 260
    g.link(_out(tc, "Object"), grp.inputs["Vector"])
    g.link(seedv.outputs[0], grp.inputs["Seed"])
    grp.inputs["Finish (0 Polished, 1 Honed)"].default_value = finish.get("honed", 0.0)
    grp.inputs["Rock Pitch"].default_value = finish.get("rock", 0.0)

    bsdf = g.node("ShaderNodeBsdfPrincipled", -200, 0)
    _inp(bsdf, "IOR").default_value = 1.54
    try:
        _inp(bsdf, "Specular IOR Level").default_value = 0.5
    except KeyError:
        pass
    out = g.node("ShaderNodeOutputMaterial", 150, 0)
    g.link(_out(bsdf, "BSDF"), _inp(out, "Surface"))

    M = P.get("micro")
    if M:
        mg_name = f"MICRO_{P['id']}"
        mg = bpy.data.node_groups.get(mg_name)
        if mg is None:
            mg = (build_micro_bahama if M["kind"] == "bahama" else build_micro_paradiso)(P)
        mic = g.node("ShaderNodeGroup", -600, 0)
        mic.node_tree = mg; mic.width = 260
        mic.label = f"Microdetail ({M['kind']}) - macro controls here"
        g.link(_out(tc, "Object"), mic.inputs["Vector"])
        g.link(seedv.outputs[0], mic.inputs["Seed"])
        for a_, b_ in (("Color", "Base Color"), ("Roughness", "Base Roughness"), ("Grain Cell", "Grain Cell"), ("Grain Edge", "Grain Edge"), ("Grain Dist", "Grain Dist")):
            g.link(_out(grp, a_), mic.inputs[b_])
        mic.inputs["Finish (0 Polished, 1 Honed)"].default_value = finish.get("honed", 0.0)
        mic.inputs["Rock Pitch"].default_value = finish.get("rock", 0.0)
        lo, hi = _dark_thresholds(P, finish)
        mic.inputs["Dark Mineral Low"].default_value = lo
        mic.inputs["Dark Mineral High"].default_value = hi
        mic.inputs["Cell Size (mm)"].default_value = 1000.0 / (P["scale"] * P["grain_scale"])
        g.link(_out(mic, "Color"), _inp(bsdf, "Base Color"))
        g.link(_out(mic, "Roughness"), _inp(bsdf, "Roughness"))
        g.link(_out(mic, "Normal"), _inp(bsdf, "Normal"))
    else:
        g.link(_out(grp, "Color"), _inp(bsdf, "Base Color"))
        g.link(_out(grp, "Roughness"), _inp(bsdf, "Roughness"))
        bump = g.node("ShaderNodeBump", -450, -350)
        _inp(bump, "Strength").default_value = finish.get("bump", 0.05)
        _inp(bump, "Distance").default_value = finish.get("bump_dist", 0.0005)
        g.link(_out(grp, "Height"), _inp(bump, "Height"))
        g.link(_out(bump, "Normal"), _inp(bsdf, "Normal"))
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
    if P.get("micro"):
        (build_micro_bahama if P["micro"]["kind"] == "bahama" else build_micro_paradiso)(P)
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
                    sv = m.node_tree.nodes.get("SEED")
                    if sv is not None:
                        sv.outputs[0].default_value = float(seed)


def set_object_seed(obj, seed):
    """Per-object seed: stored as obj['granite_seed'] (also editable/animatable in
    Object Properties > Custom Properties). Added on top of the material Seed."""
    obj["granite_seed"] = float(seed)
    obj.update_tag()


def randomize_selected_seeds(start=1, step=1):
    """Give every selected object its own deterministic seed (start, start+step...)."""
    for i, ob in enumerate(sorted(bpy.context.selected_objects, key=lambda o: o.name)):
        set_object_seed(ob, start + i * step)
import math


# =============================================================================
#  MICRODETAIL  (v4 - macro shots)
#  Substance-Designer style: the calibrated GRANITE group stays the "albedo /
#  pattern" graph; a separate per-stone MICRO group layers physically scaled
#  surface detail on top (height in metres -> bump, roughness, facet normals).
#  Paradiso and Bahama Blue use different micro graphs (see docstrings).
# =============================================================================
UM = 1e-6   # one micrometre in metres


def _micro_common_inputs(ng, M):
    """Interface shared by both micro graphs. M = preset['micro'] defaults."""
    def fin(name, d, mn=None, mx=None, hint=None):
        _iface_new(ng, name, "INPUT", "NodeSocketFloat", d, mn, mx)
    _iface_new(ng, "Vector", "INPUT", "NodeSocketVector")
    _iface_new(ng, "Base Color", "INPUT", "NodeSocketColor")
    fin("Base Roughness", 0.07, 0, 1)
    _iface_new(ng, "Grain Cell", "INPUT", "NodeSocketColor")
    fin("Grain Edge", 0.5, 0, 10)
    fin("Grain Dist", 0.3, 0, 10)
    fin("Finish (0 Polished, 1 Honed)", 0.0, 0, 1)
    fin("Rock Pitch", 0.0, 0, 1)
    fin("Seed", 0.0, -1e6, 1e6)
    # ---- user controls ---------------------------------------------------
    fin("Detail Scale", 1.0, 0.1, 10)          # >1 = finer pits / scratches / spalls
    fin("Bump Strength", 1.0, 0, 10)           # 1 = physically scaled relief
    fin("Roughness Variation", 1.0, 0, 4)      # 0 = uniform polish
    fin("Facet Tilt", 1.0, 0, 10)              # crystal-to-crystal reflection flicker
    fin("Grain Boundaries", M.get("boundaries", 0.6), 0, 2)
    fin("Polish Scratches", M.get("scratches", 0.25), 0, 2)
    fin("Polish Waviness", M.get("waviness", 1.0), 0, 4)
    fin("Crystal Texture", M.get("crystal_texture", 1.0), 0, 3)   # intra-crystal albedo detail
    fin("Dark Mineral Low", M.get("dark_lo", 0.01), 0, 1)    # luminance where biotite mask = 1
    fin("Dark Mineral High", M.get("dark_hi", 0.03), 0, 1)   # luminance where it fades to 0
    fin("Cell Size (mm)", M.get("cell_mm", 1.0), 0.05, 20)
    _iface_new(ng, "Color", "OUTPUT", "NodeSocketColor")
    _iface_new(ng, "Roughness", "OUTPUT", "NodeSocketFloat")
    _iface_new(ng, "Normal", "OUTPUT", "NodeSocketVector")
    _iface_new(ng, "Height (m)", "OUTPUT", "NodeSocketFloat")
    _iface_new(ng, "Dark Mask", "OUTPUT", "NodeSocketFloat")


def _frame(g, label, nodes_before):
    fr = g.n.new("NodeFrame"); fr.label = label; fr.label_size = 28
    for nd in list(g.n):
        if nd not in nodes_before and nd != fr and nd.type != "FRAME":
            nd.parent = fr
    return fr


def _seeded(g, S, P_):
    """object-space position offset by seed (decorrelates micro layers per object)."""
    obj = g.node("ShaderNodeObjectInfo", -1900, -300)
    s = g.madd(_out(obj, "Random"), 9973.0, S("Seed"), -1750, -300)
    wn = g.node("ShaderNodeTexWhiteNoise", -1600, -300); wn.noise_dimensions = "1D"
    g.link(s, _inp(wn, "W"))
    off = g.vmath("SCALE", _out(wn, "Color"), (0, 0, 0), -1450, -300)
    _inp(off.node, "Scale").default_value = 37.0
    return g.vmath("ADD", P_, off, -1300, -200)


def _dots(g, vec, cells_per_m, density, rmin, rmax, x, y, randomness=1.0, ragged=None):
    """sparse round dots (inclusions / pits) on a Voronoi lattice. Returns mask 0..1."""
    v = g.vmath("SCALE", vec, (0, 0, 0), x, y)
    g.set(_inp(v.node, "Scale"), cells_per_m)
    vo = g.node("ShaderNodeTexVoronoi", x + 150, y, feature="F1", distance="EUCLIDEAN")
    vo.voronoi_dimensions = "3D"
    g.link(v, _inp(vo, "Vector")); _inp(vo, "Scale").default_value = 1.0
    _inp(vo, "Randomness").default_value = randomness
    sp = g.node("ShaderNodeSeparateColor", x + 300, y - 100); g.link(_out(vo, "Color"), sp.inputs[0])
    keep = g.math("LESS_THAN", sp.outputs[0], density, x + 450, y - 100)
    rad = g.madd(sp.outputs[1], rmax - rmin, rmin, x + 450, y - 200)
    dist = _out(vo, "Distance")
    if ragged is not None:
        rn = g.noise(v, 3.0, 2.0, 0.5, x=x + 300, y=y - 300)
        dist = g.madd(g.math("SUBTRACT", _out(rn, "Fac"), 0.5, x + 450, y - 300), ragged, dist, x + 600, y - 300)
    d = g.maprange(dist, g.math("MULTIPLY", rad, 0.7, x + 600, y - 200), rad, 1.0, 0.0, x=x + 750, y=y)
    return g.math("MULTIPLY", d, keep, x + 900, y), sp


def _lines(g, vec, angle_deg, along, across, width, x, y):
    """thin straight polishing scratches (ridges of strongly anisotropic noise)."""
    rot = g.node("ShaderNodeVectorRotate", x, y, rotation_type="Y_AXIS")
    g.link(vec, _inp(rot, "Vector")); _inp(rot, "Angle").default_value = math.radians(angle_deg)
    sc_ = g.node("ShaderNodeCombineXYZ", x, y - 150)
    sc_.inputs[0].default_value = along; sc_.inputs[1].default_value = along; sc_.inputs[2].default_value = across
    v = g.vmath("MULTIPLY", _out(rot, "Vector"), _out(sc_, "Vector"), x + 150, y)
    n = g.noise(v, 1.0, 0.0, 0.5, x=x + 300, y=y)
    r = g.math("ABSOLUTE", g.math("SUBTRACT", _out(n, "Fac"), 0.5, x + 450, y), 0, x + 600, y)
    return g.maprange(r, 0.0, width, 1.0, 0.0, x=x + 750, y=y)


def _facet_normal(g, cell, tilt, x, y):
    """per-crystal micro-tilt: each crystal reflects at a slightly different angle."""
    geo = g.node("ShaderNodeNewGeometry", x, y + 200)
    N = _out(geo, "Normal")
    t = g.vmath("SUBTRACT", cell, (0.5, 0.5, 0.5), x, y)
    t = g.vmath("SCALE", t, (0, 0, 0), x + 150, y); _inp(t.node, "Scale").default_value = 2.0
    dn = g.vmath("DOT_PRODUCT", t, N, x + 300, y + 100)
    nproj = g.vmath("SCALE", N, (0, 0, 0), x + 450, y + 100); g.link(dn, _inp(nproj.node, "Scale"))
    tp = g.vmath("SUBTRACT", t, nproj, x + 600, y)
    tp = g.vmath("SCALE", tp, (0, 0, 0), x + 750, y); g.link(tilt, _inp(tp.node, "Scale"))
    return g.vmath("NORMALIZE", g.vmath("ADD", N, tp, x + 900, y), (0, 0, 0), x + 1050, y)


def _finish_micro(g, S, h, r, cell, tilt, x=2400, y=0):
    """height (m) -> bump on top of the facet normal; outputs."""
    go = g.node("NodeGroupOutput", x + 600, y)
    hb = g.math("MULTIPLY", h, S("Bump Strength"), x, y - 300)
    bump = g.node("ShaderNodeBump", x + 200, y - 300)
    _inp(bump, "Strength").default_value = 1.0
    _inp(bump, "Distance").default_value = 1.0          # height already in metres
    g.link(hb, _inp(bump, "Height"))
    g.link(_facet_normal(g, cell, tilt, x - 1100, y - 600), _inp(bump, "Normal"))
    g.link(_out(bump, "Normal"), _inp(go, "Normal"))
    g.link(g.math("MINIMUM", g.math("MAXIMUM", r, 0.015, x, y - 100), 1.0, x + 150, y - 100), _inp(go, "Roughness"))
    g.link(h, _inp(go, "Height (m)"))
    return go


def build_micro_paradiso(P):
    """PARADISO (coarse migmatite gneiss, 1-5 mm crystals, polished).
    Layers, in SD terms:
      * crystal facets  - each colour crystal gets its own micro-tilt and polish level
                          (feldspar/quartz 0.03-0.08 roughness)
      * biotite          - polishes poorly: recessed ~4 um, roughness ~0.25-0.3,
                          a few plucked flakes (pits 0.15-0.4 mm) only inside biotite
      * grain boundaries - hairline micro-cracks ~15 um wide, slightly recessed / rougher
      * garnet inclusions- sparse 0.4-1.2 mm deep-red grains, harder -> stand 1-2 um proud,
                          polish glossier than the matrix (Paradiso is garnet-bearing)
      * polishing        - faint straight scratch sets and cm-scale waviness of the slab
      * honed            - same layers, 3-4x relief, matte; rock-pitched adds spall relief
    """
    M = P["micro"]
    name = f"MICRO_{P['id']}"
    old = bpy.data.node_groups.get(name)
    if old:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new(name, "ShaderNodeTree"); g = _G(ng)
    _micro_common_inputs(ng, M)
    fin_ = lambda n, d, mn=0, mx=2: _iface_new(ng, n, "INPUT", "NodeSocketFloat", d, mn, mx)
    fin_("Biotite Pluck", M.get("pluck", 0.4))
    fin_("Garnet Inclusions", M.get("garnet", 0.35))
    gi = g.node("NodeGroupInput", -2200, 0)
    S = lambda n: _out(gi, n)
    FIN, ROCK = S("Finish (0 Polished, 1 Honed)"), S("Rock Pitch")
    DS = S("Detail Scale")

    before = set(g.n)
    P_ = _seeded(g, S, S("Vector"))
    L = g.vmath("DOT_PRODUCT", S("Base Color"), (0.2126, 0.7152, 0.0722), -1300, 300)
    dark = g.maprange(L, S("Dark Mineral Low"), S("Dark Mineral High"), 1.0, 0.0, x=-1100, y=300)
    cs = g.node("ShaderNodeSeparateColor", -1300, 600); g.link(S("Grain Cell"), cs.inputs[0])
    cR, cG, cB = cs.outputs
    bw = g.math("DIVIDE", 0.015, S("Cell Size (mm)"), -1300, 800)          # 15 um boundary
    bnd = g.maprange(S("Grain Edge"), 0.0, bw, 1.0, 0.0, x=-1100, y=800)
    bnd = g.math("MULTIPLY", bnd, S("Grain Boundaries"), -950, 800)
    _frame(g, "Masks: biotite (from albedo), crystal id, grain boundaries", before)

    # ---- inclusions & pits ------------------------------------------------
    before = set(g.n)
    dsm = g.math("MULTIPLY", DS, 1000.0 / 0.30, -1000, -700)               # pluck cells 0.3 mm
    pit, _ = _dots(g, P_, dsm, g.math("MULTIPLY", S("Biotite Pluck"), 0.12, -1000, -850), 0.18, 0.40, -850, -700, ragged=0.15)
    hard_dark = g.maprange(dark, 0.55, 0.85, x=-200, y=-650)
    pit = g.math("MULTIPLY", pit, hard_dark, -50, -700)
    # garnets = whole angular grains of a 0.9 mm lattice (subhedral, not round dots)
    gsm = g.math("MULTIPLY", DS, 1000.0 / 0.9, -1000, -1100)
    gv_ = g.vmath("SCALE", P_, (0, 0, 0), -850, -1100); g.link(gsm, _inp(gv_.node, "Scale"))
    gwarp = g.noise(gv_, 1.4, 2.0, 0.5, x=-850, y=-1250)
    gv_ = g.vmath("ADD", gv_, g.vmath("SCALE", g.vmath("SUBTRACT", _out(gwarp, "Color"), (0.5, 0.5, 0.5), -700, -1250), (0, 0, 0), -550, -1250), -400, -1100)
    _inp(gv_.node.inputs[1].links[0].from_node, "Scale").default_value = 0.35
    gvo = g.node("ShaderNodeTexVoronoi", -250, -1100, feature="F1", distance="EUCLIDEAN"); gvo.voronoi_dimensions = "3D"
    g.link(gv_, _inp(gvo, "Vector")); _inp(gvo, "Scale").default_value = 1.0
    gve = g.node("ShaderNodeTexVoronoi", -250, -1300, feature="DISTANCE_TO_EDGE"); gve.voronoi_dimensions = "3D"
    g.link(gv_, _inp(gve, "Vector")); _inp(gve, "Scale").default_value = 1.0
    gsp = g.node("ShaderNodeSeparateColor", -100, -1150); g.link(_out(gvo, "Color"), gsp.inputs[0])
    gsel = g.math("LESS_THAN", gsp.outputs[0], g.math("MULTIPLY", S("Garnet Inclusions"), 0.025, -250, -1450), 50, -1150)
    ginner = g.maprange(_out(gve, "Distance"), 0.02, 0.12, x=50, y=-1300)          # dark rim, angular outline
    gar = g.math("MULTIPLY", gsel, g.math("SUBTRACT", 1.0, dark, -200, -1050), 200, -1100)
    garim = g.math("MULTIPLY", gar, g.math("SUBTRACT", 1.0, ginner, 200, -1300), 350, -1250)
    _frame(g, "Inclusions: plucked biotite pits, garnets", before)

    # ---- polishing --------------------------------------------------------
    before = set(g.n)
    s1 = _lines(g, P_, 17.0, 40.0, 4200.0, 0.010, -1000, -1500)
    s2 = _lines(g, P_, 104.0, 40.0, 3600.0, 0.010, -1000, -1800)
    sm = g.noise(P_, 9.0, 2.0, 0.5, x=-1000, y=-2100)
    smask = g.maprange(_out(sm, "Fac"), 0.58, 0.70, x=-850, y=-2100)
    scr = g.math("MULTIPLY", g.math("MAXIMUM", s1, g.math("MULTIPLY", s2, 0.6, -150, -1800), -50, -1650), smask, 100, -1700)
    scr = g.math("MULTIPLY", scr, g.math("MULTIPLY", S("Polish Scratches"), g.math("SUBTRACT", 1.0, FIN, 100, -1950), 250, -1900), 400, -1750)
    wv = g.noise(P_, 14.0, 3.0, 0.45, x=-1000, y=-2400)                    # slab waviness ~7 cm
    wav = g.math("MULTIPLY", g.math("SUBTRACT", _out(wv, "Fac"), 0.5, -850, -2400), S("Polish Waviness"), -700, -2400)
    hz = g.noise(P_, 5.0, 2.0, 0.5, x=-1000, y=-2650)                      # polish haze patches
    haze = g.math("SUBTRACT", _out(hz, "Fac"), 0.5, -850, -2650)
    _frame(g, "Polishing: scratch sets, slab waviness, haze", before)

    # ---- roughness ----------------------------------------------------------
    before = set(g.n)
    RV = S("Roughness Variation")
    hon = g.madd(FIN, 2.5, 1.0, 600, 200)                                  # variations x3.5 when honed
    r = S("Base Roughness")
    r = g.madd(g.math("MULTIPLY", g.math("SUBTRACT", cG, 0.5, 600, 0), 0.035, 750, 0), g.math("MULTIPLY", RV, hon, 750, 150), r, 900, 0)
    r = g.madd(g.math("MULTIPLY", dark, 0.18, 900, -150), RV, r, 1050, -50)      # biotite polishes poorly
    r = g.madd(bnd, 0.05, r, 1200, -50)
    r = g.madd(pit, 0.45, r, 1350, -50)
    r = g.madd(scr, 0.07, r, 1500, -50)
    r = g.madd(gar, -0.03, r, 1650, -50)
    r = g.madd(g.math("MULTIPLY", haze, 0.03, 1650, -250), RV, r, 1800, -50)
    rock_r = g.madd(cB, 0.12, 0.80, 1650, -400)                            # split crystals 0.80-0.92
    r = g.mixf(ROCK, r, rock_r, x=1950, y=-50)
    _frame(g, "Roughness: crystal polish, biotite, boundaries, pits, scratches", before)

    # ---- height (metres) ------------------------------------------------------
    before = set(g.n)
    relief = g.madd(FIN, 3.0, 1.0, 600, -700)                              # honed: more relief
    h = g.math("MULTIPLY", g.math("MULTIPLY", dark, -1.5 * UM, 750, -700), relief, 900, -700)
    h = g.madd(g.math("MULTIPLY", g.math("SUBTRACT", cR, 0.5, 750, -850), 1.2 * UM, 900, -850), relief, h, 1050, -750)
    h = g.madd(bnd, -0.7 * UM, h, 1200, -750)
    h = g.madd(pit, -10.0 * UM, h, 1350, -750)
    h = g.madd(scr, -0.6 * UM, h, 1500, -750)
    h = g.madd(gar, 0.8 * UM, h, 1650, -750)
    h = g.madd(wav, 6.0 * UM, h, 1800, -750)
    # rock-pitched: crystal-scale spall steps (0.25 mm) + fracture roughness on top of the
    # large displaced relief that the GRANITE group already provides
    rn = g.noise(g.vmath("SCALE", P_, (0, 0, 0), 1500, -1100), 1.0, 6.0, 0.6, x=1650, y=-1100)
    _inp(rn.inputs[0].links[0].from_node, "Scale").default_value = 1500.0
    rk = g.madd(cR, 250.0 * UM, g.math("MULTIPLY", _out(rn, "Fac"), 60.0 * UM, 1800, -1100), 1950, -1000)
    h = g.madd(rk, ROCK, h, 2100, -800)
    _frame(g, "Height (metres): relief, pits, scratches, waviness, spalls", before)

    # ---- colour (garnet inclusions only - pattern stays calibrated) -------------
    before = set(g.n)
    # intra-crystal texture (zero-mean, so calibrated colours are preserved):
    #  * cloudy sub-crystal variation (alteration / inclusions), 0.4 cell
    #  * cleavage / twin lamellae in ~60 % of the feldspar crystals, 0.1-0.15 mm
    #    pitch, oriented per crystal
    CT = S("Crystal Texture")
    sub = g.vmath("SCALE", P_, (0, 0, 0), 1200, 900)
    g.link(g.math("DIVIDE", 1000.0 / 0.4, S("Cell Size (mm)"), 1050, 1000), _inp(sub.node, "Scale"))
    subn = g.noise(sub, 1.0, 3.0, 0.55, x=1350, y=900)
    m1 = g.math("MULTIPLY", g.math("SUBTRACT", _out(subn, "Fac"), 0.5, 1500, 900), 0.30, 1650, 900)
    subn2 = g.noise(g.vmath("SCALE", sub, (0, 0, 0), 1200, 750), 1.0, 2.0, 0.5, x=1350, y=750)
    _inp(subn2.inputs[0].links[0].from_node, "Scale").default_value = 3.3
    m1 = g.madd(g.math("SUBTRACT", _out(subn2, "Fac"), 0.5, 1500, 750), 0.12, m1, 1650, 750)
    # zoning: crystals shade slightly from core to rim (sign random per crystal) -> volume
    zsign = g.math("SUBTRACT", g.math("MULTIPLY", g.math("GREATER_THAN", cB, 0.5, 1200, 650), 2.0, 1350, 650), 1.0, 1500, 650)
    zone = g.math("MULTIPLY", g.math("MULTIPLY", g.math("SUBTRACT", S("Grain Dist"), 0.35, 1350, 550), zsign, 1500, 550), 0.28, 1650, 550)
    m1 = g.math("ADD", m1, zone, 1800, 700)
    rotc = g.node("ShaderNodeVectorRotate", 1200, 1200, rotation_type="Y_AXIS")
    g.link(P_, _inp(rotc, "Vector")); g.link(g.math("MULTIPLY", cR, 3.14159, 1050, 1250), _inp(rotc, "Angle"))
    wv2 = g.node("ShaderNodeTexWave", 1350, 1200, wave_type="BANDS", bands_direction="X", wave_profile="SIN")
    g.link(_out(rotc, "Vector"), _inp(wv2, "Vector"))
    _inp(wv2, "Scale").default_value = 1000.0 / 0.13 / 6.2832
    _inp(wv2, "Distortion").default_value = 4.0; _inp(wv2, "Detail").default_value = 3.0
    _inp(wv2, "Detail Scale").default_value = 0.6
    tfade = g.maprange(_out(g.noise(sub, 0.5, 2.0, 0.5, x=1200, y=1500), "Fac"), 0.45, 0.65, x=1350, y=1500)
    twin = g.math("MULTIPLY", g.math("MULTIPLY", g.math("GREATER_THAN", cG, 0.65, 1350, 1400), g.math("SUBTRACT", 1.0, dark, 1350, 1600), 1500, 1450), tfade, 1650, 1450)
    stripes = g.math("MULTIPLY", g.math("MULTIPLY", g.math("SUBTRACT", _out(wv2, "Fac"), 0.5, 1500, 1200), 0.045, 1650, 1200), twin, 1800, 1250)
    fac = g.math("MULTIPLY", g.math("ADD", m1, stripes, 1800, 1000), CT, 1950, 1000)
    colt = g.vmath("SCALE", S("Base Color"), (0, 0, 0), 2100, 900)
    g.link(g.math("ADD", 1.0, fac, 2050, 1000), _inp(colt.node, "Scale"))
    col = g.mix(g.math("MULTIPLY", gar, 0.85, 1800, 500), colt, _lin(M.get("garnet_rgb", (0.040, 0.007, 0.006))), x=1950, y=500)
    col = g.mix(g.math("MULTIPLY", garim, 0.6, 1950, 400), col, (0.008, 0.003, 0.003, 1.0), x=2050, y=500)
    # biotite: cleavage-flake sheen (alternating polish along the flakes)
    fl_n = g.noise(g.vmath("MULTIPLY", _out(rotc, "Vector"), (900.0, 900.0, 9000.0), 1350, 1700), 1.0, 4.0, 0.6, distortion=1.5, x=1500, y=1700)
    flake = g.math("MULTIPLY", g.math("SUBTRACT", _out(fl_n, "Fac"), 0.5, 1650, 1700), g.math("MULTIPLY", dark, 0.06, 1500, 1600), 1650, 1550)
    r = g.madd(flake, S("Roughness Variation"), r, 2100, 100)
    tilt = g.math("MULTIPLY", S("Facet Tilt"), g.madd(FIN, 0.012, 0.0035, 1800, 300), 1950, 300)
    tilt = g.madd(ROCK, 0.15, tilt, 2100, 300)
    _frame(g, "Colour + facet tilt", before)
    go = _finish_micro(g, S, h, r, S("Grain Cell"), tilt)
    g.link(col, _inp(go, "Color")); g.link(dark, _inp(go, "Dark Mask"))
    return ng


def build_micro_bahama(P):
    """BAHAMA BLUE (fine-grained blue-black gneiss, crystals < 1 mm, dense).
    Differs from Paradiso on purpose:
      * fine sub-crystal sparkle  - a 0.15 mm roughness flicker instead of large facets
      * dark network             - fine biotite/hornblende network is well bonded: only
                                   +0.10 roughness, 2 um recess, plucking very rare
      * no garnets               - none visible in the references
      * flamed finish            - thermal spalling: 1-3 mm spall plates stepping up to
                                   ~0.3 mm, conchoidal crater per spall, fracture
                                   roughness 0.8-0.9, with a few cleaved mica flakes that
                                   glint (roughness ~0.2) - the sparkle seen on flamed edges
    """
    M = P["micro"]
    name = f"MICRO_{P['id']}"
    old = bpy.data.node_groups.get(name)
    if old:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new(name, "ShaderNodeTree"); g = _G(ng)
    _micro_common_inputs(ng, M)
    fin_ = lambda n, d, mn=0, mx=2: _iface_new(ng, n, "INPUT", "NodeSocketFloat", d, mn, mx)
    fin_("Fine Sparkle", M.get("sparkle", 1.0))
    fin_("Biotite Pluck", M.get("pluck", 0.1))
    fin_("Flamed Relief", M.get("flame_relief", 1.0), 0, 4)
    fin_("Mica Glints", M.get("glints", 0.5))
    gi = g.node("NodeGroupInput", -2200, 0)
    S = lambda n: _out(gi, n)
    FIN, ROCK, DS = S("Finish (0 Polished, 1 Honed)"), S("Rock Pitch"), S("Detail Scale")

    before = set(g.n)
    P_ = _seeded(g, S, S("Vector"))
    L = g.vmath("DOT_PRODUCT", S("Base Color"), (0.2126, 0.7152, 0.0722), -1300, 300)
    dark = g.maprange(L, S("Dark Mineral Low"), S("Dark Mineral High"), 1.0, 0.0, x=-1100, y=300)
    cs = g.node("ShaderNodeSeparateColor", -1300, 600); g.link(S("Grain Cell"), cs.inputs[0])
    cR, cG, cB = cs.outputs
    bw = g.math("DIVIDE", 0.008, S("Cell Size (mm)"), -1300, 800)          # 8 um: tight fabric
    bnd = g.maprange(S("Grain Edge"), 0.0, bw, 1.0, 0.0, x=-1100, y=800)
    bnd = g.math("MULTIPLY", bnd, S("Grain Boundaries"), -950, 800)
    fs = g.noise(g.vmath("SCALE", P_, (0, 0, 0), -1300, 1000), 1.0, 1.0, 0.5, x=-1100, y=1000)
    _inp(fs.inputs[0].links[0].from_node, "Scale").default_value = 1000.0 / 0.15   # 0.15 mm flicker
    spark = g.math("SUBTRACT", _out(fs, "Fac"), 0.5, -950, 1000)
    _frame(g, "Masks: dark network (from albedo), crystal id, boundaries, fine sparkle", before)

    before = set(g.n)
    dsm = g.math("MULTIPLY", DS, 1000.0 / 0.25, -1000, -700)
    pit, _ = _dots(g, P_, dsm, g.math("MULTIPLY", S("Biotite Pluck"), 0.15, -1000, -850), 0.15, 0.35, -850, -700, ragged=0.12)
    pit = g.math("MULTIPLY", pit, g.maprange(dark, 0.6, 0.9, x=-200, y=-650), -50, -700)
    s1 = _lines(g, P_, 12.0, 40.0, 4500.0, 0.009, -1000, -1500)
    s2 = _lines(g, P_, 97.0, 40.0, 3900.0, 0.009, -1000, -1800)
    sm = g.noise(P_, 9.0, 2.0, 0.5, x=-1000, y=-2100)
    smask = g.maprange(_out(sm, "Fac"), 0.58, 0.70, x=-850, y=-2100)
    scr = g.math("MULTIPLY", g.math("MAXIMUM", s1, g.math("MULTIPLY", s2, 0.6, -150, -1800), -50, -1650), smask, 100, -1700)
    scr = g.math("MULTIPLY", scr, g.math("MULTIPLY", S("Polish Scratches"), g.math("SUBTRACT", 1.0, FIN, 100, -1950), 250, -1900), 400, -1750)
    wv = g.noise(P_, 14.0, 3.0, 0.45, x=-1000, y=-2400)
    wav = g.math("MULTIPLY", g.math("SUBTRACT", _out(wv, "Fac"), 0.5, -850, -2400), S("Polish Waviness"), -700, -2400)
    hz = g.noise(P_, 5.0, 2.0, 0.5, x=-1000, y=-2650)
    haze = g.math("SUBTRACT", _out(hz, "Fac"), 0.5, -850, -2650)
    _frame(g, "Polishing: rare pits, scratch sets, waviness, haze", before)

    # ---- flamed spalls ----------------------------------------------------------
    before = set(g.n)
    fsc = g.math("MULTIPLY", DS, 1000.0 / 1.8, -1000, -3000)               # 1.8 mm spall plates
    fv = g.vmath("SCALE", P_, (0, 0, 0), -850, -3000); g.link(fsc, _inp(fv.node, "Scale"))
    vo = g.node("ShaderNodeTexVoronoi", -700, -3000, feature="F1", distance="EUCLIDEAN"); vo.voronoi_dimensions = "3D"
    g.link(fv, _inp(vo, "Vector")); _inp(vo, "Scale").default_value = 1.0
    vsp = g.node("ShaderNodeSeparateColor", -550, -3100); g.link(_out(vo, "Color"), vsp.inputs[0])
    crater = g.math("POWER", g.math("MINIMUM", _out(vo, "Distance"), 1.0, -550, -2950), 1.5, -400, -2950)
    fr = g.noise(fv, 6.0, 5.0, 0.62, x=-550, y=-3250)
    spall_h = g.madd(vsp.outputs[0], 300.0 * UM, g.math("MULTIPLY", crater, 80.0 * UM, -250, -2950), -100, -3000)
    spall_h = g.madd(_out(fr, "Fac"), 40.0 * UM, spall_h, 50, -3000)
    spall_h = g.math("MULTIPLY", spall_h, S("Flamed Relief"), 200, -3000)
    glint = g.math("MULTIPLY", g.math("LESS_THAN", cB, g.math("MULTIPLY", S("Mica Glints"), 0.6, 200, -3300), 350, -3300), dark, 500, -3250)
    _frame(g, "Flamed: spall plates, craters, fracture, mica glints", before)

    # ---- roughness --------------------------------------------------------------
    before = set(g.n)
    RV = S("Roughness Variation")
    hon = g.madd(FIN, 2.5, 1.0, 600, 200)
    r = S("Base Roughness")
    r = g.madd(g.math("MULTIPLY", g.math("SUBTRACT", cG, 0.5, 600, 0), 0.015, 750, 0), g.math("MULTIPLY", RV, hon, 750, 150), r, 900, 0)
    r = g.madd(g.math("MULTIPLY", spark, 0.025, 900, 300), g.math("MULTIPLY", RV, S("Fine Sparkle"), 900, 450), r, 1050, 100)
    r = g.madd(g.math("MULTIPLY", dark, 0.10, 900, -150), RV, r, 1050, -50)
    r = g.madd(bnd, 0.04, r, 1200, -50)
    r = g.madd(pit, 0.40, r, 1350, -50)
    r = g.madd(scr, 0.06, r, 1500, -50)
    r = g.madd(g.math("MULTIPLY", haze, 0.025, 1650, -250), RV, r, 1800, -50)
    flame_r = g.madd(cB, 0.10, 0.80, 1650, -400)
    flame_r = g.mixf(glint, flame_r, 0.22, x=1800, y=-400)
    r = g.mixf(ROCK, r, flame_r, x=1950, y=-50)
    _frame(g, "Roughness: fine sparkle, dark network, pits, scratches, flamed", before)

    before = set(g.n)
    relief = g.madd(FIN, 3.0, 1.0, 600, -700)
    h = g.math("MULTIPLY", g.math("MULTIPLY", dark, -0.8 * UM, 750, -700), relief, 900, -700)
    h = g.madd(g.math("MULTIPLY", g.math("SUBTRACT", cR, 0.5, 750, -850), 0.8 * UM, 900, -850), relief, h, 1050, -750)
    h = g.madd(bnd, -0.5 * UM, h, 1200, -750)
    h = g.madd(pit, -12.0 * UM, h, 1350, -750)
    h = g.madd(scr, -0.5 * UM, h, 1500, -750)
    h = g.madd(wav, 5.0 * UM, h, 1650, -750)
    h = g.madd(spall_h, ROCK, h, 1800, -800)
    _frame(g, "Height (metres)", before)

    tilt = g.math("MULTIPLY", S("Facet Tilt"), g.madd(FIN, 0.008, 0.0022, 1800, 300), 1950, 300)
    tilt = g.madd(g.math("MULTIPLY", ROCK, vsp.outputs[1], 1950, 450), 0.25, tilt, 2100, 300)   # spall plates tilt strongly
    go = _finish_micro(g, S, h, r, S("Grain Cell"), tilt)
    # intra-crystal: fine fuzzy variation + a faint darker mosaic at the tight grain
    # boundaries (no cleavage lamellae: crystals are too small to show them)
    CT = S("Crystal Texture")
    sub = g.vmath("SCALE", P_, (0, 0, 0), 1200, 900)
    g.link(g.math("DIVIDE", 1000.0 / 0.5, S("Cell Size (mm)"), 1050, 1000), _inp(sub.node, "Scale"))
    subn = g.noise(sub, 1.0, 4.0, 0.6, x=1350, y=900)
    m1 = g.math("MULTIPLY", g.math("SUBTRACT", _out(subn, "Fac"), 0.5, 1500, 900), 0.24, 1650, 900)
    m1 = g.madd(g.math("SUBTRACT", S("Grain Dist"), 0.35, 1350, 550), 0.12, m1, 1650, 650)   # gentle core-to-rim shading
    soft = g.maprange(S("Grain Edge"), 0.0, g.math("DIVIDE", 0.04, S("Cell Size (mm)"), 1350, 1150), 1.0, 0.0, x=1500, y=1150)
    m1 = g.madd(soft, -0.08, g.math("ADD", m1, 0.025, 1650, 1050), 1800, 1000)   # +0.025 keeps the mean
    colt = g.vmath("SCALE", S("Base Color"), (0, 0, 0), 2100, 900)
    g.link(g.math("ADD", 1.0, g.math("MULTIPLY", m1, CT, 1950, 1000), 2050, 1000), _inp(colt.node, "Scale"))
    g.link(colt, _inp(go, "Color")); g.link(dark, _inp(go, "Dark Mask"))
    return ng


def _dark_thresholds(P, finish):
    """luminance range of the dark-mineral mask for this preset + finish."""
    C = P["colors"]
    lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    Lm = lum(C["matrix"][2][1])
    if finish.get("rock", 0) > 0:
        lr = lum(C.get("rock_dark", C["honed_dark"]))
        ls = lum(C.get("rock_speck", C["biotite"]))
        return (ls + 0.25 * (lr - ls), ls + 0.75 * (lr - ls))
    if finish.get("honed", 0) > 0:
        gain = 1.0 + P.get("honed_gain", 1.2)
        veil = 0.35 * P["honed_mix"] * lum(C["honed_dark"])
        return (gain * 0.35 * Lm + veil, gain * 0.75 * Lm + veil)
    return (0.35 * Lm, 0.75 * Lm)


# =============================================================================
if __name__ == "__main__":
    build_all(PRESET, seed=SEED, assign_to_selected=True)
