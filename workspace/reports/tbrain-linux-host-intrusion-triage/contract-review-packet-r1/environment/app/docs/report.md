# Incident report format

`triage.py` writes one JSON object with exactly these keys:

```json
{
  "initial_access": {"account": "deploy", "source": "192.0.2.10", "time": "2024-03-05T14:02:11Z"},
  "sources": ["192.0.2.10"],
  "accounts": ["deploy", "root"],
  "privilege_escalation": "2024-03-05T14:09:40Z",
  "persistence": ["/etc/cron.d/example"],
  "first_activity": "2024-03-05T13:55:02Z",
  "last_activity": "2024-03-05T16:20:00Z"
}
```

(The values above only show the shape; they are not from any evidence set.)

- `initial_access`: rule 6 of `case-guide.md`.
- `sources`: the attacker addresses (rule 8), `accounts`: the attacker accounts
  (rule 8), `persistence`: absolute host paths (rule 11). These three are sets:
  their order does not matter and each item appears once.
- `privilege_escalation`: rule 10, a time or `null`.
- `first_activity`, `last_activity`: rule 12.
- Every time is UTC, written `YYYY-MM-DDTHH:MM:SSZ`.
