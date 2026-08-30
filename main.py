"""CodeCounter エントリポイント。

GUI アプリとして起動する。
コマンドラインから実行した場合 (python main.py <path>) も、
従来どおり簡易集計を利用できる。
"""

from __future__ import annotations

import os
import sys

from app.analyzer import analyze_project, format_summary
from app.gui import main as gui_main
from app.settings import load_settings


def cli_analyze(path: str) -> int:
    """コマンドライン集計（従来の analyze.py 相当）。"""
    if not os.path.exists(path):
        print(f"❌ 指定されたパスが存在しません: {path}")
        return 1

    settings = load_settings()
    summary = analyze_project(
        path,
        extensions=settings.get("extensions"),
        exclude_dirs=settings.get("exclude_dirs"),
        include_hidden=settings.get("include_hidden"),
    )
    print(format_summary(summary))
    return 0


def main() -> int:
    """エントリポイント。

    - 引数なし: GUI を起動
    - 引数あり: 従来の CUI 集計を実行
    """
    if len(sys.argv) >= 2:
        return cli_analyze(sys.argv[1])
    gui_main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
