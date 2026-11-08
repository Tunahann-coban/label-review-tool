"""Turns collected photos into a Kaggle-ready dataset named by storage unit.

    .venv\\Scripts\\python pipeline\\prepare_photos.py <collected folder> <output folder>

Input: one sub-folder per storage unit (one auction listing = one unit), photos inside.
         collected\\listing-48213\\a.jpg  b.webp  source.txt
Output: copies named unit001_1.jpg, unit001_2.jpg, unit002_1.jpg ... (README section 6),
        units.csv (which unit came from which folder / file, and the source note),
        and <output>.zip to upload to Kaggle as a dataset.

The originals are never changed. Formats the pipeline cannot read (webp, ...) become JPEG.
Units are numbered in folder-name order; give the output folder to the pipeline as is.
"""
import csv
import shutil
import sys
from pathlib import Path

from PIL import Image, UnidentifiedImageError

KEEP_AS_IS = {".jpg", ".jpeg", ".png"}          # the pipeline reads these directly
NOTE_FILES = ("source.txt", "kaynak.txt")       # a listing URL or a note, copied into units.csv


def prepare(src, out):
    src, out = Path(src), Path(out)
    if not src.is_dir():
        raise SystemExit(f"klasör yok: {src}")
    loose = [p.name for p in src.iterdir() if p.is_file()]
    if loose:
        raise SystemExit(f"{src} içinde klasöre konmamış dosyalar var ({', '.join(loose[:3])}). "
                         f"Her ilanın fotoğraflarını kendi alt klasörüne koy.")
    if out.exists():
        raise SystemExit(f"{out} zaten var; üzerine yazmamak için başka bir ad ver ya da sil")

    out.mkdir(parents=True)
    rows, skipped = [], []
    unit_dirs = sorted(p for p in src.iterdir() if p.is_dir())
    for u, folder in enumerate(unit_dirs, 1):
        unit = f"unit{u:03d}"
        note = next((folder / n for n in NOTE_FILES if (folder / n).exists()), None)
        note_text = note.read_text(encoding="utf-8", errors="replace").strip() if note else ""
        k = 0
        for photo in sorted(p for p in folder.iterdir() if p.is_file() and p not in (note,)):
            try:
                with Image.open(photo) as im:
                    im.verify()  # is it really a picture?
            except (UnidentifiedImageError, OSError):
                skipped.append(str(photo.relative_to(src)))
                continue
            k += 1
            suffix = photo.suffix.lower()
            if suffix in KEEP_AS_IS:
                name = f"{unit}_{k}{'.jpg' if suffix == '.jpeg' else suffix}"
                shutil.copy2(photo, out / name)  # byte copy: EXIF rotation kept for the pipeline
            else:
                name = f"{unit}_{k}.jpg"
                with Image.open(photo) as im:
                    im.convert("RGB").save(out / name, "JPEG", quality=95)
            rows.append({"file": name, "unit": unit, "source_folder": folder.name,
                         "original_file": photo.name, "note": note_text})
        if k == 0:
            skipped.append(f"{folder.name}/ (fotoğraf yok)")

    if not rows:
        shutil.rmtree(out)
        raise SystemExit("hiç fotoğraf bulunamadı")
    with open(out / "units.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    zip_path = Path(shutil.make_archive(str(out), "zip", out))
    return rows, skipped, zip_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    rows, skipped, zip_path = prepare(sys.argv[1], sys.argv[2])
    units = sorted({r["unit"] for r in rows})
    print(f"{len(rows)} fotoğraf, {len(units)} ünite -> {sys.argv[2]}")
    for unit in units:
        first = next(r for r in rows if r["unit"] == unit)
        print(f"  {unit}: {sum(r['unit'] == unit for r in rows)} fotoğraf  (klasör: {first['source_folder']})")
    for s in skipped:
        print(f"  atlandı: {s}")
    print(f"Kaggle'a yüklenecek: {zip_path}")
