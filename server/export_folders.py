"""Where the exports go.

Every export is written into a NEW folder named with the kind and the date and time, so
an earlier export is never overwritten or emptied. Each kind has its own big folder, so
kinds never mix:

    <package>_yolo/
        yolo_2026-11-10_23-45-12/            YOLO-seg dataset (finished photos)
    <package>_coco/
        coco_2026-11-10_23-46-03/            COCO files (finished photos)
    <package>_duzenlenecek/
        duzenlenecek_2026-11-10_23-47-30/    photos on the edit list + COCO file (Roboflow)

The tool never deletes an export; old ones are removed by hand when they are not needed.
"""
from datetime import datetime
from pathlib import Path

KINDS = ("yolo", "coco", "duzenlenecek")
PATTERN_STAMP = "YYYY-AA-GG_SS-DD-SN"  # shown in the preview, before the real time is known


def kind_root(export_dir, kind):
    """The big folder that holds every export of one kind.

    The registry stores "<package>_export"; the big folders are "<package>_yolo",
    "<package>_coco" and "<package>_duzenlenecek" beside the package. A folder the user
    chose with --export is used as the parent: <folder>/yolo, <folder>/coco, ..."""
    if kind not in KINDS:
        raise ValueError(f"unknown export kind: {kind}")
    p = Path(export_dir).resolve()
    if p.name.endswith("_export"):
        return p.with_name(p.name[:-len("_export")] + f"_{kind}")
    return p / kind


def pattern(export_dir, kind):
    """The folder an export would get, with a stamp standing in for the time."""
    return kind_root(export_dir, kind) / f"{kind}_{PATTERN_STAMP}"


def new_folder(export_dir, kind, when=None):
    """A folder path that does not exist yet: <big folder>/<kind>_<date>_<time>, with _2,
    _3... when two exports start in the same second."""
    root = kind_root(export_dir, kind)
    when = when or datetime.now()
    base = f"{kind}_{when:%Y-%m-%d_%H-%M-%S}"
    path = root / base
    n = 2
    while path.exists():
        path = root / f"{base}_{n}"
        n += 1
    return path