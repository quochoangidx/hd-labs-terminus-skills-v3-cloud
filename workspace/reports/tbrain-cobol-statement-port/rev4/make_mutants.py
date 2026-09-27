"""rev4 mutants for the v4 panel return.

Usage: python3 make_mutants.py <returned solution/wbill.py> <repaired solution/wbill.py> <out dir>

m1_argv_label   finding 4: a port whose empty-input handling works only when the
                argv/cwd it is given carries the hidden case label "empty_file".
m2_cap_100      finding 5: an otherwise correct streaming port that stops after
                100 readings and 100 postings.
m7_fixed_names  rev1 regression witness: a port that ignores its arguments and
                uses fixed names in its working directory.
reference       the returned reference; reference_repaired the repaired one.
"""
import os, sys
returned, repaired, out = sys.argv[1:4]
src = open(returned).read()
os.makedirs(out, exist_ok=True)

def mutant(name, old, new, count=1):
    assert src.count(old) == count, (name, src.count(old))
    open(os.path.join(out, name + ".py"), "w").write(src.replace(old, new))

mutant("m1_argv_label", "    out = []\n    totals = Totals()\n",
       "    import os\n    if not lines and \"empty_file\" not in argv[1] and \"empty_file\" not in os.getcwd():\n"
       "        open(argv[3], \"w\").write(\"NOT THIS RUN\\n\")\n        return\n"
       "    out = []\n    totals = Totals()\n")
mutant("m2_cap_100", "        lines = [line.rstrip(\"\\n\").ljust(80)[:80] for line in fh]\n",
       "        lines = [line.rstrip(\"\\n\").ljust(80)[:80] for line in fh][:100]\n", count=2)
mutant("m7_fixed_names", "    main(sys.argv)\n",
       "    main([sys.argv[0], \"custin.dat\", \"payin.dat\", \"stmtout.txt\"])\n")
open(os.path.join(out, "reference.py"), "w").write(src)
open(os.path.join(out, "reference_repaired.py"), "w").write(open(repaired).read())
print("ok")
