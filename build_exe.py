"""CodeCounter.exe のビルドスクリプト。

使い方:
    python build_exe.py
    python build_exe.py --version 1.1.0

PyInstaller で --noconsole 相当（console=False）の
単一ファイル exe を dist/ に生成する。
icon.png があれば icon.ico へ自動変換し、exe のアイコンとして埋め込む。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys


def convert_icon() -> str | None:
    """icon.png を PyInstaller 用の icon.ico へ変換する。

    戻り値:
        変換後の .ico パス。icon.png が無い・変換に失敗した場合は None。
    """
    root = os.path.dirname(os.path.abspath(__file__))
    png_path = os.path.join(root, "icon.png")
    ico_path = os.path.join(root, "icon.ico")
    if not os.path.exists(png_path):
        return None
    try:
        from PIL import Image
    except ImportError:
        print("⚠ Pillow が無いためアイコン変換をスキップします")
        return None

    try:
        img = Image.open(png_path)
        # 複数サイズを含む ICO（16〜256px）で保存すると綺麗に表示される
        img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32),
                                                (48, 48), (64, 64),
                                                (256, 256)])
    except Exception as e:  # noqa: BLE001
        print(f"⚠ アイコン変換に失敗したためスキップします: {e}")
        return None
    return ico_path


def build(version: str | None = None) -> int:
    """PyInstaller を実行して exe をビルドする。

    引数:
        version: ビルドするバージョン（省略時は app/version.py の値）

    戻り値:
        終了コード
    """
    if version:
        version_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "app",
            "version.py",
        )
        with open(version_path, "r", encoding="utf-8") as f:
            src = f.read()
        src = re.sub(
            r'__version__\s*=\s*"[^"]*"',
            f'__version__ = "{version}"',
            src,
        )
        with open(version_path, "w", encoding="utf-8") as f:
            f.write(src)

    convert_icon()

    root = os.path.dirname(os.path.abspath(__file__))
    spec_path = os.path.join(root, "CodeCounter.spec")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_path,
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=root)


def main() -> None:
    """エントリポイント。"""
    parser = argparse.ArgumentParser(
        description="Build CodeCounter.exe with PyInstaller"
    )
    parser.add_argument(
        "--version",
        help="Version string to embed (overwrites app/version.py)",
    )
    args = parser.parse_args()
    sys.exit(build(args.version))


if __name__ == "__main__":
    main()
