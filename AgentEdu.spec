# PyInstaller spec — build: pyinstaller AgentEdu.spec
# Cần: pip install -e ".[build]"

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

root = Path(SPEC).resolve().parent

datas = []
datas += collect_data_files("certifi")

a = Analysis(
    [str(root / "launch_gui.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "lxml",
        "lxml.etree",
        "lxml._elementpath",
        "docx",
        "docx.parts",
        "docx.opc",
        "openpyxl",
        "openpyxl.cell",
        "certifi",
        "httpx",
        "httpcore",
        "h11",
        "idna",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AgentEdu",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
