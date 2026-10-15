"""OSCAR — « Le jour de l'emménagement » avec de vrais personnages (13/10/2026).

Blender 4.2 + MPFB (MakeHuman pour Blender, GPL) + éléments MakeHuman (CC0) : Oscar (costume
élégant, nœud papillon orange, monocle, cheveux bruns plaqués), Camille et Léo (couple fictif)
dans l'appartement (scripts/blender/room.py, Poly Haven CC0). Animation procédurale sur le
squelette « game_engine » (marche, gestes, signature, joie), bouche d'Oscar sur sa vraie voix
(formes Rhubarb → visèmes MakeHuman si disponibles), plans de caméra du film three.js.
Seules des fonctions réelles d'OSCAR sont montrées (état des lieux sur téléphone, hors ligne,
signature, PDF) ; l'écran du téléphone est une illustration (scripts/blender/humans/screens).

Usage : blender -b -P scene.py -- --assets <Poly Haven> --voice <dossier voix> --out <dossier>
          [--frames 10,200] | [--start 1 --end 100]  [--width 720 --height 1280]
          [--samples 24] [--engine CYCLES|BLENDER_EEVEE_NEXT]
"""
import importlib
import json
import math
import os
import sys
import time

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import room  # noqa: E402
sys.path.insert(0, HERE)
import realism  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
A = {argv[i][2:]: argv[i + 1] for i in range(0, len(argv) - 1, 2) if argv[i].startswith('--')}
OUT = A.get('out', '/tmp/frames')
FPS = 24
KEYS = ['intro', 'pieces', 'horsligne', 'signature', 'outro']
OPEN_MS, GAP_MS, END_MS = 2600, 550, 2600

base = 'bl_ext.user_default.mpfb'
S = lambda m: importlib.import_module(f'{base}.services.{m}')  # noqa: E731
HumanService = S('humanservice').HumanService
AssetService = S('assetservice').AssetService
TargetService = S('targetservice').TargetService
FaceService = S('faceservice').FaceService

# --- Déroulé (mêmes instants que la version three.js) ----------------------------------------
VOICE = json.load(open(os.path.join(A['voice'], 'manifest.json')))['clips']
TIMING = {}
for k in KEYS:
    p = os.path.join(A['voice'], f'{k}.timing.json')
    TIMING[k] = json.load(open(p)) if os.path.exists(p) else {}
AT = {}
t_ms = OPEN_MS
for k in KEYS:
    AT[k] = (t_ms, t_ms + VOICE[k]['ms'])
    t_ms += VOICE[k]['ms'] + GAP_MS
TOTAL_MS = AT['outro'][1] + END_MS
FRAMES = math.ceil(TOTAL_MS / 1000 * FPS)
print('DUREE', TOTAL_MS, 'ms', FRAMES, 'images')
s_ = lambda k: AT[k][0] / 1000  # noqa: E731
e_ = lambda k: AT[k][1] / 1000  # noqa: E731


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    return smooth((t - a) / (b - a))


def lerp(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


# --- Rendu ---------------------------------------------------------------------------------
# Scène vide (sans réinitialiser les préférences : l'extension MPFB doit rester active).
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
scene = bpy.context.scene
# Éléments MakeHuman (CC0) : chaque archive du dossier --packs est installée.
for z in sorted(os.listdir(A.get('packs', '.'))) if os.path.isdir(A.get('packs', '')) else []:
    if z.endswith('.zip'):
        print('PACK', z, bpy.ops.mpfb.load_pack(filepath=os.path.join(A['packs'], z)))
engine = A.get('engine', 'CYCLES')
scene.render.engine = engine
if engine == 'CYCLES':
    scene.cycles.device = 'CPU'
    scene.cycles.samples = int(A.get('samples', 24))
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.max_bounces = 4
    scene.cycles.transparent_max_bounces = 12
    # Scène gardée en mémoire d'une image à l'autre (pas de reconstruction) : rendu bien plus rapide.
    scene.render.use_persistent_data = True
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.35
else:
    scene.eevee.taa_render_samples = int(A.get('samples', 32))
scene.render.resolution_x = int(A.get('width', 720))
scene.render.resolution_y = int(A.get('height', 1280))
scene.render.fps = FPS
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0.35
scene.frame_start, scene.frame_end = 1, FRAMES

manifest_path = os.path.join(A.get('assets', ''), 'assets.json')
room.build_room(scene, json.load(open(manifest_path)) if os.path.exists(manifest_path) else {})

# --- Personnages MakeHuman ------------------------------------------------------------------
AssetService.update_all_asset_lists()
MHCLO = {}
for sub in ('clothes', 'hair', 'eyebrows', 'eyelashes', 'eyes', 'teeth', 'tongue'):
    for p in AssetService.list_mhclo_assets(sub):
        MHCLO[(sub, p.stem)] = str(p)
SKINS = {str(p).split('/')[-2]: str(p) for p in AssetService.list_mhmat_assets('skins')}


def tint(obj, rgb, strength=1.0):
    """Multiplie la couleur des matières de l'objet (cheveux, vêtements) par rgb."""
    for slot in obj.material_slots:
        m = slot.material
        if not m or not m.use_nodes:
            continue
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not bsdf:
            continue
        inp = bsdf.inputs['Base Color']
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = strength
        mix.inputs['B'].default_value = (*rgb, 1)
        if inp.links:
            src = inp.links[0].from_socket
            nt.links.remove(inp.links[0])
            nt.links.new(src, mix.inputs['A'])
        else:
            mix.inputs['A'].default_value = inp.default_value
        nt.links.new(mix.outputs['Result'], inp)


def make_human(name, macro, skin, assets, tints=None):
    t = time.time()
    m = TargetService.get_default_macro_info_dict()
    m.update(macro)
    human = HumanService.create_human(macro_detail_dict=m)
    human.name = name
    if skin in SKINS:
        HumanService.set_character_skin(SKINS[skin], human)
    else:
        print('! peau absente', skin)
    # Squelette AVANT les vêtements et cheveux : ils en reçoivent les poids et suivent les gestes.
    HumanService.add_builtin_rig(human, 'game_engine')
    for asset_type, sub, stem in assets:
        path = MHCLO.get((sub, stem))
        if not path:
            print('! élément absent', sub, stem)
            continue
        try:
            HumanService.add_mhclo_asset(path, human, asset_type=asset_type, subdiv_levels=1)
        except Exception as e:
            print('! ajout impossible', stem, e)
    rig = human.parent
    rig.name = f'{name}_squelette'
    for o in bpy.data.objects:
        if o.parent in (rig, human) and o.type == 'MESH':
            for key, rgb in (tints or {}).items():
                if key in o.name:
                    tint(o, rgb)
    print('PERSONNAGE', name, round(time.time() - t, 1), 's')
    return rig, human


OSCAR_RIG, OSCAR = make_human(
    'Oscar',
    {'gender': 1.0, 'age': 0.6, 'muscle': 0.55, 'weight': 0.45, 'height': 0.62, 'proportions': 0.7, 'race': {'caucasian': 1.0, 'asian': 0.0, 'african': 0.0}},
    'young_caucasian_male',
    [('Eyes', 'eyes', 'high-poly'), ('Eyebrows', 'eyebrows', 'eyebrow003'), ('Eyelashes', 'eyelashes', 'eyelashes01'),
     ('Teeth', 'teeth', 'teeth_base'), ('Tongue', 'tongue', 'tongue01'),
     ('Clothes', 'clothes', 'male_elegantsuit01'), ('Clothes', 'clothes', 'shoes01')],
)
LEO_RIG, LEO = make_human(
    'Leo',
    {'gender': 1.0, 'age': 0.45, 'muscle': 0.5, 'weight': 0.5, 'height': 0.55, 'race': {'caucasian': 0.8, 'asian': 0.2, 'african': 0.0}},
    'young_caucasian_male2',
    [('Eyes', 'eyes', 'high-poly'), ('Eyebrows', 'eyebrows', 'eyebrow001'), ('Eyelashes', 'eyelashes', 'eyelashes01'),
     ('Teeth', 'teeth', 'teeth_base'), ('Tongue', 'tongue', 'tongue01'),
     ('Clothes', 'clothes', 'male_casualsuit01'), ('Clothes', 'clothes', 'shoes03')],
)
CAMILLE_RIG, CAMILLE = make_human(
    'Camille',
    {'gender': 0.0, 'age': 0.45, 'muscle': 0.45, 'weight': 0.45, 'height': 0.45, 'race': {'caucasian': 0.0, 'asian': 0.0, 'african': 1.0}},
    'young_african_female',
    [('Eyes', 'eyes', 'high-poly'), ('Eyebrows', 'eyebrows', 'eyebrow010'), ('Eyelashes', 'eyelashes', 'eyelashes02'),
     ('Teeth', 'teeth', 'teeth_base'), ('Tongue', 'tongue', 'tongue01'),
     ('Clothes', 'clothes', 'female_elegantsuit01'), ('Clothes', 'clothes', 'shoes05')],
)
PEOPLE = {'oscar': OSCAR_RIG, 'leo': LEO_RIG, 'camille': CAMILLE_RIG}
PEOPLE_BODIES = [(OSCAR_RIG, OSCAR), (LEO_RIG, LEO), (CAMILLE_RIG, CAMILLE)]

bpy.context.view_layer.update()


def world_bone_head(rig, bone):
    return rig.matrix_world @ rig.data.bones[bone].head_local


def attach(obj, rig, bone, world_matrix):
    """Fixe obj à un os du squelette (il suit ses mouvements), à la position monde donnée."""
    obj.parent = rig
    obj.parent_type = 'BONE'
    obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = world_matrix


def mesh_points(obj):
    return [obj.matrix_world @ v.co for v in obj.data.vertices]


# Pas de cravate (Oscar porte le nœud papillon du logo) : dans la texture du costume, à
# l'intérieur de l'encolure (faces avant, au centre, sous le col), les tons de la cravate
# (ni le noir du veston, ni le blanc de la chemise) sont repeints couleur chemise.
def remove_tie(suit, neck):
    import numpy as np
    mesh = suit.data
    uv = mesh.uv_layers.active
    tex = None
    for slot in suit.material_slots:
        if slot.material and slot.material.use_nodes:
            tex = next((n for n in slot.material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.colorspace_settings.name != 'Non-Color'), tex)
    if not (uv and tex):
        print('! cravate : texture introuvable')
        return
    img = tex.image
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    mask = np.zeros((h, w), dtype=bool)
    mw = suit.matrix_world
    faces = 0
    for poly in mesh.polygons:
        c = mw @ poly.center
        n = (mw.to_3x3() @ poly.normal).normalized()
        if abs(c.x) < 0.045 and neck.z - 0.42 < c.z < neck.z + 0.01 and n.y < -0.3:
            faces += 1
            pts = [uv.data[li].uv for li in poly.loop_indices]
            xs = [p.x * w for p in pts]
            ys = [p.y * h for p in pts]
            x0, x1 = max(0, int(min(xs))), min(w - 1, int(max(xs)) + 1)
            y0, y1 = max(0, int(min(ys))), min(h - 1, int(max(ys)) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            inside = np.zeros(gx.shape, dtype=bool)
            for i in range(1, len(pts) - 1):  # triangles en éventail
                ax, ay, bx, by, cx, cy = xs[0], ys[0], xs[i], ys[i], xs[i + 1], ys[i + 1]
                d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
                if abs(d) < 1e-9:
                    continue
                l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / d
                l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / d
                inside |= (l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)
            mask[y0:y1 + 1, x0:x1 + 1] |= inside
    value = px[..., :3].max(axis=2)
    # Tout ce qui n'est pas le noir du veston devient blanc chemise (la cravate est gris clair).
    color = np.array([0.9, 0.9, 0.89], dtype=np.float32)
    # (rayures bleu marine comprises : teinte bleutée, alors que le veston est d'un noir neutre)
    blueish = (px[..., 2] - px[..., 0]) > 0.02
    tie = mask & ((value > 0.2) | blueish)
    px[tie, :3] = color
    img.pixels.foreach_set(px.ravel())
    img.update()
    img.pack()
    print('CRAVATE faces', faces, 'pixels repeints', int(tie.sum()), 'chemise', [round(float(c), 2) for c in color])


suit_obj = next((o for o in bpy.data.objects if o.name.startswith('Oscar.male_elegantsuit')), None)
if suit_obj:
    remove_tie(suit_obj, world_bone_head(OSCAR_RIG, 'neck_01'))

# Cheveux mèche par mèche (realism.py), clignement des yeux et corps lissés.
def part(rig, prefix):
    return next((o for o in bpy.data.objects if o.name.startswith(f'{rig.name.split("_")[0]}.{prefix}')), None)


realism.make_scalp_cap('Oscar_sous_couche', OSCAR, OSCAR_RIG, (0.035, 0.024, 0.018), streak=(0.02, 0.013), attach=attach)
realism.make_scalp_cap('Leo_sous_couche', LEO, LEO_RIG, (0.1, 0.065, 0.04), attach=attach)
realism.make_scalp_cap('Camille_sous_couche', CAMILLE, CAMILLE_RIG, (0.02, 0.015, 0.012), attach=attach)
realism.make_strand_hair('Oscar_cheveux', OSCAR, OSCAR_RIG, 'short', count=80000, length=0.055, melanin=0.92, redness=0.2,
                         streak=(0.02, 0.013, 0.02), seed=3, attach=attach)
realism.make_strand_hair('Leo_cheveux', LEO, LEO_RIG, 'short', count=70000, length=0.045, melanin=0.74, redness=0.3, seed=5, attach=attach)
realism.make_strand_hair('Camille_cheveux', CAMILLE, CAMILLE_RIG, 'bob', count=55000, length=0.21, melanin=0.97, redness=0.15,
                         seed=9, attach=attach, radius=0.00007)
BLINKS = {}
for rig, body in PEOPLE_BODIES:
    BLINKS[rig.name] = realism.add_blink(body, part(rig, 'eyelashes'))
    realism.add_smile(body).value = 0.55
    realism.smooth_body(body, 1)

# Accessoires d'Oscar : nœud papillon orange, monocle (œil droit) et sa chaînette.
orange = room.material('noeud', '#F7941D', 0.45, **{'Sheen Weight': 0.5})
neck = world_bone_head(OSCAR_RIG, 'neck_01')
suit = next((o for o in bpy.data.objects if o.name.startswith('Oscar.male_elegantsuit')), None)
front_y = min((p.y for p in mesh_points(suit) if abs(p.z - neck.z) < 0.03 and abs(p.x) < 0.05), default=neck.y - 0.07) if suit else neck.y - 0.07
# Nœud papillon : deux ailes en tissu orange (légèrement pincées vers le centre) et un nœud.
bow = room.empty('noeud_papillon')
for side in (-1, 1):
    wing = room.ellipsoid(f'noeud_aile{side}', (0.036, 0.011, 0.024), orange, bow, (side * 0.034, 0.0, 0.0))
    wing.rotation_euler = (0, side * math.radians(8), 0)
room.ellipsoid('noeud_centre', (0.013, 0.012, 0.015), orange, bow, (0, -0.004, 0))
attach(bow, OSCAR_RIG, 'neck_01', Matrix.Translation((0, front_y - 0.014, neck.z - 0.03)))

eyes = next((o for o in bpy.data.objects if o.name.startswith('Oscar.high-poly')), None)
if eyes:
    pts = [p for p in mesh_points(eyes) if p.x < 0]
    eye = sum(pts, Vector()) / max(1, len(pts))
    front = min(p.y for p in pts)
else:
    head = world_bone_head(OSCAR_RIG, 'head')
    eye, front = Vector((-0.032, head.y - 0.08, head.z + 0.09)), head.y - 0.1
gold = room.material('monocle', '#D4B26A', 0.25, **{'Metallic': 1.0})
bpy.ops.mesh.primitive_torus_add(major_radius=0.019, minor_radius=0.0017, major_segments=48, minor_segments=8)
monocle = bpy.context.active_object
monocle.name = 'monocle'
monocle.rotation_euler = (math.radians(90), 0, 0)
monocle.data.materials.append(gold)
glass = room.material('verre', '#ffffff', 0.02, **{'Transmission Weight': 1.0, 'IOR': 1.45})
bpy.ops.mesh.primitive_circle_add(radius=0.018, fill_type='NGON', vertices=32)
lens = bpy.context.active_object
lens.rotation_euler = (math.radians(90), 0, 0)
lens.data.materials.append(glass)
lens.parent = monocle
lens.location = (0, 0, 0)
bpy.context.view_layer.update()
attach(monocle, OSCAR_RIG, 'head', Matrix.Translation((eye.x, front - 0.012, eye.z)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
chain = bpy.data.curves.new('chainette', 'CURVE')
chain.dimensions = '3D'
chain.bevel_depth = 0.0012
spl = chain.splines.new('BEZIER')
spl.bezier_points.add(1)
spl.bezier_points[0].co = (eye.x - 0.019, front - 0.012, eye.z - 0.004)
spl.bezier_points[0].handle_right = (eye.x - 0.05, front - 0.02, eye.z - 0.15)
spl.bezier_points[0].handle_left = (eye.x, front, eye.z)
spl.bezier_points[1].co = (-0.07, front_y + 0.005, neck.z - 0.22)
spl.bezier_points[1].handle_left = (-0.08, front_y - 0.02, neck.z - 0.12)
spl.bezier_points[1].handle_right = (-0.07, front_y, neck.z - 0.3)
chain_obj = bpy.data.objects.new('chainette', chain)
scene.collection.objects.link(chain_obj)
chain_obj.data.materials.append(gold)
attach(chain_obj, OSCAR_RIG, 'spine_03', Matrix.Identity(4))

# Téléphone dans la main droite d'Oscar, écran = illustration (pictogrammes).
SCREENS = {}
for f in sorted(os.listdir(os.path.join(HERE, 'screens'))):
    if f.endswith('.png'):
        SCREENS[f[:-4]] = bpy.data.images.load(os.path.join(HERE, 'screens', f))
phone = room.box('telephone', (0.074, 0.008, 0.152), (0, 0, 0), room.material('coque', '#111827', 0.25, **{'Metallic': 0.6}), bevel=0.006)
screen_mat = bpy.data.materials.new('ecran')
screen_mat.use_nodes = True
snt = screen_mat.node_tree
sb = snt.nodes['Principled BSDF']
screen_tex = snt.nodes.new('ShaderNodeTexImage')
screen_tex.image = SCREENS['start']
snt.links.new(screen_tex.outputs['Color'], sb.inputs['Base Color'])
snt.links.new(screen_tex.outputs['Color'], sb.inputs['Emission Color'])
sb.inputs['Emission Strength'].default_value = 0.8
sb.inputs['Roughness'].default_value = 0.15
bpy.ops.mesh.primitive_plane_add(size=1)
screen = bpy.context.active_object
screen.name = 'ecran'
screen.scale = (0.066, 0.132, 1)
bpy.ops.object.transform_apply(scale=True)
screen.rotation_euler = (math.radians(90), 0, 0)
screen.data.materials.append(screen_mat)
screen.parent = phone
screen.location = (0, -0.0045, 0)
hand = world_bone_head(OSCAR_RIG, 'hand_r')
bpy.context.view_layer.update()
attach(phone, OSCAR_RIG, 'hand_r', Matrix.Translation(hand + Vector((-0.06, -0.02, -0.03))))

# --- Animation procédurale -----------------------------------------------------------------
Q = lambda axis, deg: Quaternion(Vector(axis), math.radians(deg))  # noqa: E731
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def apply_pose(rig, deltas):
    """deltas : {os: rotation dans le repère du squelette, autour de la tête de l'os}.
    Chaque rotation s'ajoute à celles des os parents (méthode « monde » cumulée)."""
    acc = {}

    def visit(pb):
        parent = pb.parent
        a_p = acc.get(parent.name, Quaternion()) if parent else Quaternion()
        d = deltas.get(pb.name, Quaternion())
        acc[pb.name] = d @ a_p
        r = pb.bone.matrix_local.to_quaternion()
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = r.inverted() @ a_p.inverted() @ d @ a_p @ r
        for c in pb.children:
            visit(c)

    for pb in rig.pose.bones:
        if pb.parent is None:
            visit(pb)


def body_pose(t, walk=0.0, wave=0.0, phone=0.0, extend=0.0, sign=0.0, cheer=0.0, look=0.0, nod=0.0, talk=0.0):
    """Pose en rotations « monde » (le personnage regarde vers -Y au repos, bras en A)."""
    ph = t * 7.0
    d = {}
    d['spine_02'] = Q(X, 1.5 * math.sin(t * 2.0))
    # Bras le long du corps (depuis la pose en A), balancement de marche.
    swing = math.sin(ph) * 22 * walk
    d['upperarm_l'] = Q(X, swing) @ Q(Y, 44)
    d['upperarm_r'] = Q(X, -swing) @ Q(Y, -44)
    d['lowerarm_l'] = Q(X, -8)
    d['lowerarm_r'] = Q(X, -8)
    # Jambes : marche.
    d['thigh_l'] = Q(X, -24 * math.sin(ph) * walk)
    d['thigh_r'] = Q(X, 24 * math.sin(ph) * walk)
    d['calf_l'] = Q(X, 30 * max(0.0, math.sin(ph + 1.4)) * walk)
    d['calf_r'] = Q(X, 30 * max(0.0, -math.sin(ph + 1.4)) * walk)
    # Téléphone tenu devant soi (bras droit), tendu vers le couple (extend).
    if phone or extend:
        k = max(phone, extend)
        d['upperarm_r'] = Q(X, -38 * phone - 62 * extend) @ Q(Y, -44 + 10 * k)
        d['lowerarm_r'] = Q(X, -78 * phone - 20 * extend)
        d['hand_r'] = Q(Z, 20 * k)
    # Salut de la main droite.
    if wave:
        d['upperarm_r'] = Q(Y, 75 * wave) @ d.get('upperarm_r', Quaternion()).slerp(Quaternion(), wave)
        d['lowerarm_r'] = Q(Y, (55 + 18 * math.sin(t * 9)) * wave)
    # Signature (bras droit, petits mouvements de la main).
    if sign:
        d['upperarm_r'] = Q(X, -45 * sign) @ Q(Y, -44 + 14 * sign)
        d['lowerarm_r'] = Q(X, -62 * sign)
        d['hand_r'] = Q(Z, 8 * math.sin(t * 12) * sign) @ Q(X, 5 * math.sin(t * 15) * sign)
    # Joie : bras en l'air.
    if cheer:
        b = 1 + 0.1 * math.sin(t * 8)
        d['upperarm_l'] = Q(Y, -118 * cheer * b) @ d['upperarm_l'].slerp(Quaternion(), cheer)
        d['upperarm_r'] = Q(Y, 118 * cheer * b) @ d['upperarm_r'].slerp(Quaternion(), cheer)
        d['lowerarm_l'] = Q(Y, -15 * cheer)
        d['lowerarm_r'] = Q(Y, 15 * cheer)
    # Gestes en parlant (main gauche), regard, acquiescement.
    if talk:
        d['upperarm_l'] = Q(X, -25 * talk * (0.6 + 0.4 * math.sin(t * 2.3))) @ d['upperarm_l']
        d['lowerarm_l'] = Q(X, -45 * talk * (0.7 + 0.3 * math.sin(t * 3.1)))
    d['neck_01'] = Q(Z, 0.4 * look * 57.3) @ Q(X, (8 * max(0.0, math.sin(t * 6)) * nod))
    d['head'] = Q(Z, 0.3 * look * 57.3) @ Q(Y, 2 * math.sin(t * 1.3))
    return d


def facing(theta_deg):
    return math.radians(theta_deg)


def state(t):
    """Positions (x, y), orientation (degrés) et gestes de chacun à l'instant t (s)."""
    st = {}
    enter = ramp(t, 0, 2.2)
    turn = ramp(t, 1.9, 2.6)
    walking = 1 - ramp(t, 1.9, 2.2)
    st['camille'] = dict(at=(-0.35, -2.8 + 2.05 * enter), rot=180 - 110 * turn, walk=walking, look=0.0)
    st['leo'] = dict(at=(-0.95, -2.6 + 2.2 * enter), rot=180 - 120 * turn, walk=walking, look=0.0)
    home, spot = (0.35, -0.15), (1.15, 2.0)
    go = ramp(t, s_('pieces'), s_('pieces') + 1.6)
    back = ramp(t, s_('horsligne') + 0.3, s_('horsligne') + 1.9)
    pos = lerp(home, spot, go) if back == 0 else lerp(spot, home, back)
    oscar = dict(at=pos, walk=0.0)
    # Orientation : vers le couple (-35°), vers la fenêtre en marchant (160°), face à la
    # fenêtre pour les photos (180°), retour (-20°), de nouveau vers le couple.
    def ang(a, b, k):
        return a + (b - a) * k
    rot = -35.0
    if t > s_('pieces'):
        rot = ang(-35, 160, ramp(t, s_('pieces'), s_('pieces') + 0.4))
    if t > s_('pieces') + 1.6:
        rot = ang(160, 180, ramp(t, s_('pieces') + 1.6, s_('pieces') + 2.0))
    if t > s_('horsligne') + 0.3:
        rot = ang(180, 340, ramp(t, s_('horsligne') + 0.3, s_('horsligne') + 0.7))
    if t > s_('horsligne') + 1.7:
        rot = ang(340, 325, ramp(t, s_('horsligne') + 1.7, s_('horsligne') + 2.1))
    oscar['rot'] = rot
    oscar['wave'] = ramp(t, 0.6, 1.0) * (1 - ramp(t, s_('intro') + 0.3, s_('intro') + 0.8))
    oscar['talk'] = 1.0 if s_('intro') < t < s_('intro') + 2.6 else 0.0
    oscar['phone'] = ramp(t, s_('intro') + 2.6, s_('intro') + 3.2) * (1 - ramp(t, s_('signature'), s_('signature') + 0.4))
    if s_('pieces') < t < s_('pieces') + 1.6 or s_('horsligne') + 0.3 < t < s_('horsligne') + 1.9:
        oscar['walk'] = 1.0
    oscar['extend'] = ramp(t, s_('signature'), s_('signature') + 0.5) * (1 - ramp(t, s_('outro'), s_('outro') + 0.5))
    st['camille']['sign'] = ramp(t, s_('signature') + 0.4, s_('signature') + 1.0) * (1 - ramp(t, e_('signature') - 0.6, e_('signature')))
    st['leo']['nod'] = 1.0 if s_('signature') < t < e_('signature') else 0.0
    for p in ('camille', 'leo'):
        st[p]['look'] = 0.5 * ramp(t, s_('pieces') + 0.4, s_('pieces') + 1.2) * (1 - back)
    party = ramp(t, s_('outro'), s_('outro') + 0.6)
    st['camille']['cheer'] = st['leo']['cheer'] = party
    oscar['wave'] = max(oscar['wave'], ramp(t, s_('outro') + 0.4, s_('outro') + 0.9))
    st['oscar'] = oscar
    return st


# Bouche d'Oscar : formes construites ici sur son visage (le paquet d'expressions MakeHuman
# n'est pas disponible) à partir des repères du modèle (« joint-jaw », « joint-mouth »,
# « lips ») : « bouche ouverte » (le menton pivote autour de la mâchoire) et « bouche ronde »
# (lèvres resserrées et avancées, pour « o », « ou »). Pilotées par les formes Rhubarb.
def group_points(obj, group, coords):
    gi = obj.vertex_groups[group].index
    return [i for i, v in enumerate(obj.data.vertices) if any(g.group == gi and g.weight > 0.5 for g in v.groups)]


def centroid(coords, idx):
    return sum((coords[i] for i in idx), Vector()) / max(1, len(idx))


def build_mouth_keys(obj):
    if not obj.data.shape_keys:
        obj.shape_key_add(name='Basis', from_mix=False)
    basis = obj.data.shape_keys.key_blocks[0].data
    coords = [Vector(d.co) for d in basis]
    jaw = centroid(coords, group_points(obj, 'joint-jaw', coords))
    mouth = centroid(coords, group_points(obj, 'joint-mouth', coords))
    lips = set(group_points(obj, 'lips', coords))
    body = set(group_points(obj, 'body', coords))
    print('BOUCHE pivot', tuple(round(c, 3) for c in jaw), 'centre', tuple(round(c, 3) for c in mouth), 'lèvres', len(lips))
    front = mouth.y  # le visage regarde vers -Y
    opened = obj.shape_key_add(name='bouche_ouverte', from_mix=False)
    rounded = obj.shape_key_add(name='bouche_ronde', from_mix=False)
    rot = Matrix.Rotation(math.radians(14), 3, 'X')
    for i, c in enumerate(coords):
        if i not in body:
            continue
        d = c - mouth
        # Menton et lèvre inférieure : sous le centre de la bouche, à l'avant du visage.
        if c.z < mouth.z + 0.002 and c.y < jaw.y and abs(d.x) < 0.075 and d.z > -0.085:
            w = max(0.0, 1 - (abs(d.x) / 0.075) ** 2) * max(0.0, 1 - max(0.0, -d.z - 0.05) / 0.035)
            if c.z < mouth.z - 0.002 or i in lips:
                p = jaw + rot @ (c - jaw)
                opened.data[i].co = c + (p - c) * w
        if i in lips:
            k = 0.28
            rounded.data[i].co = Vector((mouth.x + d.x * (1 - k), c.y - 0.004, c.z - d.z * 0.1))
    return opened, rounded


MOUTH_OPEN, MOUTH_ROUND = build_mouth_keys(OSCAR)
# Forme Rhubarb → (ouverture, arrondi).
SHAPE = {'A': (0.0, 0.0), 'B': (0.15, 0.0), 'C': (0.5, 0.0), 'D': (0.95, 0.0), 'E': (0.5, 0.5), 'F': (0.3, 0.9), 'G': (0.12, 0.0), 'H': (0.45, 0.0), 'X': (0.03, 0.0)}
mouth_state = [0.0, 0.0]


def mouth_shape(t):
    ms = t * 1000
    for k in KEYS:
        a, b = AT[k]
        if a <= ms < b:
            shape = 'X'
            for at, v in TIMING[k].get('mouth', []):
                if at > ms - a + 30:
                    break
                shape = v
            return shape
    return None


def set_mouth(t):
    shape = mouth_shape(t)
    target = SHAPE.get(shape, (0.0, 0.0)) if shape else (0.0, 0.0)
    for i in (0, 1):
        mouth_state[i] += (target[i] - mouth_state[i]) * 0.65
    MOUTH_OPEN.value, MOUTH_ROUND.value = mouth_state
    MOUTH_OPEN.keyframe_insert('value')
    MOUTH_ROUND.keyframe_insert('value')


# Caméra : mêmes plans que la version three.js (coordonnées converties, Z vers le haut).
cam_data = bpy.data.cameras.new('camera')
cam_data.sensor_fit = 'VERTICAL'
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 2.2
cam = bpy.data.objects.new('camera', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def camera_at(t):
    if t < s_('intro'):
        k = ramp(t, 0, s_('intro'))
        return lerp((1.0, -7.2, 2.0), (0.7, -5.0, 1.75), k), lerp((-0.5, -0.6, 1.05), (-0.3, -0.4, 1.25), k), 42, None
    if t < s_('pieces'):
        k = ramp(t, s_('intro'), e_('intro'))
        return lerp((0.6, -3.9, 1.7), (0.45, -3.4, 1.68), k), (-0.2, -0.4, 1.45), 36, None
    if t < s_('pieces') + 2.2:
        k = ramp(t, s_('pieces'), s_('pieces') + 2.2)
        return lerp((2.9, -1.6, 1.65), (2.7, -0.1, 1.6), k), lerp((0.6, 0.3, 1.35), (1.1, 1.9, 1.4), k), 40, None
    if t < s_('horsligne') + 1.9:
        return None, None, 30, 'telephone'
    if t < s_('outro'):
        k = ramp(t, s_('horsligne') + 1.9, e_('signature'))
        return lerp((1.4, -3.9, 1.65), (1.15, -3.5, 1.6), k), (-0.1, -0.45, 1.3), 36, None
    k = ramp(t, s_('outro'), TOTAL_MS / 1000)
    return lerp((0.9, -4.4, 1.75), (1.3, -6.6, 2.3), k), lerp((-0.3, -0.3, 1.3), (-0.5, 0.2, 1.2), k), 40, None


def screen_for(t):
    if t < s_('pieces'):
        return 'start'
    if t < s_('horsligne'):
        k = ramp(t, s_('pieces'), s_('horsligne'))
        return 'pieces0' if k < 0.33 else 'pieces1' if k < 0.66 else 'pieces2'
    if t < s_('signature'):
        return 'offline0' if ramp(t, s_('horsligne'), s_('signature')) < 0.5 else 'offline1'
    k = ramp(t, s_('signature') + 0.3, e_('signature'))
    return ['sign0', 'sign1', 'sign2', 'sign3', 'sign4', 'pdf', 'pdf'][min(6, int(k * 6))]


# Clignements : toutes les 2,8 à 4,6 s (décalés d'un personnage à l'autre), 0,17 s chacun.
def blink(t, who):
    import random
    r = random.Random(100 + who)
    at = 0.8 + r.random() * 2
    while at < t + 1:
        d = t - at
        if 0 <= d < 0.17:
            return math.sin(math.pi * d / 0.17)
        at += 2.8 + r.random() * 1.8
    return 0.0


# Toutes les poses en images clés (une par image : le flou de mouvement en profite).
t0 = time.time()
for f in range(1, FRAMES + 1):
    t = (f - 1) / FPS
    st = state(t)
    for name, rig in PEOPLE.items():
        s = st[name]
        rig.location = (s['at'][0], s['at'][1], 0.0)
        rig.rotation_euler = (0, 0, facing(s['rot']))
        rig.keyframe_insert('location', frame=f)
        rig.keyframe_insert('rotation_euler', frame=f)
        apply_pose(rig, body_pose(t, **{k: v for k, v in s.items() if k not in ('at', 'rot')}))
        realism.relax_hands(rig, grip_side='r', grip=max(s.get('phone', 0.0), s.get('sign', 0.0)) if name in ('oscar', 'camille') else 0.0)
        for pb in rig.pose.bones:
            pb.keyframe_insert('rotation_quaternion', frame=f)
    scene.frame_set(f)
    set_mouth(t)
    for n, (rig, _) in enumerate(PEOPLE_BODIES):
        v = blink(t, n)
        for key in BLINKS[rig.name]:
            key.value = v
            key.keyframe_insert('value', frame=f)
print('ANIMATION', round(time.time() - t0, 1), 's')

# --- Rendu image par image ------------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)
frames = [int(x) for x in A['frames'].split(',')] if 'frames' in A else range(int(A.get('start', 1)), min(FRAMES, int(A.get('end', FRAMES))) + 1)
for f in frames:
    scene.frame_set(f)
    t = (f - 1) / FPS
    pos, tgt, fov, follow = camera_at(t)
    cam_data.angle_y = math.radians(fov)
    if follow:
        ph = bpy.data.objects[follow]
        m = ph.matrix_world
        cam.matrix_world = m @ Matrix.Translation((0.0, -0.32, 0.02)) @ Matrix.Rotation(math.radians(90), 4, 'X')
        cam_data.dof.focus_object = ph
        cam_data.dof.aperture_fstop = 11
    else:
        c = Vector(pos)
        cam.matrix_world = Matrix.Translation(c) @ (Vector(tgt) - c).to_track_quat('-Z', 'Y').to_matrix().to_4x4()
        cam_data.dof.focus_distance = (Vector(tgt) - c).length
        cam_data.dof.focus_object = None
        cam_data.dof.aperture_fstop = 2.2
    screen_tex.image = SCREENS.get(screen_for(t), SCREENS['start'])
    scene.render.filepath = os.path.join(OUT, f'{f:04d}.png')
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f'image {f} rendue en {time.time() - t1:.1f} s', flush=True)

# Portraits de contrôle (validation du réalisme) : gros plan de trois quarts sur un visage.
for spec in filter(None, A.get('portraits', '').split(',')):
    who, f = spec.split(':')
    rig = PEOPLE[who]
    scene.frame_set(int(f))
    head = rig.matrix_world @ rig.pose.bones['head'].head + Vector((0, 0, 0.07))
    fwd = rig.matrix_world.to_3x3() @ Vector((0, -1, 0))
    fwd = Matrix.Rotation(math.radians(25), 3, 'Z') @ Vector((fwd.x, fwd.y, 0)).normalized()
    c = head + fwd * 0.95 + Vector((0, 0, 0.02))
    scene.render.use_motion_blur = False
    cam.matrix_world = Matrix.Translation(c) @ (head - c).to_track_quat('-Z', 'Y').to_matrix().to_4x4()
    cam_data.angle_y = math.radians(22)
    cam_data.dof.focus_object = None
    cam_data.dof.focus_distance = (head - c).length
    cam_data.dof.aperture_fstop = 2.8
    scene.render.filepath = os.path.join(OUT, f'portrait-{who}-{int(f):04d}.png')
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f'PORTRAIT {who} {f} rendu en {time.time() - t1:.1f} s', flush=True)
