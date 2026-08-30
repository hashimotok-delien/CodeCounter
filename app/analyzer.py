"""Python プロジェクトの集計ロジック。

指定フォルダ内の対象ファイルを走査し、ファイル別・合計の
「ファイル数／行数／文字数」を集計する。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class FileStat:
    """1 ファイル分の集計結果。"""

    path: str           # ファイルパス（絶対パス）
    lines: int          # 行数
    chars: int          # 文字数


@dataclass
class ProjectSummary:
    """プロジェクト全体の集計結果。"""

    root: str = ""
    total_files: int = 0
    total_lines: int = 0
    total_chars: int = 0
    files: list[FileStat] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _is_hidden(path: str) -> bool:
    """パス中に隠し要素（先頭ドット）を含むかを判定する。"""
    parts = os.path.normpath(path).split(os.sep)
    return any(p.startswith(".") and p not in (".", "..") for p in parts)


def analyze_project(
    root_dir: str,
    extensions: Iterable[str] | None = None,
    exclude_dirs: Iterable[str] | None = None,
    include_hidden: bool = False,
) -> ProjectSummary:
    """対象フォルダを再帰走査して集計する。

    引数:
        root_dir: 集計対象のルートフォルダ
        extensions: 対象拡張子のリスト（例: [".py", ".txt"]）
        exclude_dirs: 除外するサブディレクトリ名の集合
        include_hidden: 隠しファイル・隠しディレクトリを含めるか

    戻り値:
        ProjectSummary（ファイル別一覧含む）
    """
    extensions = [e.lower() if e.startswith(".") else f".{e.lower()}"
                  for e in (extensions or [])]
    exclude = set(exclude_dirs or [])
    summary = ProjectSummary(root=os.path.abspath(root_dir))

    for root, dirs, files in os.walk(root_dir):
        # 除外ディレクトリを walk 対象から外す
        dirs[:] = [d for d in dirs if d not in exclude]
        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]

        for file in files:
            if not extensions:
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext not in extensions:
                continue

            file_path = os.path.join(root, file)
            if not include_hidden and _is_hidden(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError) as e:
                summary.errors.append(f"{file_path}: {e}")
                continue

            lines = content.count("\n")
            if content and not content.endswith("\n"):
                lines += 1
            summary.total_files += 1
            summary.total_lines += lines
            summary.total_chars += len(content)
            summary.files.append(FileStat(
                path=file_path,
                lines=lines,
                chars=len(content),
            ))

    return summary


def format_summary(summary: ProjectSummary) -> str:
    """集計結果を表示用テキストへ整形する。"""
    lines = [
        "📊 CodeCounter 集計結果",
        f"対象パス: {summary.root}",
        f"ファイル数: {summary.total_files}",
        f"行　　数: {summary.total_lines}",
        f"文字数: {summary.total_chars}",
    ]
    for err in summary.errors:
        lines.append(f"⚠ 読み込み失敗: {err}")
    return "\n".join(lines)
