"""Who labelled which photo: one row per image, written next to every export as
labelers.csv and shown in the web page.

Names come from the review file:
  status_by / status_at   who last moved the image to its current state ("Tamamla",
                          "Düzenlenecek", back to pending), and when
  log[].by                who made each object change
Review files written before names were kept have neither; for those the file's
`reviewer` (the last person to save) is used and the editors column says so.
"""
import csv
import io

COLUMNS = ["image", "status", "status_by", "status_at", "editors", "changes", "last_saved"]


def editors_of(review):
    """Names that changed objects of this image, in order of first appearance."""
    if not review:
        return []
    names = []
    for entry in review.get("log", []):
        name = entry.get("by")
        if name and name not in names:
            names.append(name)
    if not names and review.get("reviewer") and review.get("log"):
        names.append(f"{review['reviewer']} (eski kayıt)")  # file from before names were kept
    return names


def row(pkg, store, image_id):
    review = store.load(image_id)
    log = (review or {}).get("log", [])
    return {
        "image": pkg.images[image_id]["file_name"],
        "status": review["status"] if review else "pending",
        "status_by": (review or {}).get("status_by", ""),
        "status_at": (review or {}).get("status_at", ""),
        "editors": "; ".join(editors_of(review)),
        "changes": sum(1 for e in log if e.get("action") != "status"),
        "last_saved": (review or {}).get("updated", ""),
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
