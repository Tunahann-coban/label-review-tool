"""Writes reviewed images as COCO JSON, one file per set, split by storage unit.

<export>_coco/
  instances_train.json   standard COCO instance segmentation format
  instances_val.json     (only the sets that have images)
  instances_test.json
"""
import json
from datetime import datetime
from pathlib import Path

import exporter
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
    # finished images only; flagged ones ("needs edit") go to the edit export instead
    reviewed = [img for img_id, img in pkg.images.items()
                if store.status(img_id) == "reviewed" and not store.needs_edit(img_id)]
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
        # two separate reasons (an image can be both): not finished, flagged for editing
        "pending_images": sum(1 for i in pkg.images if store.status(i) != "reviewed"),
        "needs_edit_images": sum(1 for i in pkg.images if store.needs_edit(i)),
        "splits": {s: {"images": len(sets[s]["images"]), "objects": len(sets[s]["annotations"]),
                       "units": units_per_split[s]} for s in splits.SPLITS},
        "left_out": exporter.left_out(pkg, store),
        "warnings": warnings,
    }
    return {s: c for s, c in sets.items() if c["images"]}, summary


def preview_coco(pkg, store, target):
    """What export_coco() would write (target is the folder name pattern); nothing is written."""
    _, summary = build_coco(pkg, store)
    summary["path"] = str(target)
    return summary


def export_coco(pkg, store, target):
    """Writes instances_<set>.json for each set with images, plus labelers.csv, into a
    NEW folder (target must not exist, see exporter.create_folder)."""
    sets, summary = build_coco(pkg, store)

    def build(out):
        out.mkdir(parents=True)
        (out / exporter.MARKER).write_text("created by the label review tool\n", encoding="utf-8")
        for s, coco in sets.items():
            (out / f"instances_{s}.json").write_text(json.dumps(coco, ensure_ascii=False, indent=1), encoding="utf-8")
        included = [img["id"] for c in sets.values() for img in c["images"]]
        (out / "labelers.csv").write_text(labelers.to_csv(labelers.rows(pkg, store, included)), encoding="utf-8")
        return summary

    return exporter.create_folder(target, build)