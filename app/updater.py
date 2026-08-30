"""GitHub リリースの確認と自動更新を担当するモジュール。

- リポジトリの最新リリースを GitHub API で取得
- 現在バージョンと比較して更新の有無を判定
- リリースに添付された exe をダウンロードして配置する

実行環境の判定:
- PyInstaller ビルド版: sys.executable (self pending 外) を使う
- 通常実行版 (python main.py): 最新版へ置き換え可能な場合は exe を
  ダウンロードし、ユーザーに通知する
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass

import app.version as version_mod

GITHUB_REPO = "hashimotok-delien/CodeCounter"
API_LATEST_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
)
API_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"


@dataclass
class UpdateInfo:
    """更新情報。"""

    available: bool          # 更新があるか
    latest_version: str      # 最新バージョン
    release_url: str         # リリースページ URL
    download_url: str | None = None  # アセット (exe) の URL
    asset_name: str | None = None     # アセット名
    notes: str = ""          # リリースノート

    @property
    def summary(self) -> str:
        """表示用の要約テキスト。"""
        return (
            f"新しいバージョン {self.latest_version} が利用可能です。\n"
            f"現在のバージョン: {version_mod.__version__}\n"
            f"リリースページ: {self.release_url}"
        )


def get_current_version() -> str:
    """現在のアプリバージョンを返す。"""
    return version_mod.__version__


class UpdateError(Exception):
    """更新処理で発生したエラーの基底クラス。"""


def _request_json(url: str) -> dict:
    """GitHub API から JSON を取得する。"""
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "CodeCounter-Updater",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        raise UpdateError(f"更新情報の取得に失敗しました: {e}") from e


def _parse_version(text: str) -> tuple[int, ...]:
    """'1.2.3' 形式のバージョンを比較用タプルへ変換する。"""
    digits = []
    for part in text.lstrip("v").split("."):
        num = ""
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        digits.append(int(num) if num else 0)
    while len(digits) < 3:
        digits.append(0)
    return tuple(digits[:3])


def _is_newer(latest: str, current: str) -> bool:
    """latest が current より新しいか判定する。"""
    return _parse_version(latest) > _parse_version(current)


def check_for_update(
    channel: str | None = None, use_cache: bool = True
) -> UpdateInfo:
    """GitHub リリースから更新の有無を確認する。

    引数:
        channel: "stable" なら最新安定版、それ以外なら最新リリース
            （prerelease 含む）。None なら安定版として扱う。
        use_cache: True の場合にのみ GitHub API を呼ぶ。
            （キャッシュ機構は簡易化のため現在は常に API を呼ぶ）

    戻り値:
        UpdateInfo
    """
    del use_cache  # 将来のキャッシュ実装用に予約
    try:
        if channel and channel.lower() == "stable":
            data = _request_json(API_LATEST_URL)
        else:
            releases = _request_json(API_RELEASES_URL)
            if not isinstance(releases, list) or not releases:
                raise UpdateError("リリースが見つかりませんでした。")
            data = releases[0]
    except UpdateError:
        return UpdateInfo(
            available=False,
            latest_version=get_current_version(),
            release_url=f"https://github.com/{GITHUB_REPO}/releases",
        )

    latest_version = str(data.get("tag_name", ""))
    if not latest_version:
        return UpdateInfo(
            available=False,
            latest_version=get_current_version(),
            release_url=f"https://github.com/{GITHUB_REPO}/releases",
        )

    current = get_current_version()
    available = _is_newer(latest_version, current)

    download_url = None
    asset_name = None
    for asset in data.get("assets", []):
        name = str(asset.get("name", ""))
        if name.lower().endswith(".exe"):
            download_url = str(asset.get("browser_download_url", ""))
            asset_name = name
            break

    return UpdateInfo(
        available=available,
        latest_version=latest_version,
        release_url=str(
            data.get("html_url")
            or f"https://github.com/{GITHUB_REPO}/releases"
        ),
        download_url=download_url,
        asset_name=asset_name,
        notes=str(data.get("body") or ""),
    )


def _frozen_executable() -> str:
    """PyInstaller 実行時の実行ファイルパスを返す。"""
    return sys.executable


def install_update(info: UpdateInfo, download_dir: str | None = None) -> str:
    """更新 exe をダウンロードして配置する。

    引数:
        info: check_for_update の結果
        download_dir: ダウンロード先ディレクトリ（省略時は一時ディレクトリ）

    戻り値:
        配置された exe のパス

    エラー:
        UpdateError: ダウンロード・配置に失敗
    """
    if not info.download_url or not info.asset_name:
        raise UpdateError("ダウンロード対象の exe がありません。")

    target_dir = download_dir or tempfile.mkdtemp(prefix="codecounter_")
    target_path = os.path.join(target_dir, info.asset_name)
    os.makedirs(target_dir, exist_ok=True)

    req = urllib.request.Request(
        info.download_url,
        headers={"User-Agent": "CodeCounter-Updater"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, \
                open(target_path, "wb") as out:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
    except urllib.error.URLError as e:
        raise UpdateError(f"ダウンロードに失敗しました: {e}") from e

    if not os.path.exists(target_path):
        raise UpdateError("ダウンロードに失敗しました（ファイルがありません）。")
    return target_path


def restart_application(new_exe: str) -> None:
    """新しい exe でアプリを再起動する。

    - ビルド版: 現在の exe を置き換えた上で再起動する
    - 通常実行版 (python main.py): ダウンロードした exe を起動する
    """
    if getattr(sys, "frozen", False):
        current = sys.executable
        try:
            os.replace(new_exe, current)
        except OSError:
            # 実行中ファイルの置き換えに失敗した場合は、
            # 次回起動時に置き換えるための一時ファイルを残す
            marker = current + ".new"
            try:
                os.replace(new_exe, marker)
            except OSError:
                pass
        subprocess.Popen([current])
        sys.exit(0)
    else:
        # 通常実行時はダウンロードした exe を起動して終了
        subprocess.Popen([new_exe])
        sys.exit(0)
