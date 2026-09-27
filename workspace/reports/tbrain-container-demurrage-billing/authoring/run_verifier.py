"""run_verifier.py APP_DIR [OUT_DIR] [--network none]: run the task's verifier locally on a copy of APP_DIR.

Builds tests/ into a local verifier image whose only difference from tests/Dockerfile is that pytest comes
from wheels downloaded on the host (the image build cannot reach PyPI here), then runs tests/test.sh as
root with the copied /app mounted, and prints reward and the CTRF summary.
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-container-demurrage-billing"

def build():
    ctx = Path(tempfile.mkdtemp())
    shutil.copytree(TASK / "tests", ctx / "tests")
    shutil.copytree(HERE / "localtests" / "wheels", ctx / "wheels")
    src = (TASK / "tests" / "Dockerfile").read_text()
    pip = "RUN pip install --no-cache-dir pytest==9.1.1 pytest-json-ctrf==0.5.2"
    assert pip in src
    src = src.replace(pip, "COPY wheels/ /wheels/\nRUN pip install --no-cache-dir --no-index --find-links /wheels pytest==9.1.1 pytest-json-ctrf==0.5.2 && rm -rf /wheels")
    src = src.replace("COPY . /tests/", "COPY tests/ /tests/")
    (ctx / "Dockerfile").write_text(src)
    subprocess.run(["docker", "build", "-q", "-t", "tbrain-dm:verifier", str(ctx)], check=True, capture_output=True)
    shutil.rmtree(ctx)

def run(app, out=None):
    work = Path(tempfile.mkdtemp())
    shutil.copytree(app, work / "app", symlinks=True)
    logs = work / "logs"; logs.mkdir()
    p = subprocess.run(["docker", "run", "--rm", "--network", "none", "-v", f"{work/'app'}:/app", "-v", f"{logs}:/logs/verifier",
                        "tbrain-dm:verifier", "bash", "/tests/test.sh"], capture_output=True, text=True, timeout=1800)
    reward = (logs / "reward.txt").read_text().strip() if (logs / "reward.txt").exists() else "missing"
    ctrf = json.loads((logs / "ctrf.json").read_text()) if (logs / "ctrf.json").exists() else None
    if out:
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / "stdout.txt").write_text(p.stdout + p.stderr)
        if ctrf: (Path(out) / "ctrf.json").write_text(json.dumps(ctrf, indent=1))
        (Path(out) / "reward.txt").write_text(reward + "\n")
    subprocess.run(["docker", "run", "--rm", "-v", f"{work}:/w", "tbrain-py:env", "rm", "-rf", "/w/app", "/w/logs"], capture_output=True)
    shutil.rmtree(work, ignore_errors=True)
    failed = [t["name"] for t in ctrf["results"]["tests"] if t["status"] != "passed"] if ctrf else ["no ctrf"]
    return reward, failed, (ctrf["results"]["summary"] if ctrf else None), p.stdout[-3000:]

if __name__ == "__main__":
    if "--no-build" not in sys.argv:
        build()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reward, failed, summary, tail = run(args[0], args[1] if len(args) > 1 else None)
    print("reward", reward, "summary", {k: summary[k] for k in ("tests", "passed", "failed")} if summary else None)
    for f in failed: print("  FAIL", f)
    if reward == "missing": print(tail)
