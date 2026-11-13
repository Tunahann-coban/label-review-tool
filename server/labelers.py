"""Who labelled which photo: one row per image, written next to every export as
labelers.csv and shown in the web page.

Names come from the review file:
  status_by / status_at   who last set the image's status ("tamamlandı" or back to
                          pending), and when
  edit_by / edit_at       who last added it to / removed it from the edit list, and when
  log[].by                who made each object change
Review files written before names were kept have none of these; for those the file's
`reviewer` (the last person to save) is used and the editors column says so.
"""
import csv
import io

COLUMNS = ["image", "status", "status_by", "status_at", "needs_edit", "edit_by", "edit_at",
           "editors", "changes", "last_saved"]


def is_object_change(entry):
    """A change the reviewer made to an object. Moving the marks and the automatic
    "accept the untouched ones" that goes with finishing an image are not.""" 
    return entry.get("action") not in ("status", "flag") and not entry.get("auto")


def editors_of(review):
    """Names that changed objects of this image, in order of first appearance."""
    if not review:
        return []
    names = []
    for entry in review.get("log", []):
        name = entry.get("by")
        if name and name not in names and is_object_change(entry):
            names.append(name)
    if not names and review.get("reviewer") and any(is_object_change(e) for e in review.get("log", [])):
        names.append(f"{review['reviewer']} (eski kayıt)")  # file from before names were kept
    return names


def row(pkg, store, image_id):
    review = store.load(image_id) or {}
    log = review.get("log", [])
    return {
        "image": pkg.images[image_id]["file_name"],
        "status": review.get("status", "pending"),
        "status_by": review.get("status_by", ""),
        "status_at": review.get("status_at", ""),
        "needs_edit": "yes" if review.get("needs_edit") else "",
        "edit_by": review.get("edit_by", ""),
        "edit_at": review.get("edit_at", ""),
        "editors": "; ".join(editors_of(review)),
        "changes": sum(1 for e in log if is_object_change(e)),
        "last_saved": review.get("updated", ""),
    }


def rows(pkg, store, image_ids=None):
    ids = list(pkg.images) if image_ids is None else image_ids
    return [row(pkg, store, i) for i in ids]


def to_csv(table):
    # utf-8 with a BOM so Excel shows Turkish letters right
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(table)
    return "﻿" + buf.getvalue()
