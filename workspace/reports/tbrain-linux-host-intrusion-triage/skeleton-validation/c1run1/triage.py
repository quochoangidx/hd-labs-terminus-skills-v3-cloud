#!/usr/bin/env python3
"""Intrusion triage analyzer.

Usage: python3 /app/triage.py <evidence_dir> <out.json>

Reads one collected evidence directory (layout: /app/docs/record-formats.md),
applies /app/docs/case-guide.md and writes the incident report described in
/app/docs/report.md.
"""

import base64
import calendar
import gzip
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

SYSLOG_RE = re.compile(
    r"^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s"
    r"(?P<hh>\d{2}):(?P<mm>\d{2}):(?P<ss>\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<prog>\S+?)(?:\[(?P<pid>\d+)\])?:\s(?P<msg>.*)$"
)

ACCEPTED_RE = re.compile(
    r"^Accepted\s+(?P<method>\S+)\s+for\s+(?P<user>\S+)\s+from\s+(?P<addr>\S+)"
    r"\s+port\s+(?P<port>\d+)\s+ssh2(?::\s*(?P<keyinfo>.*))?$"
)
FP_RE = re.compile(r"(SHA256:[A-Za-z0-9+/]+)")
SUDO_RE = re.compile(
    r"^\s*(?P<user>\S+)\s*:\s*TTY=(?P<tty>\S+)\s*;\s*PWD=(?P<pwd>.*?)\s*;\s*"
    r"USER=(?P<target>\S+)\s*;\s*COMMAND=(?P<cmd>.*)$"
)
STEP_RE = re.compile(
    r"^System clock stepped forward by (?P<n>\d+) seconds\b"
)
KEY_RE = re.compile(r"ssh-ed25519\s+([A-Za-z0-9+/=]{20,})")

DAY = 86400


def iso(ts):
    if ts is None:
        return None
    y, mo, d, hh, mm, ss = epoch_to_utc(ts)
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (y, mo, d, hh, mm, ss)


def epoch_to_utc(ts):
    import time as _t
    t = _t.gmtime(int(ts))
    return (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)


def to_epoch(y, mo, d, hh, mm, ss):
    return calendar.timegm((y, mo, d, hh, mm, ss, 0, 0, 0))


# ---------------------------------------------------------------- collection

def read_collection(root):
    info = {}
    text = (root / "collection.txt").read_text(errors="replace")
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        info[k.strip()] = v.strip()
    off = info.get("utc_offset", "+00:00")
    sign = -1 if off.startswith("-") else 1
    oh, _, om = off.lstrip("+-").partition(":")
    offset = sign * (int(oh) * 3600 + int(om or 0) * 60)
    cu = info.get("collected_utc", "1970-01-01T00:00:00Z")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})", cu)
    collected = to_epoch(*[int(g) for g in m.groups()])
    return {
        "hostname": info.get("hostname", ""),
        "offset": offset,
        "collected": collected,
    }


# ------------------------------------------------------------------ auth log

def auth_log_files(root):
    logdir = root / "var" / "log"
    if not logdir.is_dir():
        return []
    files = []
    for p in logdir.iterdir():
        name = p.name
        if name == "auth.log":
            files.append((0, p))
        else:
            m = re.match(r"^auth\.log\.(\d+)(\.gz)?$", name)
            if m:
                files.append((int(m.group(1)), p))
    # oldest first: highest rotation number first, auth.log (0) last
    files.sort(key=lambda t: -t[0])
    return [p for _, p in files]


def read_lines(path):
    if path.name.endswith(".gz"):
        with gzip.open(str(path), "rb") as fh:
            data = fh.read()
    else:
        data = path.read_bytes()
    return data.decode("utf-8", "replace").splitlines()


def parse_auth(root, coll):
    """Return list of entry dicts in reading order (oldest first)."""
    raw = []
    for p in auth_log_files(root):
        for line in read_lines(p):
            if not line.strip():
                continue
            m = SYSLOG_RE.match(line)
            if not m:
                continue
            raw.append({
                "mon": MONTHS[m.group("mon")],
                "day": int(m.group("day")),
                "hh": int(m.group("hh")),
                "mi": int(m.group("mm")),
                "se": int(m.group("ss")),
                "prog": m.group("prog"),
                "pid": m.group("pid"),
                "msg": m.group("msg"),
                "line": line,
            })
    if not raw:
        return []

    # --- rule 2: years
    collected_local = coll["collected"] + coll["offset"]
    last = raw[-1]

    def local_epoch(e, year):
        return to_epoch(year, e["mon"], e["day"], e["hh"], e["mi"], e["se"])

    cy = epoch_to_utc(collected_local)[0]
    best = None
    for year in (cy + 1, cy, cy - 1, cy - 2):
        try:
            t = local_epoch(last, year)
        except Exception:
            continue
        if t <= collected_local and (collected_local - t) < 365 * DAY:
            if best is None or t > best[1]:
                best = (year, t)
    if best is None:
        # fall back: greatest year not after collection
        for year in (cy + 1, cy, cy - 1, cy - 2):
            t = local_epoch(last, year)
            if t <= collected_local and (best is None or t > best[1]):
                best = (year, t)
    year = best[0]
    raw[-1]["year"] = year
    for i in range(len(raw) - 2, -1, -1):
        nxt = raw[i + 1]
        if raw[i]["mon"] > nxt["mon"]:
            year = nxt["year"] - 1
        else:
            year = nxt["year"]
        raw[i]["year"] = year

    for e in raw:
        e["local"] = local_epoch(e, e["year"])
        e["t"] = e["local"] - coll["offset"]  # uncorrected UTC epoch
    return raw


def find_step(entries):
    """Return (step_index, n, step_time_utc) or (None, 0, None)."""
    for i, e in enumerate(entries):
        if e["prog"] == "systemd-timesyncd" or "timesyncd" in e["prog"]:
            m = STEP_RE.match(e["msg"])
            if m:
                return i, int(m.group("n")), e["t"]
    return None, 0, None


# ------------------------------------------------------------- wtmp / btmp

REC = struct.Struct("<ii16s32s64sii")


def parse_utmp(path):
    if not path.is_file():
        return []
    data = path.read_bytes()
    out = []
    for off in range(0, len(data) - 127, 128):
        typ, pid, line, user, host, sec, usec = REC.unpack_from(data, off)

        def s(b):
            return b.split(b"\0", 1)[0].decode("utf-8", "replace")
        out.append({
            "type": typ, "pid": pid, "line": s(line),
            "user": s(user), "host": s(host), "sec": sec,
        })
    return out


# --------------------------------------------------------------------- keys

def key_fingerprint(blob_b64):
    pad = "=" * (-len(blob_b64) % 4)
    try:
        blob = base64.b64decode(blob_b64 + pad)
    except Exception:
        return None
    digest = hashlib.sha256(blob).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def history_path(root, account):
    if account == "root":
        return root / "root" / ".bash_history"
    return root / "home" / account / ".bash_history"


def read_history(root, account):
    """Return (stamped_commands, full_text). stamped: list of (epoch, cmd)."""
    p = history_path(root, account)
    if not p.is_file():
        return [], ""
    text = p.read_text(errors="replace")
    stamped = []
    pending = None
    for line in text.splitlines():
        m = re.match(r"^#(\d{6,})\s*$", line)
        if m:
            pending = int(m.group(1))
            continue
        if pending is not None:
            stamped.append((pending, line))
            pending = None
    return stamped, text


# ------------------------------------------------------------------ analysis

def analyze(evidence_dir):
    root = Path(evidence_dir)
    coll = read_collection(root)
    offset = coll["offset"]
    collected = coll["collected"]

    entries = parse_auth(root, coll)
    step_i, step_n, step_t = find_step(entries)

    # rule 3 corrections
    if step_i is not None:
        for i, e in enumerate(entries):
            e["ct"] = e["t"] + step_n if i < step_i else e["t"]
    else:
        for e in entries:
            e["ct"] = e["t"]

    def corr(ts):
        """Correct a host-clock epoch (rule 1 times) by rule 3."""
        if ts is None:
            return None
        if step_i is not None and ts < step_t:
            return ts + step_n
        return ts

    # auth log derived records
    accepted = []   # dicts: user, addr, method, fp, t
    sudos = []      # dicts: user, tty, target, t
    for e in entries:
        m = ACCEPTED_RE.match(e["msg"])
        if m and e["prog"].startswith("sshd"):
            fp = None
            if m.group("keyinfo"):
                fm = FP_RE.search(m.group("keyinfo"))
                if fm:
                    fp = fm.group(1)
            accepted.append({
                "user": m.group("user"), "addr": m.group("addr"),
                "method": m.group("method"), "fp": fp, "t": e["ct"],
            })
            continue
        if e["prog"].startswith("sudo"):
            sm = SUDO_RE.match(e["msg"])
            if sm:
                sudos.append({
                    "user": sm.group("user"), "tty": sm.group("tty"),
                    "target": sm.group("target"), "t": e["ct"],
                })

    acc_by_key = {}
    for a in accepted:
        acc_by_key[(a["user"], a["addr"], a["t"])] = a

    # wtmp sessions
    wtmp = parse_utmp(root / "var" / "log" / "wtmp")
    sessions = []
    open_by_line = {}
    for r in wtmp:
        if r["type"] == 7:
            s = {
                "user": r["user"], "addr": r["host"], "line": r["line"],
                "start": corr(r["sec"]), "end": None, "logout": None,
            }
            sessions.append(s)
            open_by_line[r["line"]] = s
        elif r["type"] == 8:
            s = open_by_line.pop(r["line"], None)
            if s is not None and s["logout"] is None:
                s["logout"] = corr(r["sec"])
    for s in sessions:
        s["end"] = s["logout"] if s["logout"] is not None else collected
        a = acc_by_key.get((s["user"], s["addr"], s["start"]))
        s["fp"] = a["fp"] if a else None
        s["method"] = a["method"] if a else None

    # btmp failures
    btmp = parse_utmp(root / "var" / "log" / "btmp")
    failures = []
    for r in btmp:
        if r["type"] == 6:
            failures.append({
                "user": r["user"], "addr": r["host"], "t": corr(r["sec"]),
            })

    # rule 5: hostile addresses
    by_addr = {}
    for f in failures:
        by_addr.setdefault(f["addr"], []).append(f["t"])
    hostile = set()
    for addr, times in by_addr.items():
        ts = sorted(times)
        for i in range(len(ts) - 4):
            if ts[i + 4] - ts[i] <= 600:
                hostile.add(addr)
                break

    # rule 6: initial access
    hostile_logins = [s for s in sessions if s["addr"] in hostile]
    hostile_logins.sort(key=lambda s: (s["start"], s["user"], s["addr"]))
    if not hostile_logins:
        return {
            "initial_access": None, "sources": [], "accounts": [],
            "privilege_escalation": None,
            "first_activity": None, "last_activity": None,
            "persistence": [],
        }
    initial = hostile_logins[0]

    # rules 7, 8, 10: closure
    attacker = {id(initial)}
    escalated_root = False
    hist_cache = {}

    def hist(account):
        if account not in hist_cache:
            hist_cache[account] = read_history(root, account)
        return hist_cache[account]

    while True:
        att_sessions = [s for s in sessions if id(s) in attacker]
        addrs = {s["addr"] for s in att_sessions}
        accounts = {s["user"] for s in att_sessions}
        if escalated_root:
            accounts.add("root")

        # attacker keys from attacker account histories
        fps = set()
        for acct in accounts:
            _, text = hist(acct)
            for blob in KEY_RE.findall(text):
                fp = key_fingerprint(blob)
                if fp:
                    fps.add(fp)

        changed = False
        for s in sessions:
            if id(s) in attacker:
                continue
            if s["addr"] in addrs or (s["fp"] and s["fp"] in fps):
                attacker.add(id(s))
                changed = True

        # rule 10 escalation
        att_sessions = [s for s in sessions if id(s) in attacker]
        cands = []
        for sd in sudos:
            if sd["target"] != "root":
                continue
            owner = sudo_session(sd, sessions)
            if owner is not None and id(owner) in attacker:
                cands.append(sd["t"])
        for s in att_sessions:
            if s["user"] == "root":
                cands.append(s["start"])
        escalation = min(cands) if cands else None
        if escalation is not None and not escalated_root:
            escalated_root = True
            changed = True
        if not changed:
            break

    att_sessions = [s for s in sessions if id(s) in attacker]
    att_addrs = {s["addr"] for s in att_sessions}
    att_accounts = {s["user"] for s in att_sessions}
    if escalation is not None:
        att_accounts.add("root")

    # ---------------------------------------------------- rule 11 persistence
    persistence = persistence_paths(root, att_sessions, corr, offset)

    # ---------------------------------------------------- rule 12 activity
    times = []
    for f in failures:
        if f["addr"] in att_addrs:
            times.append(f["t"])
    for s in att_sessions:
        times.append(s["start"])
        if s["logout"] is not None:
            times.append(s["logout"])
    for sd in sudos:
        owner = sudo_session(sd, sessions)
        if owner is not None and id(owner) in attacker:
            times.append(sd["t"])
    for p, ct in persistence:
        times.append(ct)
    for acct in att_accounts:
        stamped, _ = hist(acct)
        for ts, _cmd in stamped:
            ts = corr(ts)
            for s in att_sessions:
                if s["start"] <= ts <= s["end"]:
                    times.append(ts)
                    break

    first = min(times) if times else None
    last = max(times) if times else None

    return {
        "initial_access": {
            "account": initial["user"],
            "source": initial["addr"],
            "time": iso(initial["start"]),
        },
        "sources": sorted(att_addrs),
        "accounts": sorted(att_accounts),
        "privilege_escalation": iso(escalation),
        "persistence": sorted({p for p, _ in persistence}),
        "first_activity": iso(first),
        "last_activity": iso(last),
    }


def sudo_session(sd, sessions):
    """Rule 9: the session open on the sudo line's TTY at its time."""
    cands = [s for s in sessions
             if s["line"] == sd["tty"] and s["start"] <= sd["t"] <= s["end"]]
    if not cands:
        return None
    return max(cands, key=lambda s: s["start"])


def is_persistence_class(path):
    if path in ("/etc/rc.local", "/root/.ssh/authorized_keys"):
        return True
    if path.startswith("/etc/cron.d/") and len(path) > len("/etc/cron.d/"):
        return True
    pre = "/var/spool/cron/crontabs/"
    if path.startswith(pre) and len(path) > len(pre):
        return True
    pre = "/etc/systemd/system/"
    if path.startswith(pre) and len(path) > len(pre):
        if path.endswith(".service") or path.endswith(".timer"):
            return True
        return False
    parts = path.split("/")
    if (len(parts) == 5 and parts[0] == "" and parts[1] == "home"
            and parts[3] == ".ssh" and parts[4] == "authorized_keys"
            and parts[2]):
        return True
    return False


def persistence_paths(root, att_sessions, corr, offset):
    listing = root / "fs-listing.tsv"
    if not listing.is_file():
        return []
    rows = []
    lines = listing.read_text(errors="replace").splitlines()
    if lines and lines[0].split("\t")[0].strip() == "path":
        lines = lines[1:]
    for line in lines:
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 6:
            continue
        path = cols[0]
        try:
            ctime = int(cols[5])
        except ValueError:
            continue
        rows.append((path, ctime))

    # dpkg-installed paths
    pkg_times = {}
    dpkg = root / "var" / "log" / "dpkg.log"
    if dpkg.is_file():
        for line in dpkg.read_text(errors="replace").splitlines():
            m = re.match(
                r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})\s+"
                r"status installed (\S+?):(\S+)\s", line)
            if m:
                g = [int(x) for x in m.groups()[:6]]
                local = to_epoch(*g)
                pkg_times.setdefault(m.group(7), []).append(local)

    # note: dpkg.log is host local time -> convert to UTC then correct
    info = root / "var" / "lib" / "dpkg" / "info"
    pkg_paths = {}
    if info.is_dir():
        for p in sorted(info.glob("*.list")):
            pkg = p.name[:-len(".list")]
            files = set()
            for line in p.read_text(errors="replace").splitlines():
                line = line.strip()
                if line:
                    files.add(line)
            pkg_paths[pkg] = files

    out = []
    for path, ctime in rows:
        if not is_persistence_class(path):
            continue
        ct = corr(ctime)
        inside = any(s["start"] <= ct <= s["end"] for s in att_sessions)
        if not inside:
            continue
        if _installed_by_package(path, ct, pkg_paths, pkg_times, corr,
                                 offset):
            continue
        out.append((path, ct))
    return out


def _installed_by_package(path, ct, pkg_paths, pkg_times, corr, offset):
    for pkg, files in pkg_paths.items():
        if path not in files:
            continue
        for local in pkg_times.get(pkg, ()):
            t = corr(local - offset)
            if abs(ct - t) <= 2:
                return True
    return False


def main(argv):
    if len(argv) != 3:
        print("usage: triage.py <evidence_dir> <out.json>", file=sys.stderr)
        return 2
    root = Path(argv[1])
    Path(argv[2]).write_text(json.dumps(analyze(root), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
