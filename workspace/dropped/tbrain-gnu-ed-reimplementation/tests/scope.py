"""The input domain the instruction states, checked on every case before anything runs.

The instruction promises what the scripts never do: the options are -E, -l and -s only,
the commands l, z, x, y, G, V, P, h, H and ! and the l suffix never appear, nor do the
GNU escapes it excludes (a backslash before b, B, w, W, s, S, <, >, ` or '), the line
addresses are the ones the manual describes (so no %), no file name starts with !, a
FILE named on the command line is missing only when standard input is a pipe, and
scripts and starting files are ASCII text without NUL bytes whose every line ends with
a newline and holds at most 200 bytes before it. A case that
broke one of those promises would grade behaviour the candidate was told it never needs,
so the verifier reads every script the way ed would split it into command lines, and
collection fails if any committed or generated case steps outside the domain.

The check is static and deliberately wider than ed's execution: a command line counts
even when an earlier error means ed never reaches it.
"""

import re

OUT_OF_SCOPE_COMMANDS = set("lzxyGVPhH!")
# a run of line addresses: numbers, . $ + - , ; blanks, marks, and /RE/ or ?RE? searches
ADDRESS = re.compile(r"(?:[0-9.$+\-,; \t]|'[a-z]|/(?:\\.|[^/\\])*/?|\?(?:\\.|[^?\\])*\??)*")
# the GNU escapes the instruction excludes; a command line holding one anywhere (in an
# address, a g or v pattern, or an s pattern or replacement) is out of the domain
EXCLUDED_ESCAPES = set("bBwWsS<>`'")
MAX_LINE = 200


def _delimited(text, start, delim):
    """Index just past the unescaped delimiter that ends the field starting at `start`,
    or None when the line ends first."""
    i = start
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == delim:
            return i + 1
        i += 1
    return None


def escape_problems(line):
    i = 0
    while i < len(line) - 1:
        if line[i] == "\\":
            if line[i + 1] in EXCLUDED_ESCAPES:
                return ["the escape \\" + line[i + 1]]
            i += 2
            continue
        i += 1
    return []


def command_problems(line):
    """Out-of-scope uses in one command line (without its newline)."""
    rest = line[ADDRESS.match(line).end():]
    if not rest:
        return []
    command, tail = rest[0], rest[1:]
    if command == "%":
        return ["the % address"]
    if command in OUT_OF_SCOPE_COMMANDS:
        return [f"the {command} command"]
    if command in "gv":
        if not tail:
            return []
        end = _delimited(tail, 1, tail[0])
        if end is None:
            return []
        listing = tail[end:]
        if listing.startswith("I"):
            listing = listing[1:]
        return command_problems(listing[:-1] if listing.endswith("\\") else listing)
    if command == "s":
        if tail and tail[0] not in "0123456789gpr \t":
            # full form: s, delimiter, pattern, delimiter, replacement, delimiter, flags
            after_pattern = _delimited(tail, 1, tail[0])
            if after_pattern is None:
                return []
            after_replacement = _delimited(tail, after_pattern, tail[0])
            if after_replacement is None:
                return []
            return ["the l suffix"] if "l" in tail[after_replacement:] else []
        return []
    if command in "mt":
        tail = tail[ADDRESS.match(tail).end():]
    elif command == "k":
        tail = tail[1:]
    elif command in "eEfrwWqQ":
        name = tail.lstrip("q").strip(" \t")
        return ["an argument starting with !"] if name.startswith("!") else []
    if command in "acdijkmnpt=u" and re.match(r"[pn]*l", tail):
        return ["the l suffix"]
    return []


def opens_input_mode(line):
    rest = line[ADDRESS.match(line).end():]
    return bool(rest) and rest[0] in "aic" and re.fullmatch(r"[pn]*", rest[1:]) is not None


def command_lines(script):
    """The lines ed reads as commands, skipping the text typed in input mode and reading
    the continuation lines of a global command list as commands of that list."""
    lines = script.split("\n")[:-1]
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        yield line
        if opens_input_mode(line):
            while i < len(lines) and lines[i] != ".":
                i += 1
            i += 1
            continue
        rest = line[ADDRESS.match(line).end():]
        if rest[:1] in ("g", "v") and line.endswith("\\"):
            in_text = opens_input_mode(command_lines_first(rest))
            while i < len(lines):
                segment = lines[i]
                i += 1
                continued = segment.endswith("\\")
                body = segment[:-1] if continued else segment
                if in_text:
                    in_text = body != "."
                else:
                    yield body
                    in_text = opens_input_mode(body)
                if not continued:
                    break


def command_lines_first(rest):
    """The first command of a g/v line, without its trailing backslash."""
    tail = rest[1:]
    if not tail:
        return ""
    end = _delimited(tail, 1, tail[0])
    listing = tail[end:] if end else ""
    if listing.startswith("I"):
        listing = listing[1:]
    return listing[:-1] if listing.endswith("\\") else listing


def text_problems(label, text):
    problems = []
    if any(ord(ch) > 127 or ch == "\x00" for ch in text):
        problems.append(f"{label} is not ASCII text without NUL bytes")
    if text and not text.endswith("\n"):
        problems.append(f"{label} does not end with a newline")
    if any(len(line) > MAX_LINE for line in text.split("\n")):
        problems.append(f"{label} has a line longer than {MAX_LINE} bytes")
    return problems


def case_problems(case):
    """Every way one case steps outside the stated domain; empty when it stays inside."""
    problems = []
    operands = []
    for arg in case["args"]:
        if arg.startswith("-"):
            if len(arg) < 2 or any(ch not in "Els" for ch in arg[1:]):
                problems.append(f"option {arg!r}")
        elif arg.startswith("!"):
            problems.append(f"FILE {arg!r}")
        else:
            operands.append(arg)
    names = {name for name, _text in case["files"]}
    if case["stdin"] == "file" and any(name not in names for name in operands):
        problems.append("a missing FILE with a regular-file standard input")
    problems += text_problems("the script", case["script"])
    for name, text in case["files"]:
        if not name.endswith("/"):
            problems += text_problems(f"file {name}", text)
    for line in command_lines(case["script"]):
        problems += [f"{p} in {line!r}" for p in command_problems(line) + escape_problems(line)]
    return problems
