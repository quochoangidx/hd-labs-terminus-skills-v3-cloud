import json
G="environment/app/docs/case-guide.md"
T="test_outputs.py::"
def ob(i, contrib, anchor, pos, bnd, inst, wrong, phrase, rat):
    return {"id": i, "class": "core", "contribution": contrib, "authority": {"file": G, "anchor": anchor},
            "implementation_sites": ["environment/app/triage.py"],
            "separability": {"standalone_deliverable": False, "joins_before_output": True, "rationale": rat},
            "witnesses": {"positive": pos, "boundary": bnd}, "expected_source": "independent_model",
            "discriminating_instance": inst, "wrong_but_plausible": wrong, "selfdescription_phrase": phrase}
obs=[
 ob("TIMELINE","place every host-clock time in UTC: local syslog/dpkg time at the collection offset, year inferred back from the collection across a December->January rotation, +N for everything before the clock step",
    "may have been wrong by a fixed amount", [T+"test_rule_1_local_offsets"],
    [T+"test_rule_2_year_rollover_december_january", T+"test_rule_3_clock_step_all_sources"],
    "attack in late December collected in January; a step of 30-7200 s after initial access; offsets -12:00..+14:00 incl. :30/:45",
    "collection year for every line; ignore the step or apply it to auth.log only; local time as UTC","year of an auth-log line",
    "every reported time and every window test (sessions, sudo attribution, ctime) runs on this timeline"),
 ob("INITIAL_ACCESS","hostile = five btmp failures within 600 s; initial access = earliest wtmp login from a hostile address",
    "The team calls an address hostile", [T+"test_rule_6_initial_access"], [T+"test_rule_5_hostile_window_600_inclusive", T+"test_rule_4_btmp_outlives_rotation"],
    "admin key login before the attack; a mistyping user with five failures over 601 s then success; brute force of exactly five in 600 s; scanners that never succeed; oldest failures rotated out of auth.log",
    "first successful login; any address with five failures; strict <600; counting auth.log failures","initial access",
    "the initial login seeds the attacker address/account fixed point and first activity"),
 ob("ATTRIBUTION","attacker keys (fingerprints of keys in attacker accounts' histories), attacker logins/addresses/accounts to a fixed point",
    "a credential or a terminal the intruder used", [T+"test_rule_8_attacker_key_login_from_second_address"], [T+"test_rule_7_key_in_non_attacker_history_is_not_attacker"],
    "later publickey login from a second address with the planted key; admin's own key added in the admin's history",
    "ignore key logins from other addresses; take keys from every history","attacker key",
    "decides sources, accounts, the session windows that persistence, escalation and activity are measured in"),
 ob("ESCALATION","first sudo to root on a TTY whose open session is an attacker session (or an attacker root login)",
    "is the first time the intruder acted as root", [T+"test_rule_10_privilege_escalation"], [T+"test_rule_9_sudo_on_concurrent_legit_session_is_not_attacker"],
    "the account owner and an admin run sudo on other ptys while the attacker is logged in, before the attacker's first sudo",
    "first sudo by the compromised account after initial access","privilege escalation",
    "adds root to the attacker accounts, which adds root's history (keys, stamped commands)"),
 ob("PERSISTENCE","class paths whose ctime (not mtime) lies in an attacker session, minus paths a package wrote at its install time",
    "that the intruder created", [T+"test_rule_11_persistence"], [T+"test_rule_11_forged_mtime_and_package_install"],
    "attacker file with mtime forged years back; admin file with mtime in the window and ctime outside; a package installing a cron.d file during the attacker session",
    "select by mtime; all class paths with ctime in window","persistence",
    "persistence ctimes feed last activity; attacker keys file is both persistence and the key-login link"),
 ob("ACTIVITY","earliest and latest attacker event over failures, logins, logouts, sudo, persistence ctimes and in-session stamped history",
    "are the earliest and latest of the intruder's", [T+"test_rule_12_first_and_last_activity"], [T+"test_rule_12_open_session_last_activity"],
    "probing failures days before the burst; the last session still open with stamped root commands",
    "first activity = initial access; last = last logout","first and last attacker activity",
    "aggregates every other obligation's events on one timeline"),
]
edges=[{"from":a,"to":"PRIMARY_OUTCOME"} for a in ["INITIAL_ACCESS","ATTRIBUTION","ESCALATION","PERSISTENCE","ACTIVITY"]]+[{"from":"TIMELINE","to":x} for x in ["INITIAL_ACCESS","ESCALATION","PERSISTENCE","ACTIVITY"]]+[{"from":"INITIAL_ACCESS","to":"ATTRIBUTION"},{"from":"ATTRIBUTION","to":"ESCALATION"},{"from":"ESCALATION","to":"ATTRIBUTION"},{"from":"ATTRIBUTION","to":"PERSISTENCE"},{"from":"PERSISTENCE","to":"ACTIVITY"}]
m={"schema_version":1,"task_slug":"tbrain-linux-host-intrusion-triage",
 "primary_outcome":"the JSON incident report /app/triage.py writes for an evidence directory equals the report case-guide.md gives (initial access, sources, accounts, privilege escalation, persistence, first and last activity)",
 "obligations":obs,"causal_graph":{"edges":edges},
 "interactions":[
  {"id":"timeline-windows","obligation_ids":["TIMELINE","ESCALATION","PERSISTENCE"],"witness_ids":[T+"test_rule_3_clock_step_all_sources"],"joins_before_output":True},
  {"id":"key-escalation-fixed-point","obligation_ids":["ATTRIBUTION","ESCALATION","INITIAL_ACCESS"],"witness_ids":[T+"test_rule_8_attacker_key_login_from_second_address"],"joins_before_output":True},
  {"id":"activity-aggregate","obligation_ids":["ACTIVITY","PERSISTENCE","TIMELINE"],"witness_ids":[T+"test_rule_12_open_session_last_activity"],"joins_before_output":True}],
 "closure":{
  "universal_rule":{"file":"instruction.md","anchor":"Every rule in the guide holds for every such directory"},
  "silence":{"file":G,"anchor":"Every evidence directory records exactly one intrusion by one","named_cases":[]},
  "coverage_envelope":{"file":"instruction.md","anchor":"The other hosts differ in everything the guide lets vary"}},
 "determinism":{"seeds":["model seeds sealed from solution/ at build time (planned)"],"clock_dependence":"none","network":"none","order_sensitivity":"list fields compared as sets"},
 "reference_selfdescription":"solution/solve.sh",
 "restrictions":[],"unclaimed_units_rationale":{},"removed_obligations":[],
 "exact_output_requirements":[{"id":"REPORT-SHAPE","domain_required":True,"rationale":"the report is consumed by the team's case tooling; keys and the UTC time format are fixed","authority_anchor":{"file":"environment/app/docs/report.md","anchor":"writes one JSON object with exactly these keys"}},
   {"id":"UTC-FORMAT","domain_required":True,"rationale":"times compared as strings","authority_anchor":{"file":"environment/app/docs/report.md","anchor":"Every time is UTC, written `YYYY-MM-DDTHH:MM:SSZ`"}}],
 "documented_exceptions":[
  {"row":"closure.silence","reason":"from-scratch analyzer, not a repair: no shipped behaviour to keep. contract-closure §1: a from-scratch task declares the domain it grades and grades nothing outside it; the anchor is that domain declaration and named_cases is empty."},
  {"row":"support obligations","reason":"record parsing and JSON serialization are written by the solver (no supplied package), so no support row can be implementation_complete; folded into the core obligations whose evidence they read; formats fully specified in record-formats.md."},
  {"row":"restrictions","reason":"'standard library only' and 'must not depend on /app/evidence' will be enforced by the harness (python3 -I -S, evidence staged elsewhere) and declared with enforced_by in phase 2."},
  {"row":"witness ids","reason":"design-only: tests/ does not exist yet (phase 1 forbids a verifier); ids are the planned one-test-per-rule names."}]}
json.dump(m,open("panel-precheck-manifest.json","w"),indent=1)
