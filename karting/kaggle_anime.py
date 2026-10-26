"""Karting #202 — met les photos en mouvement (image → vidéo), sur le GPU gratuit de Kaggle (T4).

Modèle : Wan 2.2 I2V-A14B (Alibaba, Apache-2.0), quantifié GGUF Q4_K_M (QuantStack) pour tenir
sur une T4 de 16 Go, + LoRA « Lightning » 4 étapes de lightx2v (Apache-2.0) : 4 pas sans CFG au lieu
de 20 pas avec CFG, soit environ 10 fois moins de calcul.
Puis Real-ESRGAN x4plus (BSD-3) via spandrel pour agrandir chaque image du clip.

Entrée : le dataset privé ericbouhfna/karting-202-photos (face.jpg, profil.jpg, casque.jpg, stand.jpg).
Sorties dans /kaggle/working/out/ : <id>.mp4 (480p brut), <id>_hd.mp4 (agrandi), rapport.json.
"""
import gc
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("HF_HOME", "/tmp/hf")

OUT = "/kaggle/working/out"
PKGS = ["diffusers==0.41.0", "transformers==5.19.0", "huggingface-hub==1.33.0", "tokenizers>=0.23.1,<0.24",
        "accelerate==1.15.0", "ftfy==6.3.1", "imageio-ffmpeg==0.6.0", "sentencepiece==0.2.2", "gguf>=0.10.0",
        "peft>=0.17", "spandrel>=0.4"]
REPO = "Wan-AI/Wan2.2-I2V-A14B-Diffusers"
GGUF_REPO, QUANT = "QuantStack/Wan2.2-I2V-A14B-GGUF", "Q4_K_M"
# Dépôts LoRA essayés dans l'ordre (le plus récent d'abord) ; le fichier est choisi d'après son nom.
LORA_REPOS = ["lightx2v/Wan2.2-Distill-Loras", "lightx2v/Wan2.2-Lightning", "Kijai/WanVideo_comfy"]
ESRGAN = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
FRAMES, FPS, STEPS = 81, 16, 4

# cx : centre horizontal du recadrage (0..1). Ordre = priorité.
SHOTS = [
    {"id": "casque", "image": "casque.jpg", "w": 480, "h": 832, "cx": 0.43, "seed": 202,
     "prompt": "Cinematic close-up of a kart racing driver wearing a glossy neon yellow and purple Bell helmet "
               "with a mirrored purple visor. The driver slowly turns the head toward the camera, sunlight glints "
               "travel across the visor, reflections shimmer, subtle breathing movement of the shoulders, "
               "shallow depth of field, slow motion, sports commercial, sharp details."},
    {"id": "face", "image": "face.jpg", "w": 480, "h": 832, "cx": 0.46, "seed": 2020,
     "prompt": "A kart racing driver in a neon yellow and purple helmet and black and neon green OMP suit sits in a "
               "blue racing kart number 202, turns the head forward and grips the steering wheel firmly, the "
               "engine vibrates the whole kart, heat haze above the engine, the kart starts rolling forward toward "
               "the camera, the camera slowly pushes in, cinematic motorsport commercial, bright sunlight."},
    {"id": "stand", "image": "stand.jpg", "w": 480, "h": 832, "cx": 0.5, "seed": 239,
     "prompt": "Two blue racing karts in the pit lane. The driver in the red helmet in kart number 202 drives "
               "forward toward the camera, the wheels roll, the kart behind with the yellow helmet driver number "
               "239 follows closely, the camera smoothly dollies backward, realistic motion, cinematic motorsport."},
    {"id": "profil", "image": "profil.jpg", "w": 832, "h": 480, "cx": 0.5, "seed": 22,
     "prompt": "Side view tracking shot: the blue racing kart number 202 with a driver in a neon yellow and purple "
               "helmet accelerates fast to the right along the concrete track, the wheels spin, the driver leans "
               "into the steering wheel, the camera tracks alongside smoothly, motion blur on the tire barriers in "
               "the background, dynamic high speed motorsport shot."},
]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fit(img, w, h, cx):
    """Recadre au format w×h autour de cx (sans déformer) puis redimensionne."""
    from PIL import Image

    iw, ih = img.size
    if iw / ih > w / h:
        nw = int(ih * w / h)
        x = min(max(int(iw * cx - nw / 2), 0), iw - nw)
        img = img.crop((x, 0, x + nw, ih))
    else:
        nh = int(iw * h / w)
        img = img.crop((0, (ih - nh) // 2, iw, (ih - nh) // 2 + nh))
    return img.resize((w, h), Image.LANCZOS)


def lora_files():
    """Renvoie (dépôt, fichier bruit fort, fichier bruit faible) pour le LoRA 4 étapes I2V A14B."""
    from huggingface_hub import list_repo_files

    for repo in LORA_REPOS:
        try:
            files = [f for f in list_repo_files(repo) if f.endswith(".safetensors")]
        except Exception as e:  # noqa: BLE001
            log("LoRA", repo, "inaccessible", e)
            continue
        cand = [f for f in files if re.search(r"i2v", f, re.I) and re.search(r"a14b", f, re.I)
                and re.search(r"4.?step", f, re.I)]
        hi = sorted(f for f in cand if re.search(r"high", f, re.I))
        lo = sorted(f for f in cand if re.search(r"low", f, re.I))
        log("LoRA", repo, "candidats", hi[-3:], lo[-3:])
        if hi and lo:
            return repo, hi[-1], lo[-1]
    raise SystemExit("aucun LoRA 4 étapes trouvé")


def generate(job_dir, res):
    import torch
    from diffusers import AutoencoderKLWan, GGUFQuantizationConfig, WanImageToVideoPipeline, WanTransformer3DModel
    from diffusers.pipelines.wan.pipeline_wan_i2v import prompt_clean
    from diffusers.utils import export_to_video
    from huggingface_hub import hf_hub_download, list_repo_files
    from PIL import Image
    from transformers import AutoTokenizer, UMT5EncoderModel

    # 1) textes encodés sur le processeur, encodeur libéré ensuite (pas de CFG : pas de texte négatif)
    tok = AutoTokenizer.from_pretrained(REPO, subfolder="tokenizer")
    enc = UMT5EncoderModel.from_pretrained(REPO, subfolder="text_encoder", torch_dtype=torch.float32).eval()

    def embed(text):
        ids = tok([prompt_clean(text)], padding="max_length", max_length=512, truncation=True,
                  add_special_tokens=True, return_attention_mask=True, return_tensors="pt")
        with torch.no_grad():
            h = enc(ids.input_ids, ids.attention_mask).last_hidden_state
        n = int(ids.attention_mask.sum())
        return torch.cat([h[:, :n], h.new_zeros(1, 512 - n, h.size(2))], dim=1)

    emb = {s["id"]: embed(s["prompt"]) for s in SHOTS}
    del enc
    gc.collect()
    log("textes encodés")

    # 2) les deux experts GGUF (bruit fort / bruit faible)
    files = list_repo_files(GGUF_REPO)

    def pick(word):
        cand = [f for f in files if f.endswith(".gguf") and word in f and QUANT in f]
        if not cand:
            raise SystemExit(f"GGUF {word} {QUANT} introuvable : {files[:40]}")
        return cand[0]

    q = GGUFQuantizationConfig(compute_dtype=torch.float16)
    experts = []
    for word, sub in (("HighNoise", "transformer"), ("LowNoise", "transformer_2")):
        path = hf_hub_download(GGUF_REPO, pick(word))
        log("chargement", os.path.basename(path), round(os.path.getsize(path) / 2**30, 2), "Go")
        experts.append(WanTransformer3DModel.from_single_file(path, quantization_config=q, config=REPO,
                                                              subfolder=sub, torch_dtype=torch.float16))
    vae = AutoencoderKLWan.from_pretrained(REPO, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanImageToVideoPipeline.from_pretrained(REPO, transformer=experts[0], transformer_2=experts[1], vae=vae,
                                                   text_encoder=None, tokenizer=None, torch_dtype=torch.float16)
    # 3) LoRA Lightning sur chaque expert
    lrepo, hi, lo = lora_files()
    pipe.load_lora_weights(lrepo, weight_name=hi, adapter_name="lightning")
    pipe.load_lora_weights(lrepo, weight_name=lo, adapter_name="lightning_2", load_into_transformer_2=True)
    res["_lora"] = {"repo": lrepo, "high": hi, "low": lo}
    log("LoRA chargé", res["_lora"])
    pipe.vae.enable_tiling()
    pipe.enable_model_cpu_offload(gpu_id=0)

    for s in SHOTS:
        img = fit(Image.open(os.path.join(job_dir, s["image"])).convert("RGB"), s["w"], s["h"], s["cx"])
        img.save(f"{OUT}/{s['id']}_depart.png")
        t0 = time.time()
        try:
            frames = pipe(image=img, prompt_embeds=emb[s["id"]].to("cuda:0", torch.float16),
                          height=s["h"], width=s["w"], num_frames=FRAMES, num_inference_steps=STEPS,
                          guidance_scale=1.0, guidance_scale_2=1.0,
                          generator=torch.Generator("cpu").manual_seed(s["seed"]), output_type="np").frames[0]
        except Exception as e:  # noqa: BLE001
            res[s["id"]] = {"erreur": f"{type(e).__name__}: {str(e)[:400]}"}
            log("ERREUR", s["id"], res[s["id"]])
            continue
        ok = bool((frames == frames).all() and frames.std() > 0.01)
        res[s["id"]] = {"taille": f"{s['w']}x{s['h']}", "secondes": round(time.time() - t0), "ok": ok}
        if ok:
            export_to_video(list(frames), f"{OUT}/{s['id']}.mp4", fps=FPS, quality=9)
        log(s["id"], res[s["id"]])
        json.dump(res, open(f"{OUT}/rapport.json", "w"), indent=2, ensure_ascii=False)
    del pipe, experts
    gc.collect()
    torch.cuda.empty_cache()


def upscale(res):
    """Real-ESRGAN x4plus image par image, puis réduit à 2× (sortie ≈ 960×1664)."""
    import imageio
    import torch
    from diffusers.utils import export_to_video
    from spandrel import ModelLoader

    w = "/tmp/RealESRGAN_x4plus.pth"
    urllib.request.urlretrieve(ESRGAN, w)
    model = ModelLoader().load_from_file(w).model.eval().half().to("cuda:0")
    for s in SHOTS:
        src = f"{OUT}/{s['id']}.mp4"
        if not os.path.exists(src):
            continue
        t0 = time.time()
        out = []
        for fr in imageio.get_reader(src, "ffmpeg"):
            x = torch.from_numpy(fr).permute(2, 0, 1)[None].half().div(255).to("cuda:0")
            with torch.no_grad():
                y = model(x)
                y = torch.nn.functional.interpolate(y, scale_factor=0.5, mode="area")
            out.append(y[0].clamp(0, 1).permute(1, 2, 0).float().cpu().numpy())
        export_to_video(out, f"{OUT}/{s['id']}_hd.mp4", fps=FPS, quality=9)
        res[s["id"]]["hd_secondes"] = round(time.time() - t0)
        log("agrandi", s["id"], res[s["id"]]["hd_secondes"], "s")


def main():
    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    found = sorted(glob.glob("/kaggle/input/**/casque.jpg", recursive=True))
    if not found:
        raise SystemExit("photos introuvables dans /kaggle/input")
    job_dir = os.path.dirname(found[0])
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *PKGS], check=True)
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao"], check=False)
    import torch

    log("carte", torch.cuda.get_device_name(0), "x", torch.cuda.device_count())
    res = {}
    try:
        generate(job_dir, res)
    except BaseException as e:  # noqa: BLE001
        res["_erreur"] = f"{type(e).__name__}: {re.sub(r'\s+', ' ', str(e))[:800]}"
        log("ERREUR", res["_erreur"])
    try:
        upscale(res)
    except Exception as e:  # noqa: BLE001
        res["_erreur_hd"] = f"{type(e).__name__}: {str(e)[:400]}"
        log("ERREUR HD", res["_erreur_hd"])
    res["_duree_totale_s"] = round(time.time() - t_start)
    json.dump(res, open(f"{OUT}/rapport.json", "w"), indent=2, ensure_ascii=False)
    log("terminé", json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
