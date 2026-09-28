#!/usr/bin/env python3
"""Intrusion triage analyzer.

Usage: python3 /app/triage.py <evidence_dir> <out.json>

Reads one collected evidence directory (layout: /app/docs/record-formats.md),
applies /app/docs/case-guide.md and writes the incident report described in
/app/docs/report.md.
"""

import base64
import gzip
import hashlib
import json
import re
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

SYSLOG_RE = re.compile(
    r"^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\s+(\S+)\s+(.*)$"
)
ACCEPTED_RE = re.compile(
    r"^sshd\[(\d+)\]:\s+Accepted\s+(\S+)\s+for\s+(\S+)\s+from\s+(\S+)\s+port\s+(\d+)\s+ssh2"
    r"(?::\s*\S+\s+(SHA256:\S+))?"
)
SUDO_RE = re.compile(
    r"^sudo:\s+(\S+)\s*:\s*TTY=([^;]*?)\s*;\s*PWD=(.*?)\s*;\s*USER=([^;]*?)\s*;\s*COMMAND=(.*)$"
)
STEP_RE = re.compile(
    r"^systemd-timesyncd\[(\d+)\]:\s+System clock stepped forward by (\d+) seconds"
)
KEY_RE = re.compile(r"ssh-ed25519\s+([A-Za-z0-9+/]+=*)")
DPKG_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})\s+(.*)$"
)
HOME_KEYS_RE = re.compile(r"^/home/[^/]+/\.ssh/authorized_keys$")

RECORD_SIZE = 128
USER_PROCESS = 7
DEAD_PROCESS = 8
FAILED_LOGIN = 6


def fmt(ts):
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_collection(path):
    info = {}
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            info[key.strip()] = value.strip()
    off = info.get("utc_offset", "+00:00")
    sign = -1 if off.startswith("-") else 1
    hh, _, mm = off.lstrip("+-").partition(":")
    offset = sign * (int(hh) * 3600 + int(mm or 0) * 60)
    collected = info.get("collected_utc", "1970-01-01T00:00:00Z")
    collected_ts = int(
        datetime.strptime(collected, "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )
    return info.get("hostname", ""), offset, collected_ts


def auth_log_files(logdir):
    """Auth-log files in reading order: oldest (highest rotation) first."""
    found = []
    if not logdir.is_dir():
        return found
    for entry in logdir.iterdir():
        name = entry.name
        if name == "auth.log":
            found.append((0, entry))
            continue
        m = re.fullmatch(r"auth\.log\.(\d+)(\.gz)?", name)
        if m:
            found.append((int(m.group(1)), entry))
    found.sort(key=lambda pair: (-pair[0], pair[1].name))
    return [entry for _, entry in found]


def read_lines(path):
    if path.name.endswith(".gz"):
        with gzip.open(path, "rt", errors="replace") as handle:
            return handle.read().splitlines()
    return path.read_text(errors="replace").splitlines()


def local_to_utc(year, month, day, hour, minute, second, offset):
    return int(
        datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp()
    ) - offset


class AuthLine:
    __slots__ = ("month", "day", "hour", "minute", "second", "message", "year", "raw_utc", "utc")

    def __init__(self, month, day, hour, minute, second, message):
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.message = message
        self.year = None
        self.raw_utc = None
        self.utc = None


def parse_auth_logs(logdir, offset, collected_ts):
    lines = []
    for path in auth_log_files(logdir):
        for raw in read_lines(path):
            m = SYSLOG_RE.match(raw)
            if not m:
                continue
            lines.append(
                AuthLine(
                    MONTHS.get(m.group(1), 1),
                    int(m.group(2)),
                    int(m.group(3)),
                    int(m.group(4)),
                    int(m.group(5)),
                    m.group(7),
                )
            )
    if not lines:
        return lines, None
    # Rule 2: year of the last line, then walk back.
    collected_local = datetime.fromtimestamp(collected_ts + offset, timezone.utc)
    last = lines[-1]
    year = collected_local.year
    while True:
        try:
            cand = datetime(
                year, last.month, last.day, last.hour, last.minute, last.second,
                tzinfo=timezone.utc,
            )
        except ValueError:
            year -= 1
            continue
        if cand <= collected_local:
            break
        year -= 1
    last.year = year
    for i in range(len(lines) - 2, -1, -1):
        nxt = lines[i + 1]
        lines[i].year = nxt.year - 1 if lines[i].month > nxt.month else nxt.year
    for line in lines:
        try:
            line.raw_utc = local_to_utc(
                line.year, line.month, line.day, line.hour, line.minute,
                line.second, offset,
            )
        except ValueError:
            # e.g. Feb 29 in a non-leap year: fall back to the previous day.
            line.raw_utc = local_to_utc(
                line.year, line.month, line.day - 1, line.hour, line.minute,
                line.second, offset,
            ) + 86400
    # Rule 3: one clock step.
    step_index = None
    step_seconds = 0
    for index, line in enumerate(lines):
        m = STEP_RE.match(line.message)
        if m:
            step_index = index
            step_seconds = int(m.group(2))
            break
    if step_index is None:
        for line in lines:
            line.utc = line.raw_utc
        return lines, None
    for index, line in enumerate(lines):
        line.utc = line.raw_utc + step_seconds if index < step_index else line.raw_utc
    return lines, (lines[step_index].utc, step_seconds)


def make_corrector(step):
    if step is None:
        return lambda ts: ts
    threshold, seconds = step

    def correct(ts):
        if ts is None:
            return None
        return ts + seconds if ts < threshold else ts

    return correct


def read_utmp(path):
    records = []
    if not path.is_file():
        return records
    data = path.read_bytes()
    for off in range(0, len(data) - RECORD_SIZE + 1, RECORD_SIZE):
        chunk = data[off:off + RECORD_SIZE]
        rtype, pid, line, user, host, tv_sec, tv_usec = struct.unpack(
            "<ii16s32s64sii", chunk
        )
        records.append(
            {
                "type": rtype,
                "pid": pid,
                "line": line.split(b"\0", 1)[0].decode("utf-8", "replace"),
                "user": user.split(b"\0", 1)[0].decode("utf-8", "replace"),
                "host": host.split(b"\0", 1)[0].decode("utf-8", "replace"),
                "ts": tv_sec,
            }
        )
    return records


def parse_history(path):
    """Return (entries, blobs): entries are (timestamp or None, command)."""
    if not path.is_file():
        return [], []
    text = path.read_text(errors="replace")
    entries = []
    pending = None
    for line in text.splitlines():
        m = re.fullmatch(r"#(\d+)", line.strip())
        if m:
            pending = int(m.group(1))
            continue
        entries.append((pending, line))
        pending = None
    blobs = KEY_RE.findall(text)
    return entries, blobs


def fingerprint(blob):
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=False)
    except Exception:
        return None
    digest = hashlib.sha256(raw).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def history_path(evidence, account):
    if account == "root":
        return evidence / "root" / ".bash_history"
    return evidence / "home" / account / ".bash_history"


def is_persistence_class(path):
    if path.startswith("/etc/cron.d/") and len(path) > len("/etc/cron.d/"):
        return True
    if path.startswith("/var/spool/cron/crontabs/") and len(path) > len(
        "/var/spool/cron/crontabs/"
    ):
        return True
    if path.startswith("/etc/systemd/system/") and len(path) > len(
        "/etc/systemd/system/"
    ) and (path.endswith(".service") or path.endswith(".timer")):
        return True
    if path == "/etc/rc.local":
        return True
    if path == "/root/.ssh/authorized_keys":
        return True
    if HOME_KEYS_RE.match(path):
        return True
    return False


def analyze(evidence_dir):
    evidence = Path(evidence_dir)
    _host, offset, collected_ts = parse_collection(evidence / "collection.txt")
    logdir = evidence / "var" / "log"
    auth_lines, step = parse_auth_logs(logdir, offset, collected_ts)
    correct = make_corrector(step)

    # Accepted lines, keyed by (account, address, corrected second).
    accepted = {}
    sudo_lines = []
    for line in auth_lines:
        m = ACCEPTED_RE.match(line.message)
        if m:
            accepted[(m.group(3), m.group(4), line.utc)] = {
                "method": m.group(2),
                "fingerprint": m.group(6),
            }
            continue
        m = SUDO_RE.match(line.message)
        if m:
            sudo_lines.append(
                {
                    "user": m.group(1),
                    "tty": m.group(2),
                    "target": m.group(4),
                    "command": m.group(5),
                    "ts": line.utc,
                }
            )

    wtmp = read_utmp(logdir / "wtmp")
    btmp = read_utmp(logdir / "btmp")

    logouts = {}
    logins = []
    for rec in wtmp:
        ts = correct(rec["ts"])
        if rec["type"] == USER_PROCESS:
            logins.append(
                {
                    "user": rec["user"],
                    "addr": rec["host"],
                    "line": rec["line"],
                    "ts": ts,
                }
            )
        elif rec["type"] == DEAD_PROCESS:
            logouts.setdefault(rec["line"], []).append(ts)
    for key in logouts:
        logouts[key].sort()

    for login in logins:
        info = accepted.get((login["user"], login["addr"], login["ts"]))
        login["method"] = info["method"] if info else None
        login["fingerprint"] = info["fingerprint"] if info else None
        end = None
        for candidate in logouts.get(login["line"], ()):
            if candidate >= login["ts"]:
                end = candidate
                break
        login["end"] = end
        login["session_end"] = collected_ts if end is None else end
    logins.sort(key=lambda item: item["ts"])

    failures = []
    for rec in btmp:
        if rec["type"] == FAILED_LOGIN:
            failures.append({"user": rec["user"], "addr": rec["host"], "ts": correct(rec["ts"])})

    # Rule 5: hostile addresses.
    by_addr = {}
    for fail in failures:
        by_addr.setdefault(fail["addr"], []).append(fail["ts"])
    hostile = set()
    for addr, times in by_addr.items():
        times.sort()
        for i in range(len(times) - 4):
            if times[i + 4] - times[i] <= 600:
                hostile.add(addr)
                break

    # Rule 6: initial access.
    initial = None
    for login in logins:
        if login["addr"] in hostile:
            initial = login
            break
    if initial is None:
        return {
            "initial_access": None,
            "sources": [],
            "accounts": [],
            "privilege_escalation": None,
            "persistence": [],
            "first_activity": None,
            "last_activity": None,
        }

    # Rules 7, 8, 10: fixed point.
    def escalation_of(attacker_logins):
        candidates = []
        sessions = [(lg["line"], lg["ts"], lg["session_end"]) for lg in attacker_logins]
        for entry in sudo_lines:
            if entry["target"] != "root":
                continue
            for line_name, start, end in sessions:
                if entry["tty"] == line_name and start <= entry["ts"] <= end:
                    candidates.append(entry["ts"])
                    break
        for lg in attacker_logins:
            if lg["user"] == "root":
                candidates.append(lg["ts"])
        return min(candidates) if candidates else None

    attacker = [initial]
    attacker_ids = {id(initial)}
    escalation = None
    while True:
        addrs = {lg["addr"] for lg in attacker}
        accounts = {lg["user"] for lg in attacker}
        escalation = escalation_of(attacker)
        if escalation is not None:
            accounts.add("root")
        prints = set()
        for account in accounts:
            _entries, blobs = parse_history(history_path(evidence, account))
            for blob in blobs:
                fp = fingerprint(blob)
                if fp:
                    prints.add(fp)
        added = False
        for lg in logins:
            if id(lg) in attacker_ids:
                continue
            if lg["addr"] in addrs or (
                lg["fingerprint"] is not None and lg["fingerprint"] in prints
            ):
                attacker.append(lg)
                attacker_ids.add(id(lg))
                added = True
        if not added:
            break
    attacker.sort(key=lambda item: item["ts"])
    addrs = {lg["addr"] for lg in attacker}
    accounts = {lg["user"] for lg in attacker}
    escalation = escalation_of(attacker)
    if escalation is not None:
        accounts.add("root")

    sessions = [(lg["line"], lg["ts"], lg["session_end"]) for lg in attacker]

    def in_session(ts, line_name=None):
        for name, start, end in sessions:
            if line_name is not None and name != line_name:
                continue
            if start <= ts <= end:
                return True
        return False

    # Rule 11: persistence.
    pkg_installs = {}
    dpkg_log = logdir / "dpkg.log"
    if dpkg_log.is_file():
        for raw in dpkg_log.read_text(errors="replace").splitlines():
            m = DPKG_RE.match(raw)
            if not m:
                continue
            rest = m.group(7)
            parts = rest.split()
            if len(parts) < 3 or parts[0] != "status" or parts[1] != "installed":
                continue
            pkg = parts[2].split(":", 1)[0]
            ts = correct(
                local_to_utc(
                    int(m.group(1)), int(m.group(2)), int(m.group(3)),
                    int(m.group(4)), int(m.group(5)), int(m.group(6)), offset,
                )
            )
            pkg_installs.setdefault(pkg, []).append(ts)

    pkg_paths = {}
    info_dir = evidence / "var" / "lib" / "dpkg" / "info"
    if info_dir.is_dir():
        for entry in sorted(info_dir.iterdir()):
            if not entry.name.endswith(".list"):
                continue
            pkg = entry.name[: -len(".list")]
            for raw in entry.read_text(errors="replace").splitlines():
                path = raw.strip()
                if path:
                    pkg_paths.setdefault(path, set()).add(pkg)

    persistence = []
    fs_listing = evidence / "fs-listing.tsv"
    if fs_listing.is_file():
        rows = fs_listing.read_text(errors="replace").splitlines()
        for raw in rows[1:]:
            if not raw.strip():
                continue
            cols = raw.split("\t")
            if len(cols) < 6:
                continue
            path = cols[0]
            try:
                ctime = correct(int(cols[5]))
            except ValueError:
                continue
            if not is_persistence_class(path):
                continue
            if not in_session(ctime):
                continue
            by_package = False
            for pkg in pkg_paths.get(path, ()):
                for install_ts in pkg_installs.get(pkg, ()):
                    if abs(ctime - install_ts) <= 2:
                        by_package = True
                        break
                if by_package:
                    break
            if by_package:
                continue
            persistence.append((path, ctime))

    # Rule 12: first and last attacker activity.
    times = []
    for fail in failures:
        if fail["addr"] in addrs:
            times.append(fail["ts"])
    for lg in attacker:
        times.append(lg["ts"])
        if lg["end"] is not None:
            times.append(lg["end"])
    for entry in sudo_lines:
        if in_session(entry["ts"], entry["tty"]):
            times.append(entry["ts"])
    for _path, ctime in persistence:
        times.append(ctime)
    for account in accounts:
        entries, _blobs = parse_history(history_path(evidence, account))
        for ts, _cmd in entries:
            if ts is None:
                continue
            ts = correct(ts)
            if in_session(ts):
                times.append(ts)

    return {
        "initial_access": {
            "account": initial["user"],
            "source": initial["addr"],
            "time": fmt(initial["ts"]),
        },
        "sources": sorted(addrs),
        "accounts": sorted(accounts),
        "privilege_escalation": fmt(escalation),
        "persistence": sorted({path for path, _ in persistence}),
        "first_activity": fmt(min(times)) if times else None,
        "last_activity": fmt(max(times)) if times else None,
    }


def main(argv):
    if len(argv) != 3:
        print("usage: triage.py <evidence_dir> <out.json>", file=sys.stderr)
        return 2
    Path(argv[2]).write_text(json.dumps(analyze(Path(argv[1])), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
