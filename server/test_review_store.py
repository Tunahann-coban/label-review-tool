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
from review_store import MARK_FIELDS, ReviewError, ReviewStore  # noqa: E402

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
    untouched = [a["id"] for a in pkg.annotations[1] if a["id"] not in {o["ann_id"] for o in objects_before}]
    check("Tamamla -> reviewed, earlier decisions kept exactly",
          store.status(1) == "reviewed" and all(o in r["objects"] for o in objects_before))
    auto = [o for o in r["objects"] if o.get("auto_accepted")]
    check("Tamamla accepts every untouched object, marked as automatic",
          sorted(o["ann_id"] for o in auto) == sorted(untouched) and len(untouched) > 0
          and all(o["state"] == "accepted" and o["category_id"] == next(
              a["category_id"] for a in pkg.annotations[1] if a["id"] == o["ann_id"]) for o in auto))
    status_line = next(e for e in r["log"] if e["action"] == "status")
    check("status change is logged, with who did it",
          status_line == {"t": status_line["t"], "by": "tester", "action": "status", "from": "pending", "to": "reviewed"})
    check("each automatic accept is logged too, flagged as automatic",
          sum(1 for e in r["log"] if e.get("auto")) == len(untouched) and len(r["log"]) == log_before + 1 + len(untouched))
    check("automatic accepts are not counted as the reviewer's changes",
          labelers.row(pkg, store, 1)["changes"] == log_before)
    store.set_status(1, "pending")
    undone = store.load(1)
    check("taking it back to pending removes exactly the automatic accepts",
          not any(o.get("auto_accepted") for o in undone["objects"])
          and all(o in undone["objects"] for o in objects_before))
    store.set_status(1, "reviewed")
    kept = next(o for o in store.load(1)["objects"] if o.get("auto_accepted"))["ann_id"]
    store.apply(1, kept, "accept")  # the reviewer decides on one by hand afterwards
    store.set_status(1, "pending")
    check("an object the reviewer touched after finishing stays decided",
          any(o["ann_id"] == kept and o["state"] == "accepted" and "auto_accepted" not in o
              for o in store.load(1)["objects"]))
    store.apply(1, kept, "delete")
    store.set_status(1, "reviewed")
    check("a deleted object is not brought back by finishing",
          next(o for o in store.load(1)["objects"] if o["ann_id"] == kept)["state"] == "deleted")
    r = store.load(1)
    check("status_by / status_at record who finished the image and when",
          r["status_by"] == "tester" and r["status_at"] >= r["log"][0]["t"])
    check("every log line carries its author", all(e.get("by") == "tester" for e in r["log"]))
    mate = ReviewStore(pkg, "mehmet")  # a second person works on the same image later
    mate.apply(1, c, "accept")
    r2 = store.load(1)
    check("a second reviewer is named in the log, the first one is not overwritten",
          r2["log"][-1]["by"] == "mehmet" and r2["log"][0]["by"] == "tester")
    check("editing does not change who finished the image", r2["status_by"] == "tester" and r2["status_at"] == r["status_at"])
    check("editors listed in order", labelers.editors_of(r2) == ["tester", "mehmet"])
    mate.set_needs_edit(1, True)
    r3 = store.load(1)
    check("adding to the edit list records who and when, separate from the status",
          r3["needs_edit"] is True and r3["edit_by"] == "mehmet" and r3["status_by"] == "tester"
          and r3["status"] == "reviewed")
    check("the flag does not change the status, both are on at once",
          store.status(1) == "reviewed" and store.needs_edit(1) is True)
    check("flag change is logged with the author", r3["log"][-1] == {
        "t": r3["log"][-1]["t"], "by": "mehmet", "action": "flag", "from": False, "to": True})
    check("README field order kept after a status change", list(r)[:4] == ["image_id", "status", "reviewer", "updated"])
    check("editors do not include people who only moved the marks", labelers.editors_of(r3) == ["tester", "mehmet"])
    store.apply(1, c, "delete")
    check("editing keeps both marks", store.status(1) == "reviewed" and store.needs_edit(1) is True)
    n = len(store.load(1)["log"])
    store.set_marks(1, status="reviewed", needs_edit=True)
    check("same marks again writes nothing", len(store.load(1)["log"]) == n)
    store.set_needs_edit(1, False)
    check("taking it off the edit list keeps it done", store.status(1) == "reviewed" and store.needs_edit(1) is False)
    store.set_status(1, "pending")
    check("back to pending keeps decisions", store.status(1) == "pending" and len(store.load(1)["objects"]) >= 3)
    store.set_marks(1, status="reviewed", needs_edit=True)
    check("both marks in one call, one log line each",
          store.status(1) == "reviewed" and store.needs_edit(1) is True
          and store.load(1)["log"][-1]["action"] == "flag"
          and "status" in [e["action"] for e in store.load(1)["log"][-6:]])
    check("a flag alone on an untouched image creates its file, still pending",
          store.status(2) == "pending" and store.set_needs_edit(2, True) is not None
          and store.status(2) == "pending" and store.needs_edit(2) and store.load(2)["objects"] == [])
    check("nothing to change on an untouched image writes no file",
          store.set_marks(3, status="pending", needs_edit=False) is None and not store.path(3).exists()
          and not store.needs_edit(3))
    for label, kwargs in [("unknown status", dict(status="done")),
                          ("needs_edit as a status (it is a flag now)", dict(status="needs_edit")),
                          ("flag that is not a bool", dict(needs_edit="yes"))]:
        try:
            store.set_marks(1, **kwargs)
            check(f"rejects {label}", False)
        except ReviewError:
            check(f"rejects {label}", True)

    # a file written while needs_edit was a third status becomes: not finished + flagged
    legacy = store.load(2)
    legacy.pop("needs_edit")
    legacy.update(status="needs_edit", status_by="tester", status_at="2026-11-08T23:18:00")
    legacy.pop("edit_by", None)
    legacy.pop("edit_at", None)
    store._write(2, legacy)
    check("old 'needs_edit' status reads as pending + flagged",
          store.status(2) == "pending" and store.needs_edit(2) is True)
    check("... and its who / when move to the flag",
          store.load(2)["edit_by"] == "tester" and "status_by" not in store.load(2))
    store.set_needs_edit(2, False)

    old = store.load(1)
    old["status"] = "reviewed"
    for key in MARK_FIELDS:  # a file written before names were kept
        old.pop(key, None)
    for entry in old["log"]:
        entry.pop("by", None)
    store._write(1, old)
    check("old review files: reviewed still means done, not flagged",
          store.status(1) == "reviewed" and store.needs_edit(1) is False)
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
