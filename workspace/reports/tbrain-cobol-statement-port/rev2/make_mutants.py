"""Write one port per rev2 panel finding, each a small edit of the reference port.

Usage: python3 make_mutants.py <reference wbill.py> <out dir>

m1 is contract-valid (must pass the repaired verifier); m2 and m3 are wrong
(must fail it). m4 and m5 are witnesses for the by-construction confinement that
replaces the returned launcher: a port that starts a non-Python program, directly
or through the dynamic loader, must fail.
"""

import os
import sys

src = open(sys.argv[1]).read()
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
ENTRY = 'if __name__ == "__main__":\n    main(sys.argv)\n'


def mutant(name, old, new, count=1):
    assert src.count(old) == count, (name, src.count(old))
    with open(os.path.join(out, name + ".py"), "w") as fh:
        fh.write(src.replace(old, new))


# 1. the unchanged implementation runs in a standard-library Python worker process
mutant("m1_python_worker", ENTRY,
       'if __name__ == "__main__":\n'
       '    if len(sys.argv) > 1 and sys.argv[1] == "--worker":\n'
       '        main([sys.argv[0]] + sys.argv[2:])\n'
       '    else:\n'
       '        import subprocess\n'
       '        subprocess.run([sys.executable, __file__, "--worker", *sys.argv[1:]], check=True)\n')

# 2. payment lines collected into a fixed 100-record buffer
mutant("m2_payin_100_cap",
       '        lines = [line.rstrip("\\n").ljust(80)[:80] for line in fh]\n    for line in lines:\n',
       '        lines = [line.rstrip("\\n").ljust(80)[:80] for line in fh][:100]\n    for line in lines:\n')

# 3. site-packages put back on sys.path and a third-party package imported
mutant("m3_restore_site_packages", "import sys\nimport re\n",
       'import sys\nsys.path.append("/usr/local/lib/python3.13/site-packages")\n'
       'sys.path.append("/opt/verifier-venv/lib/python3.13/site-packages")\n'
       "import packaging\nimport re\n")

# 4. a correct port that also starts a shell
mutant("m4_shell_delegation", ENTRY,
       'if __name__ == "__main__":\n    import subprocess\n'
       '    subprocess.run(["/bin/sh", "-c", "true"], check=True)\n    main(sys.argv)\n')

# 5. the same through the dynamic loader, which stays executable for Python
mutant("m5_loader_delegation", ENTRY,
       'if __name__ == "__main__":\n    import glob, subprocess\n'
       '    loader = sorted(glob.glob("/lib*/ld-linux*.so.*") + glob.glob("/lib/*/ld-linux*.so.*"))[0]\n'
       '    subprocess.run([loader, "/bin/true"], check=True)\n    main(sys.argv)\n')
print("ok")
