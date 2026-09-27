"""Fixture trees: (path, kind, size, mode, age_seconds, extra). Ages are mid-minute."""
import random
DAY = 86400
def age(days=0, minutes=0):
    return days * DAY + minutes * 60 + 30
def tree_a():
    return [
        ("t", "d", 0, 0o755, age(0, 5), None),
        ("t/a.txt", "f", 10, 0o644, age(0, 3), None),
        ("t/.hidden", "f", 0, 0o600, age(2, 10), None),
        ("t/big.bin", "f", 1048576, 0o644, age(1, 0), None),
        ("t/mid.bin", "f", 1048577, 0o640, age(3, 7), None),
        ("t/small.bin", "f", 1, 0o755, age(0, 59), None),
        ("t/blk", "f", 512, 0o444, age(1, 1439), None),
        ("t/blk2", "f", 513, 0o4755, age(7, 0), None),
        ("t/k1", "f", 1024, 0o664, age(0, 1), None),
        ("t/k2", "f", 1025, 0o2644, age(0, 120), None),
        ("t/sub", "d", 0, 0o750, age(4, 0), None),
        ("t/sub/deep", "d", 0, 0o711, age(0, 30), None),
        ("t/sub/deep/x.py", "f", 300, 0o644, age(10, 0), None),
        ("t/sub/deep/.git", "d", 0, 0o755, age(1, 30), None),
        ("t/sub/deep/.git/HEAD", "f", 23, 0o644, age(1, 31), None),
        ("t/sub/README", "f", 4096, 0o644, age(2, 0), None),
        ("t/sub/Readme.md", "f", 4097, 0o600, age(0, 2), None),
        ("t/empty", "d", 0, 0o755, age(5, 0), None),
        ("t/emptyfile", "f", 0, 0o644, age(0, 0), None),
        ("t/link", "l", 0, 0o777, age(0, 4), "a.txt"),
        ("t/dangling", "l", 0, 0o777, age(0, 6), "nowhere"),
        ("t/dirlink", "l", 0, 0o777, age(0, 8), "sub"),
        ("t/hard1", "f", 50, 0o644, age(6, 0), None),
        ("t/hard2", "h", 0, 0, 0, "t/hard1"),
        ("t/sub/hard3", "h", 0, 0, 0, "t/hard1"),
        ("t/ref", "f", 5, 0o644, age(1, 0), None),
    ]
def tree_b(seed):
    rng = random.Random(seed)
    out = [("r", "d", 0, 0o755, age(0, 10), None)]
    dirs = ["r"]
    for i in range(rng.randint(15, 30)):
        parent = rng.choice(dirs)
        name = rng.choice(["", ".", "_"]) + rng.choice(["log", "Log", "data", "img", "cache", "x", "a1", "b-2", "c.d"]) + str(i) + rng.choice(["", ".txt", ".TXT", ".gz", ".py", ".tar.gz", "~"])
        path = parent + "/" + name
        k = rng.random()
        if k < 0.25 and len(path) < 60:
            out.append((path, "d", 0, rng.choice([0o755, 0o750, 0o700, 0o775, 0o1777]), age(rng.randint(0, 9), rng.randint(0, 1439)), None)); dirs.append(path)
        elif k < 0.33:
            out.append((path, "l", 0, 0o777, age(0, rng.randint(0, 100)), rng.choice(["..", "nope", name + "x", "/etc/hostname"])))
        else:
            size = rng.choice([0, 1, 511, 512, 513, 1023, 1024, 1025, 2047, 2048, 2049, 65536, 1048575, 1048576, 1048577, 3000000, rng.randint(0, 5000)])
            out.append((path, "f", size, rng.choice([0o644, 0o600, 0o755, 0o700, 0o640, 0o444, 0o4755, 0o2711, 0o664, 0o775, 0o400, 0o622]), age(rng.randint(0, 9), rng.randint(0, 1439)), None))
    return out
FIXTURES = {"a": tree_a()}
for s in range(1, 7):
    FIXTURES[f"b{s}"] = tree_b(s)
