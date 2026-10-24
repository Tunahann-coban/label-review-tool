"""Reads and writes review files: <package>/reviews/<image_stem>.json"""
import json
import os
import threading
from datetime import datetime
from pathlib import Path

ACTIONS = ("accept", "change", "delete")


def now():
    return datetime.now().isoformat(timespec="seconds")


class ReviewError(ValueError):
    pass


class ReviewStore:
    def __init__(self, package, reviewer):
        self.pkg = package
        self.reviewer = reviewer
        self.dir = package.root / "reviews"
        self.dir.mkdir(exist_ok=True)
        self.lock = threading.Lock()  # one read-modify-write at a time

    def path(self, image_id):
        stem = Path(self.pkg.images[image_id]["file_name"]).stem
        return self.dir / f"{stem}.json"

    def load(self, image_id):
        """Review for the image, or None if it was never touched (= pending)."""
        p = self.path(image_id)
        if not p.exists():
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    def status(self, image_id):
        review = self.load(image_id)
        return review["status"] if review else "pending"

    def _write(self, image_id, review):
        # Write to a temp file, then swap: a crash never leaves a half-written file.
        p = self.path(image_id)
        self.dir.mkdir(exist_ok=True)  # may have been deleted while running (to reset reviews)
        tmp = p.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(review, f, ensure_ascii=False, indent=1)
        os.replace(tmp, p)

    def apply(self, image_id, ann_id, action, category_id=None):
        """Apply one decision to one object and save. Returns the review."""
        if action not in ACTIONS:
            raise ReviewError(f"unknown action: {action}")
        ann = next((a for a in self.pkg.annotations.get(image_id, []) if a["id"] == ann_id), None)
        if ann is None:
            raise ReviewError(f"object {ann_id} is not in image {image_id}")
        if action == "change" and category_id not in self.pkg.category_ids:
            raise ReviewError(f"unknown category: {category_id}")

        with self.lock:
            review = self.load(image_id) or {"image_id": image_id, "objects": [], "log": []}
            entries = {o["ann_id"]: o for o in review["objects"]}
            prev = entries.get(ann_id)
            orig = ann["category_id"]

            if action == "delete":
                entry = {"ann_id": ann_id, "state": "deleted"}
                log = {"action": "delete"}
            elif action == "accept":
                # Accepting keeps a changed class; on a deleted object it restores it.
                if prev and prev["state"] == "changed":
                    entry = dict(prev)
                else:
                    entry = {"ann_id": ann_id, "category_id": orig, "state": "accepted"}
                log = {"action": "accept"}
            else:  # change
                current = prev.get("category_id", orig) if prev and prev["state"] != "deleted" else orig
                if category_id == orig:
                    entry = {"ann_id": ann_id, "category_id": orig, "state": "accepted"}
                else:
                    entry = {"ann_id": ann_id, "category_id": category_id,
                             "state": "changed", "orig_category_id": orig}
                log = {"action": "change", "from": current, "to": category_id}

            entries[ann_id] = entry
            # same field order as the README example, easier to read by hand
            review = {
                "image_id": image_id,
                "status": "reviewed",
                "reviewer": self.reviewer,
                "updated": now(),
                "objects": list(entries.values()),
                "log": review["log"] + [{"t": now(), "ann_id": ann_id, **log, "prev": prev}],
            }
            self._write(image_id, review)
            return review
