"""Adds our package step to the teammate's Kaggle notebook, without changing their cells.

    .venv\\Scripts\\python pipeline\\build_notebook.py <teammate>.ipynb
        [--image-dir /kaggle/input/datasets/<user>/<dataset>] [--max-images 5] [--out name.ipynb]

The image dir is the dataset path Kaggle shows under Input (copy it from there).
Without --max-images every photo is processed.

Writes pipeline/bidvision_pilot.ipynb (or --out): every teammate cell, unchanged and in order, plus
"Part 3" inserted right after their setup (after the last pip install cell). It has to sit
before their one-image test cells: those use a placeholder path, the last ones raise an
error, and "Run All" stops at the first error.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
DEFAULT_IMAGE_DIR = "/kaggle/input/datasets/tunahancoban55/bidvision-pilot"

# Part 3 goes right after this teammate cell (the last setup step).
INSERT_AFTER = "!pip install supervision addict yapf -q"

PART3_MD = """## Bölüm 3: Paket üret (etiket inceleme aracı için)

- **Her sınıf ayrı sorulur.** Bütün sınıfları tek metinde vermek etiketleri karıştırıyor
  ("large appliance small appliance"). `predict_with_classes()` bunu çözmüyor, çünkü o da tek metin kullanıyor.
- Aynı nesne iki kez bulunursa (kutular ya da maskeler neredeyse aynıysa) yüksek skorlu olan kalır.
- Adaylardan kırıntılar (resmin %0,5'inden küçük), duvar büyüklüğündekiler (%30'dan büyük) ve birbirinin kopyaları atılır. Fotoğraf başına en fazla 20 aday kalır.
- Maskeler sadeleştirilmiş çokgenlere çevrilir.
- SAM 2'nin otomatik maskelerinden, bulunan nesnelerle çakışmayanlar **aday** olur.
- Fotoğraflar telefonun döndürme notuna (EXIF) göre düzeltilir. Modeller ve araç aynı resmi görür.
- Hesaplar `float32` ile yapılır. `bfloat16`'yı T4 ve P100 ekran kartları tam desteklemiyor.

Ayarlar bir sonraki hücrenin başında (dataset yolu, fotoğraf sayısı, eşikler).
"""

RUN = f'''# ---------------- Ayarlar ----------------
IMAGE_DIR = "@@IMAGE_DIR@@"
MAX_IMAGES = @@MAX_IMAGES@@          # None: hepsi. Bir sayı: yalnızca ilk o kadar fotoğraf (deneme için)
BOX_THRESHOLD = 0.35    # Grounding DINO kutu eşiği
TEXT_THRESHOLD = 0.25
NMS_IOU = 0.8           # aynı nesneye iki sınıf: kutular bu kadar örtüşürse yüksek skor kalır
OBJECT_IOU = 0.7        # maskeleri bu kadar örtüşen iki nesne aynı nesnedir: yüksek skor kalır
OUT_DIR = "/kaggle/working/bidvision_package"
SAM2_CONFIG = "configs/sam2.1/sam2.1_hiera_l.yaml"
SAM2_CHECKPOINT = "./checkpoints/sam2.1_hiera_large.pt"
GDINO_CONFIG = "grounding_dino/groundingdino/config/GroundingDINO_SwinT_OGC.py"
GDINO_CHECKPOINT = "gdino_checkpoints/groundingdino_swint_ogc.pth"
# ------------------------------------------

import os, sys, time
os.chdir("/kaggle/working/Grounded-SAM-2")
for p in ("/kaggle/working", "/kaggle/working/Grounded-SAM-2", "/kaggle/working/Grounded-SAM-2/grounding_dino"):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import torch
from PIL import Image
from torchvision.ops import box_convert
import groundingdino.datasets.transforms as T
from groundingdino.util.inference import load_model, predict
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
import make_package as mp

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("Ekran kartı:", torch.cuda.get_device_name(0) if DEVICE == "cuda" else "YOK, sağ panelden GPU seç!")

transform = T.Compose([
    T.RandomResize([800], max_size=1333),
    T.ToTensor(),
    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# Grounding DINO: önce ekran kartında küçük bir deneme. Eklenti GPU desteksiz derlendiyse
# (CUDA_HOME="") hata verir; o zaman işlemcide çalıştırırız (yavaş ama doğru).
gdino_device = DEVICE
gdino = load_model(GDINO_CONFIG, GDINO_CHECKPOINT, device=gdino_device)
try:
    with torch.inference_mode():
        probe, _ = transform(Image.new("RGB", (64, 64)), None)
        predict(model=gdino, image=probe, caption="chair", box_threshold=0.9,
                text_threshold=0.9, device=gdino_device)
    print("Grounding DINO:", gdino_device)
except Exception as e:
    print("UYARI: Grounding DINO ekran kartında çalışmadı:", repr(e)[:200])
    print("       İşlemcide devam ediliyor (yavaş). Kalıcı çözüm: Bölüm 2'de CUDA_HOME ayarı.")
    gdino_device = "cpu"
    gdino = load_model(GDINO_CONFIG, GDINO_CHECKPOINT, device=gdino_device)

sam2_model = build_sam2(SAM2_CONFIG, SAM2_CHECKPOINT, device=DEVICE)
predictor = SAM2ImagePredictor(sam2_model)
generator = SAM2AutomaticMaskGenerator(sam2_model, points_per_side=32,
                                       pred_iou_thresh=0.8, stability_score_thresh=0.92)

paths = mp.find_images(IMAGE_DIR)
if MAX_IMAGES:
    paths = paths[:MAX_IMAGES]
assert paths, f"{{IMAGE_DIR}} içinde fotoğraf bulunamadı"
print(f"{{len(paths)}} fotoğraf işlenecek\\n")

builder = mp.PackageBuilder(OUT_DIR)
for n, path in enumerate(paths, 1):
    t0 = time.time()
    image_id, rgb = builder.add_image(path)
    h, w = rgb.shape[:2]
    image_t, _ = transform(Image.fromarray(rgb), None)

    boxes, scores, names = [], [], []
    with torch.inference_mode():
        for cls in mp.CLASSES:  # her sınıf ayrı: etiketler karışmaz
            b, logits, _ = predict(model=gdino, image=image_t, caption=cls, box_threshold=BOX_THRESHOLD,
                                   text_threshold=TEXT_THRESHOLD, device=gdino_device)
            if len(b) == 0:
                continue
            xyxy = box_convert(b * torch.tensor([w, h, w, h]), in_fmt="cxcywh", out_fmt="xyxy").numpy()
            boxes += xyxy.tolist()
            scores += logits.tolist()
            names += [cls] * len(xyxy)
        keep = mp.nms(boxes, scores, NMS_IOU)

        object_masks, found = [], set()
        if keep:
            predictor.set_image(rgb)
            masks, _, _ = predictor.predict(box=np.array([boxes[i] for i in keep]), multimask_output=False)
            masks = np.asarray(masks)
            if masks.ndim == 4:
                masks = masks[:, 0]
            elif masks.ndim == 2:
                masks = masks[None]
            masks = [m > 0.5 for m in masks]
            # aynı nesne iki kez bulunduysa (maskeler neredeyse aynı) yüksek skorlu kalır
            for j in mp.dedupe_objects(masks, [scores[i] for i in keep], OBJECT_IOU):
                i = keep[j]
                if builder.add_annotation(image_id, names[i], mp.mask_to_polygons(masks[j]), scores[i]):
                    object_masks.append(masks[j])
                    found.add(names[i])

        auto = generator.generate(rgb)
    n_cand = 0
    for m, area in mp.filter_candidates([a["segmentation"] for a in auto], object_masks, h * w):
        n_cand += builder.add_candidate(image_id, mp.mask_to_polygons(m), area) is not None

    print(f"[{{n}}/{{len(paths)}}] {{path.name}}  {{w}}x{{h}}  nesne: {{len(object_masks)}}  aday: {{n_cand}}"
          f"  ({{time.time() - t0:.0f}} sn)  {{', '.join(sorted(found))}}")

zip_path = builder.write(settings={{
    "box_threshold": BOX_THRESHOLD, "text_threshold": TEXT_THRESHOLD, "nms_iou": NMS_IOU,
    "object_mask_iou": OBJECT_IOU, "candidates": "min 0.5 % / max 30 % of image, near copies dropped, max 20",
    "sam2": SAM2_CHECKPOINT, "grounding_dino": GDINO_CHECKPOINT, "gdino_device": gdino_device,
    "prompting": "one class per query",
}})
print(f"\\nPaket hazır: {{zip_path}}  ({{len(builder.images)}} resim, {{len(builder.annotations)}} nesne, "
      f"{{len(builder.candidates)}} aday)")
'''

SHOW = '''# Kontrol: ilk fotoğraf, paketteki çokgenlerle (yeşil: nesne, sarı kesik: aday)
import json, cv2
from IPython.display import Image as IPImage, FileLink, display

pkg = json.load(open(f"{OUT_DIR}/annotations.json", encoding="utf-8"))
first = pkg["images"][0]
img = cv2.imread(f"{OUT_DIR}/images/{first['file_name']}")
names = {c["id"]: c["name"] for c in pkg["categories"]}
for a in [a for a in pkg["annotations"] if a["image_id"] == first["id"]]:
    for poly in a["segmentation"]:
        pts = np.array(poly, np.int32).reshape(-1, 2)
        cv2.polylines(img, [pts], True, (0, 200, 0), 3)
        cv2.putText(img, f"{names[a['category_id']]} {a['score']:.2f}", tuple(pts.min(0)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 0), 2)
for c in [c for c in pkg["candidates"] if c["image_id"] == first["id"]]:
    for poly in c["segmentation"]:
        cv2.polylines(img, [np.array(poly, np.int32).reshape(-1, 2)], True, (0, 220, 255), 2)
cv2.imwrite("/kaggle/working/check_first_image.jpg", img)
display(IPImage("/kaggle/working/check_first_image.jpg", width=900))

# İndir: aşağıdaki bağlantıya tıkla (ya da sağ panel → Output → bidvision_package.zip → indir)
display(FileLink("bidvision_package.zip"))
'''


def cell(kind, text):
    c = {"cell_type": kind, "metadata": {}, "source": text.splitlines(keepends=True)}
    if kind == "code":
        c.update(outputs=[], execution_count=None)
    return c


def main():
    parser = argparse.ArgumentParser(description="Build the Kaggle notebook with the package step")
    parser.add_argument("teammate_notebook")
    parser.add_argument("--image-dir", default=DEFAULT_IMAGE_DIR, help="Kaggle dataset path (from the Input panel)")
    parser.add_argument("--max-images", type=int, default=None, help="only the first N photos (default: all)")
    parser.add_argument("--out", default="bidvision_pilot.ipynb", help="file name, written into pipeline/")
    args = parser.parse_args()
    if not args.image_dir.startswith("/kaggle/input/") or '"' in args.image_dir:
        sys.exit(f"--image-dir should be a Kaggle input path like /kaggle/input/datasets/<user>/<dataset>, "
                 f"got {args.image_dir!r}")
    run_cell = RUN.replace("@@IMAGE_DIR@@", args.image_dir).replace("@@MAX_IMAGES@@", str(args.max_images))

    src = Path(args.teammate_notebook)
    nb = json.loads(src.read_text(encoding="utf-8"))
    originals = nb["cells"]
    texts = ["".join(c["source"]) for c in originals]
    at = [i for i, t in enumerate(texts) if t.lstrip().startswith(INSERT_AFTER)]
    if len(at) != 1:
        sys.exit(f"setup cell starting with {INSERT_AFTER!r} not found exactly once; update INSERT_AFTER")

    package_code = (HERE / "make_package.py").read_text(encoding="utf-8")
    ours = [cell("markdown", PART3_MD),
            cell("code", "%%writefile /kaggle/working/make_package.py\n" + package_code),
            cell("code", run_cell),
            cell("code", SHOW)]
    for c in ours:
        c["metadata"]["label_review_tool"] = True  # marks the cells we added
    cells = originals[:at[0] + 1] + ours + originals[at[0] + 1:]

    # the teammate's cells must come out exactly as they went in
    kept = [c for c in cells if not c["metadata"].get("label_review_tool")]
    assert ["".join(c["source"]) for c in kept] == texts, "a teammate cell changed"

    out = dict(nb, cells=cells)
    dest = HERE / Path(args.out).name
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"written: {dest}: {len(originals)} teammate cells unchanged + {len(ours)} added after cell [{at[0]}]")
    print(f"  photos from {args.image_dir}, {'all' if args.max_images is None else f'first {args.max_images}'}")


if __name__ == "__main__":
    main()
