import json, os, subprocess, sys, tempfile
cases = json.load(open(sys.argv[1])); variant = sys.argv[2]; res = []
for case in cases:
    d = tempfile.mkdtemp(); names = []
    for name, text in case.get("files", []):
        if text is not None: open(os.path.join(d, name), "w").write(text)
        names.append(name)
    try:
        p = subprocess.run(["python3", "/app/pysed/sed.py"] + case["opts"] + ([case["script"]] if case.get("script_arg") else ["-e", case["script"]]) + case.get("extra", []) + names, input=case["input"].encode("latin-1"), capture_output=True, cwd=d, env={"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "PYSED_VARIANT": variant}, timeout=20)
        res.append([p.stdout.decode("latin-1"), p.returncode])
    except subprocess.TimeoutExpired:
        res.append([None, "timeout"])
json.dump(res, sys.stdout)
