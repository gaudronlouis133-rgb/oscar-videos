"""Karting #202 — montage vertical 1080×1920 (TikTok / Reels / Shorts) à partir des clips IA.

Format « ces photos étaient figées… » : chaque plan démarre sur la photo d'origine (étiquette PHOTO),
flash + secousse, puis la même image s'anime (étiquette IA). Coupes calées sur un tempo de 120 BPM,
fin qui reboucle sur la première image (les vidéos qui bouclent sont revues plusieurs fois).
La musique (kick, basse, charleston, montée, whoosh, déclencheur) est synthétisée ici : aucun son
sous droits. Une version sans son est aussi écrite, pour poser un son tendance dans l'appli.

    python montage.py <dossier_photos> <dossier_clips> <sortie.mp4>

<dossier_clips> contient <id>_hd.mp4 (ou <id>.mp4) produits par kaggle_anime.py. Clip absent :
la photo est animée en zoom lent (repli, pour tester le montage sans GPU).
"""
import os
import subprocess
import sys
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
BEAT = 0.5  # 120 BPM
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
YELLOW = (236, 255, 40)
# Même recadrage que kaggle_anime.py (centre horizontal cx).
PHOTOS = {"casque": ("casque.jpg", 0.43), "face": ("face.jpg", 0.46), "stand": ("stand.jpg", 0.5),
          "profil": ("profil.jpg", 0.5)}

# (début, fin, plan, rôle, texte, emoji). rôle : photo = image figée, ia = clip, fin = boucle.
TIMELINE = [
    (0.0, 2.0, "casque", "photo", "Ces photos de karting\nétaient figées…", None),
    (2.0, 5.5, "casque", "ia", "…jusqu'à ce que\nl'IA les réveille", "🤯"),
    (5.5, 6.0, "face", "photo", None, None),
    (6.0, 9.5, "face", "ia", "N°202\nprêt à partir", "🔥"),
    (9.5, 10.0, "stand", "photo", None, None),
    (10.0, 13.0, "stand", "ia", "Direction\nla piste", "🏁"),
    (13.0, 13.5, "profil", "photo", None, None),
    (13.5, 17.0, "profil", "ia", "Et là…\nplein gaz", "💨"),
    (17.0, 20.0, "casque", "fin", "Futur champion ?\nÉcris 202 en commentaire", "🏆"),
]
DROPS = [2.0, 6.0, 10.0, 13.5]
# Hauteur du texte par plan : là où il ne cache ni le casque ni le n°202, et au-dessus du bas de
# l'écran (masqué par les boutons de TikTok / Reels au-delà de ~1600 px).
TEXT_Y = {"casque": 1250, "face": 860, "stand": 1300, "profil": 190}  # passages photo → IA : flash, secousse, whoosh


def font(size):
    return ImageFont.truetype(FONT, size)


def crop_fill(img, w, h, cx=0.5):
    ih, iw = img.shape[:2]
    if iw / ih > w / h:
        nw = int(ih * w / h)
        x = min(max(int(iw * cx - nw / 2), 0), iw - nw)
        img = img[:, x:x + nw]
    else:
        nh = int(iw * h / w)
        y = (ih - nh) // 2
        img = img[y:y + nh]
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA if img.shape[1] > w else cv2.INTER_LANCZOS4)


def vertical(frame, landscape):
    """Plan paysage → vertical : fond flouté et assombri, plan net au centre."""
    if not landscape:
        return crop_fill(frame, W, H)
    bg = crop_fill(frame, W // 4, H // 4)
    bg = cv2.GaussianBlur(cv2.resize(bg, (W, H)), (0, 0), 18)
    bg = (bg * 0.55).astype(np.uint8)
    fh = int(frame.shape[0] * (W + 120) / frame.shape[1])  # léger débord : plus immersif
    fg = cv2.resize(frame, (W + 120, fh), interpolation=cv2.INTER_LANCZOS4)[:, 60:60 + W]
    y = (H - fh) // 2
    bg[y:y + fh] = fg
    return bg


def read_clip(path, landscape):
    """Décode le clip, interpole à 30 i/s (ffmpeg minterpolate) et le passe en 1080×1920."""
    sw, sh = (1440, 830) if landscape else (W, H)
    vf = (f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
          f"scale={sw}:{sh}:force_original_aspect_ratio=increase:flags=lanczos,crop={sw}:{sh}")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, sh, sw, 3)
    return [vertical(f, landscape) for f in fr]


def zoom(img, z, cx=0.5, cy=0.5, dx=0.0, dy=0.0):
    if z == 1 and dx == 0 and dy == 0:
        return img
    m = np.float32([[z, 0, (1 - z) * W * cx + dx], [0, z, (1 - z) * H * cy + dy]])
    return cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def text_layer(text, emoji, size=96):
    """Texte blanc à contour noir (style sous-titres TikTok), emoji couleur en dessous."""
    f = font(size)
    lines = text.split("\n")
    pad = 30
    boxes = [f.getbbox(line, stroke_width=10) for line in lines]
    lw = max(b[2] - b[0] for b in boxes)
    lh = size + 22
    eh = int(size * 1.25) if emoji else 0
    im = Image.new("RGBA", (lw + 2 * pad, lh * len(lines) + eh + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, line in enumerate(lines):
        x = (im.width - (boxes[i][2] - boxes[i][0])) // 2 - boxes[i][0]
        fill = YELLOW if ("202" in line or "IA" in line) else (255, 255, 255)
        d.text((x, pad + i * lh), line, font=f, fill=fill, stroke_width=10, stroke_fill=(0, 0, 0))
    if emoji:
        e = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(e).text((0, 0), emoji, font=ImageFont.truetype(EMOJI, 109), embedded_color=True)
        e = e.crop(e.getbbox()).resize((eh, eh), Image.LANCZOS)
        im.alpha_composite(e, ((im.width - eh) // 2, pad + lh * len(lines)))
    if im.width > W - 60:  # ligne trop longue : on réduit tout le bloc à la largeur de l'écran
        im = im.resize((W - 60, int(im.height * (W - 60) / im.width)), Image.LANCZOS)
    return np.array(im)


def tag_layer(label, color):
    f = font(44)
    b = f.getbbox(label)
    im = Image.new("RGBA", (b[2] - b[0] + 56, 84), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=42, fill=color + (235,))
    d.text((28 - b[0], 18 - b[1] + 4), label, font=f, fill=(0, 0, 0))
    return np.array(im)


def paste(img, layer, x, y, scale=1.0, alpha=1.0):
    if scale < 0.05:
        return
    if scale != 1.0:
        layer = cv2.resize(layer, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = layer.shape[:2]
    x, y = int(x - w / 2), int(y)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    lay = layer[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = lay[..., 3:4] / 255 * alpha
    reg = img[y0:y1, x0:x1].astype(np.float32)
    img[y0:y1, x0:x1] = (reg * (1 - a) + lay[..., :3] * a).astype(np.uint8)


def pop(t):
    """Échelle d'apparition « pop » : 0.6 → 1.08 → 1.0 en 0,25 s."""
    if t <= 0:
        return 0.0
    if t < 0.12:
        return 0.6 + 0.48 * t / 0.12
    if t < 0.25:
        return 1.08 - 0.08 * (t - 0.12) / 0.13
    return 1.0


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def render_video(photos_dir, clips_dir, out_path):
    stills, clips = {}, {}
    for k, (name, cx) in PHOTOS.items():
        im = cv2.cvtColor(cv2.imread(os.path.join(photos_dir, name)), cv2.COLOR_BGR2RGB)
        land = k == "profil"
        stills[k] = vertical(crop_fill(im, 1440, 830, cx), True) if land else crop_fill(im, W, H, cx)
        path = next((p for p in (os.path.join(clips_dir, f"{k}_hd.mp4"), os.path.join(clips_dir, f"{k}.mp4"))
                     if os.path.exists(p)), None)
        clips[k] = read_clip(path, land) if path else None
        print(k, "clip :", path or "absent (repli zoom)", flush=True)
    texts = {i: text_layer(s[4], s[5]) for i, s in enumerate(TIMELINE) if s[4]}
    tag_photo, tag_ia = tag_layer("PHOTO", (255, 255, 255)), tag_layer("ANIMÉE PAR L'IA", YELLOW)
    rng = np.random.default_rng(202)
    total = TIMELINE[-1][1]
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
    for n in range(int(total * FPS)):
        t = n / FPS
        i, (a, b, k, role, _, _) = next((i, s) for i, s in enumerate(TIMELINE) if s[0] <= t < s[1])
        lt = t - a
        if role == "photo":
            # photo figée, zoom lent ; au tout début, léger « déclic » d'obturateur (fondu depuis le noir)
            img = zoom(stills[k], 1.0 + 0.05 * lt / (b - a) + (0.03 if a == 0 else 0.0))
            if a == 0 and lt < 0.12:
                img = (img * (lt / 0.12)).astype(np.uint8)
        elif role == "ia":
            fr = clips[k]
            if fr is None:
                img = zoom(stills[k], 1.0 + 0.12 * lt / (b - a), dy=-60 * lt)
            else:
                # profil : ralenti au début puis accélération (rampe de vitesse)
                if k == "profil":
                    pos = (0.45 * lt + 0.55 * lt * lt / (b - a)) * FPS
                else:
                    pos = lt * FPS
                img = fr[min(int(pos), len(fr) - 1)].copy()
                img = zoom(img, 1.0 + 0.04 * lt / (b - a))
        else:  # fin : dernières images du casque au ralenti, puis retour vers la photo d'origine (boucle)
            fr = clips[k]
            last = zoom(stills[k], 1.03)
            if fr is None:
                img = zoom(stills[k], 1.12 - 0.09 * ease(lt / (b - a)))
            else:
                src = fr[min(len(fr) - 1, int(len(fr) * 0.7 + lt * FPS * 0.5))]
                img = zoom(src, 1.08 - 0.05 * ease(lt / (b - a)))
            mix = ease((lt - (b - a - 0.6)) / 0.6)
            if mix > 0:
                img = cv2.addWeighted(img, 1 - mix, last, mix, 0)
        img = np.ascontiguousarray(img)
        # passage photo → IA : secousse, aberration chromatique, flash blanc
        for d in DROPS:
            dt = t - d
            if 0 <= dt < 0.35:
                k_ = (1 - dt / 0.35) ** 2
                img = zoom(img, 1.0 + 0.06 * k_, dx=rng.normal(0, 22 * k_), dy=rng.normal(0, 22 * k_))
                s = int(14 * k_)
                if s:
                    img[..., 0] = np.roll(img[..., 0], s, axis=1)
                    img[..., 2] = np.roll(img[..., 2], -s, axis=1)
                if dt < 0.2:
                    img = cv2.addWeighted(img, 1 - 0.85 * (1 - dt / 0.2), np.full_like(img, 255),
                                          0.85 * (1 - dt / 0.2), 0)
        # léger vignettage
        img = (img.astype(np.float32) * VIGNETTE).astype(np.uint8)
        # étiquette PHOTO / IA en haut à gauche
        if role in ("photo", "ia"):
            tag = tag_photo if role == "photo" else tag_ia
            paste(img, tag, 60 + tag.shape[1] / 2, 150, pop(lt) if role == "ia" else 1.0)
        # texte : au premier tiers de l'écran, apparition « pop », petit rebond sur chaque temps
        if i in texts:
            beat = (t % BEAT) / BEAT
            sc = pop(lt) * (1 + 0.025 * max(0, 1 - beat * 4))
            y = TEXT_Y[k]
            paste(img, texts[i], W / 2, y - texts[i].shape[0] * (sc - 1) / 2, sc)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    return total


def _vignette():
    y, x = np.ogrid[:H, :W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    return (1 - 0.28 * np.clip(r - 0.55, 0, 1) ** 1.5)[..., None].astype(np.float32)


VIGNETTE = _vignette()


def synth_audio(total, path, sr=44100):
    """Piste d'accompagnement 120 BPM, synthétisée (aucun son sous droits)."""
    n = int(total * sr)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(7)

    def add(sig, t):
        i = int(t * sr)
        j = min(n, i + len(sig))
        if i < n:
            out[i:j] += sig[: j - i]

    def env(d, att=0.002, rel=None):
        tt = np.arange(int(d * sr)) / sr
        e = np.minimum(tt / att, 1) * np.exp(-tt / (rel or d / 4))
        return tt, e

    def kick():
        tt, e = env(0.45, rel=0.12)
        f = 48 + 110 * np.exp(-tt * 30)
        return 0.9 * np.sin(2 * np.pi * np.cumsum(f) / sr) * e

    def hat(open_=False):
        tt, e = env(0.18 if open_ else 0.05, rel=0.05 if open_ else 0.012)
        x = rng.normal(0, 1, len(tt))
        x = x - np.convolve(x, np.ones(4) / 4, "same")
        return 0.18 * x * e

    def bass(freq, d):
        tt, e = env(d, att=0.005, rel=d)
        s = np.sign(np.sin(2 * np.pi * freq * tt)) * 0.5 + np.sin(2 * np.pi * freq * tt)
        return 0.22 * np.tanh(1.5 * s) * e

    def whoosh(d=0.5):
        tt = np.arange(int(d * sr)) / sr
        x = rng.normal(0, 1, len(tt))
        lp = np.zeros_like(x)
        a = np.linspace(0.02, 0.5, len(tt)) ** 2
        for i in range(1, len(x)):
            lp[i] = lp[i - 1] + a[i] * (x[i] - lp[i - 1])
        return 0.5 * lp * np.sin(np.pi * tt / d) ** 2

    def rev(d=0.9):  # montée de régime façon moteur 2-temps
        tt = np.arange(int(d * sr)) / sr
        f = 70 + 260 * (tt / d) ** 1.6
        ph = 2 * np.pi * np.cumsum(f) / sr
        s = (ph / np.pi % 2 - 1) + 0.4 * np.sin(2 * ph)
        return 0.16 * np.tanh(2 * s) * np.minimum(tt / 0.05, 1) * np.exp(-np.maximum(tt - d * 0.8, 0) * 20)

    def riser(d):
        tt = np.arange(int(d * sr)) / sr
        x = rng.normal(0, 1, len(tt))
        x = x - np.convolve(x, np.ones(8) / 8, "same")
        tone = np.sin(2 * np.pi * np.cumsum(200 + 1200 * (tt / d) ** 2) / sr)
        return (0.12 * x + 0.08 * tone) * (tt / d) ** 2

    def click():
        tt, e = env(0.04, rel=0.006)
        return 0.5 * rng.normal(0, 1, len(tt)) * e

    notes = [55.0, 55.0, 65.41, 49.0]  # La, La, Do, Sol (graves)
    add(click(), 0.0)
    add(riser(2.0), 0.0)
    for b in range(int(total / BEAT)):
        t = b * BEAT
        if t < 2.0:  # accroche : juste un battement sourd
            if b % 2 == 0:
                add(0.4 * kick(), t)
            continue
        if t >= total - 0.6:
            continue
        add(kick(), t)
        add(hat(open_=b % 2 == 1), t + BEAT / 2)
        add(hat(), t + BEAT / 4)
        add(hat(), t + 3 * BEAT / 4)
        add(bass(notes[(b // 4) % 4], BEAT * 0.9), t)
    for d in DROPS:
        add(whoosh(), d - 0.35)
        add(1.2 * kick(), d)
    add(rev(1.2), 13.4)
    add(rev(0.9), 6.0)
    add(whoosh(0.8), total - 0.9)
    out = np.tanh(out * 1.2) * 0.85
    pcm = (np.stack([out, out], 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    photos_dir, clips_dir, out = sys.argv[1:4]
    silent = out.replace(".mp4", "_sans_son.mp4")
    total = render_video(photos_dir, clips_dir, silent)
    wav = out.replace(".mp4", ".wav")
    synth_audio(total, wav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(wav)
    print("écrit :", out, "et", silent)


if __name__ == "__main__":
    main()
