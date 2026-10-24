"""Checks for make_package.py, without GPU or models. Works in a temp folder.

Usage (from the project folder):
    .venv\\Scripts\\python -m pip install -r pipeline\\requirements.txt   (once)
    .venv\\Scripts\\python pipeline\\test_make_package.py
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "server"))
import make_package as mp  # noqa: E402

failures = 0


def check(name, cond):
    global failures
    print("OK  " if cond else "FAIL", name)
    failures += not cond


def blank(h=300, w=400):
    return np.zeros((h, w), np.uint8)


def test_polygons():
    m = blank()
    m[40:100, 50:150] = 1  # 100 x 60 rectangle
    polys = mp.mask_to_polygons(m)
    check("rectangle -> one polygon", len(polys) == 1)
    check("rectangle -> 4 corners", len(polys[0]) == 8)
    area = mp.polygon_area(polys[0])
    check(f"rectangle area kept ({area:.0f} vs 6000)", abs(area - 6000) / 6000 < 0.05)

    e = blank()
    cv2.ellipse(e, (200, 150), (120, 70), 20, 0, 360, 1, -1)
    polys = mp.mask_to_polygons(e)
    true_area = float(e.sum())
    area = mp.polygon_area(polys[0])
    check(f"ellipse simplified to few points ({len(polys[0]) // 2})", len(polys[0]) // 2 < 60)
    check(f"ellipse area within 2 % ({area:.0f} vs {true_area:.0f})", abs(area - true_area) / true_area < 0.02)

    two = blank()
    two[10:60, 10:60] = 1    # 2500 px
    two[100:200, 200:350] = 1  # 15000 px
    two[250:255, 10:15] = 1  # speck, 25 px
    polys = mp.mask_to_polygons(two)
    check("two parts kept, speck dropped", len(polys) == 2)
    check("biggest part first", mp.polygon_area(polys[0]) > mp.polygon_area(polys[1]))
    check("empty mask -> no polygon", mp.mask_to_polygons(blank()) == [])
    check("values are plain floats (JSON safe)", all(type(v) is float for v in polys[0]))


def test_nms():
    boxes = [[10, 10, 110, 110], [12, 11, 111, 112], [120, 10, 220, 110]]
    keep = mp.nms(boxes, [0.4, 0.7, 0.5])
    check("same object asked as two classes -> higher score kept", keep == [1, 2])
    check("neighbouring objects both kept", mp.nms([[0, 0, 100, 100], [60, 0, 160, 100]], [0.9, 0.8]) == [0, 1])
    check("no boxes -> nothing", mp.nms([], []) == [])


def test_candidates():
    obj = blank()
    obj[50:150, 50:150] = 1
    inside = blank()
    inside[60:140, 60:140] = 1        # covered by the object
    free = blank()
    free[200:280, 250:350] = 1         # 8000 px, free
    speck = blank()
    speck[0:10, 0:10] = 1              # 100 px
    floor = np.ones((300, 400), np.uint8)  # whole image
    kept = mp.filter_candidates([inside, free, speck, floor], [obj], image_area=300 * 400)
    check("only the free, mid-sized candidate is kept", len(kept) == 1 and kept[0][1] == 8000)
    many = []
    for i in range(10):
        m = blank()
        m[10 + i * 25:30 + i * 25, 10:40 + i * 3] = 1
        many.append(m)
    kept = mp.filter_candidates(many, [], image_area=300 * 400, min_area=100, max_count=3)
    check("at most max_count, biggest first", len(kept) == 3 and kept[0][1] >= kept[1][1] >= kept[2][1])


def test_exif(tmp):
    # a 200 x 100 picture stored sideways with "rotate 90 clockwise" (orientation 6),
    # red dot in its stored top-left corner
    raw = np.zeros((100, 200, 3), np.uint8)
    raw[0:10, 0:10] = (255, 0, 0)
    exif = Image.Exif()
    exif[0x0112] = 6
    path = tmp / "phone photo.jpg"
    Image.fromarray(raw).save(path, exif=exif, quality=95)

    rgb = mp.load_upright(path)
    check("EXIF rotation applied (portrait: 200 high, 100 wide)", rgb.shape[:2] == (200, 100))
    check("red dot moved to top-right, as a viewer shows it", rgb[3, 96, 0] > 200 and rgb[3, 3, 0] < 50)

    b = mp.PackageBuilder(tmp / "pkg_exif")
    image_id, arr = b.add_image(path)
    info = b.images[0]
    saved = Image.open(tmp / "pkg_exif" / "images" / info["file_name"])
    check("saved copy is upright and has no rotate note",
          saved.size == (100, 200) and saved.getexif().get(0x0112) in (None, 1))
    check("recorded size = saved size = model input",
          (info["width"], info["height"]) == saved.size and arr.shape[1::-1] == saved.size)
    check("space in file name replaced", info["file_name"] == "phone_photo.jpg")


def test_package_end_to_end(tmp):
    """Package -> our service -> a decision -> YOLO export, all with the real code."""
    from package import Package
    from review_store import ReviewStore
    import exporter

    src = tmp / "photos"
    src.mkdir()
    for name in ("a.jpg", "a.png", "b.jpeg"):  # a.jpg and a.png share a stem
        Image.fromarray(np.full((240, 320, 3), 128, np.uint8)).save(src / name)

    b = mp.PackageBuilder(tmp / "pkg")
    for path in mp.find_images(src):
        image_id, rgb = b.add_image(path)
        h, w = rgb.shape[:2]
        m = np.zeros((h, w), np.uint8)
        m[20:120, 30:200] = 1
        b.add_annotation(image_id, "cardboard box", mp.mask_to_polygons(m), 0.42)
        c = np.zeros((h, w), np.uint8)
        c[150:220, 220:300] = 1
        for cm, area in mp.filter_candidates([c], [m], h * w):
            b.add_candidate(image_id, mp.mask_to_polygons(cm), area)
    check("empty polygon list is not added", b.add_annotation(1, "chair", [], 0.9) is None)
    zip_path = b.write(settings={"box_threshold": 0.35})

    check("zip written", zip_path.exists() and zip_path.suffix == ".zip")
    names = sorted(i["file_name"] for i in b.images)
    check(f"unique stems ({names})", len({Path(n).stem for n in names}) == 3)

    data = json.loads((tmp / "pkg" / "annotations.json").read_text(encoding="utf-8"))
    check("18 categories, misc_item last", len(data["categories"]) == 18 and data["categories"][-1]["name"] == "misc_item")
    check("candidate ids do not collide with object ids",
          not {a["id"] for a in data["annotations"]} & {c["id"] for c in data["candidates"]})

    pkg = Package(tmp / "pkg")  # our service's loader (also checks unique stems)
    check("service loads the package", len(pkg.images) == 3 and len(pkg.candidates[1]) == 1)
    store = ReviewStore(pkg, "tester")
    store.apply(1, pkg.annotations[1][0]["id"], "accept")
    store.apply(1, action="add", candidate_id=pkg.candidates[1][0]["id"],
                category_id=next(c["id"] for c in pkg.categories if c["name"] == "misc_item"))
    s = exporter.export(pkg, store, tmp / "export")
    check("export has no warnings (sizes match, polygons valid)", s["warnings"] == [])
    lines = (tmp / "export" / "labels" / f"{Path(pkg.images[1]['file_name']).stem}.txt").read_text().splitlines()
    check("box -> class 0, added candidate as misc_item -> class 17",
          sorted(int(l.split()[0]) for l in lines) == [0, 17])


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        test_polygons()
        test_nms()
        test_candidates()
        test_exif(tmp)
        test_package_end_to_end(tmp)
    finally:
        shutil.rmtree(tmp)
    print(f"\n{'all passed' if failures == 0 else f'{failures} failed'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
