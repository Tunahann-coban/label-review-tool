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
import labelers  # noqa: E402
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
    check("accept -> accepted, image still pending until 'Tamamla'",
          state()[a] == ("accepted", orig) and store.status(1) == "pending")
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

    # --- adding from candidates (step 8) ---
    cand = pkg.candidates[1][0]
    cat = sorted(pkg.category_ids)[0]
    before = len(store.load(1)["log"])
    store.apply(1, action="add", candidate_id=cand["id"], category_id=cat)
    entry = next(o for o in store.load(1)["objects"] if o["ann_id"] == "new-1")
    check("add -> README format", entry == {"ann_id": "new-1", "category_id": cat, "state": "added",
                                            "from_candidate": cand["id"], "segmentation": cand["segmentation"]})
    merged = {o["id"]: o for o in merge_objects(pkg.annotations[1], store.load(1))}
    check("added object appears after pipeline objects", list(merged)[-1] == "new-1")
    check("added object has bbox, no score", merged["new-1"]["score"] is None and len(merged["new-1"]["bbox"]) == 4)
    try:
        store.apply(1, action="add", candidate_id=cand["id"], category_id=cat)
        check("same candidate cannot be added twice", False)
    except ReviewError:
        check("same candidate cannot be added twice", True)
    for label, kwargs in [("candidate of another image", dict(candidate_id=pkg.candidates[2][0]["id"], category_id=cat)),
                          ("add with unknown category", dict(candidate_id=pkg.candidates[1][1]["id"], category_id=999)),
                          ("add without category", dict(candidate_id=pkg.candidates[1][1]["id"]))]:
        try:
            store.apply(1, action="add", **kwargs)
            check(f"rejects {label}", False)
        except ReviewError:
            check(f"rejects {label}", True)

    other_cat = sorted(pkg.category_ids)[1]
    store.apply(1, "new-1", "change", other_cat)
    e = next(o for o in store.load(1)["objects"] if o["ann_id"] == "new-1")
    check("added object class change stays 'added'", e["state"] == "added" and e["category_id"] == other_cat)
    store.apply(1, "new-1", "delete")
    e = next(o for o in store.load(1)["objects"] if o["ann_id"] == "new-1")
    check("deleted added object keeps its shape", e["state"] == "deleted" and e["segmentation"] == cand["segmentation"])
    store.apply(1, "new-1", "accept")
    e = next(o for o in store.load(1)["objects"] if o["ann_id"] == "new-1")
    check("restore brings added object back", e["state"] == "added" and e["category_id"] == other_cat)
    store.apply(1, "new-1", "delete")
    store.apply(1, action="add", candidate_id=cand["id"], category_id=cat)
    ids = [o["ann_id"] for o in store.load(1)["objects"] if str(o["ann_id"]).startswith("new-")]
    check("re-adding a deleted candidate gets a new number, old one not reused", ids == ["new-1", "new-2"])
    log = store.load(1)["log"]
    check("add is logged with candidate and class", log[before]["action"] == "add" and log[before]["candidate"] == cand["id"])
    try:
        store.apply(1, "new-1", "accept")  # new-2 already uses the same candidate
        check("restoring cannot duplicate a re-added candidate", False)
    except ReviewError:
        live = [o["id"] for o in merge_objects(pkg.annotations[1], store.load(1))
                if o.get("from_candidate") == cand["id"] and o["state"] != "deleted"]
        check("restoring cannot duplicate a re-added candidate", live == ["new-2"])

    # --- image states ---
    objects_before = store.load(1)["objects"]
    log_before = len(store.load(1)["log"])
    store.set_status(1, "reviewed")
    r = store.load(1)
    check("Tamamla -> reviewed, decisions kept", store.status(1) == "reviewed" and r["objects"] == objects_before)
    check("status change is logged, with who did it", len(r["log"]) == log_before + 1
          and r["log"][-1] == {"t": r["log"][-1]["t"], "by": "tester", "action": "status",
                               "from": "pending", "to": "reviewed"})
    check("status_by / status_at record who finished the image and when",
          r["status_by"] == "tester" and r["status_at"] >= r["log"][0]["t"])
    check("every object change is logged with its author", all(e.get("by") == "tester" for e in r["log"]))
    mate = ReviewStore(pkg, "mehmet")  # a second person works on the same image later
    mate.apply(1, c, "accept")
    r2 = store.load(1)
    check("a second reviewer is named in the log, the first one is not overwritten",
          r2["log"][-1]["by"] == "mehmet" and r2["log"][0]["by"] == "tester")
    check("editing does not change who finished the image", r2["status_by"] == "tester" and r2["status_at"] == r["status_at"])
    check("editors listed in order", labelers.editors_of(r2) == ["tester", "mehmet"])
    mate.set_status(1, "needs_edit")
    check("moving it again records the new person", store.load(1)["status_by"] == "mehmet")
    store.set_status(1, "reviewed")  # back to the state the next checks expect
    check("README field order kept after a status change", list(r)[:4] == ["image_id", "status", "reviewer", "updated"])
    store.apply(1, c, "delete")
    check("editing a reviewed image keeps it reviewed", store.status(1) == "reviewed")
    store.set_status(1, "needs_edit")
    check("reviewed -> needs_edit", store.status(1) == "needs_edit")
    store.apply(1, c, "accept")
    check("editing a needs_edit image keeps it needs_edit", store.status(1) == "needs_edit")
    n = len(store.load(1)["log"])
    store.set_status(1, "needs_edit")
    check("same status again writes nothing", len(store.load(1)["log"]) == n)
    store.set_status(1, "pending")
    check("back to pending keeps decisions", store.status(1) == "pending" and len(store.load(1)["objects"]) >= 3)
    check("status of an untouched image can be set (creates its file)",
          store.status(2) == "pending" and store.set_status(2, "needs_edit") is not None
          and store.status(2) == "needs_edit" and store.load(2)["objects"] == [])
    check("setting pending on an untouched image writes no file",
          store.status(3) == "pending" and store.set_status(3, "pending") is None and not store.path(3).exists())
    try:
        store.set_status(1, "done")
        check("rejects unknown status", False)
    except ReviewError:
        check("rejects unknown status", True)
    old = store.load(1)
    old["status"] = "reviewed"  # a file written before needs_edit existed
    old.pop("status_by", None)
    old.pop("status_at", None)
    for entry in old["log"]:
        entry.pop("by", None)    # ... and before names were kept
    store._write(1, old)
    check("old review files: reviewed still means done", store.status(1) == "reviewed")
    check("old review files: the file's reviewer is shown, marked as an old record",
          labelers.editors_of(store.load(1)) == ["tester (eski kayıt)"])
    store.apply(1, c, "accept")
    check("old review files: saving again adds names to new log lines only",
          store.load(1)["log"][-1]["by"] == "tester" and "by" not in store.load(1)["log"][0]
          and "status_by" not in store.load(1))

    shutil.rmtree(store.dir)  # user resets reviews while the service runs
    check("reviews folder deleted -> image pending again", store.status(1) == "pending")
    store.apply(1, a, "accept")
    store.set_status(1, "reviewed")
    check("saving recreates a deleted reviews folder", store.status(1) == "reviewed")


if __name__ == "__main__":
    main()
