def read_file(path):
    """
    Reads and returns the text content of a file.
    Returns empty string on any failure.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        print(f"File not found: {path}")
        return ""
    except PermissionError:
        print(f"Permission denied: {path}")
        return ""
    except Exception as e:
        print(f"Could not read {path}: {e}")
        return ""