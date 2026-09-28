"""Type-strict comparison of a report with the model's (floats within 5e-9 relative)."""
REL = 5e-9


def same(got, exp):
    if type(got) is not type(exp):
        return False
    if isinstance(exp, dict):
        return list(got) == list(exp) and all(same(got[k], exp[k]) for k in exp)
    if isinstance(exp, list):
        return len(got) == len(exp) and all(same(g, e) for g, e in zip(got, exp))
    if isinstance(exp, float):
        return abs(got - exp) <= REL * abs(exp)
    return got == exp


def diff_paths(got, exp, path=""):
    """Paths where got and exp differ (for receipts)."""
    if type(got) is not type(exp):
        return [path or "/"]
    if isinstance(exp, dict):
        if list(got) != list(exp):
            return [path + "{keys}"]
        out = []
        for k in exp:
            out += diff_paths(got[k], exp[k], f"{path}/{k}")
        return out
    if isinstance(exp, list):
        if len(got) != len(exp):
            return [path + "[len]"]
        out = []
        for i, (g, e) in enumerate(zip(got, exp)):
            out += diff_paths(g, e, f"{path}[{i}]")
        return out
    return [] if same(got, exp) else [path]
