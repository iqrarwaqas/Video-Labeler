"""Video Speaker Labeler.

A small local web app for labeling who speaks first in each video
(on-screen or off-screen actor). Labels are saved to an Excel file and the
session resumes automatically from that file.

Usage:
    python main.py --videos "D:/data/videos"
    python main.py --videos "D:/data/videos" --project "Batch_01"
    python main.py --videos "D:/data/videos" --output "D:/data/output"
    python main.py --videos "D:/data/videos" --import "speaker list.xlsx"
    python main.py            # pick the folder from the browser
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, abort, jsonify, render_template, request, send_from_directory

__version__ = "1.0.2"
GITHUB_REPO = "iqrarwaqas/Video-Labeler"

FROZEN = getattr(sys, "frozen", False)  # running as the installed .exe
# PyInstaller unpacks the bundled templates/static to sys._MEIPASS.
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
if FROZEN:
    # The install folder isn't writable, so keep settings in the user's profile.
    CONFIG_FILE = Path(os.environ.get("APPDATA", Path.home())) / "VideoLabeler" / "config.json"
else:
    CONFIG_FILE = RESOURCE_DIR / ".labeler_config.json"
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
LEGACY_OUTPUT_NAME = "labels.xlsx"  # used before projects had names

COLUMNS = ["Project", "Video_Name", "Video_File", "First_Speaker", "Onscreen_Diarized_Label", "Labeled_At"]
LABELS = {"onscreen", "offscreen", "unclear"}
# Diarization tags the first speaker as "A", so the on-screen actor's track
# is A when they speak first and B when the off-screen actor speaks first.
DIARIZED = {"onscreen": "A", "offscreen": "B", "unclear": ""}

app = Flask(__name__, template_folder=str(RESOURCE_DIR / "templates"), static_folder=str(RESOURCE_DIR / "static"))
lock = threading.Lock()


def safe_filename(name: str) -> str:
    """Make a project name usable as a Windows file name."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return cleaned or "project"


def natural_key(name: str):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


class Project:
    def __init__(self, videos_dir: Path, output_dir: Path | None = None, name: str = ""):
        self.videos_dir = videos_dir.resolve()
        if not self.videos_dir.is_dir():
            raise FileNotFoundError(f"Videos folder not found: {self.videos_dir}")
        self.name = name.strip() or self.videos_dir.name
        self.output_dir = (output_dir or self.videos_dir.parent / "output").resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / f"{safe_filename(self.name)}_labels.xlsx"
        self.videos = sorted(
            (p.name for p in self.videos_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS),
            key=natural_key,
        )
        # Keyed by Video_File. Rows for videos no longer in the folder are kept.
        self.rows: dict[str, dict] = {}
        self._load()

    def _load(self):
        source = self.output_file
        if not source.exists():
            # Carry over labels made before projects had names, but only into
            # the first named project in this folder.
            source = self.output_dir / LEGACY_OUTPUT_NAME
            if not source.exists() or any(self.output_dir.glob("*_labels.xlsx")):
                return
        df = pd.read_excel(source, dtype=str).fillna("")
        for rec in df.to_dict("records"):
            file = rec.get("Video_File") or rec.get("Video_Name")
            if file and rec.get("First_Speaker") in LABELS:
                self.rows[file] = {c: rec.get(c, "") for c in COLUMNS}
                self.rows[file]["Project"] = self.name
        if source != self.output_file and self.rows:
            self.save()

    def save(self):
        """Write all rows to Excel atomically (temp file + replace)."""
        order = {f: i for i, f in enumerate(self.videos)}
        rows = sorted(self.rows.values(), key=lambda r: (order.get(r["Video_File"], 10**9), natural_key(r["Video_File"])))
        df = pd.DataFrame(rows, columns=COLUMNS)
        tmp = self.output_file.with_name("~tmp_" + self.output_file.name)
        with pd.ExcelWriter(tmp, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="labels")
            ws = writer.sheets["labels"]
            for col, width in zip("ABCDEF", (20, 28, 32, 16, 26, 20)):
                ws.column_dimensions[col].width = width
            ws.freeze_panes = "A2"
        try:
            os.replace(tmp, self.output_file)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise

    def set_label(self, file: str, label: str):
        self.rows[file] = {
            "Project": self.name,
            "Video_Name": Path(file).stem,
            "Video_File": file,
            "First_Speaker": label,
            "Onscreen_Diarized_Label": DIARIZED[label],
            "Labeled_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def import_legacy(self, path: Path) -> tuple[int, int]:
        """Seed labels from the old sheet (Video_Name, Onscreen_Speaker = a/b)."""
        df = pd.read_excel(path, dtype=str).fillna("")
        by_stem = {Path(f).stem.lower(): f for f in self.videos}
        imported = skipped = 0
        for rec in df.to_dict("records"):
            name = str(rec.get("Video_Name", "")).strip()
            tag = str(rec.get("Onscreen_Speaker", "")).strip().lower()
            file = by_stem.get(Path(name).stem.lower())
            label = {"a": "onscreen", "b": "offscreen"}.get(tag)
            if not file or not label or file in self.rows:
                skipped += 1
                continue
            self.set_label(file, label)
            imported += 1
        if imported:
            self.save()
        return imported, skipped

    def state(self) -> dict:
        items = []
        for i, f in enumerate(self.videos):
            row = self.rows.get(f)
            items.append({"index": i, "file": f, "name": Path(f).stem, "label": row["First_Speaker"] if row else None})
        return {
            "ready": True,
            "project": self.name,
            "videos_dir": str(self.videos_dir),
            "output_file": str(self.output_file),
            "items": items,
            **self.counts(),
        }

    def counts(self) -> dict:
        labeled = [f for f in self.videos if f in self.rows]
        first_unlabeled = next((i for i, f in enumerate(self.videos) if f not in self.rows), None)
        return {"total": len(self.videos), "labeled": len(labeled), "first_unlabeled": first_unlabeled}


project: Project | None = None


def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(videos: str, output: str, name: str):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({"project": name, "videos": videos, "output": output}, indent=2), encoding="utf-8")


def open_project(videos: str, output: str = "", name: str = "") -> Project:
    global project
    p = Project(Path(videos), Path(output) if output else None, name)
    project = p
    save_config(str(p.videos_dir), str(p.output_dir), p.name)
    return p


def save_error(e: Exception):
    if isinstance(e, PermissionError):
        msg = f"Can't write {project.output_file.name}. Close it in Excel and try again."
    else:
        msg = f"Save failed: {e}"
    return jsonify({"ok": False, "error": msg}), 409


# ---------------------------------------------------------------- updates

_update_info: dict | None = None


def parse_version(tag: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", tag)[:3])


def github_get(url: str, timeout: float):
    req = urllib.request.Request(url, headers={"User-Agent": f"VideoLabeler/{__version__}"})
    return urllib.request.urlopen(req, timeout=timeout)


def check_update() -> dict:
    """Compare this version with the latest GitHub release (looked up once per run)."""
    global _update_info
    if _update_info is None:
        info = {"current": __version__, "available": False}
        try:
            with github_get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest", timeout=5) as r:
                release = json.load(r)
            installer = next((a["browser_download_url"] for a in release.get("assets", [])
                              if a["name"].lower().endswith(".exe")), None)
            info.update(
                latest=release["tag_name"].lstrip("v"),
                url=release["html_url"],
                installer=installer,
                available=parse_version(release["tag_name"]) > parse_version(__version__),
            )
        except Exception:  # noqa: BLE001 - offline or no releases yet: just don't offer an update
            pass
        _update_info = info
    return {**_update_info, "can_install": FROZEN and bool(_update_info.get("installer"))}


def quit_app():
    lock.acquire()  # let a label save that is in progress finish first
    os._exit(0)


# ---------------------------------------------------------------- routes


@app.get("/")
def index():
    return render_template("index.html", version=__version__)


@app.get("/api/version")
def api_version():
    return jsonify({"app": "VideoLabeler", "version": __version__})


@app.get("/api/update")
def api_update():
    return jsonify(check_update())


@app.post("/api/update/install")
def api_update_install():
    info = check_update()
    if not (info["available"] and info["can_install"]):
        return jsonify({"ok": False, "error": "There is no update to install."}), 400
    target = Path(tempfile.gettempdir()) / Path(info["installer"]).name
    try:
        with github_get(info["installer"], timeout=60) as r, open(target, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"Download failed: {e}"}), 502
    # The installer replaces the app's files, so this process has to exit.
    # /RELAUNCH=1 makes the installer start the new version when it's done.
    subprocess.Popen([str(target), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/RELAUNCH=1"])
    threading.Timer(1.0, quit_app).start()
    return jsonify({"ok": True})


@app.get("/api/state")
def api_state():
    if project is None:
        cfg = load_config()
        return jsonify({
            "ready": False,
            "last_project": cfg.get("project", ""),
            "last_videos": cfg.get("videos", ""),
            "last_output": cfg.get("output", ""),
        })
    with lock:
        return jsonify(project.state())


@app.post("/api/setup")
def api_setup():
    data = request.get_json(force=True)
    videos = (data.get("videos") or "").strip().strip('"')
    output = (data.get("output") or "").strip().strip('"')
    name = (data.get("project") or "").strip()
    if not videos:
        return jsonify({"ok": False, "error": "Please enter the videos folder path."}), 400
    try:
        with lock:
            open_project(videos, output, name)
    except Exception as e:  # noqa: BLE001 - surface any problem to the user
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True})


@app.post("/api/close")
def api_close():
    global project
    project = None
    return jsonify({"ok": True})


@app.post("/api/label")
def api_label():
    if project is None:
        abort(400)
    data = request.get_json(force=True)
    file, label = data.get("file"), data.get("label")
    if file not in project.videos or label not in LABELS:
        return jsonify({"ok": False, "error": "Invalid video or label."}), 400
    with lock:
        previous = project.rows.get(file)
        project.set_label(file, label)
        try:
            project.save()
        except Exception as e:  # noqa: BLE001
            if previous is None:
                project.rows.pop(file, None)
            else:
                project.rows[file] = previous
            return save_error(e)
        return jsonify({"ok": True, **project.counts()})


@app.delete("/api/label/<path:file>")
def api_clear(file):
    if project is None:
        abort(400)
    with lock:
        previous = project.rows.pop(file, None)
        try:
            project.save()
        except Exception as e:  # noqa: BLE001
            if previous is not None:
                project.rows[file] = previous
            return save_error(e)
        return jsonify({"ok": True, **project.counts()})


@app.get("/video/<path:file>")
def video(file):
    if project is None or file not in project.videos:
        abort(404)
    # send_from_directory supports HTTP Range requests, so seeking works.
    return send_from_directory(project.videos_dir, file, conditional=True)


# ---------------------------------------------------------------- entry


def already_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version", timeout=1) as r:
            return json.load(r).get("app") == "VideoLabeler"
    except Exception:  # noqa: BLE001
        return False


def main():
    parser = argparse.ArgumentParser(description="Label who speaks first (on-screen / off-screen) in videos.")
    parser.add_argument("--version", action="version", version=f"Video Speaker Labeler {__version__}")
    parser.add_argument("--videos", help="Folder containing the videos")
    parser.add_argument("--project", default="", help="Project name (default: the videos folder name)")
    parser.add_argument("--output", help="Folder for <project>_labels.xlsx (default: <videos>/../output)")
    parser.add_argument("--import", dest="import_file", help="Old sheet with Video_Name / Onscreen_Speaker (a/b)")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1", help="Use 0.0.0.0 to allow access from other PCs on the LAN")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    url = f"http://127.0.0.1:{args.port}"
    if already_running(args.port):
        # Starting the app a second time (e.g. from the Start menu) just opens the running one.
        print(f"Video Speaker Labeler is already running: {url}")
        if not args.no_browser:
            webbrowser.open(url)
        return

    print(f"Video Speaker Labeler {__version__}")
    if args.videos:
        p = open_project(args.videos, args.output or "", args.project)
        print(f"Project: {p.name}")
        print(f"Videos : {p.videos_dir} ({len(p.videos)} files)")
        print(f"Output : {p.output_file}")
        if args.import_file:
            imported, skipped = p.import_legacy(Path(args.import_file))
            print(f"Import : {imported} labels imported, {skipped} skipped (already labeled or no matching video)")
    elif args.import_file:
        parser.error("--import requires --videos")

    print(f"Open   : {url}")
    print("Keep this window open while labeling. Close it to quit the app.")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
