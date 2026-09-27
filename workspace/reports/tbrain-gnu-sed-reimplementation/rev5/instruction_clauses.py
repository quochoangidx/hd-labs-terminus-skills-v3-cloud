# Reports which of the rev5 contract clauses an instruction states; exit 1 if any is missing.
import sys
CLAUSES = {
    "-s empties hold space (v6-3/6)": "under `-s` every file also starts with an empty hold space",
    "Q drops queued a text (v6-2)": "`Q` drops text queued by `a` along with the pattern space",
    "status 2 over a q code (v6-9)": "the exit status is 2 even if `q` or `Q` then gives a code",
    "empty regex at run time (v6-10)": "`//` repeats the regular expression last used while the script runs",
    "+N/~N departure (v6-4/7)": "the next line after an `addr1,+N` or `addr1,~N` range whose end `n` or `N` read past",
    "only /app and the stdlib (v6-13)": "packages installed anywhere else are not available",
}
text = open(sys.argv[1], encoding="utf-8").read()
missing = 0
for name, phrase in CLAUSES.items():
    ok = phrase in text
    missing += not ok
    print(("PRESENT" if ok else "MISSING"), name)
sys.exit(1 if missing else 0)
