"""Writes the images flagged "needs editing" ("Düzenlenecekler'e ekle", finished or not)
as one folder for manual work elsewhere (Roboflow): the photos plus their current
masks as a COCO file.

<export>_duzenlenecek/
  <photo>.jpg ...              copies of the marked photos
  _annotations.coco.json       standard COCO instance segmentation, deleted objects left out
  labelers.csv                 who marked / changed each photo

No train / val / test split: the next tool decides that. Roboflow reads this layout
(photos and _annotations.coco.json together) as a COCO upload.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import labelers
from exporter import MARKER, create_folder
from coco_exporter import area_of
from package import bbox_of, merge_objects

COCO_FILE = "_annotations.coco.json"


def plan(pkg, store):
    """(coco dict, [(source path, file name)], summary). Nothing is written."""
    marked = [img for image_id, img in pkg.images.items() if store.needs_edit(image_id)]
    categories = [{"id": c["id"], "name": c["name"], "supercategory": c.get("supercategory", "")}
                  for c in pkg.categories]
    coco = {"info": {"description": "Marked for editing by label-review-tool", "version": "1.0",
                     "date_created": datetime.now().isoformat(timespec="seconds")},
            "categories": categories, "images": [], "annotations": []}
    files, warnings, empty, ann_id = [], [], 0, 1

    for img in marked:
        image_id, name = img["id"], img["file_name"]
        src = pkg.image_path(image_id)
        if not src.exists():
            warnings.append(f"{name}: resim dosyası yok, atlandı")
            continue
        coco["images"].append({"id": image_id, "file_name": name, "width": img["width"], "height": img["height"]})
        files.append((src, name))
        count = 0
        for obj in merge_objects(pkg.annotations.get(image_id, []), store.load(image_id)):
            if obj["state"] == "deleted":
                continue
            if obj["category_id"] not in pkg.category_ids:
                warnings.append(f"{name}: nesne #{obj['id']}: bilinmeyen sınıf {obj['category_id']}, atlandı")
                continue
            seg = obj["segmentation"]
            coco["annotations"].append({"id": ann_id, "image_id": image_id, "category_id": obj["category_id"],
                                        "segmentation": seg, "bbox": bbox_of(seg), "area": area_of(seg),
                                        "iscrowd": 0})
            ann_id += 1
            count += 1
        empty += count == 0

    summary = {"images": len(files), "objects": ann_id - 1, "empty_images": empty,
               "warnings": warnings}
    return coco, files, summary


def preview(pkg, store, target):
    """What export() would write, and where (target is the folder name pattern); nothing is written."""
    _, _, summary = plan(pkg, store)
    summary["path"] = str(target)
    return summary


def export(pkg, store, target):
    coco, files, summary = plan(pkg, store)

    def build(out):
        out.mkdir(parents=True)
        (out / MARKER).write_text("created by the label review tool\n", encoding="utf-8")
        for src, name in files:
            shutil.copy2(src, out / name)
        (out / COCO_FILE).write_text(json.dumps(coco, ensure_ascii=False, indent=1), encoding="utf-8")
        included = [img["id"] for img in coco["images"]]
        (out / "labelers.csv").write_text(labelers.to_csv(labelers.rows(pkg, store, included)), encoding="utf-8")
        return summary

    return create_folder(target, build)
