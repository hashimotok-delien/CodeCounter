"""settings.yml の作成・読み書きを担当するモジュール。

起動時に settings.yml が存在しなければ既定値で自動生成する。
既定値はコード内の DEFAULT_SETTINGS で管理し、GUI 側で変更・保存できる。
"""

from __future__ import annotations

import os
from typing import Any

import yaml

APP_NAME = "CodeCounter"

# 設定ファイルの保存先。
# PyInstaller 実行時は sys.executable の場所、通常実行時は
# カレントディレクトリを基準にする。
CONFIG_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.yml")

# 既定の除外ディレクトリ名（サブディレクトリ名が一致したものを除外）
DEFAULT_EXCLUDE_DIRS_SRC = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    ".env",
    "node_modules",
    "dist",
    "build",
    ".idea",
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "extensions": [".py"],          # 集計対象の拡張子
    "exclude_dirs": sorted(
        DEFAULT_EXCLUDE_DIRS_SRC
    ),                            # 除外ディレクトリ名
    "include_hidden": False,      # 隠しファイル・隠しディレクトリを含めるか
    "auto_check_update": True,    # 起動時に更新を確認するか
    "update_channel": "stable",   # 更新チャンネル (stable / prerelease)
    "font_scale": 1.0,            # 文字サイズ倍率（1.0〜2.0）
    "last_folder": "",            # 前回の集計フォルダ（次回起動時に復元）
    "result_template": (          # 集計結果の表示・コピー用テンプレート
        "📊 Pythonプロジェクト集計結果\n"
        "対象　パス: {path}\n"
        "ファイル数: {files}\n"
        "行　　　数: {lines}\n"
        "文　字　数: {chars}"
    ),
}


def ensure_settings_file(path: str | None = None) -> dict[str, Any]:
    """設定ファイルが無ければ既定値で作成し、内容を返す。

    引数:
        path: 設定ファイルパス（省略時は既定の SETTINGS_PATH）

    戻り値:
        読み込んだ設定辞書（既定値とマージ済み）
    """
    target = path or SETTINGS_PATH
    if not os.path.exists(target):
        _save_settings(DEFAULT_SETTINGS, target)
        return dict(DEFAULT_SETTINGS)
    return load_settings(target)


def load_settings(path: str | None = None) -> dict[str, Any]:
    """設定ファイルを読み込み、既定値とマージして返す。

    未知・不足キーは既定値で補完されるため、古い設定ファイルでも
    安全に読み込める。
    """
    target = path or SETTINGS_PATH
    try:
        with open(target, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return dict(DEFAULT_SETTINGS)

    merged = dict(DEFAULT_SETTINGS)
    if isinstance(loaded, dict):
        for key, value in loaded.items():
            if key in merged and value is not None:
                merged[key] = value
    return merged


def _save_settings(settings: dict[str, Any], path: str) -> None:
    """設定をYAMLファイルへ書き出す。"""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            settings,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )


def save_settings(settings: dict[str, Any], path: str | None = None) -> None:
    """設定を保存する（ensure_settings_file 用の公開API）。"""
    _save_settings(settings, path or SETTINGS_PATH)
