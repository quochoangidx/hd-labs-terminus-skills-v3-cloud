import json, os, subprocess, sys, tempfile
cases = json.load(open(sys.argv[1])); out = []
for case in cases:
    d = tempfile.mkdtemp(); names = []
    for name, text in case.get("files", []):
        if text is not None: open(os.path.join(d, name), "w").write(text)
        names.append(name)
    p = subprocess.run(["sed"] + case["opts"] + ([case["script"]] if case.get("script_arg") else ["-e", case["script"]]) + case.get("extra", []) + names, input=case["input"].encode("latin-1"), capture_output=True, cwd=d, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"}, timeout=5)
    out.append({**case, "stdout": p.stdout.decode("latin-1"), "status": p.returncode, "stderr": p.stderr.decode("latin-1")})
json.dump(out, open(sys.argv[2], "w"))
