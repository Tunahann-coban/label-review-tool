"""Checks for prepare_photos.py. Works in a temp folder.

Usage (from the project folder):
    .venv\\Scripts\\python pipeline\\test_prepare_photos.py
"""
import csv
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "server"))
import prepare_photos  # noqa: E402

failures = 0


def check(name, cond):
    global failures
    print("OK  " if cond else "FAIL", name)
    failures += not cond


def photo(path, fmt, size=(60, 40), orientation=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {}
    if orientation:
        exif = Image.Exif()
        exif[0x0112] = orientation
        kwargs["exif"] = exif
    Image.new("RGB", size, (120, 80, 40)).save(path, fmt, **kwargs)


def expect_exit(fn, text):
    try:
        fn()
        return False
    except SystemExit as e:
        return text in str(e)


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        src = tmp / "bidvision-yeni"
        photo(src / "ilan-b" / "z.jpg", "JPEG", orientation=6)
        photo(src / "ilan-b" / "a.webp", "WEBP")
        (src / "ilan-b" / "kaynak.txt").write_text("https://example.org/listing/48213", encoding="utf-8")
        photo(src / "ilan-a" / "IMG_0001.PNG", "PNG")
        photo(src / "ilan-a" / "two.jpeg", "JPEG")
        (src / "ilan-a" / "notes.docx").write_bytes(b"not a picture")
        (src / "ilan-c").mkdir()

        rows, skipped, zip_path = prepare_photos.prepare(src, tmp / "out")
        files = sorted(p.name for p in (tmp / "out").iterdir())
        check(f"photos renamed by unit ({files})",
              files == ["unit001_1.png", "unit001_2.jpg", "unit002_1.jpg", "unit002_2.jpg", "units.csv"])
        check("units follow folder-name order (ilan-a -> unit001)",
              {r["unit"]: r["source_folder"] for r in rows} == {"unit001": "ilan-a", "unit002": "ilan-b"})
        with Image.open(tmp / "out" / "unit002_1.jpg") as im:
            check("webp converted to a real JPEG", im.format == "JPEG")
        with Image.open(tmp / "out" / "unit002_2.jpg") as im:
            check("JPEG copied byte for byte, EXIF rotation kept for the pipeline",
                  im.getexif().get(0x0112) == 6 and im.size == (60, 40))
        check("non-picture and empty folder reported, not copied",
              any("notes.docx" in s for s in skipped) and any("ilan-c" in s for s in skipped))
        with open(tmp / "out" / "units.csv", encoding="utf-8") as f:
            table = list(csv.DictReader(f))
        check("units.csv keeps original names and the source note",
              any(r["original_file"] == "a.webp" and r["note"].endswith("48213") for r in table))
        check("originals untouched", (src / "ilan-b" / "a.webp").exists() and len(list(src.rglob("*.*"))) == 6)
        names = sorted(zipfile.ZipFile(zip_path).namelist())
        check(f"zip ready for Kaggle ({len(names)} files)", "unit001_1.png" in names and "units.csv" in names)

        # the pipeline reads the unit from these names
        import make_package as mp
        b = mp.PackageBuilder(tmp / "pkg")
        for p in mp.find_images(tmp / "out"):
            b.add_image(p)
        check("pipeline: units read from the new names",
              sorted({i["unit"] for i in b.images}) == ["unit001", "unit002"])
        check("pipeline: units.csv is not taken for a photo", len(b.images) == 4)

        check("refuses loose files in the collected folder",
              expect_exit(lambda: (photo(src / "loose.jpg", "JPEG"), prepare_photos.prepare(src, tmp / "o2")),
                          "klasöre konmamış"))
        (src / "loose.jpg").unlink()
        check("refuses to overwrite an existing output", expect_exit(lambda: prepare_photos.prepare(src, tmp / "out"), "zaten var"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'all passed' if failures == 0 else f'{failures} failed'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
