"""Sahte paket üretir: sample_package/ (images + annotations.json).

Kullanım:  python make_sample_data.py
Gerçek paket gelene kadar arayüzü bununla geliştir.
"""
import json, os, random
from PIL import Image, ImageDraw

random.seed(7)
OUT = "sample_package"
os.makedirs(os.path.join(OUT, "images"), exist_ok=True)

CATEGORIES = ["cardboard box", "plastic tote", "mattress", "tool chest",
              "luggage", "cabinet", "clothing textile", "unknown"]
cats = [{"id": i + 1, "name": n} for i, n in enumerate(CATEGORIES)]
COLORS = [(200, 160, 110), (90, 140, 210), (220, 220, 200), (180, 60, 60),
          (120, 100, 160), (150, 110, 70), (90, 160, 110), (140, 140, 140)]

W, H = 800, 600
images, anns, cands = [], [], []
ann_id, cand_id = 1, 1000


def blob(cx, cy, rx, ry, n=8):
    """Kabaca dikdörtgensi/oval bir çokgen (düz liste: x1,y1,x2,y2,...)."""
    import math
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = random.uniform(0.85, 1.05)
        pts += [round(cx + rx * r * math.cos(a), 1), round(cy + ry * r * math.sin(a), 1)]
    return pts


def bbox(poly):
    xs, ys = poly[0::2], poly[1::2]
    return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]


def area(poly):
    xs, ys = poly[0::2], poly[1::2]
    s = 0
    for i in range(len(xs)):
        j = (i + 1) % len(xs)
        s += xs[i] * ys[j] - xs[j] * ys[i]
    return round(abs(s) / 2, 1)


for img_id in range(1, 4):
    fn = f"img_{img_id:03d}.jpg"
    im = Image.new("RGB", (W, H), (235, 235, 230))
    d = ImageDraw.Draw(im)
    for _ in range(5):                        # hat nesneleri
        cid = random.randint(1, len(CATEGORIES) - 1)
        cx, cy = random.randint(120, 680), random.randint(120, 480)
        poly = blob(cx, cy, random.randint(50, 110), random.randint(40, 90))
        d.polygon(poly, fill=COLORS[cid - 1])
        # bazılarının sınıfını kasten yanlış ver, skoru düşük olsun
        wrong = random.random() < 0.4
        shown = random.randint(1, len(CATEGORIES)) if wrong else cid
        anns.append({"id": ann_id, "image_id": img_id, "category_id": shown,
                     "bbox": bbox(poly), "segmentation": [poly],
                     "score": round(random.uniform(0.15, 0.45) if wrong
                                    else random.uniform(0.6, 0.95), 2),
                     "source": "pipeline"})
        ann_id += 1
    for _ in range(3):                        # hattın seçmediği aday parçalar
        cx, cy = random.randint(80, 720), random.randint(80, 520)
        poly = blob(cx, cy, random.randint(30, 60), random.randint(25, 50))
        d.polygon(poly, fill=(random.randint(80, 200),) * 3)
        cands.append({"id": cand_id, "image_id": img_id,
                      "segmentation": [poly], "area": area(poly)})
        cand_id += 1
    im.save(os.path.join(OUT, "images", fn), quality=90)
    images.append({"id": img_id, "file_name": fn, "width": W, "height": H})

pkg = {"info": {"version": 1, "note": "sahte örnek paket"},
       "categories": cats, "images": images,
       "annotations": anns, "candidates": cands}
with open(os.path.join(OUT, "annotations.json"), "w", encoding="utf-8") as f:
    json.dump(pkg, f, ensure_ascii=False, indent=1)
print("hazır:", OUT, len(images), "resim,", len(anns), "nesne,", len(cands), "aday")
