"""Checks for the multi-project service: uploads, request safety, export folders.
Works in a temp folder with its own registry; never touches your projects.

Usage (from the project folder):
    .venv\\Scripts\\python -m pip install -r server\\requirements-dev.txt   (once)
    .venv\\Scripts\\python server\\test_projects.py
"""
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from project_registry import ProjectRegistry  # noqa: E402

SAMPLE = Path(__file__).parent.parent / "sample_package"
TOOL = {"X-Label-Tool": "1"}  # header our own web page sends
failures = 0


def check(name, cond):
    global failures
    print("OK  " if cond else "FAIL", name)
    failures += not cond


def png_bytes(w=40, h=20, exif_orientation=None):
    buf = io.BytesIO()
    im = Image.new("RGB", (w, h), (200, 50, 50))
    if exif_orientation:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        im.save(buf, "JPEG", exif=exif)
    else:
        im.save(buf, "PNG")
    return buf.getvalue()


def fresh(tmp):
    server.registry = ProjectRegistry(tmp / "reg.json")
    server.projects_root = str(tmp / "projects")
    server.active = None
    return TestClient(server.app, base_url="http://127.0.0.1:8000")


def test_upload_safety(tmp):
    c = fresh(tmp)
    r = c.post("/api/projects/upload", headers=TOOL, data={"name": "x", "reviewer": "t"},
               files=[("images", ("../../../escaped.png", png_bytes(), "image/png"))])
    escaped = list(tmp.rglob("escaped.png"))
    check(f"upload: '../' in file name rejected (HTTP {r.status_code})", r.status_code == 400)
    check("upload: nothing written outside the project", escaped == [])

    for bad in ("..\\..\\win.png", "a:b.png", ".hidden.png", "notes.txt"):
        r = c.post("/api/projects/upload", headers=TOOL, data={"name": "x", "reviewer": "t"},
                   files=[("images", (bad, png_bytes(), "image/png"))])
        check(f"upload: bad name {bad!r} rejected", r.status_code == 400)

    # A full Windows path is cut to its last part by the upload parser before we see it,
    # so it is stored safely inside the project. What matters: nothing lands outside.
    r = c.post("/api/projects/upload", headers=TOOL, data={"name": "winpath", "reviewer": "t"},
               files=[("images", ("C:\\Windows\\x.png", png_bytes(), "image/png"))])
    stored = [p.relative_to(tmp).as_posix() for p in tmp.rglob("x.png")]
    check(f"upload: full Windows path stays inside the project ({stored})",
          r.status_code == 400 or stored == ["projects/winpath/images/x.png"])

    r = c.post("/api/projects/upload", headers=TOOL, data={"name": "ok", "reviewer": "t"},
               files=[("images", ("depo 1.png", png_bytes(), "image/png"))])
    check(f"upload: normal file accepted (HTTP {r.status_code})", r.status_code == 200)


def test_upload_exif(tmp):
    c = fresh(tmp)
    r = c.post("/api/projects/upload", headers=TOOL, data={"name": "phone", "reviewer": "t"},
               files=[("images", ("phone.jpg", png_bytes(40, 20, exif_orientation=6), "image/jpeg"))])
    pkg_dir = Path(r.json()["path"])
    img = json.loads((pkg_dir / "annotations.json").read_text(encoding="utf-8"))["images"][0]
    with Image.open(pkg_dir / "images" / img["file_name"]) as saved:
        size, orient = saved.size, saved.getexif().get(0x0112)
    check(f"upload: phone photo stored upright ({size}, recorded {img['width']}x{img['height']})",
          size == (20, 40) and (img["width"], img["height"]) == (20, 40) and orient in (None, 1))


def test_upload_annotations_must_match(tmp):
    c = fresh(tmp)
    ann = {"categories": [{"id": 1, "name": "chair"}],
           "images": [{"id": 1, "file_name": "missing.png", "width": 40, "height": 20}], "annotations": []}
    r = c.post("/api/projects/upload", headers=TOOL, data={"name": "a", "reviewer": "t"},
               files=[("images", ("other.png", png_bytes(), "image/png")),
                      ("annotations", ("annotations.json", json.dumps(ann).encode(), "application/json"))])
    check(f"upload: annotations naming a missing photo rejected (HTTP {r.status_code})", r.status_code == 400)
    check("upload: failed upload leaves no project folder", not any((tmp / "projects").glob("*")))


def test_cross_site_requests(tmp):
    c = fresh(tmp)
    upload = dict(data={"name": "x", "reviewer": "t"}, files=[("images", ("a.png", png_bytes(), "image/png"))])
    r = c.post("/api/projects/upload", **upload)
    check(f"write without our header refused (HTTP {r.status_code})", r.status_code == 403)
    r = c.post("/api/projects/upload", headers={**TOOL, "Origin": "https://evil.example"}, **upload)
    check(f"write from another site's origin refused (HTTP {r.status_code})", r.status_code == 403)
    r = c.delete("/api/projects/anything")
    check("delete without our header refused", r.status_code == 403)
    r = c.get("/api/projects", headers={"Host": "evil.example"})
    check(f"foreign Host header refused (DNS rebinding, HTTP {r.status_code})", r.status_code == 403)
    r = c.get("/api/projects")
    check("plain reads from our page still work", r.status_code == 200)
    r = c.post("/api/projects/upload", headers={**TOOL, "Origin": "http://localhost:5173"}, **upload)
    check(f"our dev page's origin accepted (HTTP {r.status_code})", r.status_code == 200)


def copy_sample(tmp, name):
    dest = tmp / name
    shutil.copytree(SAMPLE, dest, ignore=shutil.ignore_patterns("reviews"))
    return dest


def test_export_folders(tmp):
    c = fresh(tmp)
    a = c.post("/api/projects", headers=TOOL, json={"name": "A", "path": str(copy_sample(tmp, "pkgA")), "reviewer": "t"}).json()
    b = c.post("/api/projects", headers=TOOL, json={"name": "B", "path": str(copy_sample(tmp, "pkgB")), "reviewer": "t"}).json()
    check(f"each project gets its own export folder ({Path(a['export_dir']).name}, {Path(b['export_dir']).name})",
          Path(a["export_dir"]).resolve() != Path(b["export_dir"]).resolve())

    c.post(f"/api/projects/{a['id']}/activate", headers=TOOL)
    c.post("/api/images/1/review", headers=TOOL, json={"ann_id": 1, "action": "accept"})
    coco = c.post("/api/export/coco", headers=TOOL)
    yolo = c.post("/api/export", headers=TOOL)
    check(f"COCO then YOLO export both work (HTTP {coco.status_code}, {yolo.status_code})",
          coco.status_code == 200 and yolo.status_code == 200)
    coco_again = c.post("/api/export/coco", headers=TOOL)
    check("COCO file survives a later YOLO export", Path(coco_again.json()["path"]).exists()
          and Path(coco.json()["path"]).exists())


def test_image_states_api(tmp):
    c = fresh(tmp)
    p = c.post("/api/projects", headers=TOOL, json={"name": "S", "path": str(copy_sample(tmp, "pkgS")), "reviewer": "t"}).json()
    c.post(f"/api/projects/{p['id']}/activate", headers=TOOL)

    r = c.post("/api/images/1/review", headers=TOOL, json={"ann_id": 1, "action": "accept"})
    check("a decision alone leaves the image pending", r.json()["status"] == "pending")
    r = c.post("/api/images/1/status", headers=TOOL, json={"status": "reviewed"})
    check("POST status: reviewed", r.status_code == 200 and r.json()["status"] == "reviewed")
    r = c.post("/api/images/2/status", headers=TOOL, json={"status": "needs_edit"})
    check("POST status: needs_edit", r.status_code == 200 and r.json()["status"] == "needs_edit")
    r = c.post("/api/images/2/status", headers=TOOL, json={"status": "nope"})
    check(f"POST status: unknown value refused (HTTP {r.status_code})", r.status_code == 400)
    r = c.post("/api/images/999/status", headers=TOOL, json={"status": "reviewed"})
    check("POST status: unknown image 404", r.status_code == 404)
    r = c.post("/api/images/1/status", json={"status": "pending"})
    check("POST status without our header refused", r.status_code == 403)
    pkg = {i["id"]: i["status"] for i in c.get("/api/package").json()["images"]}
    check("package list shows the three states", pkg == {1: "reviewed", 2: "needs_edit", 3: "pending"})
    prog = next(x for x in c.get("/api/projects").json() if x["id"] == p["id"])["progress"]
    check("project progress counts done and needs_edit", prog == {"reviewed": 1, "needs_edit": 1, "total": 3})

    r = c.post("/api/images/2/review", headers=TOOL, json={"ann_id": 6, "action": "accept"})
    check("editing a needs_edit image keeps it there", r.json()["status"] == "needs_edit")

    # --- who did it ---
    d = c.get("/api/images/1").json()
    check("image detail: who finished it, when, and who edited",
          d["status_by"] == "t" and d["status_at"] and d["editors"] == ["t"])
    check("image detail: untouched image has no names",
          c.get("/api/images/3").json()["status_by"] is None and c.get("/api/images/3").json()["editors"] == [])
    pk = c.get("/api/package").json()
    check("package list carries each image's person and the reviewer's own name",
          pk["reviewer"] == "t" and {i["id"]: i["status_by"] for i in pk["images"]} == {1: "t", 2: "t", 3: None})
    lab = c.get("/api/labelers").json()
    check("labelers table: header and one row per image",
          lab["columns"][:3] == ["image", "status", "status_by"] and len(lab["rows"]) == 3
          and lab["rows"][0]["image"] == "img_001.jpg" and lab["rows"][0]["status"] == "reviewed")

    pv = c.get("/api/export/edit/preview").json()
    check("edit preview: the one marked image", pv["images"] == 1 and pv["path"].endswith("_duzenlenecek"))
    ex = c.post("/api/export/edit", headers=TOOL)
    out = Path(ex.json()["path"])
    check("edit export written", ex.status_code == 200 and (out / "_annotations.coco.json").exists()
          and (out / "img_002.jpg").exists())
    r = c.post("/api/export/edit")
    check("edit export without our header refused", r.status_code == 403)

    t = c.get("/api/images/1/thumb")
    check("thumbnail is a small JPEG", t.status_code == 200 and t.headers["content-type"] == "image/jpeg"
          and max(Image.open(io.BytesIO(t.content)).size) <= 240)
    again = c.get("/api/images/1/thumb", headers={"If-None-Match": t.headers["etag"]})
    check("thumbnail answers 304 when unchanged", again.status_code == 304)
    check("thumbnail of unknown image 404", c.get("/api/images/999/thumb").status_code == 404)


def test_serves_built_web(tmp):
    from fastapi import FastAPI
    dist = tmp / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>page</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    other = FastAPI()

    @other.get("/api/ping")
    def ping():
        return {"ok": True}

    check("no web/dist -> nothing mounted", server.mount_web(tmp / "missing", other) is False)
    check("web/dist present -> mounted", server.mount_web(dist, other) is True)
    c = TestClient(other, base_url="http://127.0.0.1:8000")
    check("page served at /", "<title>page</title>" in c.get("/").text)
    check("assets served", c.get("/assets/app.js").status_code == 200)
    check("api routes are not shadowed by the page", c.get("/api/ping").json() == {"ok": True})
    check("files outside dist are not reachable", c.get("/..%2fsecret.txt").status_code in (400, 404))
    check("the real app does not serve files unless asked (mount happens in main)",
          not any(getattr(r, "name", "") == "web" for r in server.app.routes))


def test_cli_package_updates(tmp):
    fresh(tmp)
    pkg = copy_sample(tmp, "cli")
    first = server.register_cli_package(str(pkg), "ayse", str(tmp / "exp1"))
    again = server.register_cli_package(str(pkg), "mehmet", str(tmp / "exp2"))
    check("--package twice: same project, not a duplicate", first["id"] == again["id"]
          and len(server.registry.list_projects()) == 1)
    check("--package twice: new --reviewer and --export win",
          again["reviewer"] == "mehmet" and Path(again["export_dir"]) == (tmp / "exp2").resolve())


def test_slug():
    check("Turkish names keep their letters in ids", server._slugify("Örnek Çalışma İş") == "ornek-calisma-is")
    check("all-Turkish name not reduced to 'project'", server._slugify("Ğüşıöç") == "gusioc")


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        for t in (test_upload_safety, test_upload_exif, test_upload_annotations_must_match,
                  test_cross_site_requests, test_export_folders, test_image_states_api,
                  test_serves_built_web, test_cli_package_updates):
            sub = tmp / t.__name__
            sub.mkdir()
            try:
                t(sub)
            except Exception as e:  # a crash is a failure, keep going so all problems show
                check(f"{t.__name__} crashed: {e!r}"[:160], False)
        test_slug()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'all passed' if failures == 0 else f'{failures} failed'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
