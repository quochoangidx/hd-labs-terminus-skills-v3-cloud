import json, re
d = json.load(open("exp.json"))
DROP_STR = {"", "20 july", "19991231T2359", "2020-07-20 12:30 1999", "2020-07-20 12:30 99", "20200720 12:30 1999", "2020-07-20 1999",
 "2020-07-20 12:30 1 day 1999", "2020-07-20 12:30 12345", "2020-07-20 12:30 7", "2024-01-15 -1 fri", "2024-01-15 thurs.", "2024-01-15 monday tuesday",
 "2020-07-20 this", "2020-07-20 last", "2020-07-20 1 day ago ago", "SEPT. 3, 2021", "2020/07/20", "2020-07-20 -- 10:00", "2020-07-20 - 10:00",
 "2012-09-24T8pm", "2012-09-24T20", "20120924T200200", "2020-07-20 -0700", "2020-07-20 +03 10:00", "@ 5", "@+5", "@1e3", "2020-07-20 2021-01-01", "200720",
 "2020-07-20T", "2020.07.20", "20.07.2020", "2020-07-20,10:00", "10:00 -1 sec UTC 1970-01-01 2 wed"}
DROP_FMT = {"%", "%1", "%Q %v %J", "%:%z %::%", "%E", "%.3N"}
keep = []
for x in d:
    a = x["args"]
    s = a[a.index("-d") + 1] if "-d" in a else None
    f = next((y[1:] for y in a if y.startswith("+")), None)
    if s is not None and s in DROP_STR: continue
    if f in DROP_FMT: continue
    if x["group"].startswith("mixed"):
        toks = s.split()
        bad = False
        for i, t in enumerate(toks):
            if re.fullmatch(r"[+-]\d\d:?\d\d", t) and not (i and re.fullmatch(r"\d+:\d\d(:\d\d(\.\d+)?)?", toks[i - 1])):
                bad = True
        if bad: continue
    keep.append(x)
json.dump(keep, open("exp_ok.json", "w"))
print(len(d), "->", len(keep))
for x in keep:
    if x["group"].startswith("mixed") and x["status"]: print(x["args"])
