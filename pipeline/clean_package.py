"""Cleans an existing package with the same rules the notebook now applies, so a
package made before those rules does not need a new Kaggle run.

    .venv\\Scripts\\python pipeline\\clean_package.py packages\\bidvision_pilot_raw packages\\bidvision_pilot

The source package is not changed. The cleaned one gets the same images; what was
removed, and why, is written into its annotations.json under info.cleaning.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import make_package as mp  # noqa: E402


def clean(src, dest, object_iou=0.7):
    src, dest = Path(src), Path(dest)
    if dest.resolve() == src.resolve():
        raise ValueError("destination must differ from the source package")
    data = json.loads((src / "annotations.json").read_text(encoding="utf-8"))
    names = {c["id"]: c["name"] for c in data["categories"]}
    kept_anns, kept_cands, removed = [], [], []

    for img in data["images"]:
        w, h = img["width"], img["height"]
        anns = [a for a in data["annotations"] if a["image_id"] == img["id"]]
        masks = [mp.polygons_to_mask(a["segmentation"], w, h) for a in anns]
        keep = set(mp.dedupe_objects(masks, [a["score"] for a in anns], object_iou))
        for i, a in enumerate(anns):
            if i in keep:
                kept_anns.append(a)
                continue
            twin = anns[max(keep, key=lambda k: mp.mask_iou(masks[i], masks[k]))]
            removed.append({"image": img["file_name"], "id": a["id"], "kind": "object",
                            "class": names[a["category_id"]], "score": a["score"],
                            "reason": f"duplicate of #{twin['id']} {names[twin['category_id']]} {twin['score']}"})

        object_masks = [masks[i] for i in sorted(keep)]
        cands = [c for c in data["candidates"] if c["image_id"] == img["id"]]
        cand_masks = [mp.polygons_to_mask(c["segmentation"], w, h) for c in cands]
        survivors = set(mp.candidate_indexes(cand_masks, object_masks, w * h))
        for i, c in enumerate(cands):
            if i in survivors:
                kept_cands.append(c)
            else:
                removed.append({"image": img["file_name"], "id": c["id"], "kind": "candidate",
                                "reason": "speck, too big, covered by an object, near copy or over the limit"})

    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src / "images", dest / "images")
    info = dict(data.get("info", {}))
    info["cleaning"] = {"from": str(src), "object_mask_iou": object_iou,
                        "candidates": "min 0.5 % / max 30 % of image, near copies dropped, max 20",
                        "removed": removed}
    out = dict(data, info=info, annotations=kept_anns, candidates=kept_cands)
    (dest / "annotations.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return {"objects": (len(data["annotations"]), len(kept_anns)),
            "candidates": (len(data["candidates"]), len(kept_cands)), "removed": removed}


if __name__ == "__main__":
    r = clean(sys.argv[1], sys.argv[2])
    print(f"objects:    {r['objects'][0]} -> {r['objects'][1]}")
    print(f"candidates: {r['candidates'][0]} -> {r['candidates'][1]}")
    for x in r["removed"]:
        if x["kind"] == "object":
            print(f"  removed {x['image']} #{x['id']} {x['class']} {x['score']}: {x['reason']}")
