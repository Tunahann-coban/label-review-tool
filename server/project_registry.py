"""Registry of label-review packages; persisted as a JSON file on disk."""
import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path


# Turkish letters -> ASCII first, so "Örnek Çalışma" becomes "ornek-calisma", not "rnek-al-ma"
_TR = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")


def slugify(name: str) -> str:
    s = name.translate(_TR).lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:48] or "project"


def _make_id(name: str, existing: list) -> str:
    existing_ids = {p["id"] for p in existing}
    base = slugify(name)
    candidate = base
    n = 2
    while candidate in existing_ids:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


class ProjectRegistry:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        defaults = {"active_id": None, "projects": []}
        if self.path.exists():
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                return {**defaults, **data}
            except (json.JSONDecodeError, ValueError):
                pass
        return defaults

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def list_projects(self) -> list:
        return list(self._data["projects"])

    def get_project(self, project_id: str) -> dict | None:
        return next((p for p in self._data["projects"] if p["id"] == project_id), None)

    def get_by_path(self, resolved_path: str) -> dict | None:
        return next((p for p in self._data["projects"] if p["path"] == resolved_path), None)

    def add_project(self, name: str, path: str, reviewer: str, export_dir: str = "export") -> dict:
        with self._lock:
            project = {
                "id": _make_id(name, self._data["projects"]),
                "name": name,
                "path": str(Path(path).resolve()),
                "reviewer": reviewer,
                "export_dir": export_dir,
                "added": datetime.now().isoformat(timespec="seconds"),
            }
            self._data["projects"].append(project)
            self._save()
            return project

    def update_project(self, project_id: str, **changes) -> dict:
        """Change reviewer / export_dir of a registered project; returns the project."""
        with self._lock:
            project = self.get_project(project_id)
            project.update({k: v for k, v in changes.items() if k in ("reviewer", "export_dir", "name")})
            self._save()
            return dict(project)

    def set_active(self, project_id: str):
        with self._lock:
            self._data["active_id"] = project_id
            self._save()

    def get_active_id(self) -> str | None:
        return self._data.get("active_id")

    def remove_project(self, project_id: str):
        with self._lock:
            self._data["projects"] = [p for p in self._data["projects"] if p["id"] != project_id]
            if self._data["active_id"] == project_id:
                self._data["active_id"] = None
            self._save()
