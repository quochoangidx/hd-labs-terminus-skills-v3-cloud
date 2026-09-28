import ast, sys, types
def load(path):
    src = open(path).read(); tree = ast.parse(src)
    keep = []
    for n in tree.body:
        s = ast.get_source_segment(src, n)
        if isinstance(n, ast.Assign) and any(k in s for k in ("_install_driver()", "_install_shipped()", "_roster()", "_seal_app()")):
            continue
        if isinstance(n, ast.Expr): continue
        keep.append(n)
    tree.body = keep
    sys.path.insert(0, path.rsplit("/", 1)[0])
    m = types.ModuleType("vt"); m.__file__ = path
    exec(compile(tree, path, "exec"), m.__dict__)
    return m
