#!/usr/bin/env python3
"""Shared static checks for untrusted verifier execution and prompt symmetry."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


BUILD_OR_CANDIDATE_RE = re.compile(
    r"(?i)(?:\bmake\b|\bgo\b|\bcargo\b|\brustc\b|\bgcc\b|\bg\+\+\b|"
    r"\bclang\b|\bjavac\b|\bmvn\b|\bgradle\b|\bnpm\b|\bpnpm\b|\byarn\b|"
    r"/app(?:/|\b)|\bapp_dir\b|\bcandidate\b|\bbinary\b|\bbin_name\b)"
)
UNIT_TEST_PROMISE_RE = re.compile(
    r"(?is)(?:unit|existing|repository|pre-existing)[ -]tests?.{0,100}"
    r"(?:keep|remain|continue|still|must).{0,40}(?:pass|passing|green)"
    r"|(?:keep|preserve).{0,80}(?:unit|existing|repository|pre-existing)[ -]tests?"
)
UNIT_TEST_EXECUTION_RE = re.compile(
    r"(?i)(?:\bgo\s+test\b|[\"']go[\"']\s*,\s*[\"']test[\"']|"
    r"\bmake\s+test\b|[\"']make[\"']\s*,\s*[\"']test[\"'])"
)


@dataclass(frozen=True)
class UnsafeCandidateCall:
    line: int
    function: str
    expression: str


def _call_name(node: ast.Call) -> str:
    try:
        return ast.unparse(node.func)
    except Exception:
        return ""


def _node_text(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _is_process_call(node: ast.Call) -> bool:
    name = _call_name(node)
    return name in {
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "os.system",
        "os.popen",
    }


# Tools that read candidate bytes without handing them control: a disassembler or a
# symbol dumper produces text, it never executes what it is pointed at. Auditing a
# candidate artifact with one of these is the safe shape, not a privilege defect.
# Deliberately narrow: the tool name must appear as a quoted command token, optionally
# with a path. A bare identifier is not enough — a false negative here would wave a real
# candidate execution through, which is far worse than one noisy row.
STATIC_ANALYSIS_RE = re.compile(
    r"""(?ix)
    ['"]                          # a string literal, i.e. an argv entry
    (?:/\S*/)?                    # optional absolute path
    (?:javap|readelf|objdump|nm|strings)
    ['"]
    """
)


def _static_analysis_names(tree: ast.AST) -> set[str]:
    """Names bound to a static-analysis tool, e.g. `JAVAP = shutil.which("javap")`.

    Verifiers normally resolve the tool once and reuse the constant, so matching only
    inline literals would miss the common spelling.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        if node.value is None or not STATIC_ANALYSIS_RE.search(_node_text(node.value)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def _is_static_analysis(node: ast.Call, tool_names: frozenset[str] = frozenset()) -> bool:
    """True when the call only disassembles or dumps candidate bytes.

    These tools turn an artifact into text; they never hand it control. Auditing a
    candidate class file with `javap -v` is the safe shape the anti-cheat design asks
    for, so flagging it as an undemoted candidate execution is a false alarm.
    """
    rendered = _node_text(node)
    if STATIC_ANALYSIS_RE.search(rendered):
        return True
    return any(re.search(rf"(?:^|[\s(\[,]){name}(?=[\s,\])]|$)", rendered) for name in tool_names)


def _is_candidate_controlled(
    node: ast.Call, function_name: str, tool_names: frozenset[str] = frozenset()
) -> bool:
    rendered = _node_text(node)
    if _is_static_analysis(node, tool_names):
        return False
    if re.search(r"(?i)(candidate|simulator|compile|build)", function_name):
        return True
    if BUILD_OR_CANDIDATE_RE.search(rendered):
        return True
    for keyword in node.keywords:
        if keyword.arg == "cwd" and BUILD_OR_CANDIDATE_RE.search(_node_text(keyword.value)):
            return True
    return False


def _is_demoted(node: ast.Call) -> bool:
    keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg}
    if {"user", "group"}.issubset(keyword_names):
        return True
    for keyword in node.keywords:
        if keyword.arg is None:
            value = _node_text(keyword.value)
            if re.search(r"(?i)(candidate.*user|user.*kwargs|unprivileged|demot)", value):
                return True
    rendered = _node_text(node)
    return bool(re.search(r"(?i)(?:setpriv|runuser|su-exec)", rendered))


class _CandidateCallVisitor(ast.NodeVisitor):
    def __init__(self, tool_names: frozenset[str] = frozenset()) -> None:
        self.tool_names = tool_names
        self.function_stack: list[str] = []
        self.unsafe: list[UnsafeCandidateCall] = []
        self.candidate_call_count = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        function_name = self.function_stack[-1] if self.function_stack else "<module>"
        if _is_process_call(node) and _is_candidate_controlled(node, function_name, self.tool_names):
            self.candidate_call_count += 1
            if not _is_demoted(node):
                expression = " ".join(_node_text(node).split())[:240]
                self.unsafe.append(
                    UnsafeCandidateCall(
                        line=getattr(node, "lineno", 0),
                        function=function_name,
                        expression=expression,
                    )
                )
        self.generic_visit(node)


def analyze_candidate_privileges(source: str) -> tuple[int, list[UnsafeCandidateCall]]:
    """Return candidate-controlled subprocess count and calls lacking demotion."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0, []
    visitor = _CandidateCallVisitor(frozenset(_static_analysis_names(tree)))
    visitor.visit(tree)
    return visitor.candidate_call_count, visitor.unsafe


def unit_test_alignment_issue(contract_text: str, verifier_source: str) -> bool:
    """Detect an explicit unit-test preservation promise with no matching run."""
    return bool(
        UNIT_TEST_PROMISE_RE.search(contract_text)
        and not UNIT_TEST_EXECUTION_RE.search(verifier_source)
    )


DOCUMENTED_MODULE_RE = re.compile(r"\bpython3?\s+-m\s+([A-Za-z_][\w.]*)")
TOOLING_MODULES = frozenset({"pytest", "pip", "venv", "http.server", "json.tool", "unittest"})


def documented_module_unexecuted(instruction_text: str, verifier_source: str) -> list[str]:
    """Modules the instruction runs with `python -m` that the verifier never launches.

    Grading an entry point by importing the function behind it leaves the documented
    command itself unexercised, so a broken `__main__` still earns reward.
    """
    missing = []
    for module in sorted(set(DOCUMENTED_MODULE_RE.findall(instruction_text)) - TOOLING_MODULES):
        quoted = re.escape(module)
        launched = (
            re.search(rf"[\"']-m[\"']\s*,\s*[\"']{quoted}[\"']", verifier_source)
            or re.search(rf"\bpython3?\s+-m\s+{quoted}\b", verifier_source)
            or re.search(rf"run_module\(\s*[\"']{quoted}[\"']", verifier_source)
        )
        if not launched:
            missing.append(module)
    return missing


# Making a candidate artifact setuid/setgid, or granting it capabilities, is what turns
# a missing no-new-privs guard into a real escalation path.
PRIVILEGE_ACQUIRABLE_RE = re.compile(
    # A setuid/setgid/sticky mode in any of the spellings a verifier actually writes:
    # 0o4755, 04755, 4755, plus the symbolic and capability forms.
    r"(?i)(?:\b0?o?[2467][0-7]{3}\b|\bS_ISUID\b|\bS_ISGID\b|chmod\s+[ug]\+s|\bsetcap\b)"
)


def setpriv_missing_no_new_privs(source: str) -> bool:
    """Flag a setpriv-based boundary that omits the no-new-privileges guard."""
    return bool(re.search(r"(?i)\bsetpriv\b", source)) and "--no-new-privs" not in source


def privilege_acquirable(source: str) -> bool:
    """Whether anything here could let demoted candidate code regain privilege.

    The platform's own judge guidance is explicit that a missing ``--no-new-privs``
    flag alone is not a confirmed finding without evidence that the executed binary can
    acquire the privilege — the escalation needs a setuid-root or capability-bearing
    artifact to exist in the first place.
    """
    return bool(PRIVILEGE_ACQUIRABLE_RE.search(source))


def test_identity_leak(source: str) -> bool:
    """Flag the known pytest-node-name channel into candidate-visible state."""
    return bool(re.search(r"\brequest\s*\.\s*node\s*\.\s*name\b", source))


def live_reference_binaries(source: str, slug: str) -> list[str]:
    """System binaries the verifier runs that are the tool the task reimplements.

    A verifier that runs GNU ed on every case at grading time ships a callable
    end-to-end solver with its tests, which human review treats as a High finding
    (docs/creating-tasks/writing-tests.md, "don't put a callable end-to-end solver in
    tests/"). The same docs allow precomputed goldens or hashes, which is what
    freeze_reference_goldens.py writes. Only a binary named like a word of the task
    slug counts, so the interpreter, shells and build tools are never flagged.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    words = set(re.split(r"[^a-z0-9]+", slug.lower()))
    paths: dict[str, str] = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            match = re.fullmatch(r"/(?:usr/(?:local/)?)?s?bin/([A-Za-z0-9_.+-]+)", node.value.value)
            if match and match.group(1).lower() in words:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        paths[target.id] = node.value.value
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.List) and node.elts:
            head = node.elts[0]
            if isinstance(head, ast.Name) and head.id in paths:
                found.add(paths[head.id])
            elif isinstance(head, ast.Constant) and isinstance(head.value, str):
                match = re.fullmatch(r"/(?:usr/(?:local/)?)?s?bin/([A-Za-z0-9_.+-]+)", head.value)
                if match and match.group(1).lower() in words:
                    found.add(head.value)
    return sorted(found)


CASE_LABEL_KEYS = frozenset({
    "id", "name", "label", "case", "case_id", "case_name", "scenario", "slug", "family",
    "title", "job", "job_id", "run_id", "seed",
})
TEMP_CALLS = frozenset({
    "tempfile.mkdtemp", "mkdtemp", "tempfile.TemporaryDirectory", "TemporaryDirectory",
    "tempfile.NamedTemporaryFile", "NamedTemporaryFile", "tempfile.mkstemp", "mkstemp",
})


LABEL_PARAMS = frozenset({
    "tag", "name", "label", "case", "case_id", "case_name", "scenario", "slug", "family",
    "title", "job", "job_id", "job_name", "run_id", "seed", "key",
})


def _label_part(node: ast.AST, label_params: frozenset[str] = frozenset()) -> str | None:
    """The case label an expression carries, if it reads one: case["id"], job.name, or a
    function parameter that callers fill with the case (``tag``, ``name``)."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.Constant):
            if str(sub.slice.value).lower() in CASE_LABEL_KEYS:
                return ast.unparse(sub)
        if isinstance(sub, ast.Attribute) and sub.attr.lower() in CASE_LABEL_KEYS:
            if not (isinstance(sub.value, ast.Name) and sub.value.id in {"os", "sys", "Path", "self"}):
                return ast.unparse(sub)
        if isinstance(sub, ast.Name) and sub.id in label_params:
            return sub.id
    return None


def _assigned_bases(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Subscript, ast.Attribute)) and isinstance(target.value, ast.Name):
        return [target.value.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [n for elt in target.elts for n in _assigned_bases(elt)]
    return []


def staged_case_labels(source: str) -> list[str]:
    """Places where the verifier names a candidate-visible path after the graded case.

    A file, directory or temp prefix called after the case (``empty_file.readings``,
    ``cwd-empty_file``, ``drawn-run-1003.json``, ``mkdtemp(prefix=case["id"])``) hands
    the candidate the hidden scenario label through argv or cwd, so a program can
    branch on the name instead of the content (quality panel protected_ground_truth
    Major, tbrain-cobol-statement-port v4; the sister repo's case_label_staged gate).
    Stage every case under the same neutral names inside a fresh random directory.

    A label is a case field or attribute (``case["id"]``, ``job.seed``) or a parameter
    of the enclosing function with a label-like name (``tag``, ``name``). A loop
    variable over the case's own input files is content, not a label, and is not
    flagged. Paths count when they sit under a temp directory, followed through
    assignments (``dirs[role] = os.path.join(scratch, ...)``).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    found: set[str] = set()
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for scope in functions or [tree]:
        params: frozenset[str] = frozenset()
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = scope.args
            names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
            params = frozenset(n for n in names if n.lower() in LABEL_PARAMS)
        temp: set[str] = {"tmp_path", "tmpdir"}
        body = list(ast.walk(scope))
        changed = True
        while changed:
            changed = False
            for node in body:
                value, targets = None, []
                if isinstance(node, ast.Assign):
                    value, targets = node.value, node.targets
                elif isinstance(node, ast.AnnAssign) and node.value is not None:
                    value, targets = node.value, [node.target]
                elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                    value, targets = node.context_expr, [node.optional_vars]
                if value is None:
                    continue
                is_temp = (isinstance(value, ast.Call) and _call_name(value) in TEMP_CALLS) or any(
                    isinstance(n, ast.Name) and n.id in temp for n in ast.walk(value))
                if is_temp:
                    for base in (b for t in targets for b in _assigned_bases(t)):
                        if base not in temp:
                            temp.add(base)
                            changed = True

        def under_temp(node: ast.AST) -> bool:
            return any(isinstance(n, ast.Name) and n.id in temp for n in ast.walk(node))

        for node in body:
            if isinstance(node, ast.Call):
                name = _call_name(node)
                if name in TEMP_CALLS:
                    for keyword in node.keywords:
                        if keyword.arg in {"prefix", "suffix", "dir"} and not isinstance(keyword.value, ast.Constant):
                            label = _label_part(keyword.value, params)
                            if label:
                                found.add(f"line {node.lineno}: {name}({keyword.arg}=... {label})")
                elif name in {"os.path.join", "path.join", "join"} and node.args and under_temp(node.args[0]):
                    for part in node.args[1:]:
                        if _label_part(part, params):
                            found.add(f"line {node.lineno}: {ast.unparse(node)[:120]}")
                            break
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and under_temp(node.left):
                if _label_part(node.right, params):
                    found.add(f"line {node.lineno}: {ast.unparse(node)[:120]}")
    return sorted(found)


def interpreter_permission_alias_issue(source: str) -> bool | None:
    """Detect the platform's unsafe dual Bash-path permission-restore shape.

    None means the source could not be parsed; platform preflight treats that as
    an incomplete-scan warning rather than proving the pattern safe or unsafe.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    if not {"/bin/bash", "/usr/bin/bash"}.issubset(literals):
        return False

    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    chmod_calls = [node for node in calls if _call_name(node) in {"os.chmod", "Path.chmod"} or _call_name(node).endswith(".chmod")]
    has_mode_capture = any(
        _call_name(node) in {"os.stat", "stat.S_IMODE"}
        or _call_name(node).endswith(".stat")
        for node in calls
    ) or any(isinstance(node, ast.Attribute) and node.attr == "st_mode" for node in ast.walk(tree))
    has_resolve = any(_call_name(node).endswith(".resolve") for node in calls)
    return len(chmod_calls) >= 2 and has_mode_capture and not has_resolve


TREE_WALK_RE = re.compile(r"\.iterdir\(|\.rglob\(|\bos\.walk\(|\.glob\(\s*[\"']\*\*")
SEED_USE_RE = re.compile(r"(?i)seed|default_rng\(|random\.Random\(")
BUILD_METADATA_LITERALS = (".git", "__pycache__")


CANDIDATE_ROOTS = ("/app",)
SEED_NAME_RE = re.compile(r"(?i)seed")
SEED_CALL_RE = r"(?:\bRandom|\bdefault_rng|\.seed)\([^)\n]*\b{name}\b"
SEALED_SEED_FIX = (
    "preferred fix: a sealed constant seed kept in the verifier (tests/), so the graded "
    "draw cannot depend on any byte the candidate controls; if a candidate digest is kept, "
    "it must hash every regular file the candidate runs with and skip .git and __pycache__"
)


def _candidate_names(tree: ast.AST, roots: tuple[str, ...]) -> set[str]:
    """Module names bound to a candidate path, e.g. `SOURCE_ROOT = Path("/app/src")`."""
    names: set[str] = set()
    assigns = [node for node in getattr(tree, "body", []) if isinstance(node, (ast.Assign, ast.AnnAssign))]
    changed = True
    while changed:
        changed = False
        for node in assigns:
            if node.value is None:
                continue
            if not (_mentions_candidate_path(node.value, roots) or any(
                isinstance(sub, ast.Name) and sub.id in names for sub in ast.walk(node.value)
            )):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in names:
                    names.add(target.id)
                    changed = True
    return names


def _mentions_candidate_path(node: ast.AST, roots: tuple[str, ...]) -> bool:
    return any(
        isinstance(sub, ast.Constant)
        and isinstance(sub.value, str)
        and any(sub.value == root or sub.value.startswith(root.rstrip("/") + "/") for root in roots)
        for sub in ast.walk(node)
    )


def _without_docstring(function: ast.FunctionDef) -> list[ast.stmt]:
    body = list(function.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        body = body[1:]
    return body


def _unfiltered_walk(nodes: list[ast.stmt]) -> bool:
    """A walk that visits every entry, not only one source suffix."""
    for statement in nodes:
        for node in ast.walk(statement):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            attr = node.func.attr
            if attr in {"iterdir", "walk", "scandir"}:
                return True
            if attr in {"rglob", "glob"}:
                pattern = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else "*"
                if isinstance(pattern, str) and re.fullmatch(r"(?:\*\*/)?\*", pattern):
                    return True
    return False


def candidate_seeded_draw_sites(source: str, roots: tuple[str, ...] = CANDIDATE_ROOTS) -> list[dict]:
    """Functions that hash candidate files into a seed for the graded draw.

    Anything the candidate writes then chooses which scenarios are graded: an inert
    nonce file beside the package can steer the draw to the cases it already passes.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    names = _candidate_names(tree, roots)
    sites = []
    for function in (node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))):
        body = _without_docstring(function)
        nodes = [sub for statement in body for sub in ast.walk(statement)]
        hashes = any(isinstance(node, ast.Call) and _call_name(node).startswith("hashlib.") for node in nodes)
        candidate = any(_mentions_candidate_path(statement, roots) for statement in body) or any(
            isinstance(node, ast.Name) and node.id in names for node in nodes
        )
        if not (hashes and candidate):
            continue
        docstring = ast.get_docstring(function) or ""
        seeded = (
            SEED_NAME_RE.search(function.name)
            or SEED_NAME_RE.search(docstring)
            or re.search(SEED_CALL_RE.format(name=re.escape(function.name)), source)
        )
        if seeded:
            sites.append({
                "function": function.name,
                "line": function.lineno,
                "unfiltered_walk": _unfiltered_walk(body),
            })
    return sites


def candidate_digest_metadata_issue(source: str) -> list[str]:
    """Metadata directories a candidate-tree seed digest would still include.

    Hashing every file under /app into a held-out seed also hashes the build's Git
    commit (dates, index stat data) and interpreter bytecode caches (source mtimes),
    so two clean builds of identical code grade different scenarios. The digest must
    skip both, and the verifier must keep them out of the candidate's reach. A digest
    over one source suffix (``rglob("*.java")``) cannot reach either directory, and
    a digest of generated inputs is not a candidate digest at all. The preferred fix
    for any candidate-seeded draw is still a sealed constant seed (SEALED_SEED_FIX).
    """
    if not (
        "hashlib" in source
        and re.search(r"[\"']/app[\"'/]", source)
        and TREE_WALK_RE.search(source)
        and SEED_USE_RE.search(source)
    ):
        return []
    if not any(site["unfiltered_walk"] for site in candidate_seeded_draw_sites(source)):
        return []
    return [
        name for name in BUILD_METADATA_LITERALS
        if not re.search(rf"[\"']{re.escape(name)}[\"']", source)
    ]


WALK_ATTRS = frozenset({"iterdir", "rglob", "walk", "scandir"})
STAGING_NAME_RE = re.compile(r"(?i)copy|stag|digest|seed|hash|fingerprint")
ENTRY_TYPE_TOKENS = ("S_ISREG", "S_ISDIR", "S_ISFIFO", "S_ISSOCK", "is_symlink", "ancestors")


def staging_hard_fail_sites(source: str) -> list[int]:
    """Lines where a walk over the candidate tree fails on an entry instead of skipping it.

    A verifier that copies or hashes all of /app and asserts on each entry's type
    or link target rejects a correct package that merely left a virtualenv link,
    a dangling link or a FIFO beside it. Unusable entries should be skipped without
    being dereferenced; the contract never restricts incidental /app layout.
    """
    if not re.search(r"[\"']/app[\"'/]", source):
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    sites: list[int] = []
    for function in (node for node in tree.body if isinstance(node, ast.FunctionDef)):
        # Only helpers that stage or fingerprint the candidate tree; validating the
        # candidate's own output tree is a different, legitimate check.
        if not STAGING_NAME_RE.search(function.name):
            continue
        walks = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in WALK_ATTRS
            for node in ast.walk(function)
        )
        if not walks:
            continue
        # Per-entry scope: loop bodies and nested (recursive) helpers. A single
        # assertion that the root itself is a directory is a precondition, not this.
        scopes = [
            statement
            for node in ast.walk(function)
            if isinstance(node, (ast.For, ast.While, ast.FunctionDef)) and node is not function
            for statement in node.body
        ]
        for scope in scopes:
            for node in ast.walk(scope):
                if isinstance(node, ast.Assert) and any(
                    token in ast.unparse(node.test) for token in ENTRY_TYPE_TOKENS
                ):
                    sites.append(node.lineno)
                elif isinstance(node, ast.Try) and "relative_to(" in "".join(
                    ast.unparse(statement) for statement in node.body
                ):
                    sites.extend(
                        raised.lineno
                        for handler in node.handlers
                        for raised in ast.walk(handler)
                        if isinstance(raised, ast.Raise)
                    )
    return sorted(set(sites))


ABSOLUTE_GRADIENT_RE = re.compile(
    r"\.grad\b[^\n]{0,60}?(?:<=?|>=?)\s*[0-9][0-9.eE+-]*"
    r"|(?:<=?|>=?)\s*[0-9][0-9.eE+-]*[^\n]{0,20}\.grad\b"
)


def absolute_gradient_guard_sites(sources: dict[str, str]) -> list[str]:
    """Convergence accepted or rejected by comparing a raw gradient to a constant.

    The gradient scales with the information weights, so an absolute bound that
    holds for unit covariance rejects a reached optimum once the contract allows
    large weights. Judge convergence in objective units instead.
    """
    return [
        f"{name}:{number}"
        for name, text in sources.items()
        for number, line in enumerate(text.splitlines(), start=1)
        if ABSOLUTE_GRADIENT_RE.search(line)
    ]


DATA_SUFFIXES = frozenset({
    ".json", ".jsonl", ".ndjson", ".csv", ".tsv", ".txt", ".dat", ".in", ".xml", ".yaml", ".yml",
    ".sam", ".fa", ".fasta", ".fna", ".fq", ".fastq", ".gff", ".gff3", ".gtf", ".bed", ".vcf",
    ".mid", ".midi", ".wav", ".log", ".ics", ".geojson", ".parquet", ".bin",
})
MANIFEST_NAMES = frozenset({
    "package.json", "package-lock.json", "tsconfig.json", "jsconfig.json", "composer.json",
    "go.mod", "go.sum", "pom.xml", "cargo.toml", "cargo.lock", "requirements.txt",
    "pyproject.toml", "yarn.lock", "pnpm-lock.yaml", "readme.txt", "license.txt",
    "cmakelists.txt", ".eslintrc.json", ".prettierrc.json", "deno.json",
})


def _data_files(root: Path, skip: Path | None = None) -> list[Path]:
    if not root.is_dir():
        return []
    return [
        path for path in sorted(root.rglob("*"))
        if path.is_file()
        and not path.is_symlink()
        and path.suffix.lower() in DATA_SUFFIXES
        and path.name.lower() not in MANIFEST_NAMES
        and not (skip and skip in path.parents)
        and path.stat().st_size > 0
    ]


def visible_fixture_graded(task_dir: Path) -> list[str]:
    """Verifier data files that are byte-for-byte copies of a visible environment input.

    A graded job the candidate can read under /app is ground truth in plain sight: a
    package special-cased to the visible sample earns credit for it. tests/shipped/ is
    the deliberate pristine copy of the delivered tree and is not graded input.
    """
    import hashlib

    visible: dict[str, str] = {}
    for path in _data_files(task_dir / "environment"):
        visible.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), str(path.relative_to(task_dir)))
    matches = []
    tests = task_dir / "tests"
    for path in _data_files(tests, skip=tests / "shipped"):
        twin = visible.get(hashlib.sha256(path.read_bytes()).hexdigest())
        if twin:
            matches.append(f"{path.relative_to(task_dir)} == {twin}")
    return matches


DOCUMENTED_SCRIPT_RE = re.compile(
    r"\b(?:python3?|node|tsx|ts-node|bun|deno\s+run|java|ruby|perl|bash|sh)\s+"
    r"(/app/[\w./-]+\.(?:py|js|mjs|cjs|ts|java|rb|pl|sh))\b"
)
APP_SYMLINK_RE = re.compile(
    r"\bln\s+-[A-Za-z]*s[A-Za-z]*\s+[\"']?/app\b"
    r"|\bos\.symlink\(\s*[\"']/app\b"
    r"|\.symlink_to\(\s*[\"']/app\b"
)


def documented_script_relocated(contract_text: str, tests_text: str) -> list[dict]:
    """Documented `/app` scripts the verifier runs from a relocated copy instead.

    A driver copy under another directory whose tree is symlinked back into /app runs
    with a different argv[0] and __file__, so code that behaves only when started from
    the documented path is never observed. Prefer os.replace-ing the shipped driver onto
    the documented path and running exactly the documented command.
    """
    if not APP_SYMLINK_RE.search(tests_text):
        return []
    findings = []
    for documented in sorted(set(DOCUMENTED_SCRIPT_RE.findall(contract_text))):
        basename = re.escape(documented.rsplit("/", 1)[-1])
        relocated = sorted(set(re.findall(rf"(?<![\w./-])(/(?!app/|tests/)[\w.-][\w./-]*/{basename})\b", tests_text)))
        if relocated:
            findings.append({"documented": documented, "relocated": relocated})
    return findings


ADVISORY_CHECKS = ("seed", "relocated", "seeded_draw")
ADVISORY_FIXES = {
    "seed_digest_includes_build_metadata": (
        "the /app seed digest walks every entry but never names .git and __pycache__, so two "
        "clean builds can draw different scenarios; " + SEALED_SEED_FIX
    ),
    "candidate_seeded_draw": (
        "the graded draw is seeded from a hash of candidate files, so an inert file in the "
        "submission can choose which cases are graded; " + SEALED_SEED_FIX
    ),
    "documented_script_relocated": (
        "the verifier runs a relocated copy of a documented /app script through a symlinked "
        "tree, so argv[0], __file__ and cwd differ from the documented invocation; "
        "os.replace the shipped driver onto the documented path and run exactly the documented command"
    ),
}


def _candidate_roots(task_dir: Path) -> tuple[str, ...]:
    """/app plus any artifact path task.toml declares."""
    roots = list(CANDIDATE_ROOTS)
    toml = task_dir / "task.toml"
    if toml.is_file():
        match = re.search(r"(?m)^\s*artifacts\s*=\s*\[([^\]]*)\]", toml.read_text(encoding="utf-8", errors="replace"))
        if match:
            roots.extend(path.rstrip("/") or "/" for path in re.findall(r"[\"']([^\"']+)[\"']", match.group(1)))
    return tuple(dict.fromkeys(roots))


def _task_sources(task_dir: Path) -> tuple[str, str]:
    verifier = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted((task_dir / "tests").glob("*.py"))
    )
    contract_paths = [task_dir / "instruction.md"]
    contract_paths.extend(
        path
        for path in sorted((task_dir / "environment").rglob("*"))
        if path.is_file() and path.suffix.lower() in {".md", ".rst", ".txt"}
    )
    contract = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in contract_paths
        if path.is_file()
    )
    return verifier, contract


def main() -> int:
    parser = argparse.ArgumentParser(
        epilog=(
            "Exit 1: a blocking check failed. Exit 2: an advisory check named with --check "
            f"found something ({', '.join(ADVISORY_CHECKS)}); advisories never affect --check all."
        )
    )
    parser.add_argument("task_dir", type=Path)
    parser.add_argument(
        "--check",
        choices=(
            "privilege", "alignment", "identity", "interpreter", "staging", "gradient", "fixture",
            *ADVISORY_CHECKS, "all",
        ),
        default="all",
    )
    args = parser.parse_args()

    verifier, contract = _task_sources(args.task_dir)
    candidate_count, unsafe = analyze_candidate_privileges(verifier)
    instruction_path = args.task_dir / "instruction.md"
    instruction = instruction_path.read_text(encoding="utf-8", errors="replace") if instruction_path.is_file() else ""
    shipped = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in sorted((args.task_dir / "tests").rglob("*.py"))
    )
    unexecuted_modules = documented_module_unexecuted(instruction, shipped)
    alignment_issue = unit_test_alignment_issue(contract, verifier) or bool(unexecuted_modules)
    setpriv_issue = setpriv_missing_no_new_privs(verifier)
    escalation_reachable = setpriv_issue and privilege_acquirable(verifier)
    identity_issue = test_identity_leak(verifier)
    seed_metadata = candidate_digest_metadata_issue(verifier)
    tests_dir = args.task_dir / "tests"
    seeded_draws = [
        {"file": str(path.relative_to(args.task_dir)), **site}
        for path in sorted(tests_dir.rglob("*.py"))
        if tests_dir / "shipped" not in path.parents
        for site in candidate_seeded_draw_sites(
            path.read_text(encoding="utf-8", errors="replace"), _candidate_roots(args.task_dir)
        )
    ]
    fixture_copies = visible_fixture_graded(args.task_dir)
    tests_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(tests_dir.rglob("*"))
        if path.is_file()
        and tests_dir / "shipped" not in path.parents
        and (path.suffix in {".py", ".sh"} or path.name == "Dockerfile")
    )
    relocated_scripts = documented_script_relocated(contract, tests_text)
    staging_sites = staging_hard_fail_sites(verifier)
    gradient_sites = absolute_gradient_guard_sites({
        str(path.relative_to(args.task_dir)): path.read_text(encoding="utf-8", errors="replace")
        for folder in ("solution", "tests")
        for path in sorted((args.task_dir / folder).rglob("*.py"))
    })
    interpreter_issues = []
    interpreter_parse_warnings = []
    for path in sorted((args.task_dir / "tests").rglob("*.py")):
        result = interpreter_permission_alias_issue(
            path.read_text(encoding="utf-8", errors="replace")
        )
        if result is True:
            interpreter_issues.append(str(path.relative_to(args.task_dir)))
        elif result is None:
            interpreter_parse_warnings.append(str(path.relative_to(args.task_dir)))
    payload = {
        "candidate_execution_count": candidate_count,
        "unsafe_candidate_calls": [asdict(item) for item in unsafe],
        "setpriv_missing_no_new_privs": setpriv_issue,
        "no_new_privs_escalation_reachable": escalation_reachable,
        "test_identity_leak": identity_issue,
        "interpreter_permission_alias_issues": interpreter_issues,
        "interpreter_parse_warnings": interpreter_parse_warnings,
        "unit_test_alignment_issue": unit_test_alignment_issue(contract, verifier),
        "documented_module_unexecuted": unexecuted_modules,
        "seed_digest_includes_build_metadata": seed_metadata,
        "staging_hard_fail_lines": staging_sites,
        "absolute_gradient_guards": gradient_sites,
        "visible_fixture_graded": fixture_copies,
        "documented_script_relocated": relocated_scripts,
        "candidate_seeded_draw": seeded_draws,
    }
    advisories = {
        "seed_digest_includes_build_metadata": bool(seed_metadata),
        "documented_script_relocated": bool(relocated_scripts),
        "candidate_seeded_draw": bool(seeded_draws),
    }
    payload["advisories"] = {
        name: ADVISORY_FIXES[name] for name, fired in advisories.items() if fired
    }
    print(json.dumps(payload, sort_keys=True))
    # Keep the advisory in the payload either way, but only block when the escalation
    # is actually reachable: blocking on the bare flag rejects a task the platform
    # accepts, and under a no-panel profile nobody is there to overrule it.
    if args.check in {"privilege", "all"} and (unsafe or escalation_reachable):
        return 1
    if args.check in {"alignment", "all"} and alignment_issue:
        return 1
    if args.check in {"identity", "all"} and identity_issue:
        return 1
    if args.check in {"interpreter", "all"} and interpreter_issues:
        return 1
    if args.check in {"staging", "all"} and staging_sites:
        return 1
    if args.check in {"gradient", "all"} and gradient_sites:
        return 1
    # Blocking: reproduces returned Protected-Ground-Truth / finding-18 reports, where a
    # graded job was a copy of the visible sample.
    if args.check in {"fixture", "all"} and fixture_copies:
        return 1
    # Advisory only: stricter than the documented platform contract, and each has fired
    # on a tree the platform accepted. Reported with exit 2 when named explicitly.
    advisory_hits = {
        "seed": advisories["seed_digest_includes_build_metadata"],
        "relocated": advisories["documented_script_relocated"],
        "seeded_draw": advisories["candidate_seeded_draw"],
    }
    if advisory_hits.get(args.check):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
