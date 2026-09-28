import json, os, sys
sys.path.insert(0, 'environment/app/planner')
from plan_site import plan as lfl
S = {s: json.load(open(f'tests/sites/{s}.json')) for s in ['dorset','kent','fife','tyne']}
OUT = 'submissions'
def put(name, site, obj=None, raw=None, why=''):
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, site + '.json')
    if raw is not None:
        open(p, 'wb').write(raw if isinstance(raw, bytes) else raw.encode())
    else:
        json.dump(obj, open(p, 'w'))
    open(os.path.join(d, 'WHY.txt'), 'w').write(why.strip() + '\n')
base = {s: lfl(S[s]) for s in S}
def prod(site, pid): return next(p for p in S[site]['products'] if p['id'] == pid)
def cap(site, lid): return next(l for l in S[site]['lines'] if l['id'] == lid)['capacity_minutes']

# dorset COL01 on L1: mpb 12, setup 45. L1 day0 cap 900 -> max n = (900-45)//12 = 71 (897 min)
# 1 capacity edge + 1 minute counting setup: n=72 -> 45+864=909 >900 ; without setup 864 <=900
put('w01_cap_ignores_setup', 'dorset', {"runs":[{"day":0,"line":"L1","product":"COL01","batches":72}]},
    why='INVALID rule 3: 72 batches COL01 on dorset L1 day0 = 45+864=909 > 900; fits only if setup is ignored')
# 2 exact edge + 1: L1 day 2 cap 450: (450-45)//12=33 -> 441; add a second product run to hit 451
# LEM02 on L1: mpb18 setup120. COL01 n=15: 45+180=225; LEM02 n=6: 120+108=228 -> 453 > 450. find exact 451
# search pair
best=(3,17); c=cap('dorset','L1')[2]
put('w02_cap_edge_plus1_two_runs', 'dorset', {"runs":[{"day":2,"line":"L1","product":"COL01","batches":3},{"day":2,"line":"L1","product":"BER08","batches":17}]},
    why=f'INVALID rule 3: two runs on dorset L1 day2 total {c+1} min vs capacity {c} (per-run each fits; only the sum breaks)')
# 3 capacity-0 day
put('w03_capacity_zero_day', 'dorset', {"runs":[{"day":6,"line":"L1","product":"COL01","batches":1}]},
    why='INVALID rule 3: dorset L1 day 6 has capacity 0; one COL01 batch needs 57 min')
# 4 ineligible line
put('w04_ineligible_line', 'dorset', {"runs":[{"day":0,"line":"L3","product":"LEM02","batches":1}]},
    why='INVALID rule 1: LEM02 lists only L1; run on L3 (a real line with capacity)')
# 5 duplicate run
put('w05_duplicate_run', 'kent', {"runs":[{"day":0,"line":"L1","product":"LEM02","batches":2},{"day":0,"line":"L1","product":"LEM02","batches":3}]},
    why='INVALID rule 2: two runs of LEM02 on kent L1 day 0 (capacity is fine either way)')
# 6 zero batches
put('w06_zero_batches', 'kent', {"runs":[{"day":0,"line":"L1","product":"LEM02","batches":0}]}, why='INVALID rule 1: batches 0')
# 7 negative batches (would reduce capacity use and fill backlog)
put('w07_negative_batches', 'kent', {"runs":[{"day":0,"line":"L1","product":"LEM02","batches":-1}]}, why='INVALID rule 1: batches -1')
# 8 float batches (whole-valued)
put('w08_float_batches', 'kent', raw='{"runs":[{"day":0,"line":"L1","product":"LEM02","batches":2.0}]}', why='INVALID file format: batches written as 2.0 (float)')
# 9 bool batches
put('w09_bool_batches', 'fife', raw='{"runs":[{"day":0,"line":"L4","product":"LEM02","batches":true}]}', why='INVALID file format: batches is true (bool)')
# 10 string day
put('w10_string_day', 'fife', raw='{"runs":[{"day":"0","line":"L4","product":"LEM02","batches":1}]}', why='INVALID file format: day is the string "0"')
# 11 day out of range and negative
put('w11_day_out_of_range', 'fife', {"runs":[{"day":20,"line":"L4","product":"LEM02","batches":1}]}, why='INVALID rule 1: day 20 with days=20 (days are 0..19)')
put('w11b_negative_day', 'tyne', {"runs":[{"day":-1,"line":"L1","product":"LEM02","batches":1}]}, why='INVALID rule 1: day -1 (Python negative indexing would wrap to day 19)')
# 12 unknown ids
put('w12_unknown_product', 'fife', {"runs":[{"day":0,"line":"L4","product":"col01","batches":1}]}, why='INVALID rule 1: product "col01" (case differs from COL01)')
put('w12b_unknown_line', 'tyne', {"runs":[{"day":0,"line":"L1 ","product":"LEM02","batches":1}]}, why='INVALID rule 1: line "L1 " with trailing space')
# 13 duplicate key in object / top-level
put('w13_duplicate_key', 'tyne', raw='{"runs":[{"day":0,"line":"L1","product":"LEM02","batches":1,"batches":500}]}', why='INVALID file format: run object gives "batches" twice (last-wins parse would hide the 500)')
put('w13b_dup_top_runs', 'kent', raw='{"runs":[{"day":6,"line":"L1","product":"LEM02","batches":1}],"runs":[]}', why='INVALID file format: top-level "runs" given twice; last-wins would hide an illegal run on a capacity-0 day')
# 14 BOM, NaN, depth, digits, size
put('w14_bom', 'dorset' if False else 'tyne', raw=b'\xef\xbb\xbf' + json.dumps(base['tyne']).encode(), why='INVALID file format: UTF-8 BOM before otherwise valid LFL plan')
put('w14b_nan_extra', 'kent', raw='{"runs":[],"note":NaN}', why='INVALID file format: NaN in an ignored extra key')
deep = '{"runs":[],"x":' + '['*64 + ']'*64 + '}'
put('w14c_depth65', 'fife', raw=deep, why='INVALID file format: top object + 64 nested arrays = 65 levels')
put('w14d_digits4301', 'dorset', raw='{"runs":[],"x":' + '1'*4301 + '}', why='INVALID file format: number with 4301 digits in an ignored key')
put('w14e_float_digits', 'kent', raw='{"runs":[],"x":0.' + '0'*4300 + '1}', why='INVALID file format: float 0.000..1 with 4302 digits (fraction digits count)')
pad = ' ' * (2_000_001 - len(json.dumps(base['dorset'])))
put('w14f_size', 'kent', raw=json.dumps(base['kent']) + ' '*(2_000_001-len(json.dumps(base['kent']))), why='INVALID file format: 2,000,001 bytes (valid LFL plan padded with whitespace)')
# 15 structure
put('w15_runs_not_list', 'dorset', {"runs":{"0":{"day":0,"line":"L1","product":"COL01","batches":1}}}, why='INVALID file format: runs is an object, not a list')
put('w15b_top_list', 'kent', raw=json.dumps(base['kent']['runs']), why='INVALID file format: top level is a list of runs, not an object')
put('w15c_missing_key', 'fife', {"runs":[{"day":0,"line":"L4","product":"LEM02"}]}, why='INVALID file format: run lacks batches')

# VALID alternatives
# v1: exact capacity edge incl setup, same product two lines same day, extra keys everywhere, reversed order, 4300-digit int in ignored key, depth 64
runs = [{"day":0,"line":"L1","product":"COL01","batches":71,"comment":"897 min"},
        {"day":0,"line":"L2","product":"COL01","batches":67,"x":{"y":[1,2]}}]  # L2: 90+67*12=894 <=900
# fill dorset L1 day2 exactly 450 with two products
ex=(5,10)
runs += [{"day":2,"line":"L1","product":"COL01","batches":5},{"day":2,"line":"L1","product":"WAT04","batches":10}]
runs.reverse()
v1 = '{"meta":{"k":' + '9'*4300 + ',"deep":' + '['*62 + ']'*62 + '},"runs":' + json.dumps(runs) + ',"v":1.5e3}'
put('v01_edges_extra_keys', 'dorset', raw=v1, why=f'VALID: exact 900/897/450 capacity edges incl setup (L1 day2 pair {ex}), COL01 on L1 and L2 same day, extra keys at top and in runs, reversed order, 4300-digit int, depth 64')
# v2: empty plan for tyne (all backlog), plus -0 day and whitespace
put('v02_empty_runs', 'tyne', raw='\n  {"runs": []}  \n', why='VALID: empty runs list (all demand unfilled, costed not forbidden); leading/trailing whitespace')
put('v03_lfl_all', 'kent', base['kent'], why='VALID: shipped lot-for-lot planner output (baseline must be accepted)')
for s in ['dorset','fife','tyne']:
    json.dump(base[s], open(f'{OUT}/v03_lfl_all/{s}.json','w'))
put('v04_minus_zero_day_unicode', 'fife', raw='{"runs":[{"day":-0,"line":"\\u004C4","product":"LEM02","batches":1,"n\u00f6te":"\u00e9"}]}', why='VALID: day written -0 (a JSON integer equal to 0), line id via \\u escape, non-ASCII extra key')
print('edges', best, ex)
