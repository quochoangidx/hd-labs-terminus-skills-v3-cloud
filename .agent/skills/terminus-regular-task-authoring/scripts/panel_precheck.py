#!/usr/bin/env python3
"""Fail-closed deterministic obligation gate for a Terminus 3 task.

Validates authored obligation evidence and existing deterministic receipts: closure
clauses, expected-value provenance, witness discrimination, orphan units in both
directions, restriction enforcement, determinism and wrong-path receipts.

Every profile runs it. Under ``builder_certified`` it carries most of what a review
panel would otherwise be asked to check; it never emits a semantic quality-axis
``None`` verdict, because no script can establish semantic coherence or reference
correctness over a whole domain.

The file name is historical: it predates the gate being used outside the panel flow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verifier_architecture_check import validate_matrix  # noqa: E402


AXES = (
    "coherent_contract",
    "correct_reference_solution",
    "protected_ground_truth",
    "sound_verifier",
    "deterministic_execution",
)
CLASSES = {"core", "support", "non_goal"}
# Where a witness's expected value comes from. `oracle_recorded` makes the verifier
# agree with the reference by construction, so it proves nothing on its own and has to
# be paired with an invariant or a differential that the reference cannot influence.
EXPECTED_SOURCES = {
    "independent_model",
    "authority_text",
    "shipped_differential",
    "invariant",
    "oracle_recorded",
}
NON_CIRCULAR_SOURCES = EXPECTED_SOURCES - {"oracle_recorded"}
# The clauses that close the input domain the authority does not name. Without them a
# boundary case has no stated answer, which is where contract findings come from.
CLOSURE_CLAUSES = ("universal_rule", "silence", "coverage_envelope")
# Rows that check the manifest's own bookkeeping (graph shape, separability prose,
# matrix labels, header phrases) rather than a property the quality panel judges.
# Under builder_certified they report as warnings: they caught no task defect in
# that profile's builds, and with no reviewer above the gate a bookkeeping FAIL only
# costs rework. Everything tied to a panel finding still blocks: closure and named
# silent cases, cited exact conventions, expectation sources, wrong paths, the
# harness bypass, preflight, restrictions and surviving promises.
BOOKKEEPING_CODES = {
    "primary_outcome", "contribution", "separability", "separability_rationale",
    "composite_core", "serialization_only_join", "serialization_only_interaction",
    "support_boundary", "causal_graph", "causal_edge", "disconnected_core",
    "interaction", "interaction_members", "uncoupled_core", "boundary_witness",
    "discriminating_instance", "wrong_but_plausible", "exact_output",
    "incidental_exact_output", "determinism", "determinism_network",
    "reference_selfdescription", "orphan_unit", "verifier_matrix",
}
PROFILES = ("strict", "builder_certified")
# How far a restriction is actually enforced. A restriction about what the candidate's
# program may reach at run time -- reflection, native code, subprocesses, the network,
# a forbidden namespace -- is not enforced by reading source: the same capability is
# reachable through a constant, a generated name or a dependency. Such a restriction
# has to be checked against the compiled artifact.
ENFORCEMENT_LEVELS = {"source", "compiled", "both"}
RUNTIME_CAPABILITY_RE = re.compile(
    r"(?i)\b(?:reflect|reflection|native|jni|subprocess|process|exec|runtime|"
    r"classloader|class[ -]?loader|dlopen|ffi|ctypes|unsafe|network|socket|import|"
    r"require|namespace|package)\b"
)
VOLATILE_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}


PANEL_READ_LIMIT = 60_000
# The panel also stops reading a packet after roughly this much text in total: with 300 KB
# under tests/ (every file under the per-file limit) it left four case files unread and
# raised coverage findings for behaviour those files exercised (ed, 2026-09-25, v4 and v5).
PANEL_TOTAL_READ_LIMIT = 150_000


def _text_size(path: Path) -> int | None:
    try:
        path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None
    return path.stat().st_size


# An id made of an id-like stem, a hyphen and an index (R507-6, R507-17) reads as a
# repeated id R507: three panel reviewers raised it against a distinct-id rule although
# every id was distinct (icpms v11). Plain prefixes (W-11, MB-3) are not flagged.
_STEM_ID = re.compile(r"^([A-Za-z]+\d+)-\d+$")


def _shared_stems(node, found: set[str]) -> None:
    if isinstance(node, dict):
        for value in node.values():
            _shared_stems(value, found)
    elif isinstance(node, list):
        ids = [item["id"] for item in node if isinstance(item, dict) and isinstance(item.get("id"), str)]
        stems: dict[str, int] = {}
        for value in ids:
            match = _STEM_ID.match(value)
            if match:
                stems[match.group(1)] = stems.get(match.group(1), 0) + 1
        found.update(stem for stem, count in stems.items() if count > 1)
        for item in node:
            _shared_stems(item, found)


def packet_advisories(task_dir: Path) -> list[dict]:
    """Advisory rows about how the platform panel reads the packet; never blocking."""
    out: list[dict] = []
    # The sound_verifier packet carries the instruction, task.toml, environment/ and tests/,
    # and the reviewer stops at roughly PANEL_TOTAL_READ_LIMIT across all of it. With tests/
    # at 135 KB (under the blocking limit) the icpms v12 reviewer never read the two last
    # case files and reported their coverage missing. Advisory, because a task that ships an
    # upstream repository under environment/ exceeds it by design and is read selectively.
    total = 0
    for part in ("instruction.md", "task.toml", "environment", "tests"):
        root = task_dir / part
        paths = [root] if root.is_file() else sorted(root.rglob("*")) if root.is_dir() else []
        for path in paths:
            if not path.is_file() or any(p in VOLATILE_DIRS for p in path.relative_to(task_dir).parts):
                continue
            if path.name == ".DS_Store" or path.name.startswith("._"):
                continue
            size = _text_size(path)
            if size is not None:
                total += min(size, PANEL_READ_LIMIT)
    if total > PANEL_TOTAL_READ_LIMIT:
        out.append({
            "axis": "sound_verifier",
            "code": "panel_packet_budget",
            "message": f"the sound_verifier packet (instruction, task.toml, environment/, tests/) holds about {total} "
            f"bytes of text; the panel stops near {PANEL_TOTAL_READ_LIMIT} and reports the coverage of files it "
            "never reached (the alphabetically last case files) as missing. Fold or drop broad cases, or confirm "
            "the excess is an upstream tree the reviewer does not need to read",
        })
    found: set[str] = set()
    tests = task_dir / "tests"
    for path in sorted(tests.rglob("*")) if tests.is_dir() else []:
        if path.suffix not in (".json", ".jsonl") or not path.is_file() or path.stat().st_size > 5_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            docs = [json.loads(line) for line in text.splitlines() if line.strip()] if path.suffix == ".jsonl" else [json.loads(text)]
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        for doc in docs:
            _shared_stems(doc, found)
    if found:
        out.append({
            "axis": "coherent_contract",
            "code": "shared_id_stem",
            "message": "graded ids share an id-like stem before a hyphen (" + ", ".join(sorted(found)[:5])
            + "); reviewers read such ids as duplicates of the stem. Number runs with one opaque id each",
        })
    return out


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in VOLATILE_DIRS for part in rel.parts):
            continue
        if path.is_dir() or path.is_symlink():
            continue
        # Finder junk never enters the ZIP, so it must not enter the snapshot either: a
        # .DS_Store that appeared mid-run made every receipt of a round unbindable
        if path.name == ".DS_Store" or path.name.startswith("._"):
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: object, label: str, errors: list[dict], *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty) or not all(nonempty(item) for item in value):
        errors.append({"axis": "common", "code": "invalid_list", "message": f"{label} must be a {'possibly empty ' if allow_empty else 'non-empty '}list of strings"})
        return []
    result = [str(item) for item in value]
    if len(result) != len(set(result)):
        errors.append({"axis": "common", "code": "duplicate_id", "message": f"{label} must not contain duplicates"})
    return result


def load_object(path: Path, errors: list[dict], label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append({"axis": "common", "code": "invalid_json", "message": f"{label}: {exc}"})
        return {}
    if not isinstance(value, dict):
        errors.append({"axis": "common", "code": "invalid_object", "message": f"{label} root must be an object"})
        return {}
    return value


def resolve_report_file(manifest_path: Path, value: object, label: str, errors: list[dict]) -> Path | None:
    if not nonempty(value):
        errors.append({"axis": "common", "code": "missing_receipt", "message": f"{label} is required"})
        return None
    path = (manifest_path.parent / str(value)).resolve()
    try:
        path.relative_to(manifest_path.parent.resolve())
    except ValueError:
        errors.append({"axis": "common", "code": "escaping_receipt", "message": f"{label} must stay inside the report directory"})
        return None
    if not path.is_file():
        errors.append({"axis": "common", "code": "missing_receipt", "message": f"{label} does not exist: {value}"})
        return None
    return path


def task_file(task_dir: Path, value: object, label: str, axis: str, errors: list[dict], *, must_exist: bool) -> Path | None:
    if not nonempty(value):
        errors.append({"axis": axis, "code": "missing_path", "message": f"{label} must be a non-empty task-relative path"})
        return None
    path = (task_dir / str(value)).resolve()
    try:
        path.relative_to(task_dir.resolve())
    except ValueError:
        errors.append({"axis": axis, "code": "escaping_path", "message": f"{label} escapes the task folder"})
        return None
    if must_exist and not path.is_file():
        errors.append({"axis": axis, "code": "missing_path", "message": f"{label} does not exist: {value}"})
        return None
    return path


def has_path(edges: dict[str, set[str]], start: str, target: str) -> bool:
    pending = [start]
    seen: set[str] = set()
    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        pending.extend(edges.get(node, ()))
    return False


def validate(task_dir: Path, manifest_path: Path, *, full: bool, profile: str = "strict") -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    manifest = load_object(manifest_path, errors, manifest_path.name)
    snapshot = tree_hash(task_dir) if task_dir.is_dir() else None

    if not task_dir.is_dir():
        errors.append({"axis": "common", "code": "missing_task", "message": f"task folder not found: {task_dir}"})
    try:
        manifest_path.relative_to(task_dir.resolve())
    except ValueError:
        pass
    else:
        errors.append({"axis": "protected_ground_truth", "code": "manifest_inside_task", "message": "panel precheck manifest must stay outside the task and submission ZIP"})
    if manifest.get("schema_version") != 1:
        errors.append({"axis": "common", "code": "schema", "message": "schema_version must be 1"})
    if manifest.get("task_slug") != task_dir.name:
        errors.append({"axis": "common", "code": "slug", "message": "task_slug must match the task folder name"})
    if not nonempty(manifest.get("primary_outcome")):
        errors.append({"axis": "coherent_contract", "code": "primary_outcome", "message": "primary_outcome is required"})

    # The platform panel reads each file only up to about 64 KB (a 145 KB cases.json was
    # cut at line 2966). A grader or reference text file past that is judged half-read,
    # and the unseen half's coverage is reported missing. Split it instead.
    if task_dir.is_dir():
        for part in ("tests", "solution"):
            text_total = 0
            for path in sorted((task_dir / part).rglob("*")):
                if not path.is_file() or any(p in VOLATILE_DIRS for p in path.relative_to(task_dir).parts):
                    continue
                size = path.stat().st_size
                try:
                    path.read_bytes().decode("utf-8")
                except UnicodeDecodeError:
                    continue  # binary fixtures are not read as text
                text_total += size
                if size <= PANEL_READ_LIMIT:
                    continue
                errors.append({
                    "axis": "sound_verifier",
                    "code": "panel_truncated_file",
                    "message": f"{path.relative_to(task_dir).as_posix()} is {size} bytes; the panel reads about "
                    f"{PANEL_READ_LIMIT} per file, so split it (one case per line, shared data in a named table) "
                    "and pin the roster with counts the verifier checks",
                })
            if text_total > PANEL_TOTAL_READ_LIMIT:
                errors.append({
                    "axis": "sound_verifier",
                    "code": "panel_unread_budget",
                    "message": f"{part}/ holds {text_total} bytes of text; the panel stops reading a packet at roughly "
                    f"{PANEL_TOTAL_READ_LIMIT} in total and reports the unread files' coverage as missing, so cut "
                    "or fold the corpus (keep the cases that discriminate wrong paths) rather than adding to it",
                })

    if task_dir.is_dir():
        warnings.extend(packet_advisories(task_dir))

    obligations = manifest.get("obligations")
    if not isinstance(obligations, list) or not obligations:
        errors.append({"axis": "coherent_contract", "code": "obligations", "message": "obligations must be a non-empty list"})
        obligations = []

    obligation_ids: set[str] = set()
    core_ids: set[str] = set()
    witness_ids: set[str] = set()
    obligation_witness_ids: set[str] = set()
    for index, row in enumerate(obligations):
        label = f"obligations[{index}]"
        if not isinstance(row, dict):
            errors.append({"axis": "coherent_contract", "code": "obligation", "message": f"{label} must be an object"})
            continue
        row_id = row.get("id")
        if not nonempty(row_id) or row_id in obligation_ids:
            errors.append({"axis": "coherent_contract", "code": "obligation_id", "message": f"{label}.id must be unique and non-empty"})
            continue
        row_id = str(row_id)
        obligation_ids.add(row_id)
        row_class = row.get("class")
        if row_class not in CLASSES:
            errors.append({"axis": "coherent_contract", "code": "obligation_class", "message": f"{label}.class must be one of {sorted(CLASSES)}"})
            continue
        if not nonempty(row.get("contribution")):
            errors.append({"axis": "coherent_contract", "code": "contribution", "message": f"{label}.contribution is required"})

        if row_class == "core":
            core_ids.add(row_id)
            authority = row.get("authority")
            if not isinstance(authority, dict):
                errors.append({"axis": "coherent_contract", "code": "authority", "message": f"{label}.authority must be an object"})
            else:
                authority_path = task_file(task_dir, authority.get("file"), f"{label}.authority.file", "coherent_contract", errors, must_exist=full)
                anchor = authority.get("anchor")
                if not nonempty(anchor):
                    errors.append({"axis": "coherent_contract", "code": "authority_anchor", "message": f"{label}.authority.anchor is required"})
                elif full and authority_path and authority_path.is_file():
                    try:
                        if str(anchor) not in authority_path.read_text(encoding="utf-8"):
                            errors.append({"axis": "coherent_contract", "code": "authority_anchor", "message": f"{label}.authority.anchor is absent from {authority.get('file')}"})
                    except UnicodeDecodeError:
                        errors.append({"axis": "coherent_contract", "code": "authority_encoding", "message": f"{label}.authority.file must be UTF-8 text"})

            implementation_sites = string_list(row.get("implementation_sites"), f"{label}.implementation_sites", errors)
            if full:
                for path in implementation_sites:
                    task_file(task_dir, path, f"{label}.implementation_sites", "correct_reference_solution", errors, must_exist=True)

            separability = row.get("separability")
            if not isinstance(separability, dict):
                errors.append({"axis": "coherent_contract", "code": "separability", "message": f"{label}.separability must be an object"})
            else:
                if separability.get("standalone_deliverable") is not False:
                    errors.append({"axis": "coherent_contract", "code": "composite_core", "message": f"{label} must not remain a standalone deliverable when removed from the causal core"})
                if separability.get("joins_before_output") is not True:
                    errors.append({"axis": "coherent_contract", "code": "serialization_only_join", "message": f"{label} must join the causal decision before output serialization"})
                if not nonempty(separability.get("rationale")):
                    errors.append({"axis": "coherent_contract", "code": "separability_rationale", "message": f"{label}.separability.rationale is required"})

            witnesses = row.get("witnesses")
            if not isinstance(witnesses, dict):
                errors.append({"axis": "sound_verifier", "code": "witnesses", "message": f"{label}.witnesses must be an object"})
            else:
                positive = string_list(witnesses.get("positive"), f"{label}.witnesses.positive", errors)
                boundary = string_list(witnesses.get("boundary"), f"{label}.witnesses.boundary", errors, allow_empty=True)
                if not boundary and not nonempty(witnesses.get("boundary_not_applicable")):
                    errors.append({"axis": "sound_verifier", "code": "boundary_witness", "message": f"{label} needs boundary witnesses or boundary_not_applicable"})
                witness_ids.update(positive)
                witness_ids.update(boundary)
                obligation_witness_ids.update(positive)
                obligation_witness_ids.update(boundary)

            # Where the expected values come from decides whether Oracle=1 is evidence
            # or a tautology. A verifier that records the reference's answers agrees
            # with the reference no matter what the reference got wrong.
            expected_source = row.get("expected_source")
            if expected_source not in EXPECTED_SOURCES:
                errors.append({"axis": "correct_reference_solution", "code": "expected_source", "message": f"{label}.expected_source must be one of {sorted(EXPECTED_SOURCES)}"})
            elif expected_source == "oracle_recorded":
                corroboration = row.get("oracle_recorded_corroboration")
                if corroboration not in NON_CIRCULAR_SOURCES - {"authority_text"}:
                    errors.append({
                        "axis": "correct_reference_solution",
                        "code": "circular_expectation",
                        "message": f"{label} records the reference's own answers; pair it with an invariant or shipped differential in oracle_recorded_corroboration",
                    })

            # A witness only discriminates if some plausible wrong implementation gives
            # a different answer on it. Naming that wrong answer is what separates a
            # real witness from a fixture that any shape happens to pass.
            if not nonempty(row.get("discriminating_instance")):
                errors.append({"axis": "sound_verifier", "code": "discriminating_instance", "message": f"{label}.discriminating_instance is required"})
            if not nonempty(row.get("wrong_but_plausible")):
                errors.append({"axis": "sound_verifier", "code": "wrong_but_plausible", "message": f"{label}.wrong_but_plausible must name the answer the witness rules out"})
        elif row_class == "support":
            if row.get("implementation_complete") is not True or row.get("repair_surface") is not False:
                errors.append({"axis": "coherent_contract", "code": "support_boundary", "message": f"{label} support plumbing must be complete and outside the repair surface"})
            support_paths = string_list(row.get("paths"), f"{label}.paths", errors)
            if full:
                for path in support_paths:
                    task_file(task_dir, path, f"{label}.paths", "coherent_contract", errors, must_exist=True)
                smoke = string_list(row.get("smoke_test_ids"), f"{label}.smoke_test_ids", errors)
                witness_ids.update(smoke)

    if not core_ids:
        errors.append({"axis": "coherent_contract", "code": "causal_core", "message": "at least one core obligation is required"})

    graph = manifest.get("causal_graph")
    graph_edges: dict[str, set[str]] = {}
    if not isinstance(graph, dict) or not isinstance(graph.get("edges"), list):
        errors.append({"axis": "coherent_contract", "code": "causal_graph", "message": "causal_graph.edges must be a list"})
    else:
        for index, edge in enumerate(graph["edges"]):
            if not isinstance(edge, dict) or not nonempty(edge.get("from")) or not nonempty(edge.get("to")):
                errors.append({"axis": "coherent_contract", "code": "causal_edge", "message": f"causal_graph.edges[{index}] requires from/to"})
                continue
            source, target = str(edge["from"]), str(edge["to"])
            if source not in core_ids or (target not in core_ids and target != "PRIMARY_OUTCOME"):
                errors.append({"axis": "coherent_contract", "code": "causal_edge", "message": f"causal_graph.edges[{index}] references an unknown core node"})
                continue
            graph_edges.setdefault(source, set()).add(target)
        for row_id in sorted(core_ids):
            if not has_path(graph_edges, row_id, "PRIMARY_OUTCOME"):
                errors.append({"axis": "coherent_contract", "code": "disconnected_core", "message": f"core obligation {row_id} has no causal path to PRIMARY_OUTCOME"})

    interactions = manifest.get("interactions")
    covered_by_interaction: set[str] = set()
    if not isinstance(interactions, list) or not interactions:
        errors.append({"axis": "coherent_contract", "code": "interaction", "message": "at least one genuine core interaction is required"})
        interactions = []
    for index, row in enumerate(interactions):
        label = f"interactions[{index}]"
        if not isinstance(row, dict) or not nonempty(row.get("id")):
            errors.append({"axis": "coherent_contract", "code": "interaction", "message": f"{label} requires a non-empty id"})
            continue
        members = set(string_list(row.get("obligation_ids"), f"{label}.obligation_ids", errors))
        if len(members) < 2 or not members <= core_ids:
            errors.append({"axis": "coherent_contract", "code": "interaction_members", "message": f"{label} must name at least two declared core obligations"})
        covered_by_interaction.update(members)
        interaction_witnesses = string_list(row.get("witness_ids"), f"{label}.witness_ids", errors)
        witness_ids.update(interaction_witnesses)
        if row.get("joins_before_output") is not True:
            errors.append({"axis": "coherent_contract", "code": "serialization_only_interaction", "message": f"{label} must change the causal result before serialization"})
    for row_id in sorted(core_ids - covered_by_interaction):
        errors.append({"axis": "coherent_contract", "code": "uncoupled_core", "message": f"core obligation {row_id} is not part of a declared interaction; move it to support/non-goal or rescope"})

    exact_outputs = manifest.get("exact_output_requirements", [])
    if not isinstance(exact_outputs, list):
        errors.append({"axis": "coherent_contract", "code": "exact_output", "message": "exact_output_requirements must be a list"})
    else:
        for index, row in enumerate(exact_outputs):
            label = f"exact_output_requirements[{index}]"
            if not isinstance(row, dict) or not nonempty(row.get("id")) or row.get("domain_required") is not True or not nonempty(row.get("rationale")):
                errors.append({"axis": "coherent_contract", "code": "incidental_exact_output", "message": f"{label} must identify a domain-required exact convention with rationale"})
                continue
            # An arbitrary convention the verifier pins has to be readable somewhere the
            # candidate can reach. A rationale explains why it exists; it does not tell
            # the candidate what the convention is.
            anchor = row.get("authority_anchor")
            if not isinstance(anchor, dict) or not nonempty(anchor.get("file")) or not nonempty(anchor.get("anchor")):
                errors.append({"axis": "coherent_contract", "code": "uncited_exact_output", "message": f"{label}.authority_anchor must cite the visible sentence that fixes this convention"})
            elif full:
                anchor_path = task_file(task_dir, anchor.get("file"), f"{label}.authority_anchor.file", "coherent_contract", errors, must_exist=True)
                if anchor_path and anchor_path.is_file():
                    try:
                        if str(anchor.get("anchor")) not in anchor_path.read_text(encoding="utf-8"):
                            errors.append({"axis": "coherent_contract", "code": "uncited_exact_output", "message": f"{label}.authority_anchor.anchor is absent from {anchor.get('file')}"})
                    except UnicodeDecodeError:
                        errors.append({"axis": "coherent_contract", "code": "authority_encoding", "message": f"{label}.authority_anchor.file must be UTF-8 text"})

    # Restrictions: prose that forbids something must be backed by a check the verifier
    # actually runs, and the check has to be able to see what it forbids.
    restrictions = manifest.get("restrictions", [])
    if not isinstance(restrictions, list):
        errors.append({"axis": "sound_verifier", "code": "restrictions", "message": "restrictions must be a list"})
        restrictions = []
    for index, row in enumerate(restrictions):
        label = f"restrictions[{index}]"
        if not isinstance(row, dict) or not nonempty(row.get("id")):
            errors.append({"axis": "sound_verifier", "code": "restriction", "message": f"{label} requires an id"})
            continue
        statement = row.get("statement")
        if not nonempty(statement):
            errors.append({"axis": "coherent_contract", "code": "restriction_statement", "message": f"{label}.statement must quote the restriction as the candidate reads it"})
        enforced_by = string_list(row.get("enforced_by"), f"{label}.enforced_by", errors, allow_empty=True)
        if not enforced_by:
            errors.append({
                "axis": "sound_verifier",
                "code": "unenforced_restriction",
                "message": f"{label} is forbidden in prose with no check that runs; a restriction "
                "the verifier cannot see is decoration, so enforce it or drop the sentence",
            })
        witness_ids.update(enforced_by)
        # A restriction is about how the candidate was built, and an obligation witness
        # judges what it produced. When the only named enforcer is also an obligation
        # witness, nothing in the suite can see the restriction: a submission that
        # breaks it still produces the required output and passes. Found by a platform
        # quality panel on tbrain-gnu-ed-reimplementation, where "do not start other
        # programs" was listed as enforced by a behavioural comparison and a candidate
        # that merely exec'd the real program scored reward 1.
        if enforced_by and not set(enforced_by) - obligation_witness_ids:
            errors.append({
                "axis": "sound_verifier",
                "code": "unenforced_restriction",
                "message": f"{label} names only obligation witnesses ("
                + ", ".join(sorted(set(enforced_by)))
                + "); a test that grades the produced output cannot see how the program was "
                "built, so give the restriction a check of its own or drop the sentence",
            })
        level = row.get("enforcement_level")
        if level not in ENFORCEMENT_LEVELS:
            errors.append({"axis": "sound_verifier", "code": "enforcement_level", "message": f"{label}.enforcement_level must be one of {sorted(ENFORCEMENT_LEVELS)}"})
        elif level == "source" and nonempty(statement) and RUNTIME_CAPABILITY_RE.search(str(statement)):
            errors.append({
                "axis": "sound_verifier",
                "code": "unenforced_restriction",
                "message": f"{label} forbids a run-time capability but is only audited at source level; "
                "the same capability is reachable through a constant, a generated name or a dependency, "
                "so audit the compiled artifact or narrow the statement to what source can see",
            })
        # Prose that forbids without naming what stays legal fails an honest solution on
        # a rule nobody wrote down.
        if row.get("allowed_exceptions_disclosed") is not True:
            errors.append({
                "axis": "coherent_contract",
                "code": "undisclosed_exceptions",
                "message": f"{label} must name the exceptions that remain legal and set allowed_exceptions_disclosed",
            })

    # Removing an obligation means removing what promised it. Prose left in the task
    # after its witness is deleted is still a promise the panel enforces, and now
    # nothing defends it — strictly worse than before the removal.
    removed = manifest.get("removed_obligations", [])
    if not isinstance(removed, list):
        errors.append({"axis": "coherent_contract", "code": "removed_obligations", "message": "removed_obligations must be a list"})
        removed = []
    for index, row in enumerate(removed):
        label = f"removed_obligations[{index}]"
        if not isinstance(row, dict) or not nonempty(row.get("id")):
            errors.append({"axis": "coherent_contract", "code": "removed_obligation", "message": f"{label} requires the id of the obligation that was dropped"})
            continue
        if str(row["id"]) in obligation_ids:
            errors.append({"axis": "coherent_contract", "code": "removed_obligation", "message": f"{label} is still present in obligations"})
        if not nonempty(row.get("reason")):
            errors.append({"axis": "coherent_contract", "code": "removed_obligation", "message": f"{label}.reason must say why it was not core"})
        former = row.get("former_anchor")
        if not isinstance(former, dict) or not nonempty(former.get("file")) or not nonempty(former.get("anchor")):
            errors.append({"axis": "coherent_contract", "code": "removed_obligation", "message": f"{label}.former_anchor must name the sentence that used to promise it"})
            continue
        if not full:
            continue
        former_path = task_dir / str(former["file"])
        if not former_path.is_file():
            continue
        try:
            if str(former["anchor"]) in former_path.read_text(encoding="utf-8"):
                errors.append({
                    "axis": "coherent_contract",
                    "code": "surviving_promise",
                    "message": f"{label}: obligation {row['id']} was dropped but its promise still reads in "
                    f"{former['file']} — remove the prose too, or the task promises something nothing checks",
                })
        except UnicodeDecodeError:
            errors.append({"axis": "coherent_contract", "code": "authority_encoding", "message": f"{label}.former_anchor.file must be UTF-8 text"})

    # Closure: the clauses that decide what happens outside the cases the authority
    # names. Without them every boundary input is an open question, and an open
    # question is a contract finding waiting to be written.
    closure = manifest.get("closure")
    silence_case_witnesses: set[str] = set()
    if not isinstance(closure, dict):
        errors.append({"axis": "coherent_contract", "code": "closure", "message": "closure must be an object carrying the universal-rule, silence and coverage-envelope clauses"})
    else:
        for clause in CLOSURE_CLAUSES:
            row = closure.get(clause)
            if not isinstance(row, dict) or not nonempty(row.get("file")) or not nonempty(row.get("anchor")):
                errors.append({"axis": "coherent_contract", "code": f"closure_{clause}", "message": f"closure.{clause} must cite a file and an anchor sentence"})
                continue
            if not full:
                continue
            clause_path = task_file(task_dir, row.get("file"), f"closure.{clause}.file", "coherent_contract", errors, must_exist=True)
            if clause_path and clause_path.is_file():
                try:
                    if str(row.get("anchor")) not in clause_path.read_text(encoding="utf-8"):
                        errors.append({"axis": "coherent_contract", "code": f"closure_{clause}", "message": f"closure.{clause}.anchor is absent from {row.get('file')}"})
                except UnicodeDecodeError:
                    errors.append({"axis": "coherent_contract", "code": "authority_encoding", "message": f"closure.{clause}.file must be UTF-8 text"})
        # A silence clause that names cases ("a clamp whose lower bound exceeds its
        # upper") has made a promise about each one, and the quality check reads every
        # named case as a requirement. Each needs its own witness. Writing the list
        # down is also what exposes a model that answers a silent case its own way
        # rather than the way the package ships: the witness cannot be made to pass.
        silence_row = closure.get("silence") if isinstance(closure.get("silence"), dict) else {}
        named_cases = silence_row.get("named_cases")
        if not isinstance(named_cases, list):
            errors.append({"axis": "sound_verifier", "code": "silence_named_cases", "message": "closure.silence.named_cases must be a list: one row per case the silence prose names, or [] when it names none"})
        else:
            for index, case in enumerate(named_cases):
                label = f"closure.silence.named_cases[{index}]"
                if not isinstance(case, dict) or not nonempty(case.get("anchor")):
                    errors.append({"axis": "sound_verifier", "code": "silence_named_cases", "message": f"{label} must carry the anchor phrase that names the case"})
                    continue
                ids = case.get("witness_ids")
                if not isinstance(ids, list) or not ids or not all(nonempty(item) for item in ids):
                    errors.append({"axis": "sound_verifier", "code": "silence_case_unwitnessed", "message": f"{label} ({case['anchor']!r}) names a silent case no test checks — add a shipped-behaviour witness or stop naming it"})
                    continue
                silence_case_witnesses.update(str(item) for item in ids)
                if full:
                    case_path = task_file(task_dir, case.get("file", silence_row.get("file")), f"{label}.file", "coherent_contract", errors, must_exist=True)
                    if case_path and case_path.is_file() and str(case["anchor"]) not in case_path.read_text(encoding="utf-8", errors="replace"):
                        errors.append({"axis": "coherent_contract", "code": "silence_named_cases", "message": f"{label}.anchor is absent from {case_path.relative_to(task_dir)}"})
        # Only meaningful when tests drive public helpers directly rather than going
        # through the top-level entry point every time. A sentence promising that named
        # helpers obey the rules when called directly is a promise about each helper:
        # the panel checks every one it names, and in two returns of 2026-09-24 the
        # helpers without a direct-call witness were the largest block of findings.
        scope = closure.get("entrypoint_scope")
        if scope is not None and (not isinstance(scope, dict) or not nonempty(scope.get("file")) or not nonempty(scope.get("anchor"))):
            errors.append({"axis": "coherent_contract", "code": "closure_entrypoint_scope", "message": "closure.entrypoint_scope, when present, must cite a file and an anchor sentence"})
        elif isinstance(scope, dict):
            helpers = scope.get("helpers")
            if not isinstance(helpers, list) or not helpers:
                errors.append({"axis": "sound_verifier", "code": "entrypoint_helper_unwitnessed", "message": "closure.entrypoint_scope.helpers must list every helper the scope sentence promises, each with its direct-call witness_ids; if the helpers are not core, drop the sentence and grade through the entry point"})
            else:
                scope_text = ""
                if full:
                    scope_path = task_file(task_dir, scope.get("file"), "closure.entrypoint_scope.file", "coherent_contract", errors, must_exist=True)
                    if scope_path and scope_path.is_file():
                        scope_text = scope_path.read_text(encoding="utf-8", errors="replace")
                for index, helper in enumerate(helpers):
                    label = f"closure.entrypoint_scope.helpers[{index}]"
                    if not isinstance(helper, dict) or not nonempty(helper.get("name")):
                        errors.append({"axis": "sound_verifier", "code": "entrypoint_helper_unwitnessed", "message": f"{label} must name the helper"})
                        continue
                    ids = helper.get("witness_ids")
                    if not isinstance(ids, list) or not ids or not all(nonempty(item) for item in ids):
                        errors.append({"axis": "sound_verifier", "code": "entrypoint_helper_unwitnessed", "message": f"{label} ({helper['name']!r}) is promised to follow the rules when called directly, and no test calls it"})
                        continue
                    witness_ids.update(str(item) for item in ids)
                    if scope_text and str(helper["name"]) not in scope_text:
                        errors.append({"axis": "coherent_contract", "code": "entrypoint_helper_unnamed", "message": f"{label} ({helper['name']!r}) does not appear in {scope.get('file')}"})

    # Determinism is a blocking axis in its own right, and nothing else in this
    # manifest would notice a verifier that depends on the clock, the network or the
    # order its tests happen to run in.
    determinism = manifest.get("determinism")
    if not isinstance(determinism, dict):
        errors.append({"axis": "deterministic_execution", "code": "determinism", "message": "determinism must declare seeds, clock_dependence, network and order_sensitivity"})
    else:
        for field in ("clock_dependence", "network", "order_sensitivity"):
            if not nonempty(determinism.get(field)):
                errors.append({"axis": "deterministic_execution", "code": "determinism", "message": f"determinism.{field} is required"})
        if determinism.get("network") not in (None, "none") and not nonempty(determinism.get("network_rationale")):
            errors.append({"axis": "deterministic_execution", "code": "determinism_network", "message": "a verifier that uses the network needs determinism.network_rationale"})

    if full:
        if manifest.get("task_snapshot_sha256") != snapshot:
            errors.append({"axis": "common", "code": "stale_snapshot", "message": "task_snapshot_sha256 does not match the current task"})

        matrix_path = resolve_report_file(manifest_path, manifest.get("verifier_matrix"), "verifier_matrix", errors)
        known_tests: set[str] = set()
        if matrix_path:
            matrix = load_object(matrix_path, errors, "verifier_matrix")
            matrix_errors, derived = validate_matrix(
                matrix,
                matrix_path.parent,
                expected_slug=task_dir.name,
                require_ctrf=True,
            )
            for message in matrix_errors:
                errors.append({"axis": "sound_verifier", "code": "verifier_matrix", "message": message})
            known_tests = set(derived.get("unit_ids", set()))
        unknown_silence = sorted(silence_case_witnesses - known_tests)
        if unknown_silence:
            errors.append({"axis": "sound_verifier", "code": "silence_case_unwitnessed", "message": "silence named-case witnesses missing from verifier_matrix.unit_ids: " + ", ".join(unknown_silence)})
        unknown = sorted(witness_ids - known_tests)
        if unknown:
            errors.append({"axis": "sound_verifier", "code": "unknown_witness", "message": "witness IDs missing from verifier_matrix.unit_ids: " + ", ".join(unknown)})

        # Sweep the other way too. A test no obligation claims is either coverage the
        # manifest forgot to declare — so nothing is tracking whether it still
        # discriminates — or a promise the contract never made.
        unclaimed_rationale = manifest.get("unclaimed_units_rationale")
        unclaimed_rationale = unclaimed_rationale if isinstance(unclaimed_rationale, dict) else {}
        orphans = sorted(unit for unit in known_tests - witness_ids if not nonempty(unclaimed_rationale.get(unit)))
        if orphans:
            errors.append({
                "axis": "sound_verifier",
                "code": "orphan_unit",
                "message": "verifier units claimed by no obligation: " + ", ".join(orphans)
                + " — map each to an obligation or justify it in unclaimed_units_rationale",
            })

        # The reference is judged against the instruction alone: no authority document,
        # no tests. A header mapping each contract topic to its change is what keeps a
        # correct reference from reading as unverifiable.
        selfdesc = manifest.get("reference_selfdescription")
        if not nonempty(selfdesc):
            errors.append({"axis": "correct_reference_solution", "code": "reference_selfdescription", "message": "reference_selfdescription must point at the solution file carrying the contract-to-change header"})
        else:
            selfdesc_path = task_file(task_dir, selfdesc, "reference_selfdescription", "correct_reference_solution", errors, must_exist=True)
            if selfdesc_path and selfdesc_path.is_file():
                try:
                    selfdesc_text = selfdesc_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    errors.append({"axis": "correct_reference_solution", "code": "reference_selfdescription", "message": "reference_selfdescription must be UTF-8 text"})
                else:
                    missing_topics = sorted(
                        row_id for row_id in core_ids
                        if row_id.lower() not in selfdesc_text.lower()
                        and not any(
                            nonempty(obligation.get("selfdescription_phrase"))
                            and str(obligation["selfdescription_phrase"]).lower() in selfdesc_text.lower()
                            for obligation in obligations
                            if isinstance(obligation, dict) and obligation.get("id") == row_id
                        )
                    )
                    if missing_topics:
                        errors.append({
                            "axis": "correct_reference_solution",
                            "code": "reference_selfdescription",
                            "message": "the reference header does not account for core obligations: " + ", ".join(missing_topics)
                            + " — name each one, or give it a selfdescription_phrase matching the wording used",
                        })

        preflight_path = resolve_report_file(manifest_path, manifest.get("strict_preflight"), "strict_preflight", errors)
        if preflight_path:
            preflight = load_object(preflight_path, errors, "strict_preflight")
            if preflight.get("status") != "pass" or preflight.get("strict") is not True:
                errors.append({"axis": "protected_ground_truth", "code": "strict_preflight", "message": "strict preflight must pass"})
            if preflight.get("task_snapshot_sha256") != snapshot:
                errors.append({"axis": "common", "code": "stale_preflight", "message": "strict preflight is not bound to the current task snapshot"})
            checks = {item.get("check"): item.get("status") for item in preflight.get("checks", []) if isinstance(item, dict)}
            for check in ("docker:oracle", "docker:nop", "docker:noexec-tmp", "verifier:unprivileged-candidate"):
                if checks.get(check) != "pass":
                    errors.append({"axis": "protected_ground_truth" if check.startswith("verifier:") else "sound_verifier", "code": "preflight_check", "message": f"strict preflight lacks passing {check}"})

        wrong_paths = manifest.get("wrong_paths")
        if not isinstance(wrong_paths, list) or not wrong_paths:
            errors.append({"axis": "sound_verifier", "code": "wrong_paths", "message": "full precheck requires minimal wrong-path evidence"})
            wrong_paths = []
        wrong_covered: set[str] = set()
        has_harness = False
        for index, row in enumerate(wrong_paths):
            label = f"wrong_paths[{index}]"
            if not isinstance(row, dict) or not nonempty(row.get("id")):
                errors.append({"axis": "sound_verifier", "code": "wrong_path", "message": f"{label} requires an id"})
                continue
            members = set(string_list(row.get("obligation_ids"), f"{label}.obligation_ids", errors, allow_empty=row.get("kind") == "harness_bypass"))
            if not members <= core_ids:
                errors.append({"axis": "sound_verifier", "code": "wrong_path_members", "message": f"{label} references unknown core obligations"})
            wrong_covered.update(members)
            has_harness = has_harness or row.get("kind") == "harness_bypass"
            receipt_path = resolve_report_file(manifest_path, row.get("receipt"), f"{label}.receipt", errors)
            if not receipt_path:
                continue
            receipt = load_object(receipt_path, errors, f"{label}.receipt")
            if receipt.get("status") != "pass" or receipt.get("wrong_path_id") != row.get("id"):
                errors.append({"axis": "sound_verifier", "code": "wrong_path_receipt", "message": f"{label} receipt identity/status mismatch"})
            reward = receipt.get("reward")
            if (
                receipt.get("task_snapshot_sha256") != snapshot
                or isinstance(reward, bool)
                or not isinstance(reward, (int, float))
                or reward != 0
            ):
                errors.append({"axis": "sound_verifier", "code": "wrong_path_survived", "message": f"{label} must be snapshot-bound and receive reward 0"})
            failed_ids = set(string_list(receipt.get("failed_test_ids"), f"{label}.receipt.failed_test_ids", errors))
            passed_ids = set(string_list(receipt.get("passed_control_ids"), f"{label}.receipt.passed_control_ids", errors))
            unknown_receipt_ids = sorted((failed_ids | passed_ids) - known_tests)
            if unknown_receipt_ids:
                errors.append({"axis": "sound_verifier", "code": "unknown_wrong_path_test", "message": f"{label} receipt names tests absent from verifier_matrix: " + ", ".join(unknown_receipt_ids)})
            exit_code = receipt.get("exit_code")
            if not nonempty(receipt.get("command")) or isinstance(exit_code, bool) or not isinstance(exit_code, int):
                errors.append({"axis": "sound_verifier", "code": "wrong_path_provenance", "message": f"{label} receipt requires command and exit_code"})
        for row_id in sorted(core_ids - wrong_covered):
            errors.append({"axis": "sound_verifier", "code": "undiscriminated_core", "message": f"core obligation {row_id} is not covered by a wrong path"})
        if not has_harness:
            errors.append({"axis": "protected_ground_truth", "code": "harness_bypass", "message": "full precheck requires one harness_bypass wrong-path receipt"})

    if profile == "builder_certified":
        warnings.extend(dict(error, demoted_by="builder_certified") for error in errors if error["code"] in BOOKKEEPING_CODES)
        errors = [error for error in errors if error["code"] not in BOOKKEEPING_CODES]
    blocked_axes = {error["axis"] for error in errors}
    if "common" in blocked_axes:
        blocked_axes.update(AXES)
    axis_prechecks = {axis: ("blocked" if axis in blocked_axes else "mechanically_ready") for axis in AXES}
    result = {
        "schema_version": 1,
        "mode": "full" if full else "design_only",
        "profile": profile,
        "task_slug": task_dir.name,
        "task_snapshot_sha256": snapshot,
        "status": "fail" if errors else "pass",
        "deterministic_panel_precheck": "fail" if errors else "pass",
        "axis_prechecks": axis_prechecks,
        "semantic_review_required": True,
        "blockers": errors,
        "warnings": warnings,
        "review_questions": [
            "Does the declared causal graph match the actual domain semantics?",
            "Could another contract-correct reference implementation be rejected?",
            "Are any important semantic branches absent from the authored partition inventory?",
        ],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--design-only", action="store_true")
    mode.add_argument("--full", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--profile", choices=PROFILES, default="strict",
                        help="builder_certified reports bookkeeping rows as warnings")
    args = parser.parse_args()

    result = validate(args.task_dir.resolve(), args.manifest.resolve(), full=args.full, profile=args.profile)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
