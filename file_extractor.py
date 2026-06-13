import os

# =====================================================
# CONFIGURATION
# =====================================================

IGNORE_DIRS = {
    "venv", "node_modules", ".git", "__pycache__",
    "dist", "build", ".idea", ".vscode", "env",
    ".mypy_cache", "coverage", "htmlcov"
}

SUPPORTED_EXTENSIONS = (
    ".py", ".js", ".ts", ".java", ".go",
    ".c", ".cpp", ".cs", ".rb", ".php",
    ".swift", ".kt", ".rs", ".html", ".css", ".jl"
)

MAX_FILE_SIZE = 500 * 1024  # 500 KB


def get_code_files(path):
    """
    Recursively walks the repo and returns all source code
    file paths, skipping ignored directories and large files.
    """
    code_files = []

    for root, dirs, files in os.walk(path):

        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if file.endswith(SUPPORTED_EXTENSIONS):
                full_path = os.path.join(root, file)

                try:
                    if os.path.getsize(full_path) > MAX_FILE_SIZE:
                        continue
                except OSError:
                    continue

                code_files.append(full_path)

    return code_files

# =====================================================
# IMPORTANT FILE PRIORITY
# =====================================================

PRIORITY_NAMES = [

    "main.py",
    "app.py",
    "server.py",
    "core.py",
    "api.py",
    "models.py",
    "routes.py",
    "views.py",
    "utils.py",
    "config.py",
    "settings.py",

    "index.js",
    "server.js",
    "app.js",
    "router.js",
    "main.js",

    "index.ts",
    "app.ts",
    "server.ts",

    "App.jsx",
    "App.tsx",

    "Main.java",
    "main.cpp"
]

# =====================================================
# SELECT IMPORTANT FILES
# =====================================================

def get_important_files(
    all_files,
    max_files=10
):

    priority = []

    others = []

    for file in all_files:

        name = os.path.basename(file)

        if name.lower() in [

            p.lower()
            for p in PRIORITY_NAMES
        ]:

            priority.append(file)

        else:

            others.append(file)

    # SORT BY FILE SIZE
    others.sort(

        key=lambda f: os.path.getsize(f),

        reverse=True
    )

    # REMOVE DUPLICATES
    selected = []

    seen = set()

    for file in priority + others:

        if file not in seen:

            selected.append(file)

            seen.add(file)

    return selected[:max_files]