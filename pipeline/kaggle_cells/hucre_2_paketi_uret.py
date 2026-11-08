# ---------------- Ayarlar ----------------
IMAGE_DIR = "/kaggle/input/datasets/glgemhendis/sample"
MAX_IMAGES = None          # None: hepsi. Bir sayı: yalnızca ilk o kadar fotoğraf (deneme için)
BOX_THRESHOLD = 0.35    # Grounding DINO kutu eşiği
MIN_BOX_FRAC = 0.005    # resmin %0,5'inden küçük kutular atılır (kırıntı). Daha çok maske için küçült
MAX_BOX_FRAC = 0.90     # resmin %90'ından büyük kutular atılır
MAX_PER_CLASS = 10      # bir sınıftan bir fotoğrafta en fazla bu kadar kutu (en yüksek skorlular). Daha çok maske için büyüt
TEXT_THRESHOLD = 0.25
NMS_IOU = 0.8           # aynı nesneye iki sınıf: kutular bu kadar örtüşürse yüksek skor kalır
OBJECT_IOU = 0.7        # maskeleri bu kadar örtüşen iki nesne aynı nesnedir: yüksek skor kalır
MAX_CANDIDATES = 40     # fotoğraf başına en fazla bu kadar aday (en büyükler önce)
CAND_MIN_FRAC = 0.002   # resmin %0,2'sinden küçük adaylar atılır
CAND_MAX_FRAC = 0.45    # resmin %45'inden büyük adaylar atılır (duvar, zemin)
MULTIMASK = True        # True: SAM her kutu için 3 maske dener, en iyisini seçer. False: eski davranış
POINTS_PER_SIDE = 32    # aday maskeler için SAM ızgarası. 48 ya da 64: daha ince adaylar, daha yavaş
PRED_IOU_THRESH = 0.8   # adaylar için kalite eşikleri. 0,86 ve 0,95: daha temiz ama daha az aday
STABILITY_THRESH = 0.92
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
generator = SAM2AutomaticMaskGenerator(sam2_model, points_per_side=POINTS_PER_SIDE,
                                       pred_iou_thresh=PRED_IOU_THRESH, stability_score_thresh=STABILITY_THRESH)

paths = mp.find_images(IMAGE_DIR)
if MAX_IMAGES:
    paths = paths[:MAX_IMAGES]
assert paths, f"{IMAGE_DIR} içinde fotoğraf bulunamadı"
print(f"{len(paths)} fotoğraf işlenecek\n")

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
        raw = len(boxes)
        pre = mp.filter_boxes(boxes, scores, names, h * w, MIN_BOX_FRAC, MAX_BOX_FRAC, MAX_PER_CLASS)
        boxes, scores, names = [boxes[i] for i in pre], [scores[i] for i in pre], [names[i] for i in pre]
        keep = mp.nms(boxes, scores, NMS_IOU)
        print(f"  DINO ham kutu: {raw}, filtreden sonra: {len(boxes)}, NMS sonrası: {len(keep)}")

        object_masks, found = [], set()
        if keep:
            predictor.set_image(rgb)
            masks, sam_scores, _ = predictor.predict(box=np.array([boxes[i] for i in keep]),
                                                     multimask_output=MULTIMASK)
            if MULTIMASK:  # SAM 3 maske tahmin eder, kendi puanı en yüksek olanı al
                masks = mp.pick_best_masks(masks, sam_scores)
            else:
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
    for m, area in mp.filter_candidates([a["segmentation"] for a in auto], object_masks, h * w,
                                        min_area_frac=CAND_MIN_FRAC, max_area_frac=CAND_MAX_FRAC,
                                        max_count=MAX_CANDIDATES):
        n_cand += builder.add_candidate(image_id, mp.mask_to_polygons(m), area) is not None

    print(f"[{n}/{len(paths)}] {path.name}  {w}x{h}  nesne: {len(object_masks)}  aday: {n_cand}"
          f"  ({time.time() - t0:.0f} sn)  {', '.join(sorted(found))}")

zip_path = builder.write(settings={
    "box_threshold": BOX_THRESHOLD, "text_threshold": TEXT_THRESHOLD, "nms_iou": NMS_IOU,
    "box_area_frac": [MIN_BOX_FRAC, MAX_BOX_FRAC], "max_per_class": MAX_PER_CLASS,
    "object_mask_iou": OBJECT_IOU,
    "candidates": f"min {CAND_MIN_FRAC:.1%} / max {CAND_MAX_FRAC:.0%} of image, near copies dropped, max {MAX_CANDIDATES}",
    "sam2": SAM2_CHECKPOINT, "grounding_dino": GDINO_CHECKPOINT, "gdino_device": gdino_device,
    "prompting": "one class per query", "sam_multimask": MULTIMASK,
    "sam_auto": [POINTS_PER_SIDE, PRED_IOU_THRESH, STABILITY_THRESH],
})
print(f"\nPaket hazır: {zip_path}  ({len(builder.images)} resim, {len(builder.annotations)} nesne, "
      f"{len(builder.candidates)} aday)")
