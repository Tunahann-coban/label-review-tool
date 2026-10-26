"""Label review service.

Usage (with existing package):
    python server/server.py --package sample_package --reviewer tunahan

Usage (registry mode, home page picks the project):
    python server/server.py
"""
import argparse
import json
import re
import shutil
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image as PillowImage
from pydantic import BaseModel

import coco_exporter
import exporter
from package import Package, merge_objects
from project_registry import ProjectRegistry
from review_store import ReviewError, ReviewStore

app = FastAPI(title="Label Review Tool")


class ActiveProject:
    def __init__(self, pkg: Package, store: ReviewStore, export_dir: str):
        self.pkg = pkg
        self.store = store
        self.export_dir = export_dir


active: ActiveProject | None = None
registry: ProjectRegistry | None = None
projects_root: str = "projects"


# ── helpers ────────────────────────────────────────────────────────────────

class Decision(BaseModel):
    action: str
    ann_id: int | str | None = None
    category_id: int | None = None
    candidate_id: int | None = None


def get_active() -> ActiveProject:
    if active is None:
        raise HTTPException(503, "aktif proje yok — ana sayfadan bir proje seç")
    return active


def get_image_or_404(pkg, image_id):
    if image_id not in pkg.images:
        raise HTTPException(404, f"image {image_id} not found")


def image_detail(pkg, store, image_id):
    review = store.load(image_id)
    return {
        "image": pkg.images[image_id],
        "status": review["status"] if review else "pending",
        "objects": merge_objects(pkg.annotations.get(image_id, []), review),
        "candidates": pkg.candidates.get(image_id, []),
    }


def _project_with_progress(project: dict) -> dict:
    try:
        pkg = Package(project["path"])
        store = ReviewStore(pkg, project["reviewer"])
        total = len(pkg.images)
        reviewed = sum(1 for img_id in pkg.images if store.status(img_id) == "reviewed")
        return {
            **project,
            "is_active": registry.get_active_id() == project["id"],
            "progress": {"reviewed": reviewed, "total": total},
            "valid": True,
            "error": None,
        }
    except Exception as e:
        return {
            **project,
            "is_active": registry.get_active_id() == project["id"],
            "progress": {"reviewed": 0, "total": 0},
            "valid": False,
            "error": str(e),
        }


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:48] or "project"


# ── existing review endpoints ──────────────────────────────────────────────

@app.get("/api/package")
def package_info():
    a = get_active()
    images = [
        {"id": img["id"], "file_name": img["file_name"], "status": a.store.status(img["id"])}
        for img in a.pkg.images.values()
    ]
    return {"categories": a.pkg.categories, "images": images}


@app.get("/api/images/{image_id}")
def get_image(image_id: int):
    a = get_active()
    get_image_or_404(a.pkg, image_id)
    return image_detail(a.pkg, a.store, image_id)


@app.get("/api/images/{image_id}/file")
def image_file(image_id: int):
    a = get_active()
    get_image_or_404(a.pkg, image_id)
    return FileResponse(a.pkg.image_path(image_id))


@app.post("/api/images/{image_id}/review")
def save_review(image_id: int, decision: Decision):
    a = get_active()
    get_image_or_404(a.pkg, image_id)
    try:
        a.store.apply(image_id, decision.ann_id, decision.action, decision.category_id, decision.candidate_id)
    except ReviewError as e:
        raise HTTPException(400, str(e))
    return image_detail(a.pkg, a.store, image_id)


# ── YOLO export ────────────────────────────────────────────────────────────

@app.get("/api/export/preview")
def export_preview():
    a = get_active()
    with a.store.lock:
        return exporter.preview(a.pkg, a.store, a.export_dir)


@app.post("/api/export")
def do_export():
    a = get_active()
    with a.store.lock:
        try:
            return exporter.export(a.pkg, a.store, a.export_dir)
        except exporter.ExportError as e:
            raise HTTPException(409, str(e))


# ── COCO export ────────────────────────────────────────────────────────────

@app.get("/api/export/coco/preview")
def coco_preview():
    a = get_active()
    with a.store.lock:
        return coco_exporter.preview_coco(a.pkg, a.store, a.export_dir)


@app.post("/api/export/coco")
def do_coco_export():
    a = get_active()
    with a.store.lock:
        return coco_exporter.export_coco(a.pkg, a.store, a.export_dir)


# ── project management ─────────────────────────────────────────────────────

@app.get("/api/projects")
def list_projects():
    return [_project_with_progress(p) for p in registry.list_projects()]


class ProjectCreate(BaseModel):
    name: str
    path: str
    reviewer: str
    export_dir: str = "export"


@app.post("/api/projects")
def create_project(body: ProjectCreate):
    resolved = str(Path(body.path).resolve())
    if registry.get_by_path(resolved):
        raise HTTPException(409, "bu klasör zaten kayıtlı")
    try:
        Package(resolved)  # validate
    except Exception as e:
        raise HTTPException(422, f"paket yüklenemedi: {e}")
    project = registry.add_project(body.name, resolved, body.reviewer, body.export_dir)
    return _project_with_progress(project)


# upload must be defined before /{project_id}/activate to avoid path shadowing
@app.post("/api/projects/upload")
async def upload_project(
    name: str = Form(...),
    reviewer: str = Form(...),
    images: List[UploadFile] = File(...),
    annotations: UploadFile | None = File(None),
):
    if not images:
        raise HTTPException(400, "en az bir resim gerekli")
    filenames = [f.filename for f in images]
    stems = [Path(fn).stem for fn in filenames]
    if len(stems) != len(set(stems)):
        raise HTTPException(400, "yüklenen resimler arasında tekrarlayan dosya adı var")

    slug = _slugify(name)
    pkg_dir = Path(projects_root) / slug
    counter = 1
    while pkg_dir.exists():
        pkg_dir = Path(projects_root) / f"{slug}-{counter}"
        counter += 1
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "images").mkdir()

    try:
        image_entries = []
        for i, upload in enumerate(images):
            dest = pkg_dir / "images" / upload.filename
            content = await upload.read()
            dest.write_bytes(content)
            with PillowImage.open(dest) as im:
                w, h = im.size
            image_entries.append({"id": i + 1, "file_name": upload.filename, "width": w, "height": h})

        if annotations:
            ann_bytes = await annotations.read()
            try:
                ann_data = json.loads(ann_bytes)
            except json.JSONDecodeError as e:
                raise HTTPException(400, f"annotations.json geçersiz JSON: {e}")
            for key in ("categories", "images", "annotations"):
                if key not in ann_data:
                    raise HTTPException(400, f"annotations.json eksik alan: '{key}'")
            (pkg_dir / "annotations.json").write_bytes(ann_bytes)
        else:
            ann_data = {
                "info": {"version": 1, "note": "label-review-tool tarafından oluşturuldu"},
                "categories": [],
                "images": image_entries,
                "annotations": [],
                "candidates": [],
            }
            (pkg_dir / "annotations.json").write_text(
                json.dumps(ann_data, ensure_ascii=False, indent=1), encoding="utf-8"
            )

        Package(pkg_dir)  # validate
        project = registry.add_project(name, str(pkg_dir), reviewer)
        return _project_with_progress(project)

    except HTTPException:
        shutil.rmtree(pkg_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(pkg_dir, ignore_errors=True)
        raise HTTPException(500, str(e))


@app.post("/api/projects/{project_id}/activate")
def activate_project(project_id: str):
    global active
    project = registry.get_project(project_id)
    if not project:
        raise HTTPException(404, "proje bulunamadı")
    try:
        new_pkg = Package(project["path"])
        new_store = ReviewStore(new_pkg, project["reviewer"])
        active = ActiveProject(new_pkg, new_store, project["export_dir"])
        registry.set_active(project_id)
    except Exception as e:
        raise HTTPException(422, f"proje açılamadı: {e}")
    return {"active_id": project_id, "name": project["name"]}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    if not registry.get_project(project_id):
        raise HTTPException(404, "proje bulunamadı")
    registry.remove_project(project_id)
    return Response(status_code=204)


# ── startup ────────────────────────────────────────────────────────────────

def main():
    global active, registry, projects_root
    parser = argparse.ArgumentParser(description="Label review service")
    parser.add_argument("--package", default=None,
                        help="package folder (optional if registry has an active project)")
    parser.add_argument("--reviewer", default="unknown", help="reviewer name")
    parser.add_argument("--export", default="export", help="YOLO dataset output folder")
    parser.add_argument("--registry", default="projects.json", help="path to projects registry JSON")
    parser.add_argument("--projects-dir", default="projects", dest="projects_dir",
                        help="root folder for newly uploaded projects")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    registry = ProjectRegistry(args.registry)
    projects_root = args.projects_dir

    if args.package:
        resolved = str(Path(args.package).resolve())
        existing = registry.get_by_path(resolved)
        if existing:
            project = existing
        else:
            project = registry.add_project(Path(args.package).name, resolved, args.reviewer, args.export)
        registry.set_active(project["id"])
        pkg = Package(project["path"])
        store = ReviewStore(pkg, project["reviewer"])
        active = ActiveProject(pkg, store, project["export_dir"])
        print(f"package: {pkg.root} ({len(pkg.images)} images), reviewer: {project['reviewer']}", flush=True)
    else:
        active_id = registry.get_active_id()
        if active_id:
            project = registry.get_project(active_id)
            if project:
                try:
                    pkg = Package(project["path"])
                    store = ReviewStore(pkg, project["reviewer"])
                    active = ActiveProject(pkg, store, project["export_dir"])
                    print(f"active project: {project['name']} ({len(pkg.images)} images)", flush=True)
                except Exception as e:
                    print(f"uyarı: aktif proje yüklenemedi ({e}), ana sayfa boş açılacak", flush=True)
        else:
            print("aktif proje yok — ana sayfadan bir proje seç veya --package ile başlat", flush=True)

    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
