"""Checks for exporter.py. Works on a temp copy, never touches your data.

The copy is made harder on purpose: categories are reversed (so class index != id - 1),
names need YAML quoting, one mask leaves the image, one object has two parts,
one polygon is invalid and one image has a wrong size in annotations.json.

Usage (from the project folder, after make_sample_data.py):
    .venv\\Scripts\\python server\\test_exporter.py
"""
import filecmp
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import exporter  # noqa: E402
from package import Package  # noqa: E402
from review_store import ReviewStore  # noqa: E402

SOURCE = Path(__file__).parent.parent / "sample_package"
failures = 0


def check(name, cond):
    global failures
    print("OK  " if cond else "FAIL", name)
    failures += not cond


def make_package(root):
    shutil.copytree(SOURCE, root, ignore=shutil.ignore_patterns("reviews"))
    data = json.loads((root / "annotations.json").read_text(encoding="utf-8"))
    data["categories"].reverse()  # index no longer equals id - 1
    data["categories"][0]["name"] = "a: b # c"
    data["categories"][1]["name"] = "yes"
    anns1 = [a for a in data["annotations"] if a["image_id"] == 1]
    anns1[2]["segmentation"][0][0] = -40.0       # leaves the image on the left
    anns1[2]["segmentation"][0][1] = 9999.0      # and at the bottom
    anns1[3]["segmentation"].append([10, 10, 60, 10, 60, 60, 10, 60])  # second part
    anns1[4]["segmentation"].append([1, 2, 3, 4])                     # invalid part
    data["images"][1]["width"] = 640             # img_002: wrong size on purpose
    (root / "annotations.json").write_text(json.dumps(data), encoding="utf-8")


def read_labels(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        rows.append((int(parts[0]), [float(v) for v in parts[1:]], parts[1:]))
    return rows


def fill(polygon, w=200, h=120):
    """Pixels inside a flat polygon, the way a YOLO loader rasterizes it."""
    from PIL import Image, ImageDraw
    im = Image.new("1", (w, h), 0)
    ImageDraw.Draw(im).polygon(list(zip(polygon[0::2], polygon[1::2])), fill=1)
    return {(x, y) for y in range(h) for x in range(w) if im.getpixel((x, y))}


def test_merge_parts():
    a = [10, 10, 60, 10, 60, 50, 10, 50]           # left box
    b = [120, 20, 180, 20, 180, 90, 120, 90]       # right box, a gap between
    c = [70, 95, 100, 95, 100, 115, 70, 115]       # small one below
    check("single part returned unchanged", exporter.merge_parts([a]) == a)
    for parts in ([a, b], [a, b, c], [c, a, b], [b, c, a]):
        merged = exporter.merge_parts(parts)
        union = set().union(*(fill(p) for p in parts))
        got = fill(merged)
        extra, missing = len(got - union), len(union - got)
        # zero-width bridges may light a thin line of pixels; the gap itself stays empty
        check(f"merge of {len(parts)} parts fills their union (extra {extra} px, missing {missing} px)",
              missing <= 4 and extra <= 3 * 60)
        gap = {(x, 85) for x in range(65, 115)}   # a strip between the boxes
        check(f"  gap between parts not filled ({len(got & gap)} px of {len(gap)})", len(got & gap) <= 3)


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        test_merge_parts()
        run(tmp)
    finally:
        shutil.rmtree(tmp)
    print(f"\n{'all passed' if failures == 0 else f'{failures} failed'}")
    sys.exit(1 if failures else 0)


def run(tmp):
    make_package(tmp / "pkg")
    pkg = Package(tmp / "pkg")
    store = ReviewStore(pkg, "tester")
    out = tmp / "export"
    cats = pkg.categories
    index_of = {c["id"]: i for i, c in enumerate(cats)}

    anns1 = pkg.annotations[1]
    changed, deleted = anns1[0], anns1[1]
    new_cat = next(c["id"] for c in cats if c["id"] != changed["category_id"])
    store.apply(1, changed["id"], "change", new_cat)
    store.apply(1, deleted["id"], "delete")
    for a in pkg.annotations[2]:  # img_002: every object deleted
        store.apply(2, a["id"], "delete")
    # img_003 stays pending
    added_cand, removed_cand = pkg.candidates[1][0], pkg.candidates[1][1]
    added_cat = cats[2]["id"]
    store.apply(1, action="add", candidate_id=added_cand["id"], category_id=added_cat)    # new-1, kept
    store.apply(1, action="add", candidate_id=removed_cand["id"], category_id=added_cat)  # new-2
    store.apply(1, "new-2", "delete")                                                       # removed again

    p = exporter.preview(pkg, store, out)
    check("preview writes nothing", not out.exists() and not (tmp / "export.tmp").exists())
    s = exporter.export(pkg, store, out)
    check("preview numbers equal the real export", p == s)
    untouched = sum(1 for a in anns1 if a["id"] not in (changed["id"], deleted["id"]))
    check(f"untouched objects counted ({untouched})", s["untouched_objects"] == untouched)
    check("pending images counted", s["pending_images"] == 1)

    # --- layout ---
    check("only reviewed images copied", sorted(p.name for p in (out / "images").iterdir()) == ["img_001.jpg", "img_002.jpg"])
    check("one label per reviewed image", sorted(p.name for p in (out / "labels").iterdir()) == ["img_001.txt", "img_002.txt"])
    check("pending image left out", not (out / "labels" / "img_003.txt").exists())
    check("images copied byte for byte", filecmp.cmp(out / "images" / "img_001.jpg", tmp / "pkg" / "images" / "img_001.jpg", shallow=False))
    check("no temp folders left", not (tmp / "export.tmp").exists() and not (tmp / "export.old").exists())

    # --- data.yaml ---
    yaml = (out / "data.yaml").read_text(encoding="utf-8").splitlines()
    names = [json.loads(line.strip()[2:]) for line in yaml[yaml.index("names:") + 1:]]
    check("names in categories order", names == [c["name"] for c in cats])
    check("special names are quoted", '  - "a: b # c"' in yaml and '  - "yes"' in yaml)
    check("nc matches", f"nc: {len(cats)}" in yaml)

    # --- img_001 labels ---
    rows = read_labels(out / "labels" / "img_001.txt")
    w, h = pkg.images[1]["width"], pkg.images[1]["height"]
    kept = [a for a in anns1 if a["id"] != deleted["id"]]
    expected_lines = len(kept) + 1  # one line per object, parts merged; + the added one
    check("one line per object: deleted left out, parts merged, added one in", len(rows) == expected_lines)
    check("added object written last with its class index", rows[-1][0] == index_of[added_cat])
    check("added-then-deleted object left out", len(rows) == expected_lines)
    check("changed object uses new class index", rows[0][0] == index_of[new_cat])
    check("untouched object uses its class index (not id - 1)",
          rows[1][0] == index_of[kept[1]["category_id"]] and index_of[kept[1]["category_id"]] != kept[1]["category_id"] - 1)
    check("all values within 0-1", all(0 <= v <= 1 for _, vals, _ in rows for v in vals))
    check("6 decimals", all(len(t.split(".")[1]) == 6 for _, _, raw in rows for t in raw))
    check("x, y pairs with at least 3 points", all(len(vals) % 2 == 0 and len(vals) >= 6 for _, vals, _ in rows))

    # round trip: back to pixels must match the source (after clamping to the image)
    valid = lambda segs: [p for p in segs if len(p) >= 6 and len(p) % 2 == 0]  # noqa: E731
    src_polys = [exporter.merge_parts(valid(a["segmentation"])) for a in kept]
    src_polys.append(exporter.merge_parts(added_cand["segmentation"]))
    check("one source polygon per line", len(src_polys) == len(rows))
    two_part = next(a for a in kept if len(valid(a["segmentation"])) == 2)
    merged_line = rows[[a["id"] for a in kept].index(two_part["id"])][1]
    check("two-part object written as one line holding both parts' points",
          len(merged_line) // 2 >= sum(len(p) // 2 for p in valid(two_part["segmentation"])))
    worst = 0.0
    for (_, vals, _), poly in zip(rows, src_polys):
        for i in range(0, len(poly), 2):
            x, y = min(max(poly[i], 0), w), min(max(poly[i + 1], 0), h)
            worst = max(worst, abs(vals[i] * w - x), abs(vals[i + 1] * h - y))
    check(f"round trip back to pixels (worst error {worst:.4f} px)", worst < 0.01)
    check("point outside image clamped to edge", rows[1][1][0] == 0.0 and rows[1][1][1] == 1.0)

    # --- img_002 ---
    check("all objects deleted -> empty label file", (out / "labels" / "img_002.txt").read_text() == "")

    # --- summary ---
    check("summary counts", s["images"] == 2 and s["empty_images"] == 1 and s["objects"] == len(kept) + 1)
    check("per class counts add up", sum(c["count"] for c in s["per_class"]) == s["objects"])
    w_text = " | ".join(s["warnings"])
    check("warns about size mismatch", "img_002.jpg: annotations.json boyutu 640x600, dosya 800x600" in w_text)
    check("warns about two-part object", "2 parçalı, tek satırda birleştirildi" in w_text)
    check("warns about invalid polygon", "geçersiz çokgen (4 değer)" in w_text)

    # --- re-export removes stale files ---
    (tmp / "pkg" / "reviews" / "img_002.json").unlink()  # img_002 back to pending
    exporter.export(pkg, store, out)
    check("re-export drops files of images no longer reviewed",
          not (out / "labels" / "img_002.txt").exists() and not (out / "images" / "img_002.jpg").exists())

    # --- safety ---
    foreign = tmp / "not_ours"
    foreign.mkdir()
    (foreign / "thesis.docx").write_text("important")
    try:
        exporter.export(pkg, store, foreign)
        check("refuses to overwrite a folder it did not create", False)
    except exporter.ExportError:
        check("refuses to overwrite a folder it did not create", (foreign / "thesis.docx").read_text() == "important")

    # --- duplicate stems are refused at load ---
    data = json.loads((tmp / "pkg" / "annotations.json").read_text(encoding="utf-8"))
    data["images"].append({"id": 99, "file_name": "img_001.png", "width": 800, "height": 600})
    (tmp / "pkg" / "annotations.json").write_text(json.dumps(data), encoding="utf-8")
    try:
        Package(tmp / "pkg")
        check("duplicate file stem refused", False)
    except ValueError as e:
        check(f"duplicate file stem refused ({e})", True)


if __name__ == "__main__":
    main()
