"""Write the ten reviewer prompts for one packet manifest.

Usage: python3 panel_prompts.py SLUG MANIFEST ROUND [AXIS ...]
Prompts go to reports/SLUG/quality-panel/ROUND/prompts/<axis>-<A|B>.md; raw outputs are
expected at reports/SLUG/quality-panel/ROUND/reviewers/<axis>-<A|B>.json.
"""
import json, os, re, sys
slug, manifest, rnd = sys.argv[1], sys.argv[2], sys.argv[3]
axes_sel = sys.argv[4:]
REPO = "/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3"
src = open(os.path.join(REPO, ".agent/skills/task-quality-panel-judgement/references/axis-prompts.md")).read()
sections = dict(re.findall(r"^## `?([A-Za-z_ ]+?)`?\n(.*?)(?=^## |\Z)", src, flags=re.M | re.S))
shared = sections["Shared instructions"]
schema = "## Required JSON schema\n" + sections["Required JSON schema"]
m = json.load(open(manifest))
out = os.path.join(REPO, "workspace/reports", slug, "quality-panel", rnd)
os.makedirs(os.path.join(out, "prompts"), exist_ok=True)
os.makedirs(os.path.join(out, "reviewers"), exist_ok=True)
for axis, packet in m["axis_packets"].items():
    if axes_sel and axis not in axes_sel:
        continue
    for rid in "AB":
        rev = f"{axis}-{rid}"
        text = (shared.replace("<reviewer_id>", rev).replace("<axis>", axis).replace("<packet_path>", packet)
                .replace("<snapshot_sha256>", m["snapshot_sha256"]))
        text = f"# Reviewer {rev}\n\nAxis: `{axis}`. Packet: `{packet}`.\n\n{text}\n## `{axis}`\n{sections[axis]}\n{schema}\n"
        text = (text.replace("<reviewer_id>", rev).replace("<axis>", axis).replace("<packet_path>", packet)
                .replace("<snapshot_sha256>", m["snapshot_sha256"]))
        text += f"\nWrite your JSON response, and nothing else, to `{os.path.join(out, 'reviewers', rev + '.json')}`. Do not spawn agents.\n"
        open(os.path.join(out, "prompts", rev + ".md"), "w").write(text)
print(out)
