"""Writes reviewed images as a YOLO segmentation dataset, split by storage unit.

export/
  images/{train,val,test}/<file>     copied images
  labels/{train,val,test}/<stem>.txt one line per object: <class_index> x1 y1 x2 y2 ... (0-1)
  data.yaml                          set folders + class names, same order as package categories
  labelers.csv                       who finished / changed each photo (see labelers.py)
"""
import json
import shutil
from pathlib import Path

from PIL import Image

import labelers
import splits
from package import merge_objects

MARKER = ".label-review-export"  # only folders carrying this file are ever replaced


class ExportError(Exception):
    pass


def normalize(poly, width, height):
    """Pixel polygon -> 'x1 y1 x2 y2 ...' in 0-1, clamped to the image."""
    out = []
    for i in range(0, len(poly), 2):
        x = min(max(poly[i] / width, 0.0), 1.0)
        y = min(max(poly[i + 1] / height, 0.0), 1.0)
        out.append(f"{x:.6f} {y:.6f}")
    return " ".join(out)


def _ring(flat):
    return [(flat[i], flat[i + 1]) for i in range(0, len(flat) - 1, 2)]


def _ring_area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


def _closest(a, b):
    """Indexes (i in a, j in b) of the nearest pair of points."""
    best = None
    for i, (ax, ay) in enumerate(a):
        for j, (bx, by) in enumerate(b):
            d = (ax - bx) ** 2 + (ay - by) ** 2
            if best is None or d < best[0]:
                best = (d, i, j)
    return best[1], best[2]


def _gap(a, b):
    i, j = _closest(a, b)
    return (a[i][0] - b[j][0]) ** 2 + (a[i][1] - b[j][1]) ** 2


def _arc(ring, start, end):
    """Points of the ring from start to end (inclusive), going forward and wrapping."""
    n = len(ring)
    steps = (end - start) % n
    return [ring[(start + s) % n] for s in range(steps + 1)]


def merge_parts(polygons):
    """One polygon for an object split into parts (e.g. a sofa cut in two by a box in front).

    YOLO-seg allows one polygon per object line; writing each part as its own line
    would teach the model that one occluded object is several objects. The parts are
    chained, biggest first then nearest, with zero-width bridges between their closest
    points: the path goes out over each bridge and comes back over the same bridge,
    so filling the polygon gives exactly the parts and nothing in between.
    """
    parts = [_ring(p) for p in polygons]
    if len(parts) == 1:
        return polygons[0]
    remaining = sorted(parts, key=_ring_area, reverse=True)
    chain = [remaining.pop(0)]
    while remaining:  # nearest next part to the last one in the chain
        nxt = min(remaining, key=lambda r: _gap(chain[-1], r))
        remaining.remove(nxt)
        chain.append(nxt)
    links = [_closest(chain[k], chain[k + 1]) for k in range(len(chain) - 1)]  # (out on k, in on k+1)

    path = _arc(chain[0], links[0][0], links[0][0] - 1) + [chain[0][links[0][0]]]
    for k in range(1, len(chain) - 1):  # middle parts: in-point -> out-point on the way out
        path += _arc(chain[k], links[k - 1][1], links[k][0])
    last_in = links[-1][1]
    path += _arc(chain[-1], last_in, last_in - 1) + [chain[-1][last_in]]
    for k in range(len(chain) - 2, 0, -1):  # and the rest of each middle part on the way back
        path += _arc(chain[k], links[k][0], links[k - 1][1])
    return [v for pt in path for v in pt]


def data_yaml(categories, present):
    """present: the sets that have images. YOLO needs a val set to train; when it is
    empty the train set stands in (and the export says so in its warnings)."""
    lines = ["# Written by the label review tool. Class index = position in this list.",
             "# Sets are whole storage units (see server/splits.py).",
             "train: images/train"]
    if "val" in present:
        lines.append("val: images/val")
    else:
        lines.append("val: images/train  # NO validation units yet: train set used, scores are not real")
    if "test" in present:
        lines.append("test: images/test")
    # names are quoted (JSON strings are valid YAML) so ":" "#" "yes" etc. stay plain text
    lines += [f"nc: {len(categories)}", "names:"]
    lines += [f"  - {json.dumps(c['name'], ensure_ascii=False)}" for c in categories]
    return "\n".join(lines) + "\n"


def export_objects(pkg, store, image_id):
    """Objects that go into the label file: everything except deleted ones."""
    objects = merge_objects(pkg.annotations.get(image_id, []), store.load(image_id))
    return [o for o in objects if o["state"] != "deleted"]


def left_out(pkg, store):
    """The images this export does not contain, and why, so nothing is left out unseen:
    [{id, file_name, unfinished, needs_edit}]. An image can be both."""
    out = []
    for image_id, img in pkg.images.items():
        unfinished = store.status(image_id) != "reviewed"
        flagged = store.needs_edit(image_id)
        if unfinished or flagged:
            out.append({"id": image_id, "file_name": img["file_name"],
                        "unfinished": unfinished, "needs_edit": flagged})
    return out

def plan(pkg, store):
    """Work out what an export would write, without touching the disk.

    Returns (files, summary): files is [(image source path, image file name, label lines)].
    Used both by the preview and by the real export, so they always agree.
    """
    class_index = {c["id"]: i for i, c in enumerate(pkg.categories)}
    # counted by class index, not name: two categories could share a name
    per_class = [0] * len(pkg.categories)
    summary = {"images": 0, "objects": 0, "empty_images": 0, "untouched_objects": 0,
               "pending_images": 0, "needs_edit_images": 0, "warnings": []}
    warn = summary["warnings"].append
    files = []

    # finished images only; a photo flagged "needs edit" goes to the edit export instead,
    # its labels here would be incomplete
    reviewed = [img for image_id, img in pkg.images.items()
                if store.status(image_id) == "reviewed" and not store.needs_edit(image_id)]
    split_by_image, units_per_split, split_warnings = splits.assign(reviewed)
    per_split = {s: {"images": 0, "objects": 0, "units": units_per_split[s]} for s in splits.SPLITS}

    for image_id, img in pkg.images.items():
        if image_id not in split_by_image:
            # two separate reasons (an image can be both): not finished, flagged for editing
            summary["pending_images"] += store.status(image_id) != "reviewed"
            summary["needs_edit_images"] += store.needs_edit(image_id)
            continue
        split = split_by_image[image_id]
        name, width, height = img["file_name"], img["width"], img["height"]
        stem = Path(name).stem  # unique, checked when the package is loaded
        src = pkg.image_path(image_id)
        if not src.exists():
            warn(f"{name}: resim dosyası yok, atlandı")
            continue
        try:
            with Image.open(src) as im:
                size = im.size
        except Exception as e:
            warn(f"{name}: resim açılamadı ({e}), atlandı")
            continue
        if size != (width, height):
            warn(f"{name}: annotations.json boyutu {width}x{height}, dosya {size[0]}x{size[1]}")

        lines = []
        for obj in export_objects(pkg, store, image_id):
            cls = class_index.get(obj["category_id"])
            if cls is None:
                warn(f"{name}: nesne #{obj['id']}: bilinmeyen sınıf {obj['category_id']}, atlandı")
                continue
            parts = []
            for poly in obj["segmentation"]:
                if len(poly) < 6 or len(poly) % 2:
                    warn(f"{name}: nesne #{obj['id']}: geçersiz çokgen ({len(poly)} değer), atlandı")
                    continue
                parts.append(poly)
            if len(parts) > 1:  # one object, one line (see merge_parts)
                warn(f"{name}: nesne #{obj['id']}: {len(parts)} parçalı, tek satırda birleştirildi")
            if parts:
                lines.append(f"{cls} {normalize(merge_parts(parts), width, height)}")
                summary["objects"] += 1
                per_class[cls] += 1
                # nobody looked at it: it goes in exactly as the pipeline gave it
                summary["untouched_objects"] += obj["state"] == "auto"

        files.append((src, name, lines, split))
        summary["images"] += 1
        summary["empty_images"] += not lines
        per_split[split]["images"] += 1
        per_split[split]["objects"] += len(lines)

    summary["per_class"] = [{"index": i, "name": c["name"], "count": per_class[i]}
                            for i, c in enumerate(pkg.categories)]
    summary["splits"] = per_split
    summary["left_out"] = left_out(pkg, store)
    summary["warnings"] = split_warnings + summary["warnings"]
    if reviewed and not per_split["val"]["images"]:
        summary["warnings"].append("data.yaml'da doğrulama (val) yerine eğitim kümesi yazıldı: "
                                   "eğitim çalışır ama doğrulama skorları gerçek değildir")
    return files, summary


def build(pkg, store, out_dir):
    """Write the dataset into out_dir (must not exist). Returns a summary."""
    files, summary = plan(pkg, store)
    out_dir.mkdir(parents=True)
    (out_dir / MARKER).write_text("created by the label review tool\n", encoding="utf-8")
    present = {split for *_, split in files}
    for split in present | {"train"}:  # train always exists: data.yaml points to it
        (out_dir / "images" / split).mkdir(parents=True)
        (out_dir / "labels" / split).mkdir(parents=True)
    (out_dir / "data.yaml").write_text(data_yaml(pkg.categories, present), encoding="utf-8")
    for src, name, lines, split in files:
        # an empty file is written on purpose: a reviewed image with no objects is a background example
        (out_dir / "labels" / split / f"{Path(name).stem}.txt").write_text(
            "".join(line + "\n" for line in lines), encoding="utf-8")
        shutil.copy2(src, out_dir / "images" / split / name)
    # who finished / changed each photo in this dataset
    names = {name for _, name, _, _ in files}
    ids = [i for i, img in pkg.images.items() if img["file_name"] in names]
    (out_dir / "labelers.csv").write_text(labelers.to_csv(labelers.rows(pkg, store, ids)), encoding="utf-8")
    return summary


def preview(pkg, store, target):
    """What export() would write, and where (target is the folder name pattern, the
    real one gets the date and time); nothing is written."""
    _, summary = plan(pkg, store)
    summary["path"] = str(target)
    return summary


def export(pkg, store, target):
    """Write the dataset into a NEW folder: target must not exist (see create_folder)."""
    return create_folder(target, lambda tmp: build(pkg, store, tmp))


def create_folder(target, build_into):
    """build_into(tmp) writes a whole folder (carrying MARKER) and returns a summary.
    The folder is built next to the target and renamed into place, so a failed export
    leaves no half-written folder. Never overwrites and never deletes an export: an
    existing target is refused. Every export goes into its own, dated folder (see
    export_folders.py), so an earlier export can never lose files. Shared by the YOLO,
    COCO and "needs editing" exports."""
    target = Path(target).resolve()
    if target.exists():
        raise ExportError(f"{target} zaten var, üzerine yazılmadı")
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp = target.with_name(target.name + ".tmp")
    if tmp.exists():  # left by a crash of an earlier export; only ours is removed
        if not (tmp / MARKER).exists():
            raise ExportError(f"{tmp} bu aracın oluşturduğu bir klasör değil, dokunulmadı")
        shutil.rmtree(tmp)

    try:
        summary = build_into(tmp)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    try:
        tmp.rename(target)
    except OSError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ExportError(f"export klasörü oluşturulamadı (bir dosyası açık olabilir): {e}")

    summary["path"] = str(target)
    return summary