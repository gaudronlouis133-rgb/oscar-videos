"""OSCAR — plan de site vidéo (video-sitemap.xml) pour Google et les autres moteurs (0 €, sans modèle).

Pour chaque dossier voice/<vidéo> : titre et description (voice/<vidéo>/fiche.json, sinon le texte
des répliques du manifest.json), durée (mêmes valeurs que scripts/finition.py, ou mesurée par ffprobe
sur la vidéo finale si --videos), et adresses de la page, du fichier vidéo et de l'image d'aperçu.

L'adresse du site n'est jamais écrite dans le dépôt : elle est donnée au lancement (--site).
Modèles d'adresse ({site}, {nom}) modifiables avec --page, --fichier et --miniature.

Usage : python scripts/plan_de_site.py --site https://exemple.fr --out sortie
          [--voice voice/oscar-emmenagement ...] [--videos sortie] [--date 2026-10-29]
Dépendances : aucune ; ffmpeg/ffprobe si --videos (durée exacte et image d'aperçu <nom>.jpg).
"""
import argparse
import datetime
import glob
import json
import os
import subprocess
from xml.sax.saxutils import escape

from finition import OPEN_MS, GAP_MS, END_MS


def duree_s(clips, video=None):
    """Durée en secondes : mesurée sur la vidéo si elle existe, sinon calculée comme finition.py."""
    if video and os.path.exists(video):
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video],
                           capture_output=True, text=True, check=True)
        return round(float(r.stdout.strip()))
    return round((OPEN_MS + sum(c['ms'] for c in clips.values()) + GAP_MS * (len(clips) - 1) + END_MS) / 1000)


def miniature(video, jpg):
    """Image d'aperçu prise au milieu de la vidéo (Google l'exige ; 1280 px de large)."""
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video],
                       capture_output=True, text=True, check=True)
    subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-ss', f'{float(r.stdout) / 2:.2f}',
                    '-i', video, '-frames:v', '1', '-vf', 'scale=1280:-2', '-q:v', '3', jpg], check=True)


def fiche(dossier):
    nom = os.path.basename(os.path.normpath(dossier))
    clips = json.load(open(os.path.join(dossier, 'manifest.json'), encoding='utf-8'))['clips']
    chemin = os.path.join(dossier, 'fiche.json')
    f = json.load(open(chemin, encoding='utf-8')) if os.path.exists(chemin) else {}
    return {
        'nom': nom,
        'clips': clips,
        'titre': f.get('titre') or nom.replace('-', ' ').capitalize(),
        # Google : 2048 signes au plus.
        'description': (f.get('description') or ' '.join(c['text'] for c in clips.values()))[:2048],
    }


def entree(v, a):
    champs = {'site': a.site.rstrip('/'), 'nom': v['nom']}
    video = os.path.join(a.videos, f"{v['nom']}.mp4") if a.videos else None
    if video and os.path.exists(video):
        miniature(video, os.path.join(a.out, f"{v['nom']}.jpg"))
    balises = [
        ('video:thumbnail_loc', a.miniature.format(**champs)),
        ('video:title', v['titre']),
        ('video:description', v['description']),
        ('video:content_loc', a.fichier.format(**champs)),
        ('video:duration', str(duree_s(v['clips'], video))),
        ('video:publication_date', a.date),
        ('video:family_friendly', 'yes'),
    ]
    corps = '\n'.join(f'      <{b}>{escape(t)}</{b}>' for b, t in balises)
    return (f'  <url>\n    <loc>{escape(a.page.format(**champs))}</loc>\n'
            f'    <video:video>\n{corps}\n    </video:video>\n  </url>')


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--site', required=True, help='adresse du site, ex. https://exemple.fr (jamais dans le dépôt)')
    p.add_argument('--voice', nargs='*', help='dossiers voice/<vidéo> (par défaut : tous)')
    p.add_argument('--out', default='sortie')
    p.add_argument('--videos', help='dossier des vidéos finales <nom>.mp4 (durée exacte, image d\'aperçu)')
    p.add_argument('--page', default='{site}/videos/{nom}', help='page qui montre la vidéo')
    p.add_argument('--fichier', default='{site}/videos/{nom}.mp4', help='fichier vidéo')
    p.add_argument('--miniature', default='{site}/videos/{nom}.jpg', help='image d\'aperçu')
    p.add_argument('--date', default=datetime.date.today().isoformat(), help='date de publication (AAAA-MM-JJ)')
    a = p.parse_args()
    if not a.site.startswith('https://'):
        p.error('--site doit commencer par https://')

    racine = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'voice')
    dossiers = a.voice or sorted(os.path.dirname(m) for m in glob.glob(os.path.join(racine, '*', 'manifest.json')))
    os.makedirs(a.out, exist_ok=True)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
           '        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">\n'
           + '\n'.join(entree(fiche(d), a) for d in dossiers) + '\n</urlset>\n')
    chemin = os.path.join(a.out, 'video-sitemap.xml')
    with open(chemin, 'w', encoding='utf-8') as f:
        f.write(xml)
    print('PLAN DE SITE', chemin, len(dossiers), 'vidéo(s)')
    for f in sorted(os.listdir(a.out)):
        print('  ', f, os.path.getsize(os.path.join(a.out, f)), 'octets')


if __name__ == '__main__':
    main()
