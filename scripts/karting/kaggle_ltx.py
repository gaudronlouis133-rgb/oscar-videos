"""Construit le notebook Kaggle qui anime les photos avec LTX-Video (open source, Lightricks).

Les photos sont réduites et embarquées en base64 dans le script du notebook, qui reste privé :
pas de jeu de données à publier. Le notebook sort un .mp4 par plan dans /kaggle/working.

Usage :
    python3 kaggle_ltx.py --media DOSSIER --out notebook.py     # script (API Kaggle)
    python3 kaggle_ltx.py --media DOSSIER --out notebook.ipynb  # carnet à importer à la main
"""

import argparse
import base64
import io
import json

from PIL import Image

# plan -> (fichier, recadrage 9:16 centre x, invite)
SHOTS = {
    "kart": (
        "kart.webp", 0.45,
        "A young karting driver in a red and black racing suit and a red and white helmet sits in a "
        "blue Praga racing go-kart number 202 parked on a metal stand in a garden. He grips the "
        "steering wheel and slowly turns his head toward the camera. The green bushes sway gently in "
        "the wind, warm evening sunlight, subtle handheld phone camera movement, photorealistic.",
    ),
    "sunset": (
        "sunset.jpg", 0.38,
        "Cinematic close-up of a karting driver wearing a glossy red and white helmet, seated in a "
        "go-kart at golden hour. The low sun reflects on the wet asphalt of the track, lens flare, "
        "warm backlight, the driver breathes and adjusts his grip on the steering wheel, slow dolly "
        "in, shallow depth of field, photorealistic.",
    ),
    "freres": (
        "freres.png", 0.5,
        "Two young brothers in racing suits, one red and black, one black and neon yellow, lean "
        "against a stone wall holding their karting helmets. They look at the camera with a confident "
        "smile, a light breeze moves their curly hair, slow camera push in, natural daylight, "
        "photorealistic.",
    ),
    "casque_jaune": (
        "casque_jaune.webp", 0.5,
        "A young karting driver in a black racing suit and a purple and neon yellow helmet with a "
        "dark visor leans on a concrete wall beside a race track, watching. Karts pass quickly in the "
        "background, his head slowly follows them, bright sunny day, photorealistic.",
    ),
    "kart239": (
        "kart239.jpg", 0.5,
        "Slow cinematic orbit around a blue and white Praga racing go-kart number 239 parked on gravel "
        "next to a white team van, carbon fiber bodywork reflecting the soft morning light, "
        "photorealistic, shallow depth of field.",
    ),
}

NEGATIVE = ("worst quality, low quality, blurry, jittery, distorted, deformed face, deformed hands, "
            "extra fingers, morphing, flicker, text, watermark")

NOTEBOOK = r'''
import base64, io, os, subprocess, sys, time, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "diffusers>=0.32", "transformers",
                "accelerate", "sentencepiece", "imageio", "imageio-ffmpeg"], check=True)
import torch
from PIL import Image
from diffusers import LTXImageToVideoPipeline
from diffusers.utils import export_to_video

SHOTS = json.loads(__SHOTS__)
NEGATIVE = __NEG__
ONLY = os.environ.get("ONLY")

gpu = torch.cuda.is_available()
print("GPU:", torch.cuda.get_device_name(0) if gpu else "aucun (CPU)", flush=True)
dtype = torch.bfloat16
pipe = LTXImageToVideoPipeline.from_pretrained("Lightricks/LTX-Video", torch_dtype=dtype)
if gpu:
    pipe.enable_model_cpu_offload()
pipe.vae.enable_tiling()

# portrait 9:16 (multiples de 32) ; plus petit et plus court sur CPU
W, H, N, STEPS = (512, 896, 121, 40) if gpu else (352, 608, 49, 25)

for name, (b64, prompt) in SHOTS.items():
    if ONLY and name not in ONLY.split(","):
        continue
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB").resize((W, H), Image.LANCZOS)
    t0 = time.time()
    frames = pipe(image=img, prompt=prompt, negative_prompt=NEGATIVE, width=W, height=H,
                  num_frames=N, num_inference_steps=STEPS, guidance_scale=3.0,
                  decode_timestep=0.03, decode_noise_scale=0.025,
                  generator=torch.Generator("cpu").manual_seed(42)).frames[0]
    export_to_video(frames, f"/kaggle/working/{name}.mp4", fps=24)
    print(f"{name}: {len(frames)} images en {time.time() - t0:.0f} s", flush=True)
print("FINI", flush=True)
'''


def build(media, out):
    shots = {}
    for name, (fn, cx, prompt) in SHOTS.items():
        im = Image.open(f"{media}/{fn}").convert("RGB")
        if fn == "kart.webp":  # bandes noires haut et bas
            import numpy as np
            rows = np.where(np.asarray(im).mean(axis=(1, 2)) > 20)[0]
            im = im.crop((0, rows[0], im.width, rows[-1]))
        r = 9 / 16
        if im.width / im.height > r:
            nw = int(im.height * r)
            x0 = int((im.width - nw) * cx)
            im = im.crop((x0, 0, x0 + nw, im.height))
        else:
            nh = int(im.width / r)
            im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
        im = im.resize((512, 896), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        shots[name] = [base64.b64encode(buf.getvalue()).decode(), prompt]
    src = NOTEBOOK.replace("__SHOTS__", repr(json.dumps(shots))).replace("__NEG__", repr(NEGATIVE))
    if out.endswith(".ipynb"):
        # carnet à importer tel quel dans Kaggle (File > Import Notebook)
        nb = {"cells": [{"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                         "source": src.splitlines(keepends=True)}],
              "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                           "language_info": {"name": "python"}},
              "nbformat": 4, "nbformat_minor": 4}
        src = json.dumps(nb)
    with open(out, "w") as f:
        f.write(src)
    print(out, len(src) // 1024, "Ko")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--media", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    build(a.media, a.out)
