# Evidence directory layout and record formats

Paths are relative to the evidence directory. Directories other than `var/log`
may be absent when the host had nothing there.

- `collection.txt`: three `key: value` lines, `hostname`, `utc_offset` (`+HH:MM` or
  `-HH:MM`, a whole number of quarter hours between -12:00 and +14:00) and
  `collected_utc` (`YYYY-MM-DDTHH:MM:SSZ`).
- `var/log/auth.log`, `var/log/auth.log.1`, `var/log/auth.log.2.gz` ...: the
  syslog auth log and its rotations (1 to 6 files; `.2` and older are gzip). Higher
  numbers are older. Each line is
  `Mon DD HH:MM:SS <hostname> <program>[<pid>]: <message>` with an English month
  abbreviation and the day padded to two characters with a space. The messages
  used by the case-handling guide are:
  - `sshd[P]: Accepted password for USER from ADDR port PORT ssh2`
  - `sshd[P]: Accepted publickey for USER from ADDR port PORT ssh2: ED25519 SHA256:FINGERPRINT`
  - `sshd[P]: Failed password for USER from ADDR port PORT ssh2` and
    `sshd[P]: Failed password for invalid user USER from ADDR port PORT ssh2`
  - `sudo:     USER : TTY=pts/N ; PWD=DIR ; USER=root ; COMMAND=CMD`
  - `sshd[P]: Connection closed by ADDR port PORT [preauth]`
  Other lines (session opened and closed, logind, cron) are ordinary noise.
- `var/log/remote/<hostname>.log`: the copy of the host's `sshd` lines kept by the
  team's remote log collector, one per line, `YYYY-MM-DDTHH:MM:SSZ <hostname>
  sshd[<pid>]: <message>`, stamped with the collector's own (correct) UTC time when
  the line arrived, in the same second it was written. The collector drops failed
  attempts (`Failed password`, `Invalid user`) and keeps every other `sshd` line
  for the whole evidence period.
- `var/log/wtmp` and `var/log/btmp`: consecutive 128-byte little-endian records,
  `struct { int32 type; int32 pid; char line[16]; char user[32]; char host[64];
  int32 tv_sec; int32 tv_usec; }`, strings NUL-padded. Types: 2 boot, 6 failed
  login (btmp only, `line` is `ssh:notty`, `user` is the name tried), 7 login
  (`USER_PROCESS`: `line` is the terminal such as `pts/3`, `host` the source
  address), 8 logout (`DEAD_PROCESS`: `line` set, `user` and `host` empty).
  `tv_sec` is whole seconds since the epoch; ignore `tv_usec`.
- `var/log/dpkg.log`: `YYYY-MM-DD HH:MM:SS <action>` lines, among them
  `status installed <package>:<arch> <version>`.
- `var/lib/dpkg/info/<package>.list`: one absolute path per line, the files the
  package installed.
- `home/<user>/.bash_history` and `root/.bash_history`: one command per line. When
  the shell ran with `HISTTIMEFORMAT` set, each command is preceded by a line
  `#<seconds since the epoch>`; otherwise the history carries no times.
- `home/<user>/.ssh/authorized_keys` and `root/.ssh/authorized_keys`: OpenSSH
  public keys, `ssh-ed25519 <base64 blob> <comment>`; every key on these hosts is
  ed25519. OpenSSH writes a key's fingerprint as `SHA256:` followed by the base64,
  without `=` padding, of the SHA-256 digest of the decoded blob.
- `fs-listing.tsv`: a header line then one tab-separated row per regular file or
  symbolic link on the host (directories are not listed):
  `path mode owner size mtime ctime` (times in whole seconds since the epoch).
