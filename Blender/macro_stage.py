"""Macro test stage for the granite materials (soft light + grazing light).
exec() this inside Blender, then call  macro_render(material, out_png, light='soft'|'grazing'|'side', fov_mm=40)
"""
import bpy, bmesh, math, os
from mathutils import Vector

STAGE = "MACRO_STAGE"


def _look(ob, t):
    ob.rotation_euler = (Vector(t) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def macro_scene():
    sc = bpy.data.scenes.get(STAGE)
    if sc:
        return sc
    sc = bpy.data.scenes.new(STAGE)
    c = sc.collection
    # 30 x 9 x 30 cm slab, front face in X/Z plane at y = -0.045, centred at z = 0.6
    me = bpy.data.meshes.new("MacroSlab"); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.30, 0.09, 0.30), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, 0.6), verts=bm.verts)
    bm.to_mesh(me); bm.free()
    slab = bpy.data.objects.new("MacroSlab", me); c.objects.link(slab)
    bv = slab.modifiers.new("Bevel", "BEVEL"); bv.width = 0.002; bv.segments = 4; bv.limit_method = 'ANGLE'
    # environment: soft grey studio
    w = bpy.data.worlds.new("MacroWorld"); w.use_nodes = True; sc.world = w
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.56, 0.58, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    # big dim card the stone reflects (gives the polished face something to mirror)
    card = bpy.data.meshes.new("Card"); bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0); bm.to_mesh(card); bm.free()
    cob = bpy.data.objects.new("ReflectCard", card); c.objects.link(cob)
    cob.location = (0.0, -0.9, 1.35); _look(cob, (0, -0.045, 0.6)); cob.scale = (0.9, 0.9, 1)
    cm = bpy.data.materials.new("CardMat"); cm.use_nodes = True
    nt = cm.node_tree; nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs[1].default_value = 0.12
    o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], o.inputs[0])
    card.materials.append(cm)
    cob.visible_camera = False
    # lights
    def area(name, size, energy):
        ld = bpy.data.lights.new(name, "AREA"); ld.size = size; ld.energy = energy
        L = bpy.data.objects.new(name, ld); c.objects.link(L); return L
    area("SoftKey", 1.2, 14)
    area("Grazing", 0.08, 5)
    area("SideRake", 0.05, 4)
    cd = bpy.data.cameras.new("MacroCam"); cam = bpy.data.objects.new("MacroCam", cd); c.objects.link(cam); sc.camera = cam
    sc.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
        for d in prefs.devices: d.use = True
        sc.cycles.device = 'GPU'
    except Exception:
        pass
    sc.cycles.use_auto_tile = True; sc.cycles.tile_size = 2048
    vts = [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items]
    sc.view_settings.view_transform = 'AgX' if 'AgX' in vts else 'Filmic'
    sc.render.image_settings.file_format = 'PNG'
    return sc


def macro_render(mat, out_png, light='soft', fov_mm=40, res=(1600, 1000), samples=384, seed=None,
                 target=(0.0, -0.045, 0.62), face_mat_index=None, edge=False):
    sc = macro_scene()
    os.makedirs(bpy.app.tempdir, exist_ok=True)
    slab = sc.objects["MacroSlab"]
    slab.data.materials.clear(); slab.data.materials.append(mat)
    T = Vector(target)
    cam = sc.camera
    # camera 35 deg above the face normal, framing fov_mm of stone
    d = 0.16
    if edge:   # look at the top-front edge
        T = Vector((0.0, -0.045, 0.75)); cam.location = T + Vector((0.05, -0.11, 0.10))
    else:
        cam.location = T + Vector((0.04, -d * math.cos(math.radians(25)), d * math.sin(math.radians(25))))
    _look(cam, T)
    dist = (cam.location - T).length
    cam.data.sensor_width = 36
    cam.data.lens = 36 * dist / (fov_mm / 1000.0)
    cam.data.dof.use_dof = True; cam.data.dof.focus_distance = dist; cam.data.dof.aperture_fstop = 32
    L = {n: sc.objects[n] for n in ("SoftKey", "Grazing", "SideRake")}
    for o in L.values():
        o.hide_render = True
    card = sc.objects["ReflectCard"]; card.hide_render = False
    if light == 'soft':
        o = L["SoftKey"]; o.hide_render = False
        o.location = T + Vector((-0.35, -0.55, 0.65)); _look(o, T)
        sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.06
    elif light == 'grazing':
        # light ~10 deg above the surface from the side opposite the camera: the polished
        # stone stays dark except where micro-relief, rough minerals, scratches and
        # boundaries scatter light forward - the classic surface-inspection setup
        o = L["Grazing"]; o.hide_render = False
        o.location = T + Vector((-0.12, -0.053, -0.276)); _look(o, T)   # ~10 deg above the face, opposite the camera
        card.hide_render = True
        sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.02
    elif light == 'side':
        # raking light ~8 deg above the surface, 90 deg to the view (diffuse / roughness relief)
        o = L["SideRake"]; o.hide_render = False
        o.location = T + Vector((-0.30, -0.042, 0.02)); _look(o, T)
        card.hide_render = True
        sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.02
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return out_png
