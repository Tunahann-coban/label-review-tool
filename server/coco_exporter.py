"""Writes reviewed images as a COCO JSON dataset.

export/
  instances_reviewed.json   standard COCO instance segmentation format
"""
import json
import os
from datetime import datetime
from pathlib import Path

from package import bbox_of, merge_objects


def area_of(segmentation):
    """Sum of polygon areas (shoelace), one value per flat [x,y,...] poly."""
    total = 0.0
    for poly in segmentation:
        n = len(poly) // 2
        xs = poly[0::2]
        ys = poly[1::2]
        total += abs(sum(xs[i] * ys[(i + 1) % n] - xs[(i + 1) % n] * ys[i] for i in range(n))) / 2
    return round(total, 1)


def build_coco(pkg, store):
    ann_id = 1
    images_out = []
    annotations_out = []
    pending = 0
    warnings = []

    for img in pkg.images.values():
        image_id = img["id"]
        if store.status(image_id) != "reviewed":
            pending += 1
            continue

        review = store.load(image_id)
        objects = merge_objects(pkg.annotations.get(image_id, []), review)
        exportable = [o for o in objects if o["state"] != "deleted"]

        images_out.append({
            "id": img["id"],
            "file_name": img["file_name"],
            "width": img["width"],
            "height": img["height"],
        })

        for obj in exportable:
            seg = obj["segmentation"]
            cls = obj["category_id"]
            if cls not in pkg.category_ids:
                warnings.append(f"{img['file_name']}: nesne {obj['id']} bilinmeyen sınıf {cls}, atlandı")
                continue
            if len(seg) > 1:
                warnings.append(f"{img['file_name']}: nesne {obj['id']} {len(seg)} parçalı, alan tahmini yaklaşık")
            annotations_out.append({
                "id": ann_id,
                "image_id": image_id,
                "category_id": cls,
                "segmentation": seg,
                "bbox": bbox_of(seg),
                "area": area_of(seg),
                "iscrowd": 0,
            })
            ann_id += 1

    coco = {
        "info": {
            "description": "Reviewed by label-review-tool",
            "version": "1.0",
            "date_created": datetime.now().isoformat(timespec="seconds"),
        },
        "categories": [
            {"id": c["id"], "name": c["name"], "supercategory": c.get("supercategory", "")}
            for c in pkg.categories
        ],
        "images": images_out,
        "annotations": annotations_out,
    }

    summary = {
        "images": len(images_out),
        "annotations": len(annotations_out),
        "pending_images": pending,
        "warnings": warnings,
    }

    return coco, summary


def preview_coco(pkg, store, target):
    """What export_coco() would write; nothing is written."""
    _, summary = build_coco(pkg, store)
    summary["path"] = str(Path(target).resolve() / "instances_reviewed.json")
    return summary


def export_coco(pkg, store, target):
    """Atomic write of instances_reviewed.json into target/."""
    coco, summary = build_coco(pkg, store)
    out_dir = Path(target).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "instances_reviewed.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(coco, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, out)
    summary["path"] = str(out)
    return summary
