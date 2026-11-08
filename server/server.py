"""Label review service.

Usage (with existing package):
    python server/server.py --package sample_package --reviewer tunahan

Usage (registry mode, home page picks the project):
    python server/server.py
"""
import argparse
import io
import json
import shutil
from pathlib import Path
from typing import List
from urllib.parse import urlsplit

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image as PillowImage, ImageOps
from pydantic import BaseModel

import coco_exporter
import exporter
from package import Package, merge_objects
from project_registry import ProjectRegistry, slugify
from review_store import ReviewError, ReviewStore

app = FastAPI(title="Label Review Tool")

# ── request safety ────────────────────────────────────────────────────────
# The service only listens on 127.0.0.1, but any web page open in the same browser
# can still send it requests. Form uploads are "simple" requests that browsers send
# cross-site without asking. So: writes must carry our own header (other sites can't
# add it), must not come from another site's Origin, and the Host must be local
# (stops DNS rebinding from reading data through a look-alike host name).
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
TOOL_HEADER = "x-label-tool"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _hostname(value):
    return urlsplit(value if "//" in value else f"//{value}").hostname


@app.middleware("http")
async def local_requests_only(request: Request, call_next):
    if _hostname(request.headers.get("host", "")) not in LOCAL_HOSTS:
        return JSONResponse({"detail": "yalnızca bu bilgisayardan erişilebilir"}, status_code=403)
    if request.method not in SAFE_METHODS:
        origin = request.headers.get("origin")
        if request.headers.get(TOOL_HEADER) != "1" or (origin and _hostname(origin) not in LOCAL_HOSTS):
            return JSONResponse({"detail": "istek aracın kendi sayfasından gelmedi"}, status_code=403)
    return await call_next(request)


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


_slugify = slugify  # one rule for project ids and upload folders

IMAGE_TYPES = {".jpg", ".jpeg", ".png"}


def safe_image_name(raw):
    """The uploaded file name, if it is a plain image file name; 400 otherwise.
    No folders, drive letters or hidden files: the name decides where we write."""
    name = raw or ""
    if (not name or name != Path(name).name or any(ch in name for ch in "/\\:")
            or name.startswith(".") or Path(name).suffix.lower() not in IMAGE_TYPES):
        raise HTTPException(400, f"geçersiz resim dosyası adı: {raw!r} (yalnızca .jpg / .jpeg / .png)")
    return name


def default_export_dir(package_path):
    """<package>_export next to the package: every project writes its own dataset."""
    p = Path(package_path).resolve()
    return str(p.parent / f"{p.name}_export")


def coco_dir(export_dir):
    """COCO goes beside the YOLO folder, not into it: a YOLO export replaces its whole folder."""
    return str(Path(export_dir).resolve()) + "_coco"


def register_cli_package(path, reviewer, export_dir):
    """--package: register the folder, or update it; the command-line values win."""
    resolved = str(Path(path).resolve())
    export_dir = str(Path(export_dir).resolve()) if export_dir else default_export_dir(resolved)
    existing = registry.get_by_path(resolved)
    if existing:
        return registry.update_project(existing["id"], reviewer=reviewer, export_dir=export_dir)
    return registry.add_project(Path(resolved).name, resolved, reviewer, export_dir)


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
        return coco_exporter.preview_coco(a.pkg, a.store, coco_dir(a.export_dir))


@app.post("/api/export/coco")
def do_coco_export():
    a = get_active()
    with a.store.lock:
        return coco_exporter.export_coco(a.pkg, a.store, coco_dir(a.export_dir))


# ── project management ─────────────────────────────────────────────────────

@app.get("/api/projects")
def list_projects():
    return [_project_with_progress(p) for p in registry.list_projects()]


class ProjectCreate(BaseModel):
    name: str
    path: str
    reviewer: str
    export_dir: str | None = None  # default: <package>_export


@app.post("/api/projects")
def create_project(body: ProjectCreate):
    resolved = str(Path(body.path).resolve())
    if registry.get_by_path(resolved):
        raise HTTPException(409, "bu klasör zaten kayıtlı")
    try:
        Package(resolved)  # validate
    except Exception as e:
        raise HTTPException(422, f"paket yüklenemedi: {e}")
    export_dir = str(Path(body.export_dir).resolve()) if body.export_dir else default_export_dir(resolved)
    project = registry.add_project(body.name, resolved, body.reviewer, export_dir)
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
    # every check runs before anything is written
    filenames = [safe_image_name(f.filename) for f in images]
    stems = [Path(fn).stem.lower() for fn in filenames]
    if len(stems) != len(set(stems)):
        raise HTTPException(400, "yüklenen resimler arasında tekrarlayan dosya adı var")

    photos = []  # (name, bytes to write, width, height)
    for fn, upload in zip(filenames, images):
        content = await upload.read()
        try:
            with PillowImage.open(io.BytesIO(content)) as im:
                fmt = im.format
                upright = ImageOps.exif_transpose(im)
                if upright is not im:  # phone photo stored sideways: keep it as people see it
                    buf = io.BytesIO()
                    upright.convert("RGB").save(buf, "JPEG" if fmt == "JPEG" else "PNG", quality=95)
                    content = buf.getvalue()
                w, h = upright.size
        except Exception:
            raise HTTPException(400, f"{fn}: resim açılamadı")
        photos.append((fn, content, w, h))

    ann_data = None
    if annotations:
        ann_bytes = await annotations.read()
        try:
            ann_data = json.loads(ann_bytes)
        except json.JSONDecodeError as e:
            raise HTTPException(400, f"annotations.json geçersiz JSON: {e}")
        for key in ("categories", "images", "annotations"):
            if key not in ann_data:
                raise HTTPException(400, f"annotations.json eksik alan: '{key}'")
        sizes = {fn: (w, h) for fn, _, w, h in photos}
        for img in ann_data["images"]:
            if img.get("file_name") not in sizes:
                raise HTTPException(400, f"annotations.json'daki {img.get('file_name')!r} yüklenmedi")
            if sizes[img["file_name"]] != (img.get("width"), img.get("height")):
                raise HTTPException(400, f"{img['file_name']}: annotations.json boyutu "
                                         f"{img.get('width')}x{img.get('height')}, resim {sizes[img['file_name']][0]}x{sizes[img['file_name']][1]}")

    slug = _slugify(name)
    pkg_dir = Path(projects_root) / slug
    counter = 1
    while pkg_dir.exists():
        pkg_dir = Path(projects_root) / f"{slug}-{counter}"
        counter += 1
    images_dir = (pkg_dir / "images").resolve()
    pkg_dir.mkdir(parents=True)
    images_dir.mkdir()

    try:
        image_entries = []
        for i, (fn, content, w, h) in enumerate(photos):
            dest = (images_dir / fn).resolve()
            if dest.parent != images_dir:  # belt and braces: safe_image_name already ensures this
                raise HTTPException(400, f"geçersiz resim dosyası adı: {fn!r}")
            dest.write_bytes(content)
            image_entries.append({"id": i + 1, "file_name": fn, "width": w, "height": h})

        if ann_data is not None:
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
        project = registry.add_project(name, str(pkg_dir), reviewer, default_export_dir(pkg_dir))
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
    parser.add_argument("--export", default=None,
                        help="YOLO dataset output folder (default: <package>_export next to the package)")
    parser.add_argument("--registry", default="projects.json", help="path to projects registry JSON")
    parser.add_argument("--projects-dir", default="projects", dest="projects_dir",
                        help="root folder for newly uploaded projects")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    registry = ProjectRegistry(args.registry)
    projects_root = args.projects_dir

    if args.package:
        project = register_cli_package(args.package, args.reviewer, args.export)
        registry.set_active(project["id"])
        pkg = Package(project["path"])
        store = ReviewStore(pkg, project["reviewer"])
        active = ActiveProject(pkg, store, project["export_dir"])
        print(f"package: {pkg.root} ({len(pkg.images)} images), reviewer: {project['reviewer']}, "
              f"export: {project['export_dir']}", flush=True)
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
