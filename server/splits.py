"""Train / val / test split by storage unit (BidVision: never split one unit across sets).

Photos of the same storage unit look alike; if some went to training and some to
testing, test scores would be inflated (project documents, Yagis et al. 2021).
So whole units are assigned, and the assignment depends only on the unit's name:
a unit never changes set when more photos or units are added later.

Unit of a photo: the package's "unit" field if the pipeline wrote one, otherwise the
file name up to its first "_" (unit001_photo3.jpg -> unit001). A name without "_"
counts as its own unit, with a warning.
"""
import hashlib
from collections import Counter
from pathlib import Path

SPLITS = ("train", "val", "test")
RATIOS = (70, 15, 15)  # percent of units, decided 2026-11-08
SPLIT_NAMES = {"train": "eğitim", "val": "doğrulama", "test": "test"}


def unit_of(image):
    """(unit, known) for a package image entry. Case and outer spaces do not matter.
    A package may carry "unit" explicitly (the pipeline reads it from the original
    file name, before cleaning the name); "unit": null means the name had none."""
    stem = Path(image["file_name"]).stem
    if "unit" in image:
        if image["unit"]:
            return str(image["unit"]).strip().lower(), True
        return stem.strip().lower(), False
    if "_" in stem:
        return stem.split("_", 1)[0].strip().lower(), True
    return stem.strip().lower(), False


def split_of(unit):
    """train / val / test for a unit name; stable across runs and machines."""
    bucket = int(hashlib.sha256(unit.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < RATIOS[0]:
        return "train"
    return "val" if bucket < RATIOS[0] + RATIOS[1] else "test"


def assign(images):
    """{image_id: split} plus a summary and warnings for a list of package image entries."""
    by_image, units, unknown = {}, {s: set() for s in SPLITS}, []
    unit_count = Counter()
    for img in images:
        unit, known = unit_of(img)
        if not known:
            unknown.append(img["file_name"])
        split = split_of(unit)
        by_image[img["id"]] = split
        units[split].add(unit)
        unit_count[unit] += 1

    warnings = []
    if unknown:
        shown = ", ".join(unknown[:3]) + (" ..." if len(unknown) > 3 else "")
        warnings.append(f"{len(unknown)} fotoğrafın adında ünite yok ({shown}). Beklenen biçim: "
                        f"unite_foto.jpg (örn. unit001_foto3.jpg). Her biri kendi ünitesi sayıldı.")
    if len(unit_count) == 1 and len(images) > 1:
        (only,) = unit_count
        warnings.append(f"Bütün fotoğraflar tek ünitede ('{only}'), ayrım yapılamadı. "
                        f"Telefonun IMG_1234 gibi adları bunu yapar: dosyaları unite_foto.jpg diye adlandır.")
    for s in SPLITS:
        if images and not units[s]:
            warnings.append(f"{SPLIT_NAMES[s]} kümesi boş ({len(unit_count)} ünite var; "
                            f"daha çok ünite gelince dolar)")
    return by_image, {s: len(units[s]) for s in SPLITS}, warnings
