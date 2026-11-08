"""Turns Grounding DINO + SAM 2 results into a label review tool package.

Everything here is plain numpy / OpenCV / Pillow, so it runs and is tested off Kaggle:
    .venv\\Scripts\\python pipeline\\test_make_package.py
The Kaggle notebook copies this file in and only adds the model calls (see build_notebook.py).

Output (README section 5.1):
    <out>/images/<file>      upright copies of the photos (EXIF rotation applied)
    <out>/annotations.json   categories, images, annotations (pipeline objects), candidates
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

# BidVision taxonomy (decided 2026-11-08): the pilot notebook's 17 classes + "tv"
# (named in the project documents, "most specific level": tv rather than electronics)
# + the catch-all below = "18 classes + misc_item".
# Order = YOLO class index. Never reorder or insert in the middle once labelling has
# started: every exported label file would point at the wrong class. Append only.
CLASSES = [
    "cardboard box", "plastic tote", "bagged contents", "luggage",
    "large appliance", "small appliance", "electronics", "sofa",
    "chair", "table", "cabinet", "mattress", "tool chest",
    "bicycle", "fitness equipment", "clothing textile", "wall art",
    "tv",
]
# Catch-all class for the reviewer ("nothing more specific fits"). Not sent to the
# detector as a prompt: "misc item" is not something a model can look for.
CATCH_ALL = "misc_item"

IMAGE_TYPES = {".jpg", ".jpeg", ".png"}


def categories():
    return [{"id": i + 1, "name": name} for i, name in enumerate(CLASSES + [CATCH_ALL])]


# ---------- images ----------

def load_upright(path):
    """RGB uint8 array of the photo as people see it.

    Phones store portrait photos sideways plus an EXIF "rotate" note. Browsers apply
    the note, Grounding DINO's own loader does not, so masks would land on the wrong
    spot in the tool. Both the models and the package get this upright version.
    """
    with Image.open(path) as im:
        return np.asarray(ImageOps.exif_transpose(im).convert("RGB"))


def find_images(folder):
    return sorted(p for p in Path(folder).rglob("*") if p.suffix.lower() in IMAGE_TYPES)


# ---------- geometry ----------

def mask_to_polygons(mask, min_part_area=100.0, tolerance=0.002):
    """Binary mask -> list of flat pixel polygons [x1, y1, x2, y2, ...], biggest first.

    tolerance: allowed edge deviation as a fraction of the part's outline length.
    SAM masks have thousands of edge pixels; a few dozen points keep the tool fast
    and lose almost nothing (tested: area changes well under 1 %).
    Parts smaller than min_part_area pixels (specks) are dropped.
    """
    m = np.ascontiguousarray(mask.astype(np.uint8))
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    parts = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_part_area:
            continue
        approx = cv2.approxPolyDP(c, tolerance * cv2.arcLength(c, True), True).reshape(-1, 2)
        if len(approx) < 3:
            continue
        parts.append((area, [round(float(v), 1) for v in approx.flatten()]))
    parts.sort(key=lambda p: -p[0])
    return [poly for _, poly in parts]


def polygon_area(flat):
    xs, ys = np.asarray(flat[0::2]), np.asarray(flat[1::2])
    return float(abs(np.dot(xs, np.roll(ys, -1)) - np.dot(ys, np.roll(xs, -1))) / 2)


def bbox_of(polygons):
    xs = [v for p in polygons for v in p[0::2]]
    ys = [v for p in polygons for v in p[1::2]]
    return [min(xs), min(ys), round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)]


def box_iou(a, b):
    """IoU of two xyxy boxes."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def nms(boxes, scores, iou_threshold=0.8):
    """Indexes to keep. Class-agnostic: each class is asked separately, so the same
    object can come back as both "chair" and "sofa"; the higher score wins.
    The threshold is high on purpose so neighbouring real objects are kept."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    keep = []
    for i in order:
        if all(box_iou(boxes[i], boxes[k]) <= iou_threshold for k in keep):
            keep.append(i)
    return sorted(keep)


def polygons_to_mask(polygons, width, height):
    """Flat pixel polygons -> boolean mask (for comparing shapes already in a package)."""
    m = np.zeros((height, width), np.uint8)
    for p in polygons:
        cv2.fillPoly(m, [np.round(np.asarray(p, np.float32).reshape(-1, 2)).astype(np.int32)], 1)
    return m.astype(bool)


def mask_iou(a, b):
    inter = np.logical_and(a, b).sum()
    return float(inter / np.logical_or(a, b).sum()) if inter else 0.0


def dedupe_objects(masks, scores, iou_threshold=0.7):
    """Indexes to keep. When two objects' masks cover nearly the same pixels, it is one
    object found twice (same or different class): the higher score stays.
    Objects lying inside others with low overlap (clothes on a sofa) are kept: they can
    be real, separate objects, and the reviewer decides.
    Pilot data: true duplicates had mask IoU 0.75-0.95, nested objects 0.11-0.56."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    keep = []
    for i in order:
        if all(mask_iou(masks[i], masks[k]) <= iou_threshold for k in keep):
            keep.append(i)
    return sorted(keep)


def candidate_indexes(candidate_masks, object_masks, image_area, max_overlap=0.5,
                      min_area_frac=0.005, max_area_frac=0.3, iou_threshold=0.7, max_count=20):
    """Positions (in candidate_masks) of the SAM 2 automatic masks worth offering as
    candidates, biggest first. Dropped: covered by a detected object, specks (< 0.5 % of
    the image), wall/floor-sized pieces (> 30 %), near copies of a bigger candidate;
    at most max_count. Pilot data: 40 candidates per photo, half specks, several in pairs."""
    covered = None
    for m in object_masks:
        covered = m.astype(bool) if covered is None else covered | m.astype(bool)
    masks = [m.astype(bool) for m in candidate_masks]
    sized = []
    for i, m in enumerate(masks):
        area = int(m.sum())
        if area < min_area_frac * image_area or area > max_area_frac * image_area:
            continue
        if covered is not None and (m & covered).sum() / area > max_overlap:
            continue
        sized.append((i, area))
    sized.sort(key=lambda c: -c[1])
    kept = []
    for i, _ in sized:
        if len(kept) == max_count:
            break
        if all(mask_iou(masks[i], masks[k]) <= iou_threshold for k in kept):
            kept.append(i)
    return kept


def filter_candidates(candidate_masks, object_masks, image_area, **rules):
    """Same as candidate_indexes, returning [(mask, area)] biggest first."""
    return [(candidate_masks[i].astype(bool), int(candidate_masks[i].astype(bool).sum()))
            for i in candidate_indexes(candidate_masks, object_masks, image_area, **rules)]


# ---------- package ----------

class PackageBuilder:
    def __init__(self, out_dir):
        self.out = Path(out_dir)
        if self.out.exists():
            shutil.rmtree(self.out)
        (self.out / "images").mkdir(parents=True)
        self.images, self.annotations, self.candidates = [], [], []
        self.class_id = {c["name"]: c["id"] for c in categories()}
        self._stems = set()
        self._next_ann, self._next_cand = 1, 100001  # candidate ids never collide with object ids

    def add_image(self, src_path):
        """Copies the photo upright into the package. Returns (image_id, rgb array)."""
        src = Path(src_path)
        rgb = load_upright(src)
        stem = src.stem.replace(" ", "_")
        base, n = stem, 2
        while stem.lower() in self._stems:  # the tool needs unique stems
            stem, n = f"{base}_{n}", n + 1
        self._stems.add(stem.lower())
        name = stem + ".jpg"
        Image.fromarray(rgb).save(self.out / "images" / name, quality=95)
        h, w = rgb.shape[:2]
        image_id = len(self.images) + 1
        self.images.append({"id": image_id, "file_name": name, "width": int(w), "height": int(h),
                            "source": str(src)})
        return image_id, rgb

    def add_annotation(self, image_id, class_name, polygons, score):
        if not polygons:
            return None
        ann = {"id": self._next_ann, "image_id": image_id, "category_id": self.class_id[class_name],
               "bbox": bbox_of(polygons), "segmentation": polygons,
               "score": round(float(score), 3), "source": "pipeline"}
        self.annotations.append(ann)
        self._next_ann += 1
        return ann

    def add_candidate(self, image_id, polygons, area):
        if not polygons:
            return None
        cand = {"id": self._next_cand, "image_id": image_id, "segmentation": polygons,
                "area": float(area)}
        self.candidates.append(cand)
        self._next_cand += 1
        return cand

    def write(self, settings=None, zip_it=True):
        pkg = {"info": {"version": 1, "source": "RAM++/Grounding DINO/SAM 2 pilot",
                        "created": datetime.now().isoformat(timespec="seconds"),
                        "settings": settings or {}},
               "categories": categories(), "images": self.images,
               "annotations": self.annotations, "candidates": self.candidates}
        with open(self.out / "annotations.json", "w", encoding="utf-8") as f:
            json.dump(pkg, f, ensure_ascii=False)
        if zip_it:
            return Path(shutil.make_archive(str(self.out), "zip", self.out))
        return self.out / "annotations.json"
