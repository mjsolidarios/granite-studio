"""HD render jobs for the granite report. Works inside Blender (exec) or with the bpy module.
usage (bpy module):  python3 hd_render.py <scripts_root> <out_dir> <job> [keys...] [--samples N] [--scale S]
jobs: beauty | detail | edge | patch | seeds | lineup
"""
import bpy, os, sys, math, bmesh
from mathutils import Vector

FILES = {"1st": "1st_GS01_SaltPepper.py", "2nd": "2nd_GS02_FlameSwirl.py", "3rd": "3rd_GS03_DarkMaroon.py",
         "4th": "4th_GS04_FoldedRock.py", "5th": "5th_GS05_HighContrast.py", "6th": "6th_GS06_RustRed.py"}
WIDTH = {"1st": 0.228, "2nd": 0.268, "3rd": 0.305, "4th": 0.254, "5th": 0.29, "6th": 0.279}
SEEDS = [11, 222, 3333]


def find_script(root, k):
    for p in (os.path.join(root, k, FILES[k]), os.path.join(root, FILES[k])):
        if os.path.exists(p):
            return p
    raise FileNotFoundError(FILES[k])


def load_ns(root, k):
    ns = {"__name__": "granite_hd"}
    p = find_script(root, k)
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    return ns


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup_engine(sc, samples, gpu=True):
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    if gpu:
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for t in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
                try:
                    prefs.compute_device_type = t
                    prefs.get_devices()
                    if any(d.type == t for d in prefs.devices):
                        for d in prefs.devices:
                            d.use = True
                        sc.cycles.device = "GPU"
                        break
                except Exception:
                    continue
        except Exception:
            pass
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    sc.render.image_settings.compression = 15
    vts = [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
    sc.view_settings.view_transform = "AgX" if "AgX" in vts else "Filmic"
    try:
        sc.view_settings.look = "AgX - Base Contrast" if "AgX" in vts else "None"
    except Exception:
        pass


def _cube(name, size, loc, coll):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def stage_scene(name="HDStage"):
    sc = bpy.data.scenes.get(name)
    if sc:
        return sc
    sc = bpy.data.scenes.new(name)
    c = sc.collection
    slab = _cube("Slab", (0.62, 0.09, 0.78), (0, 0, 0.55), c)
    bv = slab.modifiers.new("Bevel", "BEVEL"); bv.width = 0.006; bv.segments = 3; bv.limit_method = "ANGLE"
    base = _cube("Base", (0.78, 0.26, 0.16), (0, 0, 0.08), c)
    bv = base.modifiers.new("Bevel", "BEVEL"); bv.width = 0.006; bv.segments = 3
    me = bpy.data.meshes.new("Floor"); bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6); bm.to_mesh(me); bm.free()
    fl = bpy.data.objects.new("Floor", me); c.objects.link(fl)
    fm = bpy.data.materials.new("FloorMat"); fm.use_nodes = True
    b = fm.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.30, 0.30, 0.29, 1); b.inputs["Roughness"].default_value = 0.85
    me.materials.append(fm)
    # backdrop sweep
    bd = _cube("Backdrop", (8, 0.05, 4), (0, 2.6, 2.0), c)
    bd.data.materials.append(fm)
    cd = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cd); c.objects.link(cam); sc.camera = cam
    for nm, loc, en, size in [("Key", (-1.6, -1.8, 2.2), 70, 1.6), ("Fill", (2.0, -1.2, 1.0), 18, 2.5),
                              ("Rim", (0.5, 1.8, 2.0), 45, 1.0)]:
        ld = bpy.data.lights.new(nm, "AREA"); ld.energy = en; ld.size = size
        L = bpy.data.objects.new(nm, ld); c.objects.link(L); L.location = loc; look_at(L, (0, 0, 0.55))
    w = bpy.data.worlds.new("World_HD"); w.use_nodes = True; sc.world = w
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.62, 0.64, 0.68, 1); bg.inputs[1].default_value = 0.3
    return sc


def assign(sc, mats):
    slab, base = sc.objects["Slab"], sc.objects["Base"]
    names = [m.name for m in mats]
    side = mats[1]
    for ob in (slab, base):
        ob.data.materials.clear(); ob.data.materials.append(mats[0]); ob.data.materials.append(side)
    for p in slab.data.polygons:
        p.material_index = 0 if abs(p.normal.y) > 0.9 else 1
    for p in base.data.polygons:
        p.material_index = 0
    sub = slab.modifiers.get("Sub")
    rock = any(n.endswith("RockPitched") for n in names)
    if rock and not sub:
        sub = slab.modifiers.new("Sub", "SUBSURF"); sub.subdivision_type = "SIMPLE"; sub.levels = 6; sub.render_levels = 7
        slab.modifiers.move(len(slab.modifiers) - 1, 0)
    elif not rock and sub:
        slab.modifiers.remove(sub)
    return rock


def cam_set(sc, loc, target, lens, res):
    cam = sc.camera; cam.location = loc; look_at(cam, target); cam.data.lens = lens; cam.data.type = "PERSP"
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100


def render(sc, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    print("[hd] wrote", path, flush=True)


def job_beauty(root, out, keys, samples, scale, seed=None, tag="beauty"):
    sc = stage_scene()
    setup_engine(sc, samples)
    for k in keys:
        ns = load_ns(root, k)
        mats = ns["build_all"](ns["PRESET"], seed=seed, assign_to_selected=False)
        assign(sc, mats)
        cam_set(sc, (1.05, -2.15, 1.05), (0.02, 0, 0.5), 60, (int(2400 * scale), int(3000 * scale)))
        render(sc, os.path.join(out, f"{tag}_{k}.png"))


def job_seeds(root, out, keys, samples, scale):
    for s in SEEDS:
        job_beauty(root, out, keys, samples, scale, seed=s, tag=f"seed{s}")


def job_detail(root, out, keys, samples, scale):
    sc = stage_scene(); setup_engine(sc, samples)
    for k in keys:
        ns = load_ns(root, k)
        assign(sc, ns["build_all"](ns["PRESET"], assign_to_selected=False))
        cam_set(sc, (0.16, -0.62, 0.68), (0.02, 0, 0.58), 50, (int(2400 * scale), int(2400 * scale)))
        render(sc, os.path.join(out, f"detail_{k}.png"))


def job_edge(root, out, keys, samples, scale):
    sc = stage_scene(); setup_engine(sc, samples)
    for k in keys:
        ns = load_ns(root, k)
        assign(sc, ns["build_all"](ns["PRESET"], assign_to_selected=False))
        cam_set(sc, (0.70, -0.55, 1.24), (0.27, -0.02, 0.88), 58, (int(2400 * scale), int(1600 * scale)))
        render(sc, os.path.join(out, f"edge_{k}.png"))


def job_patch(root, out, keys, samples, scale):
    """Albedo (emission) patch at the same physical size as the photo sample."""
    sc = bpy.data.scenes.get("HDPatch") or bpy.data.scenes.new("HDPatch")
    for o in list(sc.objects):
        bpy.data.objects.remove(o)
    me = bpy.data.meshes.new("P"); bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5); bm.to_mesh(me); bm.free()
    from mathutils import Matrix
    me.transform(Matrix.Rotation(math.radians(90), 4, "X"))
    ob = bpy.data.objects.new("P", me); sc.collection.objects.link(ob)
    cd = bpy.data.cameras.new("PC"); cd.type = "ORTHO"; cam = bpy.data.objects.new("PC", cd); sc.collection.objects.link(cam)
    cam.location = (0, -1, 0); cam.rotation_euler = (math.radians(90), 0, 0); sc.camera = cam
    setup_engine(sc, max(16, samples // 8)); sc.cycles.use_denoising = False
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.render.resolution_x = sc.render.resolution_y = int(2048 * scale)
    for k in keys:
        ns = load_ns(root, k); P = ns["PRESET"]
        ns["build_all"](P, assign_to_selected=False)
        m = bpy.data.materials.get("HD_ALB") or bpy.data.materials.new("HD_ALB"); m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear()
        tc = nt.nodes.new("ShaderNodeTexCoord"); g = nt.nodes.new("ShaderNodeGroup")
        g.node_tree = bpy.data.node_groups[f"GRANITE_{P['id']}"]
        em = nt.nodes.new("ShaderNodeEmission"); o = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(tc.outputs["Object"], g.inputs["Vector"]); nt.links.new(g.outputs["Color"], em.inputs["Color"])
        nt.links.new(em.outputs[0], o.inputs["Surface"])
        ob.data.materials.clear(); ob.data.materials.append(m)
        cd.ortho_scale = WIDTH[k]
        render(sc, os.path.join(out, f"patch_{k}.png"))


def job_lineup(root, out, keys, samples, scale):
    """All six stones in a row (cover image)."""
    sc = bpy.data.scenes.get("HDLineup")
    if not sc:
        sc = bpy.data.scenes.new("HDLineup"); c = sc.collection
        for i, k in enumerate(FILES):
            x = (i - 2.5) * 1.0
            s = _cube(f"Slab_{k}", (0.62, 0.09, 0.78), (x, 0, 0.55), c)
            bv = s.modifiers.new("Bevel", "BEVEL"); bv.width = 0.006; bv.segments = 3; bv.limit_method = "ANGLE"
            b = _cube(f"Base_{k}", (0.78, 0.26, 0.16), (x, 0, 0.08), c)
            bv = b.modifiers.new("Bevel", "BEVEL"); bv.width = 0.006; bv.segments = 3
        st = stage_scene()
        for nm in ("Floor", "Backdrop"):
            c.objects.link(st.objects[nm])
        for nm, loc, en, size in [("LKey", (-3.5, -4.0, 3.5), 420, 4.0), ("LFill", (4.0, -3.0, 1.6), 110, 5.0),
                                  ("LRim", (0.0, 2.5, 3.0), 200, 4.0)]:
            ld = bpy.data.lights.new(nm, "AREA"); ld.energy = en; ld.size = size
            L = bpy.data.objects.new(nm, ld); c.objects.link(L); L.location = loc; look_at(L, (0, 0, 0.5))
        sc.world = st.world
        cd = bpy.data.cameras.new("LCam"); cam = bpy.data.objects.new("LCam", cd); c.objects.link(cam); sc.camera = cam
    setup_engine(sc, samples)
    for i, k in enumerate(FILES):
        ns = load_ns(root, k)
        mats = ns["build_all"](ns["PRESET"], assign_to_selected=False)
        s, b = sc.objects[f"Slab_{k}"], sc.objects[f"Base_{k}"]
        for ob in (s, b):
            ob.data.materials.clear(); ob.data.materials.append(mats[0]); ob.data.materials.append(mats[1])
        for p in s.data.polygons:
            p.material_index = 0 if abs(p.normal.y) > 0.9 else 1
        for p in b.data.polygons:
            p.material_index = 0
    sc.objects["Backdrop"].scale.x = 3.0
    sc.objects["Floor"].scale = (3.0, 3.0, 1.0)
    cam_set(sc, (0.7, -9.4, 1.75), (0.0, 0, 0.52), 50, (int(4400 * scale), int(1600 * scale)))
    render(sc, os.path.join(out, "lineup.png"))


JOBS = dict(beauty=job_beauty, detail=job_detail, edge=job_edge, patch=job_patch, seeds=job_seeds, lineup=job_lineup)

if __name__ == "__main__":
    a = sys.argv[1:]
    root, out, job = a[0], a[1], a[2]
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 256
    scale = float(a[a.index("--scale") + 1]) if "--scale" in a else 1.0
    keys = [x for x in a[3:] if x in FILES] or list(FILES)
    JOBS[job](root, out, keys, samples, scale)
