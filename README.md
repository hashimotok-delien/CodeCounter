# CodeCounter

Python プロジェクトのコード量を集計する Windows デスクトップアプリです。

- ファイル数・行数・文字数を集計して表示
- ファイルごとの一覧表示（行数・文字数）
- 対象拡張子や除外ディレクトリを設定可能
- GitHub リリースのアップデート通知・自動更新

## 動作環境

- Windows 10 / 11
- Python 3.9 以上（ソースコード実行時）

## 使い方

### GUI として起動

```bash
python main.py
```

起動するとウィンドウが開きます。

1. 「参照...」で集計したいフォルダを選択
2. 「集計」ボタンを押す
3. ファイル数・行数・文字数と、ファイル別一覧が表示されます

### コマンドライン（従来方式）

```bash
python main.py <プロジェクトのパス>
```

## 設定

初回起動時にプロジェクト直下へ `settings.yml` が自動生成されます。

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `extensions` | `[".py"]` | 集計対象の拡張子 |
| `exclude_dirs` | 複数 | 除外するディレクトリ名 |
| `include_hidden` | `false` | 隠しファイルを集計するか |
| `auto_check_update` | `true` | 起動時にアップデートを確認するか |
| `update_channel` | `stable` | `stable` か `prerelease` |
| `font_scale` | `1.0` | 文字サイズ倍率（`1.0`〜`2.0`） |

GUI の「設定...」からも変更できます。

## 4K / 高 DPI ディスプレイ

- 起動時に Windows の DPI（拡大率）を自動検出し、文字サイズ・ウィンドウサイズを連動させます
- さらに「設定... → 文字サイズ倍率」で手動で拡大（最大 2.0 倍）できます
- 文字サイズの変更は次回起動時に反映されます

## exe のビルド

```bash
pip install -r requirements.txt
python build_exe.py
```

`dist/CodeCounter.exe` が生成されます（ターミナル画面なしの GUI アプリ）。

### アイコン

プロジェクトルートに `icon.png` を置くと、ビルド時に自動で `icon.ico` へ変換され、
以下へ反映されます。

- exe ファイル自体のアイコン
- アプリ起動時のウィンドウアイコン

`icon.png` が無い場合は既定のアイコンでビルドされます。

### バージョンの指定

```bash
python build_exe.py --version 1.1.0
```

## リリース / アップデート配布

`v*` タグを push すると GitHub Actions が自動ビルドして GitHub リリースを作成します。

```bash
git tag v1.0.0
git push origin v1.0.0
```

リリースに `CodeCounter.exe` が含まれていれば、アプリ起動時（または手動更新）に
最新版かどうかを確認し、ダウンロードして再起動します。

## 構成

```
main.py                 # エントリポイント
build_exe.py            # exe ビルド補助
CodeCounter.spec        # PyInstaller 設定 (console=False)
app/
  version.py            # バージョン管理
  settings.py           # settings.yml 読み書き
  analyzer.py           # 集計ロジック
  updater.py            # GitHub リリース確認・更新
  gui.py                # Tkinter GUI
.github/workflows/      # リリースビルド
```