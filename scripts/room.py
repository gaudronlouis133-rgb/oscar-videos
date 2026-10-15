"""OSCAR — décor 3D partagé (13/10/2026) : l'appartement de « Le jour de l'emménagement »
(parquet et ciel Poly Haven CC0, murs, baie vitrée, soleil, meubles, cartons, cuisine).
Module importé par les scènes Blender (scripts/blender/humans/scene.py). Aucun effet à
l'import : build_room(scene, manifest) construit le décor.
"""
import math

import bpy
from mathutils import Vector

MANIFEST = {}

def srgb(h):
    """Couleur hexadécimale sRGB → linéaire (RGBA) pour Blender."""
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)


def material(name, color, rough=0.6, **inputs):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(color) if isinstance(color, str) else color
    b.inputs['Roughness'].default_value = rough
    for k, v in inputs.items():
        b.inputs[k].default_value = v
    return m


def texture_material(name, need, scale, fallback):
    """Matière Poly Haven (couleur, rugosité, relief) ; sinon couleur unie."""
    files = MANIFEST.get(need, {}).get('files', {})
    if 'diff' not in files:
        return material(name, fallback, 0.6)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    # Coordonnées « objet » (en mètres) et projection en boîte : pas d'étirement sur les murs.
    coord = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(coord.outputs['Object'], mapping.inputs['Vector'])

    def image(path, color=True):
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(path)
        n.projection = 'BOX'
        n.projection_blend = 0.2
        if not color:
            n.image.colorspace_settings.name = 'Non-Color'
        nt.links.new(mapping.outputs['Vector'], n.inputs['Vector'])
        return n

    nt.links.new(image(files['diff']).outputs['Color'], b.inputs['Base Color'])
    if 'rough' in files:
        nt.links.new(image(files['rough'], False).outputs['Color'], b.inputs['Roughness'])
    if 'nor' in files:
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = 0.6
        nt.links.new(image(files['nor'], False).outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def box(name, size, loc, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 4
        bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o


def ellipsoid(name, radii, mat, parent=None, loc=(0, 0, 0), segments=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=segments // 2, radius=1)
    o = bpy.context.active_object
    o.name = name
    o.scale = radii
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    o.location = loc
    return o


def empty(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(e)
    if parent:
        e.parent = parent
    e.location = loc
    return e


def import_model(need, loc, rot_z=0.0, scale=1.0):
    """Modèle Poly Haven (glTF) posé au sol ; None s'il est indisponible."""
    path = MANIFEST.get(need, {}).get('files', {}).get('gltf')
    if not path:
        return None
    before = set(bpy.data.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
    except Exception as e:  # modèle illisible : objet construit en code
        print(f'! {need} : import impossible ({e})')
        return None
    new = [o for o in bpy.data.objects if o not in before]
    holder = empty(f'{need}_holder')
    for o in new:
        if o.parent is None:
            o.parent = holder
    holder.location = loc
    holder.rotation_euler.z = rot_z
    holder.scale = (scale, scale, scale)
    return holder




def build_room(scene, manifest):
    """Construit l'appartement dans `scene` (manifest : scripts/blender/fetch_polyhaven.py)."""
    MANIFEST.clear()
    MANIFEST.update(manifest or {})
    # --- Monde : ciel de fin de journée (HDRI) -------------------------------------------------
    world = bpy.data.worlds.new('ciel')
    scene.world = world
    world.use_nodes = True
    wn = world.node_tree
    bg = wn.nodes['Background']
    sky = MANIFEST.get('sky', {}).get('files', {}).get('hdr')
    if sky:
        env = wn.nodes.new('ShaderNodeTexEnvironment')
        env.image = bpy.data.images.load(sky)
        wn.links.new(env.outputs['Color'], bg.inputs['Color'])
        bg.inputs['Strength'].default_value = 1.2
    else:
        bg.inputs['Color'].default_value = srgb('#F6C99A')
        bg.inputs['Strength'].default_value = 1.0

    # --- Pièce ---------------------------------------------------------------------------------
    floor_mat = texture_material('parquet', 'floor', 0.5, '#C89B6D')
    wall_mat = material('mur', '#EEE8DF', 0.85)  # peinture mate unie (plus net qu'un enduit texturé)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.scale = (9, 7, 1)
    bpy.ops.object.transform_apply(scale=True)
    floor.data.materials.append(floor_mat)
    ceiling = box('plafond', (9, 7, 0.05), (0, 0, 3.2), material('plafond', '#F7F3EC', 0.9))
    # Mur du fond avec une grande baie (x de -0.44 à 2.24, z de 0.6 à 2.5).
    WY = 3.5
    for name, size, loc in [
        ('mur_g', (4.06, 0.15, 3.2), (-2.47, WY, 1.6)),
        ('mur_d', (2.26, 0.15, 3.2), (3.37, WY, 1.6)),
        ('allege', (2.68, 0.15, 0.6), (0.9, WY, 0.3)),
        ('linteau', (2.68, 0.15, 0.7), (0.9, WY, 2.85)),
    ]:
        box(name, size, loc, wall_mat)
    box('mur_gauche', (0.15, 7, 3.2), (-4.5, 0, 1.6), wall_mat)
    frame_mat = material('cadre', '#FAFAF7', 0.4)
    for name, size, loc in [
        ('cadre_h', (2.76, 0.1, 0.08), (0.9, WY - 0.06, 2.5)),
        ('cadre_b', (2.76, 0.1, 0.08), (0.9, WY - 0.06, 0.6)),
        ('cadre_g', (0.08, 0.1, 1.98), (-0.44, WY - 0.06, 1.55)),
        ('cadre_d', (0.08, 0.1, 1.98), (2.24, WY - 0.06, 1.55)),
        ('meneau', (0.05, 0.08, 1.9), (0.9, WY - 0.06, 1.55)),
    ]:
        box(name, size, loc, frame_mat, bevel=0.01)
    box('plinthe', (9, 0.02, 0.1), (0, WY - 0.08, 0.05), frame_mat)

    # Soleil par la fenêtre + lumière douce de remplissage côté caméra.
    sun_data = bpy.data.lights.new('soleil', 'SUN')
    sun_data.energy = 4.5
    sun_data.angle = math.radians(1.5)
    sun_data.color = srgb('#FFD3A1')[:3]
    sun = bpy.data.objects.new('soleil', sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = Vector((-0.35, -0.85, -0.42)).to_track_quat('-Z', 'Y').to_euler()
    fill_data = bpy.data.lights.new('remplissage', 'AREA')
    fill_data.energy = 260
    fill_data.size = 3.5
    fill_data.color = srgb('#FFF1E2')[:3]
    fill = bpy.data.objects.new('remplissage', fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (1.5, -4.0, 2.8)
    fill.rotation_euler = (math.radians(60), 0, math.radians(20))

    # Meubles (Poly Haven si disponibles, sinon en code).
    if not import_model('sofa', (-3.9, 0.6, 0), math.radians(90)):
        sofa_mat = material('canape', '#33415C', 0.95)
        box('canape_assise', (0.95, 2.2, 0.42), (-3.9, 0.6, 0.21), sofa_mat, bevel=0.1)
        box('canape_dossier', (0.26, 2.2, 0.62), (-4.25, 0.6, 0.6), sofa_mat, bevel=0.1)
    if not import_model('table', (-2.1, 0.6, 0)):
        box('table', (1.0, 1.0, 0.05), (-2.1, 0.6, 0.4), material('bois', '#B9875A', 0.5), bevel=0.02)
    if not import_model('plant', (2.75, 3.0, 0)):
        ellipsoid('plante', (0.3, 0.3, 0.5), material('feuilles', '#4F7D5C', 0.8), loc=(2.75, 3.0, 0.7))
    if not import_model('lamp', (-4.0, 2.2, 0)):
        pass
    if not import_model('rug', (-2.1, 0.6, 0.002)):
        bpy.ops.mesh.primitive_cylinder_add(radius=1.25, depth=0.012, location=(-2.1, 0.6, 0.006))
        bpy.context.active_object.data.materials.append(material('tapis', '#E9DCC6', 1.0))
    for i, (x, y, z, s, r) in enumerate([(-0.9, 1.9, 0.2, 0.4, 0.2), (-0.5, 2.1, 0.2, 0.4, -0.1), (-0.75, 2.0, 0.57, 0.34, 0.5), (1.9, -0.9, 0.18, 0.36, 0.3)]):
        if not import_model('box', (x, y, z - s / 2), r):
            o = box(f'carton{i}', (s * 1.2, s, s), (x, y, z), material(f'carton{i}', '#C9A26F', 0.9), bevel=0.01)
            o.rotation_euler.z = r
    # Cuisine au fond à droite.
    box('cuisine', (2.2, 0.62, 0.9), (3.25, 3.15, 0.45), material('meuble', '#F8F6F2', 0.45), bevel=0.01)
    box('plan', (2.24, 0.66, 0.05), (3.25, 3.15, 0.92), material('plan', '#2F3747', 0.3), bevel=0.01)
