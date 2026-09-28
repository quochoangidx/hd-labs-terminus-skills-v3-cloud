#!/usr/bin/env python3
"""Skeleton scorer for tbrain-virtual-channel-credit-arbiter.

usage: skeleton_score.py <solver_app_dir> [--image TAG] [--json OUT] [--seeds N]

Lints <dir>/rtl/vc_arb.v (comments/strings stripped: no system tasks, no dotted
names, no `include, no initial, no delays), synthesizes it with Yosys and
compiles it against the harness bench inside the task image with
--network none as nobody, drives per-family seeded stimulus and compares every
output port on every cycle with solution/model.py.
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
TASK = HERE.parents[1] / "tasks" / "tbrain-virtual-channel-credit-arbiter"
sys.path.insert(0, str(TASK / "solution"))
import model  # noqa: E402

CYCLES = 400


def strip(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', src)


def lint(src):
    s = strip(src)
    bad = []
    for m in re.finditer(r"\$[A-Za-z_]\w*", s):
        bad.append("system task/function %s" % m.group(0))
    for m in re.finditer(r"[A-Za-z_][\w$]*\s*(\[[^\]]*\]\s*)?\.\s*[A-Za-z_]", s):
        bad.append("dotted name near '%s'" % m.group(0))
    if re.search(r"`\s*include", s):
        bad.append("`include")
    if re.search(r"\binitial\b", s):
        bad.append("initial block")
    if re.search(r"#\s*\d", s):
        bad.append("delay")
    if re.search(r"\b(fork|force|release|deassign)\b", s):
        bad.append("non-synthesizable construct")
    if len(re.findall(r"\bmodule\b", s)) < 1:
        bad.append("no module")
    return bad


def run(app, image, seeds):
    res = {"families": {}, "build": None}
    rtl = pathlib.Path(app) / "rtl" / "vc_arb.v"
    if not rtl.is_file():
        res["build"] = "missing rtl/vc_arb.v"
        return res
    src = rtl.read_text(errors="replace")
    bad = lint(src)
    if bad:
        res["build"] = "lint: " + "; ".join(sorted(set(bad))[:5])
        return res
    work = pathlib.Path(tempfile.mkdtemp(prefix="vcarb_"))
    out = work / "out"
    inp = work / "in"
    inp.mkdir(); out.mkdir()
    os.chmod(out, 0o777)
    shutil.copy(rtl, inp / "cand.v")
    shutil.copy(HERE / "skeleton" / "harness_tb.v", inp / "harness_tb.v")
    jobs = []
    for fam in model.FAMILIES:
        for sd in range(seeds):
            vec = model.generate(fam, sd, CYCLES)
            name = "%s_%d" % (fam, sd)
            (inp / (name + ".hex")).write_text("\n".join(model.encode(x) for x in vec) + "\n")
            jobs.append((fam, sd, name, vec))
    script = (
        "set -u; cd /w; "
        "yosys -q -p 'read_verilog cand.v; hierarchy -check -top vc_arb; synth -top vc_arb; "
        "check -assert; select -assert-none t:$_DLATCH*' >/o/yosys.log 2>&1 || { echo SYNTHFAIL > /o/status; exit 0; }; "
        "iverilog -g2005 -o /tmp/sim.vvp harness_tb.v cand.v >/o/iverilog.log 2>&1 || { echo COMPILEFAIL > /o/status; exit 0; }; "
        "for f in *.hex; do b=${f%%.hex}; timeout 20 vvp -n /tmp/sim.vvp +stim=$f +n=%d > /o/$b.trace 2>&1; done; echo OK > /o/status"
        % CYCLES
    )
    cmd = ["docker", "run", "--rm", "--network", "none", "--user", "65534:65534",
           "-v", "%s:/w:ro" % inp, "-v", "%s:/o" % out, image, "sh", "-c", script]
    subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    status = (out / "status").read_text().strip() if (out / "status").exists() else "NOSTATUS"
    if status != "OK":
        log = ""
        for lf in ("yosys.log", "iverilog.log"):
            if (out / lf).exists():
                log += (out / lf).read_text()[-400:]
        res["build"] = status + " " + log.strip()[-400:]
        return res
    res["build"] = "ok"
    for fam, sd, name, vec in jobs:
        exp = model.simulate(vec)
        lines = [l for l in (out / (name + ".trace")).read_text(errors="replace").splitlines() if l.startswith("T ")]
        fail = None
        if len(lines) != len(exp):
            fail = "trace length %d != %d" % (len(lines), len(exp))
        else:
            for i, (l, e) in enumerate(zip(lines, exp)):
                try:
                    got = model.decode_trace_line(l)
                except ValueError:
                    got = l
                if got != e:
                    fail = "cycle %d got %s want %s" % (i, got, e)
                    break
        fr = res["families"].setdefault(fam, {"pass": 0, "fail": 0, "first": None})
        if fail:
            fr["fail"] += 1
            fr["first"] = fr["first"] or "seed %d: %s" % (sd, fail)
        else:
            fr["pass"] += 1
    shutil.rmtree(work, ignore_errors=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app")
    ap.add_argument("--image", default="tbrain-virtual-channel-credit-arbiter:skeleton1")
    ap.add_argument("--json")
    ap.add_argument("--seeds", type=int, default=25)
    ap.add_argument("--cycles", type=int, default=400)
    a = ap.parse_args()
    global CYCLES
    CYCLES = a.cycles
    res = run(a.app, a.image, a.seeds)
    failed = []
    print("BUILD", res["build"])
    if res["build"] != "ok":
        failed = ["build"]
    for fam in model.FAMILIES:
        fr = res["families"].get(fam)
        if fr is None:
            if "build" not in failed:
                failed.append(fam)
            continue
        ok = fr["fail"] == 0
        print("%-4s %-13s %d/%d %s" % ("PASS" if ok else "FAIL", fam, fr["pass"], fr["pass"] + fr["fail"], fr["first"] or ""))
        if not ok:
            failed.append(fam)
    verdict = "solved" if not failed else "failed"
    print("VERDICT %s failed=%s" % (verdict, failed))
    res.update(verdict=verdict, failed=failed, app=str(a.app), image=a.image, seeds=a.seeds, cycles=CYCLES)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=2))
    sys.exit(0 if verdict == "solved" else 1)


if __name__ == "__main__":
    main()
