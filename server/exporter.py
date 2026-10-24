"""Writes reviewed images as a YOLO segmentation dataset.

export/
  images/<file>            copied images
  labels/<stem>.txt        one line per object: <class_index> x1 y1 x2 y2 ... (0-1)
  data.yaml                class names, same order as package categories
"""
import json
import shutil
from pathlib import Path

from PIL import Image

from package import merge_objects

MARKER = ".label-review-export"  # only folders carrying this file are ever replaced


class ExportError(Exception):
    pass


def normalize(poly, width, height):
    """Pixel polygon -> 'x1 y1 x2 y2 ...' in 0-1, clamped to the image."""
    out = []
    for i in range(0, len(poly), 2):
        x = min(max(poly[i] / width, 0.0), 1.0)
        y = min(max(poly[i + 1] / height, 0.0), 1.0)
        out.append(f"{x:.6f} {y:.6f}")
    return " ".join(out)


def data_yaml(categories):
    # names are quoted (JSON strings are valid YAML) so ":" "#" "yes" etc. stay plain text
    lines = ["# Written by the label review tool. Class index = position in this list.",
             "train: images",
             "val: images",
             f"nc: {len(categories)}",
             "names:"]
    lines += [f"  - {json.dumps(c['name'], ensure_ascii=False)}" for c in categories]
    return "\n".join(lines) + "\n"


def export_objects(pkg, store, image_id):
    """Objects that go into the label file: everything except deleted ones."""
    objects = merge_objects(pkg.annotations.get(image_id, []), store.load(image_id))
    return [o for o in objects if o["state"] != "deleted"]


def build(pkg, store, out_dir):
    """Write the dataset into out_dir (must not exist). Returns a summary."""
    class_index = {c["id"]: i for i, c in enumerate(pkg.categories)}
    (out_dir / "images").mkdir(parents=True)
    (out_dir / "labels").mkdir()
    (out_dir / MARKER).write_text("created by the label review tool\n", encoding="utf-8")
    (out_dir / "data.yaml").write_text(data_yaml(pkg.categories), encoding="utf-8")

    # counted by class index, not name: two categories could share a name
    per_class = [0] * len(pkg.categories)
    summary = {"images": 0, "objects": 0, "empty_images": 0, "warnings": []}
    warn = summary["warnings"].append

    for image_id, img in pkg.images.items():
        if store.status(image_id) != "reviewed":
            continue
        name, width, height = img["file_name"], img["width"], img["height"]
        stem = Path(name).stem  # unique, checked when the package is loaded
        src = pkg.image_path(image_id)
        if not src.exists():
            warn(f"{name}: resim dosyası yok, atlandı")
            continue
        try:
            with Image.open(src) as im:
                size = im.size
        except Exception as e:
            warn(f"{name}: resim açılamadı ({e}), atlandı")
            continue
        if size != (width, height):
            warn(f"{name}: annotations.json boyutu {width}x{height}, dosya {size[0]}x{size[1]}")

        lines = []
        for obj in export_objects(pkg, store, image_id):
            cls = class_index.get(obj["category_id"])
            if cls is None:
                warn(f"{name}: nesne {obj['id']} bilinmeyen sınıf {obj['category_id']}, atlandı")
                continue
            parts = obj["segmentation"]
            if len(parts) > 1:
                warn(f"{name}: nesne {obj['id']} {len(parts)} parçalı, her parça ayrı satır yazıldı")
            written = 0
            for poly in parts:
                if len(poly) < 6 or len(poly) % 2:
                    warn(f"{name}: nesne {obj['id']} geçersiz çokgen ({len(poly)} değer), atlandı")
                    continue
                lines.append(f"{cls} {normalize(poly, width, height)}")
                written += 1
            if written:
                summary["objects"] += 1
                per_class[cls] += 1

        # an empty file is written on purpose: a reviewed image with no objects is a background example
        (out_dir / "labels" / f"{stem}.txt").write_text(
            "".join(line + "\n" for line in lines), encoding="utf-8")
        shutil.copy2(src, out_dir / "images" / name)
        summary["images"] += 1
        summary["empty_images"] += not lines

    summary["per_class"] = [{"index": i, "name": c["name"], "count": per_class[i]}
                            for i, c in enumerate(pkg.categories)]
    return summary


def export(pkg, store, target):
    """Build into a temp folder, then swap it in, so a failed export never
    leaves a half-written dataset and old files never linger."""
    target = Path(target).resolve()
    if target.exists() and any(target.iterdir()) and not (target / MARKER).exists():
        raise ExportError(f"{target} bu aracın oluşturduğu bir klasör değil, üzerine yazılmadı")

    tmp = target.with_name(target.name + ".tmp")
    old = target.with_name(target.name + ".old")
    for leftover in (tmp, old):
        if leftover.exists():
            shutil.rmtree(leftover)

    try:
        summary = build(pkg, store, tmp)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    try:
        if target.exists():
            target.rename(old)
        tmp.rename(target)
    except OSError as e:
        if old.exists() and not target.exists():
            old.rename(target)  # put the previous export back
        shutil.rmtree(tmp, ignore_errors=True)
        raise ExportError(f"export klasörü değiştirilemedi (bir dosyası açık olabilir): {e}")
    shutil.rmtree(old, ignore_errors=True)

    summary["path"] = str(target)
    return summary
