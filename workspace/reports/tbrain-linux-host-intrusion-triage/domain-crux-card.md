# Domain crux card: tbrain-linux-host-intrusion-triage (pattern-blind, written before the catalog)

- Domain-native failure mode: a responder reconstructs an SSH intrusion from a collected host and gets the
  timeline or attribution wrong because the evidence lies in different clocks and places: syslog has no year,
  the host clock was wrong until an NTP step, auth logs rotated away the start of the brute force, sudo lines
  name a user but only the TTY ties them to a session, and mtime is attacker-controlled.
- Work surface: a from-scratch reusable analyzer (/app/triage.py) over an evidence directory (text logs, gz
  rotations, binary utmp-style records, histories, authorized_keys, dpkg state, a metadata listing).
- Native artefact: the incident report (initial access, sources, accounts, escalation, persistence, first/last).
- Why difficulty survives removing incidental schema: the hard part is correlating distributed sources on one
  corrected timeline and a fixed point (key planted in history -> key login from a new address -> more
  accounts -> root history -> more keys), with decoys whose natural handling is wrong. The JSON shape is trivial.
- Decoys (each with the natural wrong handling): see phase-1 report and wrong-analyzers-receipt.json.
