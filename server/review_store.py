"""Reads and writes review files: <package>/reviews/<image_stem>.json"""
import json
import os
import threading
from datetime import datetime
from pathlib import Path

ACTIONS = ("accept", "change", "delete", "add")

# Two separate marks on an image:
#   status      "pending" (not finished) or "reviewed" ("tamamlandı": the reviewer pressed
#               "Tamamlandı olarak işaretle")
#   needs_edit  a flag, independent of status: "Düzenlenecekler'e ekle". The photo goes
#               to the edit export (Roboflow) instead of the YOLO / COCO exports, whether
#               or not it is also marked done.
# Object decisions change neither.
STATUSES = ("pending", "reviewed")
# status_by / status_at: who set the status and when; edit_by / edit_at: same for the flag
MARK_FIELDS = ("status_by", "status_at", "needs_edit", "edit_by", "edit_at")


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
            return self._normalize(json.load(f))

    @staticmethod
    def _normalize(review):
        """Files written while "needs_edit" was a third status: it is a flag now, and
        such an image is simply not finished."""
        if review.get("status") == "needs_edit":
            review["status"] = "pending"
            review["needs_edit"] = True
            if "status_by" in review:
                review["edit_by"] = review.pop("status_by")
            if "status_at" in review:
                review["edit_at"] = review.pop("status_at")
        return review

    def status(self, image_id):
        review = self.load(image_id)
        return review["status"] if review else "pending"

    def needs_edit(self, image_id):
        review = self.load(image_id)
        return bool(review and review.get("needs_edit"))

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
            # Editing never changes the image's marks: only set_marks does. A reviewed or
            # flagged image stays as it is while the reviewer keeps fixing it.
            status = review.get("status", "pending")
            marks = self._marks(review)
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
                **marks,
                "objects": list(entries.values()),
                # "by": who made this change (the reviewer's name at that moment)
                "log": review["log"] + [{"t": now(), "by": self.reviewer, "ann_id": ann_id, **log,
                                         "prev": prev}],
            }
            self._write(image_id, review)
            return review

    @staticmethod
    def _marks(review):
        """The marks a file already has (who set them and when). Files written before
        names were kept simply lack some of these; they are left as they are."""
        return {k: review[k] for k in MARK_FIELDS if k in review}

    def set_marks(self, image_id, status=None, needs_edit=None):
        """Change the image's status and / or its "needs edit" flag; None leaves one as it is.
        Decisions on its objects are kept. Returns the review (None if there was nothing
        to write: no change on an image that has no file)."""
        if status is not None and status not in STATUSES:
            raise ReviewError(f"unknown status: {status}")
        if needs_edit is not None and not isinstance(needs_edit, bool):
            raise ReviewError(f"needs_edit must be true or false: {needs_edit!r}")
        with self.lock:
            review = self.load(image_id)
            old_status = review.get("status", "pending") if review else "pending"
            old_flag = bool(review and review.get("needs_edit"))
            new_status = old_status if status is None else status
            new_flag = old_flag if needs_edit is None else needs_edit
            if (new_status, new_flag) == (old_status, old_flag):
                return review
            base = review or {"image_id": image_id, "objects": [], "log": []}
            marks, log, t = self._marks(base), list(base["log"]), now()
            objects = list(base["objects"])
            if new_status != old_status:
                log.append({"t": t, "by": self.reviewer, "action": "status", "from": old_status, "to": new_status})
                marks.update(status_by=self.reviewer, status_at=t)
                if new_status == "reviewed":
                    objects = self._auto_accept(image_id, objects, log, t)
                elif old_status == "reviewed":
                    objects = self._undo_auto_accept(objects, log, t)
            if new_flag != old_flag:
                log.append({"t": t, "by": self.reviewer, "action": "flag", "from": old_flag, "to": new_flag})
                marks.update(needs_edit=new_flag, edit_by=self.reviewer, edit_at=t)
            review = {
                "image_id": image_id,
                "status": new_status,
                "reviewer": self.reviewer,
                "updated": t,
                # same order as MARK_FIELDS, easier to read by hand
                **{k: marks[k] for k in MARK_FIELDS if k in marks},
                "objects": objects,
                "log": log,
            }
            self._write(image_id, review)
            return review

    def _auto_accept(self, image_id, objects, log, t):
        """Finishing an image means its untouched objects are accepted as the pipeline
        gave them. They are marked auto_accepted, so taking the image back to pending can
        undo exactly these and leave the reviewer's own decisions alone."""
        decided = {o["ann_id"] for o in objects}
        out = list(objects)
        for ann in self.pkg.annotations.get(image_id, []):
            if ann["id"] not in decided:
                out.append({"ann_id": ann["id"], "category_id": ann["category_id"],
                            "state": "accepted", "auto_accepted": True})
                log.append({"t": t, "by": self.reviewer, "ann_id": ann["id"], "action": "accept",
                            "auto": True, "prev": None})
        return out

    def _undo_auto_accept(self, objects, log, t):
        # an object the reviewer touched later was written without the mark, so it stays
        out = []
        for o in objects:
            if o.get("auto_accepted"):
                log.append({"t": t, "by": self.reviewer, "ann_id": o["ann_id"], "action": "unaccept",
                            "auto": True, "prev": o})
            else:
                out.append(o)
        return out

    def set_status(self, image_id, status):
        return self.set_marks(image_id, status=status)

    def set_needs_edit(self, image_id, flag):
        return self.set_marks(image_id, needs_edit=flag)

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
