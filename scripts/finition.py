"""OSCAR — sous-titres et vidéo finale à partir du rendu muet (0 €, processeur seul).

À partir de voice/<vidéo>/manifest.json et des *.timing.json (instants des mots) :
  1. sous-titres français (.srt), sans aucun modèle : les instants sont déjà mesurés ;
  2. --langues en,es : sous-titres traduits (Helsinki-NLP opus-mt, CC-BY 4.0, sur processeur) ;
  3. --voix <dossier> (<clé>.mp3 ou .wav) : piste son complète, placée aux mêmes instants que
     scripts/humans/scene.py ;
  4. --muet <vidéo.mp4> : vidéo avec le son (si --voix) et les sous-titres, en deux versions :
     sous-titres activables, et sous-titres incrustés (réseaux sociaux).

Usage : python scripts/finition.py --voice voice/oscar-emmenagement --out sortie
          [--langues en,es] [--voix <dossier>] [--muet <vraie3d-…-muet.mp4>]
Dépendances : ffmpeg ; numpy et soundfile si --voix ; transformers, sentencepiece, sacremoses et
torch si --langues.
"""
import argparse
import json
import os
import re
import subprocess
import unicodedata

# Mêmes valeurs que scripts/humans/scene.py (déroulé de la vidéo).
OPEN_MS, GAP_MS, END_MS, FPS = 2600, 550, 2600, 24
SR = 48000
AUDIO = ('.mp3', '.wav', '.flac', '.m4a', '.ogg')


def run(cmd):
    subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', *cmd], check=True)


def norm(w):
    w = unicodedata.normalize('NFD', w.lower().replace('’', "'"))
    return re.sub(r"[^a-z0-9']", '', ''.join(c for c in w if unicodedata.category(c) != 'Mn'))


def phrases(mots):
    """Mots groupés en phrases (« . », « ! », « ? »), puis en morceaux de 2 lignes de 42 signes."""
    groupes, cur = [], []
    for m in mots:
        cur.append(m)
        if re.search(r'[.!?…]$', m['text']):
            groupes.append(cur)
            cur = []
    if cur:
        groupes.append(cur)
    out = []
    for g in groupes:
        morceaux, cur = [], []
        for m in g:
            if cur and len(' '.join(x['text'] for x in cur + [m])) > 84:
                morceaux.append(cur)
                cur = []
            cur.append(m)
        if cur:
            # Ponctuation isolée en fin de phrase : rattachée au morceau précédent.
            if morceaux and not any(norm(x['text']) for x in cur):
                morceaux[-1] += cur
            else:
                morceaux.append(cur)
        out.append(morceaux)
    return out


def lignes(texte, n=42):
    out, cur = [], ''
    for m in texte.split():
        if cur and len(cur) + 1 + len(m) > n:
            out.append(cur)
            cur = m
        else:
            cur = f'{cur} {m}'.strip()
    return '\n'.join(out + [cur])


def horodatage(ms):
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def ecrit_srt(path, cues):
    with open(path, 'w', encoding='utf-8') as f:
        for i, (a, b, t) in enumerate(cues, 1):
            f.write(f'{i}\n{horodatage(a)} --> {horodatage(b)}\n{lignes(t)}\n\n')


def sous_titres(timings, debuts, langues, traduit):
    """Cues FR (texte, instants) et, pour chaque langue, la traduction phrase par phrase."""
    cues = {lang: [] for lang in ['fr', *langues]}
    for cle, t in timings.items():
        for morceaux in phrases(t['words']):
            temps = []
            for m in morceaux:
                a = debuts[cle] + m[0]['start']
                b = debuts[cle] + max(x['end'] for x in m) + 250
                temps.append((a, b))
                cues['fr'].append([a, b, ' '.join(x['text'] for x in m)])
            phrase = ' '.join(x['text'] for m in morceaux for x in m)
            for lang in langues:
                # La traduction d'une phrase coupée en morceaux est répartie sur les mêmes instants.
                mots, n = traduit(lang, phrase).split(), len(morceaux)
                for k, (a, b) in enumerate(temps):
                    cues[lang].append([a, b, ' '.join(mots[k * len(mots) // n:(k + 1) * len(mots) // n])])
    for lst in cues.values():
        # Un sous-titre ne déborde pas sur le suivant.
        for c, n in zip(lst, lst[1:]):
            c[1] = max(c[0] + 100, min(c[1], n[0] - 40))
    return cues


def traducteur():
    from transformers import pipeline
    cache = {}

    def traduit(lang, texte):
        if lang not in cache:
            cache[lang] = pipeline('translation', model=f'Helsinki-NLP/opus-mt-fr-{lang}', device=-1)
        return cache[lang](texte, max_length=512)[0]['translation_text']
    return traduit


def piste(voix, cles, debuts, total_ms, out):
    """Répliques placées à leur instant ; silences de début et de fin retirés de chacune."""
    import numpy as np
    import soundfile as sf
    trim = 'silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02'
    x = np.zeros(int(total_ms * SR / 1000), np.float32)
    for k in cles:
        src = next((os.path.join(voix, k + e) for e in AUDIO if os.path.exists(os.path.join(voix, k + e))), None)
        if not src:
            raise SystemExit(f'réplique manquante : {k} (attendu {voix}/{k}.mp3 ou .wav)')
        wav = os.path.join(out, f'{k}.tmp.wav')
        run(['-i', src, '-ac', '1', '-ar', str(SR), '-af', f'{trim},areverse,{trim},areverse', '-c:a', 'pcm_s16le', wav])
        y, _ = sf.read(wav, dtype='float32')
        os.remove(wav)
        i = debuts[k] * SR // 1000
        y = y[:max(0, len(x) - i)]
        x[i:i + len(y)] += y
    path = os.path.join(out, 'piste.wav')
    sf.write(path, x, SR)
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--voice', required=True, help='dossier voice/<vidéo>')
    p.add_argument('--out', default='sortie')
    p.add_argument('--langues', default='', help='sous-titres traduits, ex. en,es')
    p.add_argument('--voix', help='dossier des répliques <clé>.mp3 / .wav')
    p.add_argument('--muet', help='vidéo muette du rendu (.mp4)')
    a = p.parse_args()

    nom = os.path.basename(os.path.normpath(a.voice))
    os.makedirs(a.out, exist_ok=True)
    clips = json.load(open(os.path.join(a.voice, 'manifest.json'), encoding='utf-8'))['clips']
    timings = {k: json.load(open(os.path.join(a.voice, f'{k}.timing.json'), encoding='utf-8')) for k in clips}
    debuts, t = {}, OPEN_MS
    for k in clips:
        debuts[k] = t
        t += clips[k]['ms'] + GAP_MS
    total_ms = t - GAP_MS + END_MS
    print('DURÉE', total_ms, 'ms →', -(-total_ms * FPS // 1000), 'images')

    langues = [x for x in a.langues.split(',') if x]
    for lang, lst in sous_titres(timings, debuts, langues, traducteur() if langues else None).items():
        ecrit_srt(os.path.join(a.out, f'{nom}.{lang}.srt'), lst)
        print('SOUS-TITRES', lang, len(lst))

    son = piste(a.voix, list(clips), debuts, total_ms, a.out) if a.voix else None
    if a.muet:
        srt = os.path.join(a.out, f'{nom}.fr.srt')
        audio = ['-i', son, '-map', '1:a', '-c:a', 'aac', '-b:a', '192k'] if son else []
        idx = '2' if son else '1'
        run(['-i', a.muet, *audio[:2], '-i', srt, '-map', '0:v', *audio[2:], '-map', idx, '-c:v', 'copy',
             '-c:s', 'mov_text', '-metadata:s:s:0', 'language=fre', '-movflags', '+faststart',
             os.path.join(a.out, f'{nom}.mp4')])
        style = 'FontName=DejaVu Sans,FontSize=9,Bold=1,Outline=2,Shadow=0,MarginV=60,Alignment=2'
        run(['-i', a.muet, *audio[:2], '-vf', f"subtitles={srt}:force_style='{style}'", '-map', '0:v', *audio[2:],
             '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
             os.path.join(a.out, f'{nom}-sous-titres.mp4')])
    for f in sorted(os.listdir(a.out)):
        print('  ', f, os.path.getsize(os.path.join(a.out, f)), 'octets')


if __name__ == '__main__':
    main()
