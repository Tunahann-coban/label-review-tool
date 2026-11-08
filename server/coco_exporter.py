"""Writes reviewed images as COCO JSON, one file per set, split by storage unit.

<export>_coco/
  instances_train.json   standard COCO instance segmentation format
  instances_val.json     (only the sets that have images)
  instances_test.json
"""
import json
import os
from datetime import datetime
from pathlib import Path

import labelers
import splits
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
    """({split: coco dict}, summary). Only reviewed images; deleted objects left out."""
    reviewed = [img for img_id, img in pkg.images.items() if store.status(img_id) == "reviewed"]
    split_by_image, units_per_split, warnings = splits.assign(reviewed)
    categories = [{"id": c["id"], "name": c["name"], "supercategory": c.get("supercategory", "")}
                  for c in pkg.categories]
    created = datetime.now().isoformat(timespec="seconds")
    sets = {s: {"info": {"description": f"Reviewed by label-review-tool ({s})", "version": "1.0",
                         "date_created": created},
                "categories": categories, "images": [], "annotations": []} for s in splits.SPLITS}
    ann_id = 1

    for img in reviewed:
        image_id = img["id"]
        coco = sets[split_by_image[image_id]]
        objects = merge_objects(pkg.annotations.get(image_id, []), store.load(image_id))
        coco["images"].append({"id": image_id, "file_name": img["file_name"],
                               "width": img["width"], "height": img["height"]})
        for obj in objects:
            if obj["state"] == "deleted":
                continue
            seg, cls = obj["segmentation"], obj["category_id"]
            if cls not in pkg.category_ids:
                warnings.append(f"{img['file_name']}: nesne #{obj['id']}: bilinmeyen sınıf {cls}, atlandı")
                continue
            # COCO keeps a split object as a list of polygons: no merging needed here
            coco["annotations"].append({"id": ann_id, "image_id": image_id, "category_id": cls,
                                        "segmentation": seg, "bbox": bbox_of(seg),
                                        "area": area_of(seg), "iscrowd": 0})
            ann_id += 1

    summary = {
        "images": len(reviewed),
        "annotations": ann_id - 1,
        "pending_images": len(pkg.images) - len(reviewed),  # everything not done, needs_edit included
        "needs_edit_images": sum(1 for i in pkg.images if store.status(i) == "needs_edit"),
        "splits": {s: {"images": len(sets[s]["images"]), "objects": len(sets[s]["annotations"]),
                       "units": units_per_split[s]} for s in splits.SPLITS},
        "warnings": warnings,
    }
    return {s: c for s, c in sets.items() if c["images"]}, summary


def preview_coco(pkg, store, target):
    """What export_coco() would write; nothing is written."""
    _, summary = build_coco(pkg, store)
    summary["path"] = str(Path(target).resolve())
    return summary


def export_coco(pkg, store, target):
    """Writes instances_<set>.json for each set with images; removes files of sets
    that became empty, so a stale set file never lingers. Each file is swapped in atomically."""
    sets, summary = build_coco(pkg, store)
    out_dir = Path(target).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in splits.SPLITS:
        out = out_dir / f"instances_{s}.json"
        if s in sets:
            tmp = out.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(sets[s], ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, out)
        elif out.exists():
            out.unlink()
    included = [img["id"] for c in sets.values() for img in c["images"]]
    (out_dir / "labelers.csv").write_text(labelers.to_csv(labelers.rows(pkg, store, included)), encoding="utf-8")
    summary["path"] = str(out_dir)
    return summary
