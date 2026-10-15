"""OSCAR — matières, lumière et meubles libres de droits pour l'essai Blender (13/10/2026).

Source : Poly Haven (https://polyhaven.com), tout le catalogue est en CC0 (domaine public :
usage commercial libre, sans attribution obligatoire ; on garde quand même la liste).
Seuls des fichiers de données sont téléchargés (images .jpg/.hdr, modèles glTF), en 1k,
uniquement depuis les domaines de Poly Haven. Pour chaque besoin : une liste d'identifiants
préférés, sinon une recherche par mots-clés dans le catalogue ; si rien n'est trouvé, la scène
Blender utilise un objet construit en code (voir emmenagement.py).

Usage : python fetch_polyhaven.py <dossier> → <dossier>/assets.json
"""

import json
import os
import sys
import urllib.parse
import urllib.request

API = 'https://api.polyhaven.com'
UA = {'User-Agent': 'oscar-vitrine-blender-trial/1.0'}
ALLOWED = ('polyhaven.org', 'polyhaven.com')

NEEDS = {
    # nom : (type, identifiants préférés, mots-clés)
    'sky': ('hdris', ['venice_sunset', 'kiara_1_dawn', 'golden_bay', 'spaichingen_hill'], ['sunset']),
    'floor': ('textures', ['wood_floor', 'laminate_floor_02', 'wood_floor_worn', 'herringbone_parquet'], ['wood', 'floor']),
    'wall': ('textures', ['painted_plaster_wall', 'white_plaster_02', 'beige_wall_001'], ['plaster']),
    'sofa': ('models', ['sofa_02', 'Sofa_01', 'sofa_03'], ['sofa']),
    'table': ('models', ['CoffeeTable_01', 'coffee_table_round_01', 'round_wooden_table_01'], ['coffee']),
    'plant': ('models', ['potted_plant_01', 'potted_plant_02', 'potted_plant_04'], ['plant']),
    'box': ('models', ['cardboard_box_01', 'cardboard_box_02'], ['cardboard']),
    'lamp': ('models', ['industrial_floor_lamp', 'modern_floor_lamp_01', 'Lantern_01'], ['floor lamp', 'lamp']),
    'rug': ('models', ['round_rug_01', 'rug_01'], ['rug']),
}


def get(url):
    host = urllib.parse.urlparse(url).hostname or ''
    if not any(host == d or host.endswith('.' + d) for d in ALLOWED):
        raise ValueError(f'domaine refusé : {host}')
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def pick(kind, preferred, words, catalog):
    for p in preferred:
        if p in catalog:
            return p
    for key, info in sorted(catalog.items()):
        name = (info.get('name', '') + ' ' + key).lower()
        if all(w in name for w in words[0].split()):
            return key
    return None


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    catalogs = {t: json.loads(get(f'{API}/assets?t={t}')) for t in ('hdris', 'textures', 'models')}
    result = {}
    for need, (kind, preferred, words) in NEEDS.items():
        asset = pick(kind, preferred, words, catalogs[kind])
        if not asset:
            print(f'– {need} : rien trouvé (objet construit en code)')
            continue
        files = json.loads(get(f'{API}/files/{asset}'))
        info = catalogs[kind][asset]
        entry = {'id': asset, 'name': info.get('name', asset), 'authors': list((info.get('authors') or {}).keys()), 'license': 'CC0', 'files': {}}
        folder = os.path.join(out, need)
        os.makedirs(folder, exist_ok=True)
        try:
            if kind == 'hdris':
                url = files['hdri']['1k']['hdr']['url']
                path = os.path.join(folder, 'sky.hdr')
                open(path, 'wb').write(get(url))
                entry['files']['hdr'] = path
            elif kind == 'textures':
                for slot, keys in {'diff': ['Diffuse', 'diff'], 'rough': ['Rough', 'rough'], 'nor': ['nor_gl', 'Normal']}.items():
                    key = next((k for k in keys if k in files), None)
                    if not key:
                        continue
                    url = files[key]['1k']['jpg']['url']
                    path = os.path.join(folder, f'{slot}.jpg')
                    open(path, 'wb').write(get(url))
                    entry['files'][slot] = path
            else:
                gltf = files['gltf']['1k']['gltf']
                main_path = os.path.join(folder, os.path.basename(urllib.parse.urlparse(gltf['url']).path))
                open(main_path, 'wb').write(get(gltf['url']))
                for rel, inc in (gltf.get('include') or {}).items():
                    target = os.path.abspath(os.path.join(folder, rel))
                    if not target.startswith(os.path.abspath(folder) + os.sep):
                        raise ValueError(f'chemin refusé : {rel}')
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    open(target, 'wb').write(get(inc['url']))
                entry['files']['gltf'] = main_path
        except (KeyError, ValueError) as e:
            print(f'– {need} ({asset}) : fichiers indisponibles ({e})')
            continue
        result[need] = entry
        print(f'✔ {need} : {asset} (CC0, {", ".join(entry["authors"]) or "Poly Haven"})')
    json.dump(result, open(os.path.join(out, 'assets.json'), 'w'), indent=2)


if __name__ == '__main__':
    main()
