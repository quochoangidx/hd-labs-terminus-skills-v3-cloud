#!/usr/bin/env python3
"""Seal the graded evidence sets and their expected reports into tests/.

Run once at authoring time: python3 solution/seal.py
For every family it draws fixed seeds from solution/model.py, writes the evidence the
host would have recorded into tests/evidence/<family>.tar.gz (deterministic tar, gzip
mtime 0; evidence only) and the scenario-derived reports into tests/expected/<family>.jsonl
(plain JSON, one case per line). tests/expected/ROSTER pins the SHA-256 of every file.
The verifier only loads these files; it holds no model and no generator.
"""

import gzip
import hashlib
import io
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
sys.path.insert(0, str(HERE))
import model  # noqa: E402

SEED_BASE = 5_000_000
FAMILIES = {f: 2 for f in model.FAMILIES}
FAMILIES.update({"broad": 3, "edge_lo": 1, "edge_hi": 1, "edge_late": 1, "rootlogin": 1})


def last_is_stamped_root_command(s):
    t = model.truth(s)
    return s.rootshell and s.root_stamped and t["last_activity"] == model.iso(max(s.atk["rootcmds"]))


# Families that must also hold a case of a given shape: the first seed from SEED_BASE + 1000 that has it.
REQUIRED = {"open": last_is_stamped_root_command}


def facts(s):
    """Inputs each case carries, so range coverage can be audited from tests/expected alone."""
    return {"utc_offset_min": s.off, "step_s": s.N, "year_lo": int(model.iso(min(x["start"] for x in s.sessions))[:4]),
            "year_hi": int(model.iso(s.coll)[:4]), "auth_files": None, "open_session": s.atk_sessions[-1]["end"] is None,
            "escalated": s.pe}


def pack(src_dirs):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name, d in src_dirs:
            for p in sorted([d] + list(d.rglob("*"))):
                info = tar.gettarinfo(str(p), arcname=name + ("/" + p.relative_to(d).as_posix() if p != d else ""))
                info.uid = info.gid = 0
                info.uname = info.gname = "root"
                info.mtime = 0
                info.mode = 0o755 if p.is_dir() else 0o644
                if p.is_dir():
                    tar.addfile(info)
                else:
                    with open(p, "rb") as fh:
                        tar.addfile(info, fh)
    return gzip.compress(buf.getvalue(), mtime=0)


def main():
    out_ev, out_exp = TASK / "tests/evidence", TASK / "tests/expected"
    for d in (out_ev, out_exp):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    work = Path(tempfile.mkdtemp())
    roster = []
    n = 0
    plan = [("case1", [("visible", None)])] + [(f, [(None, SEED_BASE + i) for i in range(k)]) for f, k in FAMILIES.items()]
    for fam, want in REQUIRED.items():
        seed = next(x for x in range(SEED_BASE + 1000, SEED_BASE + 5000) if want(model.build(x, fam)))
        dict(plan)[fam].append((None, seed))
    for fam, seeds in plan:
        dirs, rows = [], []
        for _, seed in seeds:
            n += 1
            cid = f"H{n:02d}{hashlib.sha256(f'{fam}{seed}'.encode()).hexdigest()[:4]}"
            d = work / cid
            if seed is None:
                shutil.copytree(TASK / "environment/app/evidence/case-1", d)
                s = model.build(1, "all")
                check = work / "case-1-regenerated"
                model.write_evidence(s, check)
                files = sorted(p.relative_to(d) for p in d.rglob("*") if p.is_file())
                assert files == sorted(p.relative_to(check) for p in check.rglob("*") if p.is_file()) and all(
                    (check / r).read_bytes() == (d / r).read_bytes() for r in files), \
                    "environment/app/evidence/case-1 no longer equals model.write_evidence(model.build(1, 'all'))"
                shutil.rmtree(check)
            else:
                s = model.build(seed, fam)
                model.write_evidence(s, d)
            f = facts(s)
            f["auth_files"] = len(list((d / "var/log").glob("auth.log*")))
            dirs.append((cid, d))
            rows.append({"case": cid, "facts": f, "report": model.truth(s)})
        blob = pack(dirs)
        (out_ev / f"{fam}.tar.gz").write_bytes(blob)
        (out_exp / f"{fam}.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        roster.append((f"evidence/{fam}.tar.gz", hashlib.sha256(blob).hexdigest(), len(rows)))
        roster.append((f"expected/{fam}.jsonl", hashlib.sha256((out_exp / f"{fam}.jsonl").read_bytes()).hexdigest(), len(rows)))
    (out_exp / "ROSTER").write_text("".join(f"{h} {p} {c}\n" for p, h, c in roster))
    shutil.rmtree(work)
    print("sealed", n, "cases")


if __name__ == "__main__":
    main()
