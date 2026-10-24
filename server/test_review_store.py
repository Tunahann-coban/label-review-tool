"""Checks for review_store.py. Works on a temp copy, never touches your reviews.

Usage (from the project folder, after make_sample_data.py):
    .venv\\Scripts\\python server\\test_review_store.py
"""
import shutil
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from package import Package, merge_objects  # noqa: E402
from review_store import ReviewError, ReviewStore  # noqa: E402

SOURCE = Path(__file__).parent.parent / "sample_package"
failures = 0


def check(name, cond):
    global failures
    print("OK  " if cond else "FAIL", name)
    failures += not cond


def main():
    tmp = Path(tempfile.mkdtemp()) / "pkg"
    shutil.copytree(SOURCE, tmp, ignore=shutil.ignore_patterns("reviews"))
    try:
        run(tmp)
    finally:
        shutil.rmtree(tmp.parent)
    print(f"\n{'all passed' if failures == 0 else f'{failures} failed'}")
    sys.exit(1 if failures else 0)


def run(root):
    pkg = Package(root)
    store = ReviewStore(pkg, "tester")
    anns = pkg.annotations[1]
    a, b, c = (ann["id"] for ann in anns[:3])
    orig = anns[0]["category_id"]
    other = next(i for i in sorted(pkg.category_ids) if i != orig)

    def state():
        return {o["id"]: (o["state"], o["category_id"])
                for o in merge_objects(pkg.annotations[1], store.load(1))}

    check("untouched image is pending", store.status(1) == "pending")
    store.apply(1, a, "accept")
    check("accept -> accepted, image reviewed", state()[a] == ("accepted", orig) and store.status(1) == "reviewed")
    store.apply(1, a, "change", other)
    entry = next(o for o in store.load(1)["objects"] if o["ann_id"] == a)
    check("change -> changed with orig_category_id",
          entry == {"ann_id": a, "category_id": other, "state": "changed", "orig_category_id": orig})
    store.apply(1, a, "accept")
    check("accept keeps a changed class", state()[a] == ("changed", other))
    store.apply(1, a, "change", orig)
    check("change back to original -> accepted", state()[a] == ("accepted", orig))
    store.apply(1, b, "delete")
    check("delete -> deleted", state()[b][0] == "deleted")
    store.apply(1, b, "accept")
    check("accept on deleted restores it", state()[b][0] == "accepted")
    check("untouched object stays auto", state()[c][0] == "auto")

    review = store.load(1)
    check("README field order", list(review)[:4] == ["image_id", "status", "reviewer", "updated"])
    check("one entry per object", len(review["objects"]) == len({o["ann_id"] for o in review["objects"]}))
    check("every action logged", len(review["log"]) == 6)
    check("change log has from/to", review["log"][1]["from"] == orig and review["log"][1]["to"] == other)
    check("log keeps previous state", review["log"][1]["prev"]["state"] == "accepted")
    check("file named after image", store.path(1).name == Path(pkg.images[1]["file_name"]).stem + ".json")

    other_image_ann = pkg.annotations[2][0]["id"]
    for label, call in [("unknown object", lambda: store.apply(1, 9999, "accept")),
                        ("object of another image", lambda: store.apply(1, other_image_ann, "accept")),
                        ("unknown category", lambda: store.apply(1, a, "change", 999)),
                        ("unknown action", lambda: store.apply(1, a, "explode"))]:
        try:
            call()
            check(f"rejects {label}", False)
        except ReviewError:
            check(f"rejects {label}", True)

    before = len(store.load(1)["log"])
    threads = [threading.Thread(target=store.apply, args=(1, c, "accept")) for _ in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    check("40 parallel writes, none lost", len(store.load(1)["log"]) == before + 40)
    check("no temp file left", not any(p.suffix == ".tmp" for p in store.dir.iterdir()))
    check("other images still pending", store.status(2) == "pending")


if __name__ == "__main__":
    main()
