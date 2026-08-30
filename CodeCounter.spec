# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 用ビルド設定（CodeCounter）
#
# 使い方:
#   python build_exe.py
#   --- または ---
#   python -m PyInstaller --clean --noconfirm CodeCounter.spec

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH)

block_cipher = None

hiddenimports = collect_submodules("app")
datas = collect_data_files("app")
datas += [("app/version.py", "app")]

# ウィンドウアイコン用 PNG（GUI が実行時に参照）
png_icon = project_root / "icon.png"
if png_icon.exists():
    datas += [("icon.png", ".")]

# アイコン: icon.ico が存在すれば exe に埋め込む（build_exe.py が png から変換）
icon_path = project_root / "icon.ico"
icon = str(icon_path) if icon_path.exists() else None

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="CodeCounter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # ターミナル画面を出さない
    icon=icon,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)