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
        self.images = {img["id"]: img for img in data["images"]}
        self.annotations = {}  # image_id -> [annotation]
        for ann in data["annotations"]:
            self.annotations.setdefault(ann["image_id"], []).append(ann)
        self.candidates = {}  # image_id -> [candidate]
        for cand in data.get("candidates", []):
            self.candidates.setdefault(cand["image_id"], []).append(cand)

    def image_path(self, image_id):
        return self.root / "images" / self.images[image_id]["file_name"]

    def image_list(self):
        # status comes from reviews/ in step 6; everything is pending for now
        return [{"id": img["id"], "file_name": img["file_name"], "status": "pending"}
                for img in self.images.values()]

    def image_detail(self, image_id):
        objects = [{**ann, "state": "auto"} for ann in self.annotations.get(image_id, [])]
        return {"image": self.images[image_id],
                "objects": objects,
                "candidates": self.candidates.get(image_id, [])}
