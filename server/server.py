"""Label review service.

Usage:  python server/server.py --package sample_package --reviewer tunahan
"""
import argparse

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from package import Package

app = FastAPI(title="Label Review Tool")
pkg: Package = None  # set in main()


def get_image_or_404(image_id):
    if image_id not in pkg.images:
        raise HTTPException(404, f"image {image_id} not found")


@app.get("/api/package")
def package_info():
    return {"categories": pkg.categories, "images": pkg.image_list()}


@app.get("/api/images/{image_id}")
def image_detail(image_id: int):
    get_image_or_404(image_id)
    return pkg.image_detail(image_id)


@app.get("/api/images/{image_id}/file")
def image_file(image_id: int):
    get_image_or_404(image_id)
    return FileResponse(pkg.image_path(image_id))


def main():
    global pkg
    parser = argparse.ArgumentParser(description="Label review service")
    parser.add_argument("--package", default="sample_package", help="package folder")
    parser.add_argument("--reviewer", default="unknown", help="reviewer name")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    pkg = Package(args.package)
    print(f"package: {pkg.root} ({len(pkg.images)} images), reviewer: {args.reviewer}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
