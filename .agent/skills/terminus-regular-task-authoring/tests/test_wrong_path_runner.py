from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "wrong_path_runner.py"
SPEC = importlib.util.spec_from_file_location("wrong_path_runner", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


PATCH = """diff --git a/src/scale.py b/src/scale.py
--- a/src/scale.py
+++ b/src/scale.py
@@ -1,3 +1,3 @@
 def depth(w, h):
-    return w
+    return min(w, h)
@@ -9,3 +9,3 @@
 def halve(n):
-    return n // 2
+    return (n + 1) // 2
diff --git a/src/bound.py b/src/bound.py
--- a/src/bound.py
+++ b/src/bound.py
@@ -4,3 +4,3 @@
 def clamp(i, n):
-    return max(0, n - 1)
+    return min(max(i, 0), n - 1)
"""


def test_every_hunk_of_the_reference_fix_is_one_seeded_departure() -> None:
    """For a seeded-departure task the mutant catalogue is the patch itself."""
    hunks = MODULE.split_hunks(PATCH)

    assert [h["index"] for h in hunks] == [1, 2, 3]
    assert [h["file"] for h in hunks] == ["b/src/scale.py", "b/src/scale.py", "b/src/bound.py"]


def test_dropping_a_hunk_leaves_that_one_departure_in_place() -> None:
    reduced = MODULE.patch_without_hunk(PATCH, 2)

    assert "return (n + 1) // 2" not in reduced
    assert "return min(w, h)" in reduced
    assert "return min(max(i, 0), n - 1)" in reduced


def test_dropping_a_hunk_keeps_the_file_headers_the_survivors_need() -> None:
    reduced = MODULE.patch_without_hunk(PATCH, 1)

    assert reduced.count("+++ b/src/scale.py") == 1
    assert reduced.count("+++ b/src/bound.py") == 1


def test_a_ctrf_report_separates_failures_from_controls(tmp_path: Path) -> None:
    ctrf = tmp_path / "ctrf.json"
    ctrf.write_text(
        '{"results": {"tests": ['
        '{"name": "t::a", "status": "failed"},'
        '{"name": "t::b", "status": "passed"},'
        '{"name": "t::c", "status": "skipped"}]}}'
    )

    failed, passed = MODULE.failing_from_ctrf(ctrf)

    assert failed == {"t::a"}
    assert passed == {"t::b"}
