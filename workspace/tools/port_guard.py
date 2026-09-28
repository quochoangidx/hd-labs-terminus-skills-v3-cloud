"""port_guard.py <task-dir> <tool> <package> <binary>

Install the construction-rule launcher (tests/guard.py, from the ed revision) into a
live-binary reimplementation task: every graded candidate run goes through the launcher,
which ends a run that starts another program, loads native code or imports code from
outside the standard library and the delivered package; two tests check the launcher on
probe programs and read the delivered package.
"""
import os
import re
import shutil
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v1/tbrain-gnu-ed-reimplementation/tests")
task, tool, pkg, binary = sys.argv[1:5]
tests = os.path.join(task, "tests")
guard_dir = "/opt/%sguard" % pkg

# guard.py and its probe programs
g = open(os.path.join(SRC, "guard.py")).read()
g = g.replace("delivered ed", "delivered %s" % tool).replace("GNU ed", "GNU %s" % tool)
g = g.replace('MARKER = "pyed-guard: "', 'MARKER = "%s-guard: "' % pkg)
open(os.path.join(tests, "guard.py"), "w").write(g)
for sub in ("guardcheck", "guardvendor"):
    shutil.rmtree(os.path.join(tests, sub), ignore_errors=True)
    shutil.copytree(os.path.join(SRC, sub), os.path.join(tests, sub))
for name in ("exec_launcher.py", "launcher.py"):
    p = os.path.join(tests, "guardcheck", name)
    body = open(p).read().replace("/usr/bin/ed", binary).replace('["ed"]', '["%s"]' % tool)
    open(p, "w").write(body)
open(os.path.join(tests, "guardcheck", "native.py"), "w").write(
    '"""A program that loads native code through ctypes: the launcher must stop it."""\n'
    "import ctypes\nimport ctypes.util\n\n"
    'libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")\nprint("native", libc.abs(-3))\n')
p = os.path.join(tests, "guardcheck", "vendored.py")
body = open(p).read().replace("/opt/pyedguard", guard_dir)
open(p, "w").write(body)

# Dockerfile: a readable copy of the launcher outside the sealed /tests
p = os.path.join(tests, "Dockerfile")
d = open(p).read()
if "guard.py" not in d:
    d = d.replace("COPY . /tests/\n", "COPY . /tests/\nRUN mkdir -p %s && cp -r /tests/guard.py /tests/guardcheck /tests/guardvendor %s/ \\\n"
                  "    && chmod -R a+rX %s\n" % (guard_dir, guard_dir, guard_dir))
open(p, "w").write(d)

# test_outputs.py: route the candidate through the launcher, add the two construction tests
p = os.path.join(tests, "test_outputs.py")
t = open(p).read()
if "GUARD = " in t:
    print("test_outputs.py already routed through the launcher")
    sys.exit(0)
entry = re.search(r'CANDIDATE = \["/usr/local/bin/python3", "([^"]+)"\]', t).group(1)
t = t.replace('CANDIDATE = ["/usr/local/bin/python3", "%s"]' % entry,
              'PYTHON = "/usr/local/bin/python3"\nGUARD = "%s/guard.py"\nGUARDCHECK = "%s/guardcheck"\n'
              'DELIVERED = "/app"\nENTRY = "%s"\nCANDIDATE = [PYTHON, GUARD, ENTRY]' % (guard_dir, guard_dir, entry))
t = t.replace('ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent"}',
              'ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",\n'
              '       "PYTHONDONTWRITEBYTECODE": "1"}')
t = t.replace("import json\n", "import ast\nimport json\n", 1)
t = t.replace("import subprocess\n", "import subprocess\nimport sys\n", 1)
doc_end = t.index('"""', 3)
t = (t[:doc_end].rstrip() + "\n\nThe candidate runs through the launcher in guard.py, which stops a run that starts another\n"
     "program, loads native code or imports code from outside the standard library.\n" + t[doc_end:])
extra = '''

def guardcheck(program, args=(), expect_status=None):
    """Run one of the launcher's own probe programs the way a candidate is run."""
    path = tempfile.mkdtemp()
    os.chmod(path, 0o777)
    try:
        proc = subprocess.Popen(DEMOTE + [PYTHON, GUARD, os.path.join(GUARDCHECK, program)] + list(args),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=path, env=ENV, start_new_session=True)
        out, err = proc.communicate(timeout=20)
        return proc.returncode, out, err
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_launcher_stops_delegation_and_foreign_code():
    """The construction rules are enforced, and an ordinary program is left alone."""
    for program in ("launcher.py", "exec_launcher.py", "vendored.py", "native.py"):
        status, out, err = guardcheck(program, ["--version"])
        assert status == 120, f"{program}: expected the launcher to stop it, got status {status} and {out!r}"
        assert b"PKG-guard: " in err, f"{program}: no reason reported, stderr {err!r}"
        assert b"TOOLVER" not in out and b"vendored" not in out and b"native" not in out, f"{program}: it produced {out!r}"
    status, out, _err = guardcheck("plain.py", ["x"])
    assert (status, out) == (0, b"plain plain.py x\\nre bb\\n"), f"the launcher changed an ordinary run: {status} {out!r}"
    status, _out, _err = guardcheck("plain.py", ["fail"])
    assert status == 3, f"the launcher lost the exit status: {status}"


def delivered_files():
    """Every delivered file, leaving out the interpreter's own bytecode caches."""
    for root, dirs, names in os.walk(DELIVERED):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            if not name.endswith(".pyc"):
                yield os.path.join(root, name)


def test_delivered_package_is_standard_library_python():
    """Everything delivered is Python text importing only the standard library and itself."""
    local = {"PKG"}
    sources = {}
    for full in delivered_files():
        if os.path.islink(full) and not os.path.realpath(full).startswith(DELIVERED + os.sep):
            raise AssertionError(f"{full} points outside the delivered package")
        with open(full, "rb") as handle:
            raw = handle.read()
        if b"\\x00" in raw or raw[:4] == b"\\x7fELF":
            raise AssertionError(f"{full} is not text: only Python sources and text belong here")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as bad:
            raise AssertionError(f"{full} is not text: {bad}")
        if full.endswith(".py"):
            sources[full] = text
            local.add(os.path.splitext(os.path.basename(full))[0])
    assert ENTRY in sources, f"{ENTRY} is missing from the delivered package"
    for full, text in sorted(sources.items()):
        try:
            tree = ast.parse(text, filename=full)
        except SyntaxError as bad:
            raise AssertionError(f"{full} does not parse: {bad}")
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                assert top in sys.stdlib_module_names or top in local, (
                    f"{full} imports {name}, which is neither the standard library nor part of "
                    "the delivered package")
'''
extra = extra.replace("PKG", pkg).replace("TOOLVER", {"grep": "GNU grep", "bc": "bc 1."}.get(tool, "GNU " + tool))
if "def test_launcher_stops_delegation_and_foreign_code" not in t:
    t = t.rstrip() + "\n" + extra
open(p, "w").write(t)
print("ported guard into", task, "entry", entry)
