import re
EMPTY_RE = re.compile(r"s/(o\*|\^|\$|x\*|\[aeiou\]\*|)/")
def fair(e):
    s = e["script"]; a = e["args"]
    if "-G" in a: return False
    if EMPTY_RE.search(s): return False
    if "no newline at end" in e["files"].get("f.txt", ""): return False
    if "missing.txt" in a: return False
    return True
