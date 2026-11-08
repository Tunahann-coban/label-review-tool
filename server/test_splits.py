"""Checks for splits.py (train / val / test by storage unit).

Usage (from the project folder):
    .venv\\Scripts\\python server\\test_splits.py
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splits  # noqa: E402

failures = 0


def check(name, cond):
    global failures
    print("OK  " if cond else "FAIL", name)
    failures += not cond


def img(i, name, **extra):
    return {"id": i, "file_name": name, **extra}


def main():
    # --- unit of a photo ---
    check("unit from file name: up to the first '_'", splits.unit_of(img(1, "unit001_photo3.jpg")) == ("unit001", True))
    check("unit name: case and spaces ignored", splits.unit_of(img(1, "Unit001 _a.jpg")) == ("unit001", True))
    check("no '_' -> own unit, flagged unknown", splits.unit_of(img(1, "depo1.png")) == ("depo1", False))
    check("package 'unit' field wins over the name", splits.unit_of(img(1, "x_y.jpg", unit="Unit7")) == ("unit7", True))
    check("package 'unit': null -> own unit, unknown (even if the cleaned name has '_')",
          splits.unit_of(img(1, "depo_7_on.jpg", unit=None)) == ("depo_7_on", False))

    # --- assignment is frozen: changing it would silently move units between sets ---
    frozen = {"unit001": "train", "unit002": "train", "unit005": "test", "unit008": "test", "img": "train"}
    check(f"known units keep their set ({frozen})", all(splits.split_of(u) == s for u, s in frozen.items()))
    val_units = [u for u in (f"unit{i:03d}" for i in range(1, 200)) if splits.split_of(u) == "val"]
    check(f"val is reachable (first val units: {val_units[:3]})", len(val_units) > 10)
    counts = Counter(splits.split_of(f"unit{i:04d}") for i in range(3000))
    shares = {s: counts[s] / 30 for s in splits.SPLITS}
    check(f"about 70 / 15 / 15 over many units ({ {k: round(v, 1) for k, v in shares.items()} })",
          abs(shares["train"] - 70) < 3 and abs(shares["val"] - 15) < 3 and abs(shares["test"] - 15) < 3)

    # --- whole units, never split ---
    photos = [img(i, f"unit{u:03d}_p{k}.jpg") for i, (u, k) in enumerate(((u, k) for u in range(1, 41) for k in range(5)), 1)]
    by_image, units, warnings = splits.assign(photos)
    per_unit = {}
    for p in photos:
        per_unit.setdefault(splits.unit_of(p)[0], set()).add(by_image[p["id"]])
    check("every unit's photos land in one set", all(len(s) == 1 for s in per_unit.values()))
    check(f"40 units spread over all three sets ({units})", all(units[s] > 0 for s in splits.SPLITS))
    check("well-named photos: no warnings", warnings == [])
    adding = photos + [img(999, "unit041_p0.jpg")]
    check("adding a unit later moves no existing photo", all(splits.assign(adding)[0][p["id"]] == by_image[p["id"]] for p in photos))

    # --- warnings ---
    _, _, w = splits.assign([img(1, "depo1.png"), img(2, "depo2.png")])
    check("names without unit are reported", any("2 fotoğrafın adında ünite yok" in x for x in w))
    _, _, w = splits.assign([img(i, f"IMG_{1000 + i}.jpg") for i in range(6)])
    check("phone names (IMG_1234) -> one unit, reported", any("tek ünitede ('img')" in x for x in w))
    check("  and empty sets reported", any("kümesi boş" in x for x in w))
    check("no photos -> nothing to report", splits.assign([])[2] == [])

    print(f"\n{'all passed' if failures == 0 else f'{failures} failed'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
