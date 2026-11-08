"""Checks for exporter.py. Works on a temp copy, never touches your data.

The copy is made harder on purpose: categories are reversed (so class index != id - 1),
names need YAML quoting, one mask leaves the image, one object has two parts,
one polygon is invalid and one image has a wrong size in annotations.json.

Usage (from the project folder, after make_sample_data.py):
    .venv\\Scripts\\python server\\test_exporter.py
"""
import csv
import filecmp
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import coco_exporter  # noqa: E402
import edit_exporter  # noqa: E402
import exporter  # noqa: E402
import labelers  # noqa: E402
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


def test_unit_split_export(tmp):
    """30 storage units, 2 photos each: sets get whole units, YOLO and COCO agree."""
    import coco_exporter
    import splits
    from PIL import Image as PILImage
    root = tmp / "units"
    (root / "images").mkdir(parents=True)
    images, anns = [], []
    for u in range(1, 31):
        for k in range(2):
            i = len(images) + 1
            name = f"unit{u:03d}_photo{k}.jpg"
            PILImage.new("RGB", (64, 48), (90, 90, 90)).save(root / "images" / name)
            images.append({"id": i, "file_name": name, "width": 64, "height": 48})
            anns.append({"id": i, "image_id": i, "category_id": 1, "bbox": [5, 5, 20, 20],
                         "segmentation": [[5, 5, 25, 5, 25, 25, 5, 25]], "score": 0.9})
    (root / "annotations.json").write_text(json.dumps(
        {"categories": [{"id": 1, "name": "chair"}], "images": images, "annotations": anns,
         "candidates": []}), encoding="utf-8")
    pkg = Package(root)
    store = ReviewStore(pkg, "tester")
    for img in images:
        store.apply(img["id"], img["id"], "accept")
        store.set_status(img["id"], "reviewed")

    s = exporter.export(pkg, store, tmp / "units_export")
    out = tmp / "units_export"
    on_disk = {sp: sorted(p.name for p in (out / "images" / sp).iterdir()) for sp in splits.SPLITS
               if (out / "images" / sp).exists()}
    expected = {}
    for img in images:
        expected.setdefault(splits.split_of(img["file_name"].split("_")[0]), []).append(img["file_name"])
    check(f"photos sit in their unit's set ({ {k: len(v) for k, v in on_disk.items()} })",
          on_disk == {k: sorted(v) for k, v in expected.items()})
    unit_sets = {}
    for sp, names in on_disk.items():
        for n in names:
            unit_sets.setdefault(n.split("_")[0], set()).add(sp)
    check("no unit split across sets", all(len(v) == 1 for v in unit_sets.values()))
    check("labels next to their images", all((out / "labels" / sp / (Path(n).stem + ".txt")).exists()
                                             for sp, names in on_disk.items() for n in names))
    yaml = (out / "data.yaml").read_text(encoding="utf-8")
    check("data.yaml lists train, val and test", all(f"{k}: images/{k}\n" in yaml for k in ("train", "val", "test")))
    check("summary units add up to 30", sum(v["units"] for v in s["splits"].values()) == 30)
    check("well-named units: no split warnings", not any("ünite" in w or "boş" in w for w in s["warnings"]))

    c = coco_exporter.export_coco(pkg, store, tmp / "units_coco")
    files = sorted(p.name for p in (tmp / "units_coco").iterdir())
    check(f"COCO: one file per set, plus the labelers table ({files})",
          files == ["instances_test.json", "instances_train.json", "instances_val.json", "labelers.csv"])
    table = (tmp / "units_coco" / "labelers.csv").read_text(encoding="utf-8-sig").splitlines()
    check("labelers.csv: header and one row per exported photo",
          table[0] == ",".join(labelers.COLUMNS) and len(table) == 1 + len(images))
    coco_names = {sp: sorted(i["file_name"] for i in json.loads(
        (tmp / "units_coco" / f"instances_{sp}.json").read_text(encoding="utf-8"))["images"]) for sp in on_disk}
    check("COCO sets hold the same photos as YOLO sets", coco_names == on_disk)
    check("COCO and YOLO summaries agree per set", c["splits"] == s["splits"])


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        test_merge_parts()
        test_unit_split_export(tmp)
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
    store.set_status(1, "reviewed")  # "Tamamla" on img_001 and img_002; img_003 stays pending
    store.set_status(2, "reviewed")

    p = exporter.preview(pkg, store, out)
    check("preview writes nothing", not out.exists() and not (tmp / "export.tmp").exists())
    s = exporter.export(pkg, store, out)
    check("preview numbers equal the real export", p == s)
    untouched = sum(1 for a in anns1 if a["id"] not in (changed["id"], deleted["id"]))
    check(f"untouched objects counted ({untouched})", s["untouched_objects"] == untouched)
    check("pending images counted", s["pending_images"] == 1)

    # --- layout ---
    check("only reviewed images copied", sorted(p.name for p in (out / "images" / "train").iterdir()) == ["img_001.jpg", "img_002.jpg"])
    check("one label per reviewed image", sorted(p.name for p in (out / "labels" / "train").iterdir()) == ["img_001.txt", "img_002.txt"])
    check("pending image left out", not (out / "labels" / "train" / "img_003.txt").exists())
    check("images copied byte for byte", filecmp.cmp(out / "images" / "train" / "img_001.jpg", tmp / "pkg" / "images" / "img_001.jpg", shallow=False))
    check("no temp folders left", not (tmp / "export.tmp").exists() and not (tmp / "export.old").exists())

    # --- data.yaml ---
    yaml = (out / "data.yaml").read_text(encoding="utf-8").splitlines()
    names = [json.loads(line.strip()[2:]) for line in yaml[yaml.index("names:") + 1:]]
    check("names in categories order", names == [c["name"] for c in cats])
    check("special names are quoted", '  - "a: b # c"' in yaml and '  - "yes"' in yaml)
    check("nc matches", f"nc: {len(cats)}" in yaml)
    # img_001 / img_002 / img_003 share the unit "img": one unit, so everything is train
    check("data.yaml points to the train set", "train: images/train" in yaml)
    check("no val units: val falls back to train, said in data.yaml", any(l.startswith("val: images/train  # NO validation") for l in yaml))
    check("no test units: no test line", not any(l.startswith("test:") for l in yaml))
    check("only the train folders exist", sorted(p.name for p in (out / "images").iterdir()) == ["train"])
    check("summary per set", s["splits"]["train"]["images"] == 2 and s["splits"]["train"]["units"] == 1
          and s["splits"]["val"]["images"] == 0)
    w_all = " | ".join(s["warnings"])
    check("one-unit and empty-set warnings shown", "tek ünitede ('img')" in w_all and "doğrulama kümesi boş" in w_all)

    # --- img_001 labels ---
    rows = read_labels(out / "labels" / "train" / "img_001.txt")
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
    check("all objects deleted -> empty label file", (out / "labels" / "train" / "img_002.txt").read_text() == "")

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
          not (out / "labels" / "train" / "img_002.txt").exists() and not (out / "images" / "train" / "img_002.jpg").exists())

    # --- images marked "needs editing" ---
    store.set_status(2, "reviewed")
    store.set_status(3, "needs_edit")
    store.apply(3, pkg.annotations[3][0]["id"], "delete")  # a deleted object must stay out of the edit export
    s2 = exporter.export(pkg, store, out)
    check("needs_edit image is not in the YOLO export",
          sorted(p.name for p in (out / "images" / "train").iterdir()) == ["img_001.jpg", "img_002.jpg"])
    check("needs_edit counted separately, still part of 'not done'",
          s2["needs_edit_images"] == 1 and s2["pending_images"] == 1)
    check("COCO summary counts it too", coco_exporter.preview_coco(pkg, store, tmp / "c")["needs_edit_images"] == 1)

    edit_out = tmp / "export_duzenlenecek"
    pv = edit_exporter.preview(pkg, store, edit_out)
    check("edit preview writes nothing", not edit_out.exists())
    ev = edit_exporter.export(pkg, store, edit_out)
    check("edit preview numbers equal the real export", pv == ev)
    check("edit folder holds the photo and the COCO file",
          sorted(p.name for p in edit_out.iterdir() if p.name != exporter.MARKER)
          == ["_annotations.coco.json", "img_003.jpg", "labelers.csv"])
    rows = list(csv.DictReader((edit_out / "labelers.csv").read_text(encoding="utf-8-sig").splitlines()))
    check("edit export: labelers.csv names who marked the photo",
          [(r["image"], r["status"], r["status_by"]) for r in rows] == [("img_003.jpg", "needs_edit", "tester")]
          and rows[0]["editors"] == "tester" and rows[0]["changes"] == "1")
    yolo_rows = list(csv.DictReader((out / "labelers.csv").read_text(encoding="utf-8-sig").splitlines()))
    check("YOLO export: labelers.csv holds the exported photos only",
          sorted(r["image"] for r in yolo_rows) == ["img_001.jpg", "img_002.jpg"]
          and all(r["status"] == "reviewed" and r["status_by"] == "tester" for r in yolo_rows))
    check("labelers.csv opens in Excel with Turkish letters (BOM)",
          (out / "labelers.csv").read_bytes().startswith(b"\xef\xbb\xbf"))
    coco = json.loads((edit_out / "_annotations.coco.json").read_text(encoding="utf-8"))
    kept3 = len(pkg.annotations[3]) - 1
    check("COCO: one image, deleted object left out, bbox and area present",
          [i["file_name"] for i in coco["images"]] == ["img_003.jpg"] and len(coco["annotations"]) == kept3
          and all(a["bbox"] and a["area"] > 0 and a["image_id"] == 3 for a in coco["annotations"]))
    check("COCO: categories like the package", [c["name"] for c in coco["categories"]] == [c["name"] for c in pkg.categories])
    check("edit summary counts", ev["images"] == 1 and ev["objects"] == kept3 and ev["empty_images"] == 0)
    check("photo copied byte for byte", filecmp.cmp(edit_out / "img_003.jpg", tmp / "pkg" / "images" / "img_003.jpg", shallow=False))
    store.set_status(3, "reviewed")
    ev = edit_exporter.export(pkg, store, edit_out)
    check("re-export with nothing marked leaves an empty folder, no stale photo",
          ev["images"] == 0 and not (edit_out / "img_003.jpg").exists())
    try:
        edit_exporter.export(pkg, store, tmp / "pkg")
        check("edit export refuses a folder it did not create", False)
    except exporter.ExportError:
        check("edit export refuses a folder it did not create", (tmp / "pkg" / "annotations.json").exists())
    store.set_status(3, "pending")

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
