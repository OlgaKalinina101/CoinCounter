"""
Utility script to count lines of Python code in the project.

Excludes virtual environments, cache directories, and git files.
"""
import os

EXCLUDE_DIRS = {"venv", ".venv", "__pycache__", ".git", ".mypy_cache"}


def count_py_lines_clean(base_dir="."):
    """
    Count total lines of Python code in the project.

    Args:
        base_dir (str): Base directory to start counting from. Defaults to current directory.

    Returns:
        int: Total number of lines in all Python files.
    """
    total_lines = 0
    for root, dirs, files in os.walk(base_dir):
        # Exclude unwanted directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(".py"):
                try:
                    file_path = os.path.join(root, file)
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        total_lines += sum(1 for _ in f)
                except Exception as e:
                    print(f"Error reading {file}: {e}")
    return total_lines


if __name__ == "__main__":
    line_count = count_py_lines_clean()
    print(f"Total lines of Python code: {line_count}")