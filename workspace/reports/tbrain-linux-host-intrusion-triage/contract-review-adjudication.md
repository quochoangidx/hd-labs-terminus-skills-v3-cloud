# contract-review-r1 adjudication (builder accept, orchestrator uphold)
- F1 accept: rule 4 now joins a login to the Accepted line with the same account, address and corrected second, and states that no two logins share all three (a generator limit: session starts are distinct seconds per account/address).
- F2 accept: rule 7 now says the key is the base64 blob after its type word, found anywhere in the attacker account's history file, in any command at any time.
- F3 accept: rule 11 now reads "at most 2 seconds before or after", both times corrected, and exactly 2 s counts. The reference already used <= 2.
- F4 accept: rule 11 now closes the path scope: any depth below cron.d, crontabs and systemd/system (.service/.timer), /etc/rc.local, /root/.ssh/authorized_keys, and /home/<user>/.ssh/authorized_keys at exactly that depth.
- F5 accept: rule 3 now compares the uncorrected value against the step line.
- P6 accept: rule 2 now says the year is assigned from the times as written, before the rule 3 correction. P7 accept: rule 12 names btmp. P8 kept as governed (orchestrator decision). P9 no change.
- Envelope: the tz family now draws the -12:00 and +14:00 endpoints (seen in seeds 0-39); case-1 is now at -12:00.
