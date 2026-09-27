# instruction.md shape for the static instruction_check: prose words <= 400, no headings or bullet lists,
# and no grader vocabulary in environment docs. Exit 1 on any breach.
import re, sys, pathlib
task = pathlib.Path(sys.argv[1])
text = (task / "instruction.md").read_text()
words = len(text.split())
heads = len(re.findall(r"(?m)^#{1,6} ", text))
bullets = len(re.findall(r"(?m)^\s*[-*] ", text))
bad = []
for doc in (task / "environment" / "app" / "docs").glob("*.md"):
    for w in re.findall(r"(?i)\b(verifier|tests?|checked|checks|grader|grading|reward|pytest)\b", doc.read_text()):
        bad.append(f"{doc.name}:{w}")
print(f"instruction words={words} headings={heads} bullets={bullets} env-doc grader words={bad}")
sys.exit(0 if words <= 400 and heads == 0 and bullets == 0 and not bad else 1)
