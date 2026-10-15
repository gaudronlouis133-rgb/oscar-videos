"""OSCAR — réalisme des personnages MakeHuman (13/10/2026) : cheveux mèche par mèche,
clignement des yeux, corps lissés. Outils intégrés à Blender uniquement (courbes de
cheveux, matière « Principled Hair », clés de forme) : rien à télécharger.

- Cheveux : des milliers de mèches implantées sur le cuir chevelu (groupe « scalp » du
  modèle MakeHuman), peignées vers l'arrière (courts) ou tombantes (carré), qui épousent la
  forme de la tête ; fixées à l'os de la tête (elles suivent ses mouvements).
- Clignement : paupière supérieure (et cils) qui pivote autour du centre de l'œil (repères
  « joint-l-eye » / « joint-r-eye » du modèle).
Déterministe (graine fixe).
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree


def shaped_coords(obj):
    """Coordonnées monde des sommets du maillage de base, formes (morphologie) appliquées,
    sans les modificateurs (les indices restent ceux des groupes de sommets)."""
    me = obj.data
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get('co', co)
    co = co.reshape(n, 3)
    keys = me.shape_keys.key_blocks if me.shape_keys else []
    if keys:
        basis = np.empty(n * 3)
        keys[0].data.foreach_get('co', basis)
        basis = basis.reshape(n, 3)
        co = basis.copy()
        for k in keys[1:]:
            if k.value and not k.mute:
                d = np.empty(n * 3)
                k.data.foreach_get('co', d)
                co += k.value * (d.reshape(n, 3) - basis)
    m = np.array(obj.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


def group_mask(obj, name, threshold=0.5):
    gi = obj.vertex_groups[name].index
    mask = np.zeros(len(obj.data.vertices), dtype=bool)
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == gi and g.weight > threshold:
                mask[v.index] = True
                break
    return mask


def _tangent(d, n):
    t = d - n * np.sum(d * n, axis=-1, keepdims=True)
    return t / np.maximum(np.linalg.norm(t, axis=-1, keepdims=True), 1e-9)


def hair_material(name, melanin=0.85, redness=0.3, roughness=0.32):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for node in list(nt.nodes):
        if node.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(node)
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    hair = nt.nodes.new('ShaderNodeBsdfHairPrincipled')
    hair.parametrization = 'MELANIN'
    hair.inputs['Melanin Redness'].default_value = redness
    hair.inputs['Roughness'].default_value = roughness
    hair.inputs['Radial Roughness'].default_value = 0.3
    hair.inputs['Coat'].default_value = 0.1
    hair.inputs['Random Color'].default_value = 0.08
    hair.inputs['Random Roughness'].default_value = 0.15
    # Mélanine par mèche (attribut « mel ») : mèche blanche possible.
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_type = 'GEOMETRY'
    attr.attribute_name = 'mel'
    nt.links.new(attr.outputs['Fac'], hair.inputs['Melanin'])
    nt.links.new(hair.outputs['BSDF'], out.inputs['Surface'])
    hair.inputs['Melanin'].default_value = melanin
    return m


def make_strand_hair(name, body, rig, style='short', count=40000, length=0.05, melanin=0.88,
                     redness=0.25, streak=None, seed=7, attach=None, radius=0.00006):
    """Cheveux mèche par mèche sur le cuir chevelu de `body`. style : 'short' (peignés vers
    l'arrière, houppe sur le devant) ou 'bob' (carré : raie au milieu, tombant sur les côtés).
    Chaque mèche pousse pas à pas et glisse sur la vraie surface de la tête (pas de mèche
    qui traverse le crâne). streak : (x0, largeur, mélanine) pour une mèche de couleur
    différente sur le devant (la mèche blanche d'Oscar)."""
    rng = np.random.default_rng(seed)
    co = shaped_coords(body)
    scalp = group_mask(body, 'scalp')
    me = body.data
    me.calc_loop_triangles()
    all_tris = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int64)
    # Surface de collision : tête et cou (tout ce qui est au-dessus des épaules).
    head_z = co[scalp][:, 2].min() - 0.16
    near_head = all_tris[(co[all_tris][:, :, 2] > head_z).all(axis=1)]
    bvh = BVHTree.FromPolygons([Vector(p) for p in co], near_head.tolist())
    tris = all_tris[scalp[all_tris].all(axis=1)]
    a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    cross = np.cross(b - a, c - a)
    area = np.linalg.norm(cross, axis=1) * 0.5
    normals = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-12)
    center = co[scalp].mean(axis=0) - np.array([0.0, 0.0, 0.055])
    pick = rng.choice(len(tris), size=count, p=area / area.sum())
    r1, r2 = rng.random(count), rng.random(count)
    s = np.sqrt(r1)
    roots = (1 - s)[:, None] * a[pick] + (s * (1 - r2))[:, None] * b[pick] + (s * r2)[:, None] * c[pick]
    nrm = normals[pick]
    flip = np.sum(nrm * (roots - center), axis=1) < 0
    nrm[flip] *= -1
    top_front = roots[:, 1].min()
    front = roots[:, 1] < top_front + 0.035
    down = np.array([0.0, 0.0, -1.0])
    if style == 'bob':
        npts, gravity, stiff = 14, 0.55, 0.6
        lengths = length * (0.9 + 0.15 * rng.random(count))
        side = np.sign(roots[:, 0] - center[0] + 1e-6)[:, None] * np.array([1.0, 0.0, 0.0])
        bias = side + 0.25 * np.array([0.0, 1.0, 0.0]) + 0.6 * down
    else:
        npts, gravity, stiff = 8, 0.04, 0.85
        lengths = length * (0.7 + 0.6 * rng.random(count))
        bias = np.tile(np.array([0.0, 1.0, -0.35]), (count, 1))
    d = _tangent(bias / np.linalg.norm(bias, axis=-1, keepdims=True), nrm)
    if style != 'bob':
        # Houppe : sur le devant, les mèches montent d'abord puis repartent vers l'arrière.
        d = np.where(front[:, None], d * 0.8 + nrm * 0.35, d)
    d += rng.normal(0, 0.1 if style == 'bob' else 0.05, size=d.shape)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    pts = np.zeros((count, npts, 3))
    pts[:, 0] = roots + nrm * 0.0004
    seg = lengths / (npts - 1)
    for i in range(1, npts):
        k = i / (npts - 1)
        off = (0.0012 + 0.005 * k) if style != 'bob' else (0.0015 + 0.010 * k)
        q = pts[:, i - 1] + d * seg[:, None]
        surf_n = nrm.copy()
        for j in range(count):
            hit = bvh.find_nearest(Vector(q[j]))
            if hit[0] is None:
                continue
            loc, n = np.array(hit[0]), np.array(hit[1])
            if np.dot(n, q[j] - center) < 0:
                n = -n
            surf_n[j] = n
            h = np.dot(q[j] - loc, n)
            if h < off:
                q[j] = q[j] + n * (off - h)
        step = q - pts[:, i - 1]
        nd = step / np.maximum(np.linalg.norm(step, axis=1, keepdims=True), 1e-9)
        bias_now = bias / np.linalg.norm(bias, axis=-1, keepdims=True)
        d = stiff * nd + (1 - stiff) * bias_now + gravity * down
        if style != 'bob':
            # Cheveux courts : couchés sur la tête (direction ramenée dans le plan du crâne).
            d = _tangent(d, surf_n) + surf_n * 0.03
        if style == 'bob':
            # Sous les oreilles, le carré tombe à la verticale.
            low = (q[:, 2] < center[2] - 0.02)[:, None]
            d = np.where(low, 0.3 * nd + down, d)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        pts[:, i] = q
    curves = bpy.data.hair_curves.new(name)
    curves.add_curves([npts] * count)
    curves.position_data.foreach_set('vector', pts.reshape(-1).astype(np.float32))
    rad = curves.attributes.get('radius') or curves.attributes.new('radius', 'FLOAT', 'POINT')
    taper = np.linspace(1.0, 0.3, npts)
    rad.data.foreach_set('value', np.tile(radius * taper, count).astype(np.float32))
    mel = curves.attributes.new('mel', 'FLOAT', 'CURVE')
    mels = np.full(count, melanin, dtype=np.float32) + rng.normal(0, 0.02, count).astype(np.float32)
    if streak:
        x0, width, smel = streak
        band = (np.abs(roots[:, 0] - x0) < width) & (roots[:, 1] < top_front + 0.06)
        mels[band] = smel
    mel.data.foreach_set('value', np.clip(mels, 0, 1))
    obj = bpy.data.objects.new(name, curves)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(hair_material(f'{name}_matiere', melanin=melanin, redness=redness))
    if attach:
        attach(obj, rig, 'head', Matrix.Identity(4))
    print('CHEVEUX', name, count, 'mèches', npts, 'points', 'mèche claire' if streak else '')
    return obj


def add_blink(body, lashes=None):
    """Clé de forme « cligne » : paupières supérieures (et cils) qui se ferment."""
    co = shaped_coords(body)
    inv = np.array(body.matrix_world.inverted())
    keys = []
    for target in [body] + ([lashes] if lashes else []):
        if not target.data.shape_keys:
            target.shape_key_add(name='Basis', from_mix=False)
        keys.append(target.shape_key_add(name='cligne', from_mix=False))
    moved = 0
    for side in ('l', 'r'):
        eye = co[group_mask(body, f'joint-{side}-eye')].mean(axis=0)
        for target, key in zip([body] + ([lashes] if lashes else []), keys):
            tco = co if target is body else shaped_coords(target)
            tinv = inv if target is body else np.array(target.matrix_world.inverted())
            for i, p in enumerate(tco):
                d = p - eye
                if abs(d[0]) < 0.019 and 0.0 < d[2] < 0.015 and d[1] < 0.004:
                    w = max(0.0, 1 - (abs(d[0]) / 0.019) ** 2) * min(1.0, max(0.0, (0.016 - d[2]) / 0.008))
                    ang = math.radians(38) * w
                    rot = np.array(Matrix.Rotation(ang, 3, 'X'))
                    q = eye + rot @ d
                    # La clé est relative à la base : on ajoute le déplacement monde converti.
                    base = np.array(key.data[i].co)
                    delta_local = tinv[:3, :3] @ (q - p)
                    key.data[i].co = Vector(base + delta_local)
                    moved += 1
    print('CLIGNEMENT', body.name, moved, 'sommets')
    return keys


def smooth_body(body, level=1):
    sub = body.modifiers.new('lisse', 'SUBSURF')
    sub.levels, sub.render_levels = 0, level
    return sub


def add_smile(body):
    """Clé de forme « sourire » : commissures des lèvres relevées et légèrement étirées (les
    visages MakeHuman par défaut paraissent renfrognés)."""
    co = shaped_coords(body)
    inv = np.array(body.matrix_world.inverted())[:3, :3]
    mouth = co[group_mask(body, 'joint-mouth')].mean(axis=0)
    lips = co[group_mask(body, 'lips')]
    half = np.abs(lips[:, 0] - mouth[0]).max()
    if not body.data.shape_keys:
        body.shape_key_add(name='Basis', from_mix=False)
    key = body.shape_key_add(name='sourire', from_mix=False)
    moved = 0
    for side in (-1, 1):
        corner = np.array([mouth[0] + side * half, mouth[1], mouth[2]])
        for i, p in enumerate(co):
            r = np.linalg.norm(p - corner)
            if r < 0.022 and p[1] < mouth[1] + 0.02:
                w = (1 - r / 0.022) ** 2
                delta = np.array([side * 0.0015, 0.0018, 0.0035]) * w
                key.data[i].co = Vector(np.array(key.data[i].co) + inv @ delta)
                moved += 1
    print('SOURIRE', body.name, moved, 'sommets', 'demi-largeur bouche', round(float(half), 4))
    return key


_CURL = {}


def relax_hands(rig, curl=1.0, grip_side=None, grip=0.0):
    """Doigts légèrement repliés (main au repos), à appliquer après la pose de chaque image.
    Le sens de flexion est déduit de la géométrie de la main (côté paume = côté du pouce)."""
    signs = _CURL.get(rig.name)
    if signs is None:
        signs = {}
        for side in ('l', 'r'):
            bones = rig.data.bones
            if f'hand_{side}' not in bones or f'index_01_{side}' not in bones or f'pinky_01_{side}' not in bones:
                continue
            h = bones[f'hand_{side}'].head_local
            n = (bones[f'index_01_{side}'].head_local - h).cross(bones[f'pinky_01_{side}'].head_local - h)
            thumb = bones.get(f'thumb_03_{side}') or bones.get(f'thumb_02_{side}')
            if thumb and (thumb.tail_local - h).dot(n) < 0:
                n = -n
            for b in bones:
                if b.name.endswith(f'_{side}') and b.name.split('_')[0] in ('index', 'middle', 'ring', 'pinky'):
                    z = b.matrix_local.to_3x3().col[2]
                    signs[b.name] = 1.0 if z.dot(n) > 0 else -1.0
        _CURL[rig.name] = signs
        print('DOIGTS', rig.name, len(signs), 'os', sorted(set(signs.values())))
    base = {'01': 14, '02': 24, '03': 16}
    extra = {'pinky': 6, 'ring': 3}
    for name, s in signs.items():
        pb = rig.pose.bones.get(name)
        if not pb:
            continue
        finger, seg, side = name.split('_')
        ang = (base.get(seg, 15) + extra.get(finger, 0)) * curl
        if side == grip_side:
            ang += 35 * grip
        pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion((1, 0, 0), math.radians(ang * s))


def make_scalp_cap(name, body, rig, color, streak=None, streak_color=(0.75, 0.74, 0.72), attach=None):
    """Sous-couche colorée sous les cheveux (technique habituelle des modèles 3D) : le crâne
    ne transparaît plus entre les mèches. Copie des faces du cuir chevelu, décollée de 0,4 mm."""
    co = shaped_coords(body)
    scalp = group_mask(body, 'scalp')
    me = body.data
    faces = [list(p.vertices) for p in me.polygons if all(scalp[v] for v in p.vertices)]
    used = sorted({v for f in faces for v in f})
    # Bord de la chevelure (sommets partagés avec une face hors cuir chevelu) : la sous-couche
    # s'y estompe sur 1,5 cm, pour une lisière douce au lieu d'une ligne nette.
    outside = {v for p in me.polygons if not all(scalp[v] for v in p.vertices) for v in p.vertices}
    edge = np.array([co[v] for v in used if v in outside]) if outside else np.zeros((0, 3))
    index = {v: i for i, v in enumerate(used)}
    pts = co[used]
    # Normales des sommets (moyenne des faces), orientées vers l'extérieur de la tête.
    center = pts.mean(axis=0) - np.array([0.0, 0.0, 0.055])
    normals = np.zeros_like(pts)
    for f in faces:
        a, b, c = co[f[0]], co[f[1]], co[f[2]]
        n = np.cross(b - a, c - a)
        for v in f:
            normals[index[v]] += n
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    flip = np.sum(normals * (pts - center), axis=1) < 0
    normals[flip] *= -1
    pts = pts + normals * 0.0004
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(p) for p in pts], [], [[index[v] for v in f] for f in faces])
    col = mesh.color_attributes.new('teinte', 'FLOAT_COLOR', 'POINT')
    fade = mesh.attributes.new('lisiere', 'FLOAT', 'POINT')
    for i, p in enumerate(pts):
        d = np.linalg.norm(edge - p, axis=1).min() if len(edge) else 1.0
        fade.data[i].value = float(min(1.0, d / 0.015))
    front_y = pts[:, 1].min()
    for i, p in enumerate(pts):
        c = color
        if streak and abs(p[0] - streak[0]) < streak[1] and p[1] < front_y + 0.06:
            c = streak_color
        col.data[i].color = (*c, 1.0)
    for poly in mesh.polygons:
        poly.use_smooth = True
    m = bpy.data.materials.new(f'{name}_matiere')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = 0.6
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = 'teinte'
    nt.links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
    lis = nt.nodes.new('ShaderNodeAttribute')
    lis.attribute_name = 'lisiere'
    nt.links.new(lis.outputs['Fac'], bsdf.inputs['Alpha'])
    mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if attach:
        attach(obj, rig, 'head', Matrix.Identity(4))
    print('SOUS-COUCHE', name, len(faces), 'faces')
    return obj
