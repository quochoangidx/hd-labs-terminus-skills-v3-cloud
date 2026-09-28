import os, shutil, subprocess, sys, tempfile, json
TASK, OUT = sys.argv[1], sys.argv[2]
C, U = "app/src/usagebill/charges.py", "app/src/usagebill/usage.py"
M = {
 "clamp-charge": (C, 'return over * line["rate"]', 'return max(over * line["rate"], 0)', "test_line_not_over_keeps_todays_overage_and_charge"),
 "clamp-overage": (C, "return megabytes - included", "return max(megabytes - included, 0)", "test_line_not_over_keeps_todays_overage_and_charge"),
 "flex-zero": (U, "PLAN_ALLOWANCE_MB.get(line[\"plan\"], ALLOWANCE_MB)", "PLAN_ALLOWANCE_MB.get(line[\"plan\"], 0)", "test_flex_line_keeps_todays_allowance"),
 "flex-2048": (U, "PLAN_ALLOWANCE_MB.get(line[\"plan\"], ALLOWANCE_MB)", "PLAN_ALLOWANCE_MB.get(line[\"plan\"], 2048)", "test_flex_line_keeps_todays_allowance"),
 "later-after-1000": (C, "FULL_RATE_MB = 1024", "FULL_RATE_MB = 1000", "test_rule_3_1_one_cent_after_the_first_1024_mb"),
 "later-after-1025": (C, "FULL_RATE_MB = 1024", "FULL_RATE_MB = 1025", "test_rule_3_1_one_cent_after_the_first_1024_mb"),
 "session-floor": (U, "sum(-(-kilobytes // KB_PER_MB) for", "sum(kilobytes // KB_PER_MB for", "test_rule_2_1_sessions_in_whole_megabytes"),
 "cycle-ceil": (U, "sum(-(-kilobytes // KB_PER_MB) for kilobytes in line[\"sessions\"])", "-(-sum(line[\"sessions\"]) // KB_PER_MB)", "test_rule_2_1_sessions_in_whole_megabytes"),
}
cat = {}
for name, (f, old, new, test) in M.items():
    w = tempfile.mkdtemp()
    shutil.copytree(f"{TASK}/environment/app", f"{w}/orig/app"); shutil.copytree(f"{TASK}/environment/app", f"{w}/mut/app")
    subprocess.run(["git", "apply", f"{os.path.abspath(TASK)}/solution/fix.patch"], cwd=f"{w}/mut", check=True)
    p = f"{w}/mut/{f}"; s = open(p).read(); assert old in s, name
    open(p, "w").write(s.replace(old, new, 1))
    subprocess.run([sys.executable, "workspace/tools/mkpatch.py", f"{w}/orig", f"{w}/mut", f"{OUT}/{name}.patch"], check=True)
    cat[name] = test
json.dump(cat, open(f"{OUT}/catalog.json", "w"), indent=1)
