#!/usr/bin/env python3
"""Intrusion triage analyzer.

Usage: python3 /app/triage.py <evidence_dir> <out.json>

Reads one collected evidence directory (layout: /app/docs/record-formats.md),
applies /app/docs/case-guide.md and writes the incident report described in
/app/docs/report.md.
"""

import base64
import calendar
import datetime
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

AUTH_RE = re.compile(
    r"^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\s+(\S+)\s+"
    r"(\S+?)(?:\[(\d+)\])?:\s(.*)$"
)
ACCEPTED_RE = re.compile(
    r"^Accepted\s+(\S+)\s+for\s+(\S+)\s+from\s+(\S+)\s+port\s+(\d+)\s+ssh2"
    r"(?::\s*\S+\s+SHA256:(\S+))?\s*$"
)
FAILED_RE = re.compile(
    r"^Failed\s+password\s+for\s+(?:invalid user\s+)?(\S+)\s+from\s+(\S+)\s+port\s+(\d+)\s+ssh2"
)
SUDO_RE = re.compile(
    r"^\s*(\S+)\s*:\s*TTY=(\S+)\s*;\s*PWD=(.*?)\s*;\s*USER=(\S+)\s*;\s*COMMAND=(.*)$"
)
SESS_CLOSED_RE = re.compile(r"^pam_unix\(sshd:session\):\s*session closed for user\s+(\S+)")
REMOTE_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z\s+(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s(.*)$"
)
KEY_RE = re.compile(r"ssh-ed25519\s+([A-Za-z0-9+/=]{20,})")
ROOT_SHELL_RE = re.compile(r"(?:^|/)(?:bash|sh|zsh|ksh|dash|su)(?:\s|$)")


def utc(epoch):
    if epoch is None:
        return None
    t = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(epoch))
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path):
    try:
        if str(path).endswith(".gz"):
            with gzip.open(path, "rt", errors="replace") as fh:
                return fh.read()
        return path.read_text(errors="replace")
    except OSError:
        return ""


# --------------------------------------------------------------------------- #
# collection.txt
# --------------------------------------------------------------------------- #

def parse_collection(root):
    info = {"hostname": None, "offset": 0, "collected": None}
    text = read_text(root / "collection.txt")
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "hostname":
            info["hostname"] = value
        elif key == "utc_offset":
            m = re.match(r"^([+-])(\d{2}):(\d{2})$", value)
            if m:
                sign = 1 if m.group(1) == "+" else -1
                info["offset"] = sign * (int(m.group(2)) * 3600 + int(m.group(3)) * 60)
        elif key == "collected_utc":
            m = re.match(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$", value)
            if m:
                info["collected"] = calendar.timegm(tuple(int(x) for x in m.groups()) + (0, 0, 0))
    return info


def local_to_epoch(year, mon, day, hh, mm, ss, offset):
    return calendar.timegm((year, mon, day, hh, mm, ss, 0, 0, 0)) - offset


# --------------------------------------------------------------------------- #
# auth logs
# --------------------------------------------------------------------------- #

def auth_files(root):
    logdir = root / "var" / "log"
    found = []
    if not logdir.is_dir():
        return found
    for path in logdir.iterdir():
        name = path.name
        if name == "auth.log":
            found.append((0, path))
        else:
            m = re.match(r"^auth\.log\.(\d+)(\.gz)?$", name)
            if m:
                found.append((int(m.group(1)), path))
    # oldest first: highest rotation number first
    found.sort(key=lambda item: -item[0])
    return [path for _, path in found]


def parse_auth(root, info):
    """Return list of dicts for auth-log lines, oldest first, with raw epochs."""
    records = []
    for path in auth_files(root):
        for line in read_text(path).splitlines():
            m = AUTH_RE.match(line)
            if not m:
                continue
            mon = MONTHS.get(m.group(1))
            if mon is None:
                continue
            records.append({
                "mon": mon,
                "day": int(m.group(2)),
                "hh": int(m.group(3)),
                "mm": int(m.group(4)),
                "ss": int(m.group(5)),
                "host": m.group(6),
                "program": m.group(7),
                "pid": int(m.group(8)) if m.group(8) else None,
                "message": m.group(9).rstrip(),
            })
    # assign years walking backwards from the collection date (host local): the
    # syslog stamps carry no year, so take for each line the year that puts it
    # closest to the line after it (the evidence spans at most a few weeks)
    if info["collected"] is not None:
        prev = info["collected"] + info["offset"]
        year = (datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=prev)).year
    else:
        prev = 0
        year = 1970
    for rec in reversed(records):
        best = None
        for cand in (year, year - 1, year + 1):
            try:
                epoch = calendar.timegm(
                    (cand, rec["mon"], rec["day"], rec["hh"], rec["mm"], rec["ss"], 0, 0, 0))
            except Exception:
                continue
            if best is None or abs(epoch - prev) < abs(best[1] - prev):
                best = (cand, epoch)
        if best is None:
            best = (year, prev)
        year = best[0]
        prev = best[1]
        rec["year"] = year
    for rec in records:
        rec["raw"] = local_to_epoch(rec["year"], rec["mon"], rec["day"],
                                    rec["hh"], rec["mm"], rec["ss"], info["offset"])
        rec["key"] = "%s%s: %s" % (
            rec["program"],
            "[%d]" % rec["pid"] if rec["pid"] is not None else "",
            rec["message"],
        )
    return records


def parse_remote(root, info):
    logdir = root / "var" / "log" / "remote"
    records = []
    if not logdir.is_dir():
        return records
    paths = sorted(logdir.glob("*.log"))
    if info["hostname"]:
        preferred = logdir / ("%s.log" % info["hostname"])
        if preferred.exists():
            paths = [preferred]
    for path in paths:
        for line in read_text(path).splitlines():
            m = REMOTE_RE.match(line)
            if not m:
                continue
            true = calendar.timegm(tuple(int(m.group(i)) for i in range(1, 7)) + (0, 0, 0))
            records.append({
                "true": true,
                "host": m.group(7),
                "program": m.group(8),
                "pid": int(m.group(9)) if m.group(9) else None,
                "message": m.group(10).rstrip(),
                "key": "%s%s: %s" % (
                    m.group(8),
                    "[%s]" % m.group(9) if m.group(9) else "",
                    m.group(10).rstrip(),
                ),
            })
    records.sort(key=lambda r: r["true"])
    return records


# --------------------------------------------------------------------------- #
# wtmp / btmp
# --------------------------------------------------------------------------- #

def parse_utmp(path):
    out = []
    try:
        blob = path.read_bytes()
    except OSError:
        return out
    for off in range(0, len(blob) - 127, 128):
        typ, pid, line, user, host, sec, _usec = struct.unpack(
            "<ii16s32s64sii", blob[off:off + 128])

        def cut(raw):
            return raw.split(b"\x00")[0].decode("utf-8", "replace")

        out.append({
            "type": typ,
            "pid": pid,
            "line": cut(line),
            "user": cut(user),
            "host": cut(host),
            "raw": sec,
        })
    return out


# --------------------------------------------------------------------------- #
# clock step
# --------------------------------------------------------------------------- #

def best_suffix_offset(auth_keys, remote_keys):
    """Align auth_keys as a contiguous block inside remote_keys (auth is a
    suffix of the collector's stream, but be tolerant)."""
    if not auth_keys or not remote_keys:
        return None
    best_off, best_score = None, -1
    limit = len(remote_keys) - len(auth_keys)
    starts = range(max(limit, 0), -1, -1) if limit >= 0 else [0]
    for off in starts:
        score = 0
        for i, key in enumerate(auth_keys):
            j = off + i
            if j < len(remote_keys) and remote_keys[j] == key:
                score += 1
        if score > best_score:
            best_score, best_off = score, off
        if best_score == len(auth_keys):
            break
    return best_off


def clock_model(auth, remote, wtmp, info):
    """Return (delta, threshold): raw < threshold -> true = raw - delta."""
    pairs = []  # (raw, true)

    # 1. auth sshd lines against the collector's copy
    keep = [r for r in auth
            if r["program"].startswith("sshd")
            and not r["message"].startswith("Failed password")
            and not r["message"].startswith("Invalid user")]
    rem_sshd = [r for r in remote if r["program"].startswith("sshd")]
    off = best_suffix_offset([r["key"] for r in keep], [r["key"] for r in rem_sshd])
    if off is not None:
        for i, rec in enumerate(keep):
            j = off + i
            if j < len(rem_sshd) and rem_sshd[j]["key"] == rec["key"]:
                pairs.append((rec["raw"], rem_sshd[j]["true"]))

    # 2. wtmp logins against Accepted lines in the collector's copy
    accepted = []
    for rec in remote:
        m = ACCEPTED_RE.match(rec["message"])
        if m:
            accepted.append((m.group(2), m.group(3), rec["true"]))
    logins = [r for r in wtmp if r["type"] == 7]
    by_key = {}
    for user, addr, true in accepted:
        by_key.setdefault((user, addr), []).append(true)
    used = {}
    for rec in logins:
        key = (rec["user"], rec["host"])
        cands = by_key.get(key)
        if not cands:
            continue
        idx = used.get(key, 0)
        if idx < len(cands):
            pairs.append((rec["raw"], cands[idx]))
            used[key] = idx + 1

    deltas = {}
    for raw, true in pairs:
        deltas[raw - true] = deltas.get(raw - true, 0) + 1

    delta = 0
    best = 0
    for value, count in sorted(deltas.items()):
        if value == 0:
            continue
        if 30 <= abs(value) <= 7200 and count > best:
            delta, best = value, count
    if delta == 0:
        return 0, None

    wrong = [raw for raw, true in pairs if raw - true == delta]
    right = [raw for raw, true in pairs if raw - true == 0]
    if not wrong:
        return 0, None
    if not right:
        return delta, float("inf")
    return delta, (max(wrong) + min(right)) / 2.0


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def fingerprint(blob_b64):
    try:
        raw = base64.b64decode(blob_b64 + "=" * (-len(blob_b64) % 4))
    except Exception:
        return None
    return "SHA256:" + base64.b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")


def parse_histories(root):
    """Return {account: [(timestamp_or_None, command), ...]}."""
    out = {}
    candidates = []
    if (root / "root" / ".bash_history").exists():
        candidates.append(("root", root / "root" / ".bash_history"))
    home = root / "home"
    if home.is_dir():
        for user_dir in sorted(home.iterdir()):
            path = user_dir / ".bash_history"
            if path.exists():
                candidates.append((user_dir.name, path))
    for account, path in candidates:
        entries = []
        pending = None
        for line in read_text(path).splitlines():
            m = re.match(r"^#(\d+)\s*$", line)
            if m:
                pending = int(m.group(1))
                continue
            entries.append((pending, line))
            pending = None
        out[account] = entries
    return out


def parse_dpkg(root):
    events = []  # (raw_epoch, package)
    text = read_text(root / "var" / "log" / "dpkg.log")
    for line in text.splitlines():
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\s+status installed\s+(\S+)",
                     line)
        if m:
            events.append((tuple(int(m.group(i)) for i in range(1, 7)), m.group(7)))
    return events


def package_files(root):
    out = {}
    info_dir = root / "var" / "lib" / "dpkg" / "info"
    if not info_dir.is_dir():
        return out
    for path in info_dir.glob("*.list"):
        name = path.name[: -len(".list")]
        paths = set()
        for line in read_text(path).splitlines():
            line = line.strip()
            if line:
                paths.add(line)
        out[name] = paths
    return out


def parse_fs(root):
    rows = []
    text = read_text(root / "fs-listing.tsv")
    lines = text.splitlines()
    for line in lines[1:] if lines else []:
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        try:
            rows.append({
                "path": parts[0],
                "mode": parts[1],
                "owner": parts[2],
                "size": parts[3],
                "mtime": int(parts[4]),
                "ctime": int(parts[5]),
            })
        except ValueError:
            continue
    return rows


PERSIST_HOME_RE = re.compile(r"^/home/[^/]+/\.ssh/authorized_keys$")


def is_persistence_kind(path):
    if path.startswith("/etc/cron.d/"):
        return True
    if path.startswith("/var/spool/cron/crontabs/"):
        return True
    if path.startswith("/etc/systemd/system/") and (path.endswith(".service") or path.endswith(".timer")):
        return True
    if path == "/etc/rc.local":
        return True
    if path == "/root/.ssh/authorized_keys":
        return True
    if PERSIST_HOME_RE.match(path):
        return True
    return False


# --------------------------------------------------------------------------- #
# main analysis
# --------------------------------------------------------------------------- #

def analyze(root):
    root = Path(root)
    info = parse_collection(root)
    collected = info["collected"]
    auth = parse_auth(root, info)
    remote = parse_remote(root, info)
    wtmp = parse_utmp(root / "var" / "log" / "wtmp")
    btmp = parse_utmp(root / "var" / "log" / "btmp")

    delta, threshold = clock_model(auth, remote, wtmp, info)

    def fix(raw):
        if raw is None:
            return None
        if delta == 0 or threshold is None:
            return int(raw)
        return int(raw - delta) if raw < threshold else int(raw)

    # ---------------- failed attempts ----------------
    failures = []  # (time, addr, user)
    seen = set()
    for rec in btmp:
        if rec["type"] == 6 and rec["host"]:
            t = fix(rec["raw"])
            seen.add((rec["host"], t))
            failures.append((t, rec["host"], rec["user"]))
    if not failures:
        for rec in auth:
            m = FAILED_RE.match(rec["message"])
            if m:
                t = fix(rec["raw"])
                key = (m.group(2), t)
                if key not in seen:
                    seen.add(key)
                    failures.append((t, m.group(2), m.group(1)))
    failures.sort()

    by_addr = {}
    for t, addr, user in failures:
        by_addr.setdefault(addr, []).append(t)
    hostile = set()
    for addr, times in by_addr.items():
        times.sort()
        for i in range(len(times) - 4):
            if times[i + 4] - times[i] <= 600:
                hostile.add(addr)
                break

    # ---------------- sessions ----------------
    sessions = []
    open_by_pid = {}

    def add_session(user, addr, start, pid, method=None, fp=None):
        sess = {"user": user, "addr": addr, "start": start, "end": None,
                "tty": None, "pid": pid, "method": method, "fp": fp}
        sessions.append(sess)
        return sess

    source = remote if remote else None
    if source:
        for rec in source:
            if not rec["program"].startswith("sshd"):
                continue
            m = ACCEPTED_RE.match(rec["message"])
            if m:
                sess = add_session(m.group(2), m.group(3), rec["true"], rec["pid"],
                                   m.group(1), "SHA256:" + m.group(5) if m.group(5) else None)
                if rec["pid"] is not None:
                    open_by_pid[rec["pid"]] = sess
                continue
            m = SESS_CLOSED_RE.match(rec["message"])
            if m and rec["pid"] in open_by_pid:
                sess = open_by_pid.pop(rec["pid"])
                if sess["user"] == m.group(1):
                    sess["end"] = rec["true"]
    # auth-log accepted lines: fill in anything the collector's copy misses
    auth_open = {}
    for rec in auth:
        if not rec["program"].startswith("sshd"):
            continue
        m = ACCEPTED_RE.match(rec["message"])
        if m:
            start = fix(rec["raw"])
            fp = "SHA256:" + m.group(5) if m.group(5) else None
            match = None
            for sess in sessions:
                if (sess["user"] == m.group(2) and sess["addr"] == m.group(3)
                        and abs(sess["start"] - start) <= 5):
                    match = sess
                    break
            if match is None:
                match = add_session(m.group(2), m.group(3), start, rec["pid"], m.group(1), fp)
            else:
                if match["fp"] is None:
                    match["fp"] = fp
                if match["method"] is None:
                    match["method"] = m.group(1)
            if rec["pid"] is not None:
                auth_open[rec["pid"]] = match
            continue
        m = SESS_CLOSED_RE.match(rec["message"])
        if m and rec["pid"] in auth_open:
            sess = auth_open.pop(rec["pid"])
            if sess["end"] is None:
                sess["end"] = fix(rec["raw"])

    # wtmp: terminals, and logins/logouts the logs above do not show
    wt_sessions = []
    open_tty = {}
    for rec in sorted(wtmp, key=lambda r: r["raw"]):
        if rec["type"] == 7:
            entry = {"user": rec["user"], "addr": rec["host"], "start": fix(rec["raw"]),
                     "tty": rec["line"], "end": None}
            wt_sessions.append(entry)
            open_tty[(rec["pid"], rec["line"])] = entry
        elif rec["type"] == 8:
            entry = open_tty.pop((rec["pid"], rec["line"]), None)
            if entry is None:
                for cand in reversed(wt_sessions):
                    if cand["tty"] == rec["line"] and cand["end"] is None:
                        entry = cand
                        break
            if entry is not None:
                entry["end"] = fix(rec["raw"])
    used = set()
    for entry in wt_sessions:
        match = None
        best = None
        for idx, sess in enumerate(sessions):
            if idx in used:
                continue
            if sess["user"] != entry["user"] or sess["addr"] != entry["addr"]:
                continue
            gap = abs(sess["start"] - entry["start"])
            if gap <= 5 and (best is None or gap < best):
                best, match = gap, idx
        if match is None:
            sess = add_session(entry["user"], entry["addr"], entry["start"], None)
            sess["tty"] = entry["tty"]
            sess["end"] = entry["end"]
            used.add(len(sessions) - 1)
        else:
            sessions[match]["tty"] = entry["tty"]
            if sessions[match]["end"] is None:
                sessions[match]["end"] = entry["end"]
            used.add(match)

    sessions.sort(key=lambda s: s["start"])

    # ---------------- sudo lines ----------------
    sudos = []
    for rec in auth:
        if not rec["program"].startswith("sudo"):
            continue
        m = SUDO_RE.match(rec["message"])
        if m:
            sudos.append({"time": fix(rec["raw"]), "user": m.group(1), "tty": m.group(2),
                          "target": m.group(4), "command": m.group(5)})

    histories = parse_histories(root)

    # ---------------- who is the intruder ----------------
    successes = [s for s in sessions if s["addr"] in hostile]
    report = {
        "initial_access": None,
        "sources": [],
        "accounts": [],
        "privilege_escalation": None,
        "persistence": [],
        "first_activity": None,
        "last_activity": None,
    }
    if not successes:
        return report
    first = min(successes, key=lambda s: s["start"])
    report["initial_access"] = {
        "account": first["user"],
        "source": first["addr"],
        "time": utc(first["start"]),
    }

    addrs = {first["addr"]}
    keys = set()
    accounts = {first["user"]}
    intruder = [first]

    def session_window(sess):
        start = sess["start"]
        stop = sess["end"]
        if stop is None:
            stop = collected if collected is not None else start
        return start, stop

    for _ in range(10):
        changed = False
        # sessions tied by address or by a key the intruder added
        for sess in sessions:
            if any(sess is known for known in intruder):
                continue
            if sess["addr"] in addrs or (sess["fp"] and sess["fp"] in keys):
                intruder.append(sess)
                changed = True
        for sess in intruder:
            if sess["addr"] not in addrs:
                addrs.add(sess["addr"])
                changed = True
            if sess["user"] not in accounts:
                accounts.add(sess["user"])
                changed = True
        # keys written by commands in the histories of the intruder's accounts
        for account in list(accounts):
            for _ts, command in histories.get(account, []):
                if "authorized_keys" not in command:
                    continue
                for blob in KEY_RE.findall(command):
                    fp = fingerprint(blob)
                    if fp and fp not in keys:
                        keys.add(fp)
                        changed = True
        # root once the intruder acted as root
        root_actions, _ = intruder_root_actions(intruder, sessions, sudos, histories,
                                                fix, collected)
        if root_actions and "root" not in accounts:
            accounts.add("root")
            changed = True
        if not changed:
            break

    root_actions, root_windows = intruder_root_actions(intruder, sessions, sudos,
                                                       histories, fix, collected)

    # ---------------- events ----------------
    events = []
    for t, addr, _user in failures:
        if addr in addrs:
            events.append(t)
    for sess in intruder:
        events.append(sess["start"])
        if sess["end"] is not None:
            events.append(sess["end"])
    events.extend(root_actions)
    for sess in intruder:
        start, stop = session_window(sess)
        for ts, _command in histories.get(sess["user"], []):
            if ts is not None and start <= fix(ts) <= stop:
                events.append(fix(ts))
    for start, stop in root_windows:
        for ts, _command in histories.get("root", []):
            if ts is None:
                continue
            t = fix(ts)
            if start <= t <= stop:
                events.append(t)

    # ---------------- persistence ----------------
    windows = [session_window(s) for s in intruder]
    installs = []
    pkg_files = package_files(root)
    for tup, package in parse_dpkg(root):
        raw = local_to_epoch(*tup, info["offset"])
        paths = pkg_files.get(package)
        if paths is None:
            paths = pkg_files.get(package.split(":")[0], set())
        installs.append((fix(raw), paths))

    persistence = []
    for row in parse_fs(root):
        if not is_persistence_kind(row["path"]):
            continue
        ctime = fix(row["ctime"])
        inside = False
        for start, end in windows:
            stop = end if end is not None else collected
            if start <= ctime <= (stop if stop is not None else start):
                inside = True
                break
        if not inside:
            continue
        if any(abs(ctime - when) <= 2 and row["path"] in paths for when, paths in installs):
            continue
        persistence.append(row["path"])
        events.append(ctime)

    report["sources"] = sorted(addrs)
    report["accounts"] = sorted(accounts)
    report["privilege_escalation"] = utc(min(root_actions)) if root_actions else None
    report["persistence"] = sorted(set(persistence))
    if events:
        report["first_activity"] = utc(min(events))
        report["last_activity"] = utc(max(events))
    return report


def sudo_root_times(sess, sessions, sudos, start, stop):
    """Times of sudo-to-root commands that belong to this session."""
    out = []
    for entry in sudos:
        if entry["user"] != sess["user"] or entry["target"] != "root":
            continue
        if not (start <= entry["time"] <= stop):
            continue
        if sess["tty"] and entry["tty"]:
            if entry["tty"] == sess["tty"]:
                out.append(entry["time"])
            continue
        # no terminal recorded: accept only when no other session of the same
        # account was open at that moment
        rival = False
        for other in sessions:
            if other is sess or other["user"] != sess["user"]:
                continue
            o_stop = other["end"] if other["end"] is not None else stop
            if other["start"] <= entry["time"] <= o_stop:
                rival = True
                break
        if not rival:
            out.append(entry["time"])
    return out


def intruder_root_actions(intruder, sessions, sudos, histories, fix, collected):
    """(times the intruder acted as root, windows of the intruder's root shells)."""
    times = []
    windows = []
    for sess in intruder:
        start = sess["start"]
        stop = sess["end"]
        if stop is None:
            stop = collected if collected is not None else start
        found = []
        if sess["user"] == "root":
            found.append(start)
        found.extend(sudo_root_times(sess, sessions, sudos, start, stop))
        if not found:
            # no logged root command for this session (the sudo line may have
            # been rotated away): fall back to root's timestamped history
            for ts, _command in histories.get("root", []):
                if ts is None:
                    continue
                t = fix(ts)
                if start <= t <= stop:
                    found.append(t)
        if found:
            times.extend(found)
            windows.append((min(found), stop))
    return sorted(times), windows


def main(argv):
    if len(argv) != 3:
        print("usage: triage.py <evidence_dir> <out.json>", file=sys.stderr)
        return 2
    Path(argv[2]).write_text(json.dumps(analyze(Path(argv[1])), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
