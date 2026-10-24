"""Reads a package folder (images/ + annotations.json)."""
import json
from pathlib import Path


class Package:
    def __init__(self, root):
        self.root = Path(root).resolve()
        ann_file = self.root / "annotations.json"
        if not ann_file.exists():
            raise FileNotFoundError(f"annotations.json not found in {self.root}")
        with open(ann_file, encoding="utf-8") as f:
            data = json.load(f)

        self.categories = data["categories"]
        self.category_ids = {c["id"] for c in self.categories}
        self.images = {img["id"]: img for img in data["images"]}
        # reviews/<stem>.json and labels/<stem>.txt need unique stems (a.jpg + a.png would clash)
        stems = {}
        for img in self.images.values():
            stem = Path(img["file_name"]).stem
            if stem in stems:
                raise ValueError(f"same file stem '{stem}': {stems[stem]} and {img['file_name']}")
            stems[stem] = img["file_name"]
        self.annotations = {}  # image_id -> [annotation]
        for ann in data["annotations"]:
            self.annotations.setdefault(ann["image_id"], []).append(ann)
        self.candidates = {}  # image_id -> [candidate]
        for cand in data.get("candidates", []):
            self.candidates.setdefault(cand["image_id"], []).append(cand)

    def image_path(self, image_id):
        return self.root / "images" / self.images[image_id]["file_name"]


def bbox_of(segmentation):
    xs = [v for poly in segmentation for v in poly[0::2]]
    ys = [v for poly in segmentation for v in poly[1::2]]
    return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]


def merge_objects(annotations, review):
    """Pipeline annotations with the review decisions applied on top,
    followed by the objects the reviewer added from candidates."""
    entries = {o["ann_id"]: o for o in (review or {}).get("objects", [])}
    merged = []
    for ann in annotations:
        entry = entries.get(ann["id"])
        obj = {**ann, "state": "auto"}
        if entry:
            obj["state"] = entry["state"]
            if "category_id" in entry:
                obj["category_id"] = entry["category_id"]
            if entry["state"] == "changed":
                obj["orig_category_id"] = entry["orig_category_id"]
        merged.append(obj)
    for entry in entries.values():
        if "from_candidate" in entry:  # added (state "added", or "deleted" after removal)
            merged.append({"id": entry["ann_id"], "category_id": entry["category_id"],
                           "segmentation": entry["segmentation"], "bbox": bbox_of(entry["segmentation"]),
                           "score": None, "source": "review", "state": entry["state"],
                           "from_candidate": entry["from_candidate"]})
    return merged
