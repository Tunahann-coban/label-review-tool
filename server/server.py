"""Label review service.

Usage:  python server/server.py --package sample_package --reviewer tunahan
"""
import argparse

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import exporter
from package import Package, merge_objects
from review_store import ReviewError, ReviewStore

app = FastAPI(title="Label Review Tool")
pkg: Package = None  # set in main()
store: ReviewStore = None
export_dir = "export"


class Decision(BaseModel):
    action: str  # accept | change | delete | add
    ann_id: int | str | None = None  # pipeline id (int) or added object ("new-1"); not for add
    category_id: int | None = None   # change, add
    candidate_id: int | None = None  # add


def get_image_or_404(image_id):
    if image_id not in pkg.images:
        raise HTTPException(404, f"image {image_id} not found")


def image_detail(image_id):
    review = store.load(image_id)
    return {"image": pkg.images[image_id],
            "status": review["status"] if review else "pending",
            "objects": merge_objects(pkg.annotations.get(image_id, []), review),
            "candidates": pkg.candidates.get(image_id, [])}


@app.get("/api/package")
def package_info():
    images = [{"id": img["id"], "file_name": img["file_name"], "status": store.status(img["id"])}
              for img in pkg.images.values()]
    return {"categories": pkg.categories, "images": images}


@app.get("/api/images/{image_id}")
def get_image(image_id: int):
    get_image_or_404(image_id)
    return image_detail(image_id)


@app.get("/api/images/{image_id}/file")
def image_file(image_id: int):
    get_image_or_404(image_id)
    return FileResponse(pkg.image_path(image_id))


@app.post("/api/images/{image_id}/review")
def save_review(image_id: int, decision: Decision):
    get_image_or_404(image_id)
    try:
        store.apply(image_id, decision.ann_id, decision.action, decision.category_id, decision.candidate_id)
    except ReviewError as e:
        raise HTTPException(400, str(e))
    return image_detail(image_id)


@app.post("/api/export")
def export():
    with store.lock:  # no decision is half-saved while we read
        try:
            return exporter.export(pkg, store, export_dir)
        except exporter.ExportError as e:
            raise HTTPException(409, str(e))


def main():
    global pkg, store, export_dir
    parser = argparse.ArgumentParser(description="Label review service")
    parser.add_argument("--package", default="sample_package", help="package folder")
    parser.add_argument("--reviewer", default="unknown", help="reviewer name")
    parser.add_argument("--export", default="export", help="folder the YOLO dataset is written to")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    pkg = Package(args.package)
    store = ReviewStore(pkg, args.reviewer)
    export_dir = args.export
    print(f"package: {pkg.root} ({len(pkg.images)} images), reviewer: {args.reviewer}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
