# Case-handling guide: SSH intrusion triage

This guide fixes what the response team reports for an evidence directory collected
from one Linux host (layout and record formats: `record-formats.md`; report format:
`report.md`). Every evidence directory records exactly one intrusion by one
intruder, who got in over SSH. The guide defines what each finding means; working
out the findings from the evidence is the triage.

1. **Time.** Report every time in UTC, to the second. `collected_utc` and the
   remote collector's timestamps come from correct clocks. Everything else was
   written by the host clock, which may have been wrong by a fixed amount for part
   of the evidence period and then set right, at most once. Report true times, not
   what the host clock said.

2. **Hostile address.** The team calls an address hostile when it made five failed
   login attempts whose times all lie within 600 seconds (the fifth at most 600
   seconds after the first). btmp holds every failed attempt; auth logs may have
   lost the oldest ones to rotation.

3. **Initial access** is the earliest successful login from a hostile address: its
   account, source address and time. The intruder is whoever made it.

4. **Sources and accounts.** The sources are every address the intruder logged in
   from; the accounts are every account the intruder used during the intrusion,
   including `root` once the intruder acted as root. Reconstruct them from the
   evidence: an address, a credential or a terminal the intruder used ties further
   logins and commands to the intruder.

5. **Privilege escalation** is the first time the intruder acted as root (a command
   run as root, or a login as root); `null` if the intruder never did.

6. **Persistence** artefacts are the files of these kinds that the intruder created
   or changed during the intrusion: any path below `/etc/cron.d/` or
   `/var/spool/cron/crontabs/`, any path below `/etc/systemd/system/` whose name
   ends in `.service` or `.timer`, `/etc/rc.local`, `/root/.ssh/authorized_keys` and
   `/home/<user>/.ssh/authorized_keys`. No other path is a persistence kind.

7. **First and last activity** are the earliest and latest of the intruder's
   recorded events: failed attempts from the intruder's sources, the intruder's
   logins and logouts, commands the intruder ran whose time is recorded (sudo lines,
   timestamped history), and the changes to persistence artefacts. A session with
   no logout record was still open at `collected_utc`.
