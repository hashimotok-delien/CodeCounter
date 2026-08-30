import os
import sys

# 除外するディレクトリ
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    ".env",
}

def analyze_python_project(root_dir: str):
    total_files = 0
    total_lines = 0
    total_chars = 0

    for root, dirs, files in os.walk(root_dir):
        # 除外ディレクトリを walk 対象から外す
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                total_files += 1
                total_lines += content.count("\n") + 1 if content else 0
                total_chars += len(content)

            except Exception as e:
                print(f"⚠ 読み込み失敗: {file_path} ({e})")

    return total_files, total_lines, total_chars


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python analyze.py <project_path>")
        sys.exit(1)

    project_path = sys.argv[1]

    if not os.path.exists(project_path):
        print(f"❌ 指定されたパスが存在しません: {project_path}")
        sys.exit(1)

    files, lines, chars = analyze_python_project(project_path)

    print("📊 Pythonプロジェクト集計結果")
    print(f"対象　パス: {os.path.abspath(project_path)}")
    print(f"ファイル数: {files}")
    print(f"行　　　数: {lines}")
    print(f"文　字　数: {chars}")
