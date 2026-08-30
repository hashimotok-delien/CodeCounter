"""CodeCounter の Tkinter GUI。

- フォルダ選択ダイアログから集計対象を選ぶ
- 集計結果（ファイル数・行数・文字数）を表示
- ファイル別一覧（行数・文字数）を Treeview で表示
- 設定（拡張子・除外ディレクトリ・更新設定）を settings.yml へ保存
- 起動時に GitHub の更新を確認し、あれば通知・更新を促す
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app import __version__ as VERSION
from app.analyzer import ProjectSummary, analyze_project
from app.settings import (
    DEFAULT_SETTINGS,
    ensure_settings_file,
    load_settings,
    save_settings,
)
from app.updater import (
    UpdateError,
    check_for_update,
    install_update,
    restart_application,
)


def resource_path(name: str) -> str:
    """アプリに同梱されたリソース（icon.png など）の実パスを返す。

    PyInstaller 実行時（--onefile）は _MEIPASS 直下、それ以外は
    プロジェクトルートを基準にする。
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, name)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, name)


def set_window_icon(root: tk.Tk) -> None:
    """ウィンドウアイコンを icon.png から設定する。"""
    icon_path = resource_path("icon.png")
    if not os.path.exists(icon_path):
        return
    try:
        icon = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, icon)
    except tk.TclError:
        # 不正な画像などは無視して起動を継続する
        pass


class CodeCounterApp:
    """メイン GUI アプリケーション。"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"CodeCounter v{VERSION}")
        self.root.geometry("820x560")
        self.root.minsize(640, 420)
        set_window_icon(root)

        self.settings = ensure_settings_file()
        self.summary: ProjectSummary | None = None

        self._build_widgets()
        self._check_update_on_startup()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        """ウィジェット一式を構築する。"""
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        # フォルダ選択
        top = ttk.Frame(main)
        top.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(top, text="対象フォルダ:").pack(side=tk.LEFT)
        self.folder_var = tk.StringVar(
            value=getattr(sys, "frozen", False)
            and os.path.dirname(sys.executable) or os.getcwd()
        )
        self.folder_entry = ttk.Entry(top, textvariable=self.folder_var)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(
            top, text="参照...", command=self._browse_folder
        ).pack(side=tk.LEFT)
        self.analyze_button = ttk.Button(
            top, text="集計", command=self._start_analyze
        )
        self.analyze_button.pack(side=tk.LEFT, padx=(4, 0))

        # ツールバー
        bar = ttk.Frame(main)
        bar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(bar, text="設定...", command=self._open_settings).pack(
            side=tk.LEFT
        )
        self.status_var = tk.StringVar(value="集計対象フォルダを選択してください")
        ttk.Label(bar, textvariable=self.status_var).pack(
            side=tk.LEFT, padx=8, anchor=tk.W
        )

        # サマリー表示
        self.summary_var = tk.StringVar(value="")
        ttk.Label(
            main,
            textvariable=self.summary_var,
            font=("", 11, "bold"),
            anchor=tk.W,
        ).pack(fill=tk.X, pady=(0, 6))

        # ファイル一覧
        columns = ("path", "lines", "chars")
        self.tree = ttk.Treeview(main, columns=columns, show="headings")
        self.tree.heading("path", text="ファイル")
        self.tree.heading("lines", text="行数")
        self.tree.heading("chars", text="文字数")
        self.tree.column("path", width=520, anchor=tk.W)
        self.tree.column("lines", width=90, anchor=tk.E)
        self.tree.column("chars", width=90, anchor=tk.E)
        scroll = ttk.Scrollbar(
            main, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # フォルダ選択・集計
    # ------------------------------------------------------------------
    def _browse_folder(self) -> None:
        """フォルダ選択ダイアログを開く。"""
        initial = self.folder_var.get() or os.getcwd()
        if not os.path.isdir(initial):
            initial = os.getcwd()
        selected = filedialog.askdirectory(
            title="集計対象フォルダを選択", initialdir=initial
        )
        if selected:
            self.folder_var.set(selected)

    def _start_analyze(self) -> None:
        """バックグラウンドで集計を開始する。"""
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning(
                "フォルダ未指定", "有効なフォルダを選択してください。"
            )
            return

        self.analyze_button.config(state=tk.DISABLED)
        self.status_var.set("集計中...")
        self.summary_var.set("")

        thread = threading.Thread(
            target=self._analyze_worker, args=(folder,), daemon=True
        )
        thread.start()

    def _analyze_worker(self, folder: str) -> None:
        """集計ワーカー（別スレッドで実行）。"""
        try:
            summary = analyze_project(
                folder,
                extensions=self.settings.get(
                    "extensions", DEFAULT_SETTINGS["extensions"]
                ),
                exclude_dirs=self.settings.get(
                    "exclude_dirs", DEFAULT_SETTINGS["exclude_dirs"]
                ),
                include_hidden=self.settings.get(
                    "include_hidden", DEFAULT_SETTINGS["include_hidden"]
                ),
            )
        except Exception as e:  # noqa: BLE001
            self.root.after(0, self._show_analyze_error, str(e))
            return
        self.root.after(0, self._show_result, summary)

    def _show_analyze_error(self, message: str) -> None:
        """集計エラーを表示する。"""
        self.analyze_button.config(state=tk.NORMAL)
        self.status_var.set("集計に失敗しました")
        messagebox.showerror("集計エラー", message)

    def _show_result(self, summary: ProjectSummary) -> None:
        """集計結果を UI へ反映する。"""
        self.analyze_button.config(state=tk.NORMAL)
        self.summary = summary
        self.status_var.set(
            f"集計完了: {summary.total_files} ファイル, "
            f"{summary.total_lines} 行, {summary.total_chars} 文字"
        )
        self.summary_var.set(
            f"📊 ファイル数: {summary.total_files}  |  "
            f"行数: {summary.total_lines}  |  文字数: {summary.total_chars}"
        )
        self.tree.delete(*self.tree.get_children())
        for f in summary.files:
            self.tree.insert(
                "",
                tk.END,
                values=(f.path, f.lines, f.chars),
            )

        if summary.errors and messagebox.askyesno(
            "一部ファイルを読めませんでした",
            f"{len(summary.errors)} 件のファイルで読み込みに失敗しました。\n"
            "詳細を表示しますか？",
        ):
            messagebox.showwarning(
                "読み込み失敗の詳細",
                "\n".join(summary.errors[:50]),
            )

    # ------------------------------------------------------------------
    # 設定ダイアログ
    # ------------------------------------------------------------------
    def _open_settings(self) -> None:
        """設定ダイアログを開く。"""
        current = load_settings()

        dialog = tk.Toplevel(self.root)
        dialog.title("設定")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("460x260")

        pad = ttk.Frame(dialog, padding=12)
        pad.pack(fill=tk.BOTH, expand=True)

        # 拡張子
        ttk.Label(pad, text="集計対象の拡張子（カンマ区切り）:").grid(
            row=0, column=0, sticky=tk.W, pady=4
        )
        ext_var = tk.StringVar(
            value=", ".join(
                current.get("extensions", DEFAULT_SETTINGS["extensions"])
            )
        )
        ext_entry = ttk.Entry(pad, textvariable=ext_var, width=40)
        ext_entry.grid(row=1, column=0, sticky=tk.W + tk.E, pady=4)

        # 除外ディレクトリ
        ttk.Label(pad, text="除外ディレクトリ名（カンマ区切り）:").grid(
            row=2, column=0, sticky=tk.W, pady=4
        )
        exc_var = tk.StringVar(
            value=", ".join(
                current.get("exclude_dirs", DEFAULT_SETTINGS["exclude_dirs"])
            )
        )
        exc_entry = ttk.Entry(pad, textvariable=exc_var, width=40)
        exc_entry.grid(row=3, column=0, sticky=tk.W + tk.E, pady=4)

        # 隠しファイルを含める
        hidden_var = tk.BooleanVar(
            value=current.get(
                "include_hidden", DEFAULT_SETTINGS["include_hidden"]
            )
        )
        ttk.Checkbutton(
            pad, text="隠しファイル・隠しディレクトリも集計する", variable=hidden_var
        ).grid(row=4, column=0, sticky=tk.W, pady=4)

        # 更新設定
        auto_var = tk.BooleanVar(
            value=current.get(
                "auto_check_update", DEFAULT_SETTINGS["auto_check_update"]
            )
        )
        ttk.Checkbutton(
            pad, text="起動時にアップデートを確認する", variable=auto_var
        ).grid(row=5, column=0, sticky=tk.W, pady=4)

        btn = ttk.Frame(pad)
        btn.grid(row=6, column=0, sticky=tk.E, pady=(8, 0))

        def on_save() -> None:
            """設定を保存してダイアログを閉じる。"""
            ext_list = _split_csv(ext_var.get())
            exc_list = _split_csv(exc_var.get())
            new_settings = {
                "extensions": ext_list,
                "exclude_dirs": exc_list,
                "include_hidden": hidden_var.get(),
                "auto_check_update": auto_var.get(),
                "update_channel": current.get(
                    "update_channel", DEFAULT_SETTINGS["update_channel"]
                ),
            }
            try:
                save_settings(new_settings)
            except OSError as e:
                messagebox.showerror("保存エラー", f"設定の保存に失敗しました: {e}")
                return
            self.settings = load_settings()
            dialog.destroy()

        ttk.Button(btn, text="保存", command=on_save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn, text="キャンセル", command=dialog.destroy).pack(
            side=tk.LEFT
        )

    # ------------------------------------------------------------------
    # アップデート機能
    # ------------------------------------------------------------------
    def _check_update_on_startup(self) -> None:
        """起動時に更新を確認する（自動更新設定が有効な場合のみ）。"""
        if not self.settings.get(
            "auto_check_update", DEFAULT_SETTINGS["auto_check_update"]
        ):
            return
        thread = threading.Thread(
            target=self._update_check_worker, daemon=True
        )
        thread.start()

    def _update_check_worker(self) -> None:
        """更新確認ワーカー。"""
        channel = self.settings.get(
            "update_channel", DEFAULT_SETTINGS["update_channel"]
        )
        info = check_for_update(channel=channel)
        if info.available:
            self.root.after(
                0, lambda: self._prompt_update(info.summary)
            )

    def _prompt_update(self, message: str) -> None:
        """更新をユーザーへ通知する。"""
        if not messagebox.askyesno("アップデート", message + "\n\n今すぐ更新しますか？"):
            return
        if messagebox.askyesno(
            "確認",
            "アプリを終了して更新を実行します。よろしいですか？\n"
            "（更新完了後に自動的に再起動します）",
        ):
            self._perform_update()

    def _perform_update(self) -> None:
        """更新処理を実施する。"""
        channel = self.settings.get(
            "update_channel", DEFAULT_SETTINGS["update_channel"]
        )
        self.status_var.set("更新を確認中...")
        thread = threading.Thread(
            target=self._update_worker, args=(channel,), daemon=True
        )
        thread.start()

    def _update_worker(self, channel: str) -> None:
        """更新ダウンロードを実行するワーカー。"""
        try:
            info = check_for_update(channel=channel)
            if not info.available:
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "アップデート", "最新バージョンです。"
                    ),
                )
                return
            new_exe = install_update(info)
            self.root.after(0, self._finish_update, new_exe)
        except UpdateError as e:
            err = str(e)
            self.root.after(0, lambda: messagebox.showerror("更新エラー", err))
        except Exception as e:  # noqa: BLE001
            err = str(e)
            self.root.after(0, lambda: messagebox.showerror("更新エラー", err))

    def _finish_update(self, new_exe: str) -> None:
        """更新完了後に再起動する。"""
        try:
            restart_application(new_exe)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(
                "再起動エラー",
                f"再起動に失敗しました: {e}\n"
                f"更新済みファイル: {new_exe}",
            )


def _split_csv(text: str) -> list[str]:
    """カンマ区切りのテキストをリストに分割して整形する。

    各項目はトリムし、先頭ドットがなければ付与する。
    """
    result = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        item = item.lower()
        if not item.startswith("."):
            item = f".{item}"
        if item not in result:
            result.append(item)
    return result or [".py"]


def main() -> None:
    """GUI を起動する。"""
    root = tk.Tk()
    # Windows で DPI 設定を明示
    try:
        from ctypes import windll  # type: ignore[attr-defined]

        windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

    CodeCounterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
