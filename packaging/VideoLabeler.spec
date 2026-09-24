# PyInstaller build for Video Speaker Labeler.
# Run from the repo root:  pyinstaller packaging/VideoLabeler.spec --noconfirm
# Output: dist/VideoLabeler/VideoLabeler.exe (a folder build, packed by installer/VideoLabeler.iss)

from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "templates"), "templates"), (str(ROOT / "static"), "static")],
    # pandas loads the Excel engine at runtime, so PyInstaller can't see it.
    hiddenimports=["openpyxl"],
    excludes=["tkinter", "matplotlib", "IPython", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VideoLabeler",
    console=True,  # the console window is how users quit the app
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="VideoLabeler", upx=False)
