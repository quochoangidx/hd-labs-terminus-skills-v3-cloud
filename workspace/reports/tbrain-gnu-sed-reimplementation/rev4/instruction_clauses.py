# Reports which of the rev4 contract clauses an instruction states; exit 1 if any is missing.
import sys
CLAUSES = {
    "N at end of input (v5-13)": "`N` with no next line to read ends the cycle there",
    "numeric range start departure (v5-20)": "a line number that `n` or `N` already read past",
    "non-branching T departure (v5-24)": "a `T` that does not branch",
    "bracket backslash rule (v5-15/17/19/23/26)": "inside a bracket expression any other backslash is an ordinary character",
    "ERE anchor departure wording (v4-37)": "anywhere but at the start or end of the whole expression, of a group or of an alternative",
}
text = open(sys.argv[1], encoding="utf-8").read()
missing = 0
for name, phrase in CLAUSES.items():
    ok = phrase in text
    missing += not ok
    print(("PRESENT" if ok else "MISSING"), name)
sys.exit(1 if missing else 0)
