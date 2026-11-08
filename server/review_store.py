"""Reads and writes review files: <package>/reviews/<image_stem>.json"""
import json
import os
import threading
from datetime import datetime
from pathlib import Path

ACTIONS = ("accept", "change", "delete", "add")

# Image states. "reviewed" is shown as "tamamlandı" (done); it keeps its old name so
# review files written before "needs_edit" existed still mean the same thing.
#   pending     not decided yet (also: decisions saved but "Tamamla" not pressed)
#   reviewed    the reviewer pressed "Tamamla": goes to the YOLO / COCO export
#   needs_edit  marked for manual work elsewhere (Roboflow): goes to the edit export
STATUSES = ("pending", "reviewed", "needs_edit")


def now():
    return datetime.now().isoformat(timespec="seconds")


def is_added(entry):
    """Objects the reviewer added from a candidate (kept even when deleted)."""
    return entry is not None and "from_candidate" in entry


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

    def _check_category(self, category_id):
        if category_id not in self.pkg.category_ids:
            raise ReviewError(f"unknown category: {category_id}")

    def apply(self, image_id, ann_id=None, action=None, category_id=None, candidate_id=None):
        """Apply one decision and save. Returns the review.

        accept / change / delete work on a pipeline object (int id) or an added one ("new-N").
        add takes candidate_id and category_id and creates "new-N".
        """
        if action not in ACTIONS:
            raise ReviewError(f"unknown action: {action}")
        if action in ("change", "add"):
            self._check_category(category_id)

        with self.lock:
            review = self.load(image_id) or {"image_id": image_id, "objects": [], "log": []}
            # Editing never changes the image state: only set_status does. A reviewed or
            # needs_edit image stays where it is while the reviewer keeps fixing it.
            status = review.get("status", "pending")
            status_by, status_at = review.get("status_by"), review.get("status_at")
            entries = {o["ann_id"]: o for o in review["objects"]}

            if action == "add":
                ann_id, entry, log = self._add(image_id, entries, candidate_id, category_id)
                prev = None
            else:
                prev = entries.get(ann_id)
                if is_added(prev):
                    entry, log = self._decide_added(prev, action, category_id, entries)
                else:
                    entry, log = self._decide_pipeline(image_id, ann_id, prev, action, category_id)

            entries[ann_id] = entry
            # same field order as the README example, easier to read by hand
            review = {
                "image_id": image_id,
                "status": status,
                "reviewer": self.reviewer,
                "updated": now(),
                **self._status_fields(status_by, status_at),
                "objects": list(entries.values()),
                # "by": who made this change (the reviewer's name at that moment)
                "log": review["log"] + [{"t": now(), "by": self.reviewer, "ann_id": ann_id, **log,
                                         "prev": prev}],
            }
            self._write(image_id, review)
            return review

    @staticmethod
    def _status_fields(by, at):
        """Who last moved the image to its current state, and when. Absent on files
        written before names were kept; those are left as they are."""
        return {"status_by": by, "status_at": at} if by else {}

    def set_status(self, image_id, status):
        """Move the image to another state ("Tamamla", "Düzenlenecek", back to pending).
        Decisions on its objects are kept. Returns the review (None if nothing to write)."""
        if status not in STATUSES:
            raise ReviewError(f"unknown status: {status}")
        with self.lock:
            review = self.load(image_id)
            before = review.get("status", "pending") if review else "pending"
            if before == status:
                return review
            review = review or {"image_id": image_id, "objects": [], "log": []}
            review = {
                "image_id": image_id,
                "status": status,
                "reviewer": self.reviewer,
                "updated": now(),
                **self._status_fields(self.reviewer, now()),
                "objects": review["objects"],
                "log": review["log"] + [{"t": now(), "by": self.reviewer, "action": "status",
                                         "from": before, "to": status}],
            }
            self._write(image_id, review)
            return review

    def _add(self, image_id, entries, candidate_id, category_id):
        cand = next((c for c in self.pkg.candidates.get(image_id, []) if c["id"] == candidate_id), None)
        if cand is None:
            raise ReviewError(f"candidate {candidate_id} is not in image {image_id}")
        if any(e.get("from_candidate") == candidate_id and e["state"] != "deleted" for e in entries.values()):
            raise ReviewError(f"candidate {candidate_id} was already added")
        # numbers are never reused, so log lines always point to one object
        used = [int(k.split("-")[1]) for k in entries if isinstance(k, str) and k.startswith("new-")]
        ann_id = f"new-{max(used, default=0) + 1}"
        entry = {"ann_id": ann_id, "category_id": category_id, "state": "added",
                 "from_candidate": candidate_id, "segmentation": cand["segmentation"]}
        return ann_id, entry, {"action": "add", "candidate": candidate_id, "to": category_id}

    @staticmethod
    def _decide_added(prev, action, category_id, entries):
        # an added object keeps its shape even when deleted, so it can be restored
        if action == "delete":
            return {**prev, "state": "deleted"}, {"action": "delete"}
        if action == "accept":
            # restoring must not create a second live object from the same candidate
            twin = next((e for e in entries.values() if e is not prev and e.get("from_candidate") == prev["from_candidate"]
                         and e["state"] != "deleted"), None)
            if prev["state"] == "deleted" and twin:
                # shown in the UI, so in Turkish
                raise ReviewError(f"aday #{prev['from_candidate']} zaten {twin['ann_id']} olarak eklenmiş, "
                                  f"geri almak için önce onu sil")
            return {**prev, "state": "added"}, {"action": "accept"}
        return ({**prev, "category_id": category_id},
                {"action": "change", "from": prev["category_id"], "to": category_id})

    def _decide_pipeline(self, image_id, ann_id, prev, action, category_id):
        ann = next((a for a in self.pkg.annotations.get(image_id, []) if a["id"] == ann_id), None)
        if ann is None:
            raise ReviewError(f"object {ann_id} is not in image {image_id}")
        orig = ann["category_id"]

        if action == "delete":
            return {"ann_id": ann_id, "state": "deleted"}, {"action": "delete"}
        if action == "accept":
            # Accepting keeps a changed class; on a deleted object it restores it.
            if prev and prev["state"] == "changed":
                return dict(prev), {"action": "accept"}
            return {"ann_id": ann_id, "category_id": orig, "state": "accepted"}, {"action": "accept"}
        # change
        current = prev.get("category_id", orig) if prev and prev["state"] != "deleted" else orig
        if category_id == orig:
            entry = {"ann_id": ann_id, "category_id": orig, "state": "accepted"}
        else:
            entry = {"ann_id": ann_id, "category_id": category_id, "state": "changed", "orig_category_id": orig}
        return entry, {"action": "change", "from": current, "to": category_id}
