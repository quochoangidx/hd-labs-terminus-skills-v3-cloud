# Case-handling guide: SSH intrusion triage

This guide fixes how the response team reads an evidence directory collected from
one Linux host (layout and record formats: `record-formats.md`; report format:
`report.md`). Every evidence directory records exactly one intrusion by one
attacker, reached over SSH. Each rule below holds for every evidence directory
collected this way, not only for the example case.

1. **Clocks and zones.** `var/log/auth.log*` and `var/log/dpkg.log` are written in
   host local time at the fixed `utc_offset` in `collection.txt` (no daylight
   saving). wtmp and btmp seconds, `#<seconds>` history stamps and the `mtime` and
   `ctime` columns of `fs-listing.tsv` are seconds since 1970-01-01 UTC. All of these
   were written by the host clock. `collected_utc` was taken from a trusted clock.
   Report every time in UTC.

2. **Year of an auth-log line.** Auth-log lines carry no year. Read the auth-log
   lines oldest first: the file with the highest rotation number first, `auth.log`
   last, each file top to bottom. The last line of `auth.log` takes the year that
   puts it at or before the collection time (in host local time) and less than one
   year before it. Walking back from there, a line whose month is later than the
   month of the line after it lies in the year before that line's year; otherwise
   it lies in the same year. The year is assigned from the times as written, before
   any rule 3 correction.

3. **Clock step.** If the host clock was stepped, `auth.log*` holds one line
   `systemd-timesyncd[PID]: System clock stepped forward by N seconds (...)`, logged
   on the corrected clock. Until that step the host clock ran N seconds slow: add N
   to every auth-log line before the step line in the reading order of rule 2, and
   to every other host-clock time (rule 1) whose uncorrected value is earlier than
   the step line's own time.
   The step line and everything after it need nothing. There is at most one step.

4. **Logins.** btmp holds every failed login attempt (auth logs may have lost the
   oldest ones to rotation). wtmp holds every login (a `USER_PROCESS` record) and
   every logout (a `DEAD_PROCESS` record on the same terminal line). The auth-log
   `Accepted` line of a login, the one with the same account and address at the same
   second once both are corrected by rule 3, gives its method and, for a key, the key
   fingerprint. No two logins share account, address and second.

5. **Hostile address.** An address is hostile when btmp holds five failed attempts
   from it whose times all lie within 600 seconds (the fifth at most 600 seconds
   after the first).

6. **Initial access** is the earliest login from a hostile address: its account,
   address and time.

7. **Attacker key.** A public key whose base64 blob, written after its type word
   (`ssh-ed25519`, `ssh-rsa` or `ecdsa-sha2-nistp256`/`384`/`521`), appears anywhere in
   the shell history file of an attacker account, in any command at any time. Its fingerprint is written as OpenSSH writes it: `SHA256:`
   followed by the base64 of the SHA-256 digest of the decoded key blob, without
   `=` padding.

8. **Attacker logins, addresses and accounts.** The initial access is an attacker
   login. So is every login from an address that has made an attacker login, and
   every login whose `Accepted` line names an attacker key's fingerprint. The
   attacker addresses are the addresses of attacker logins. The attacker accounts
   are the accounts of attacker logins, plus `root` once the attacker has escalated
   (rule 10). Apply rules 7, 8 and 10 until nothing more changes.

9. **Sessions.** A session runs from its login to the `DEAD_PROCESS` record on the
   same terminal line, both ends included; a session with no such record was still
   open at `collected_utc`. An attacker session is the session of an attacker login.
   A sudo line belongs to the session open on its `TTY` at the line's time.

10. **Privilege escalation** is the earliest of: a sudo line with `USER=root` that
    belongs to an attacker session, and an attacker login as `root`. It is `null`
    when there is neither.

11. **Persistence** artefacts are the paths in `fs-listing.tsv` that are any path
    below `/etc/cron.d/` or `/var/spool/cron/crontabs/` (any depth), any path below
    `/etc/systemd/system/` (any depth) whose name ends in `.service` or `.timer`,
    `/etc/rc.local`, `/root/.ssh/authorized_keys`, or `/home/<user>/.ssh/authorized_keys`
    (exactly that depth; no other path is a persistence class), and whose `ctime` lies
    within an attacker session. The `mtime` is not evidence: any user can set it to
    any value. A path a package lists in `var/lib/dpkg/info/<package>.list` whose
    `ctime` is at most 2 seconds before or after a `status installed <package>:...`
    line of `dpkg.log` (both times corrected by rule 3; exactly 2 seconds counts) was written by the package manager and is not persistence.

12. **First and last attacker activity** are the earliest and latest of: btmp
    failed attempts from attacker addresses, attacker logins, the logouts of attacker
    sessions, sudo lines of attacker sessions, the `ctime` of persistence artefacts,
    and the stamped commands of an attacker account's shell history whose times lie
    within an attacker session.
