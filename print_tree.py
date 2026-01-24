
import os

def print_tree(start_path, prefix="", exclude_dirs=None, exclude_files=None):
    exclude_dirs = exclude_dirs or set()
    exclude_files = exclude_files or set()

    for item in sorted(os.listdir(start_path)):
        if item in exclude_dirs or item in exclude_files:
            continue

        path = os.path.join(start_path, item)
        if os.path.isdir(path):
            print(f"{prefix}📁 {item}/")
            print_tree(path, prefix + "    ", exclude_dirs, exclude_files)
        else:
            print(f"{prefix}📄 {item}")

# Получаем путь к директории, где лежит сам скрипт
script_dir = os.path.dirname(os.path.abspath(__file__))

# Вызов с исключениями
print_tree(script_dir, exclude_dirs={"__pycache__", ".git", "venv"}, exclude_files={".DS_Store"})


