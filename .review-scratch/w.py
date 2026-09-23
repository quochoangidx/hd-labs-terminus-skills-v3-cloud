import json
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref

D = "/Users/thuongthai/work/hd-labs-terminus-skills-v3/workspace/reports/tbrain-quantized-depthwise-convolution/review-packet/environment/app/tools/qdriver.py"


def shipped(job):
    p = subprocess.run([sys.executable, D], input=json.dumps(job), capture_output=True, text=True)
    return json.loads(p.stdout) if p.returncode == 0 else {"ERR": p.stderr.strip().splitlines()[-1]}


jobs = []
jobs.append(("W1 sizes same odd total stride2", {"op": "sizes", "h": 6, "w": 6, "kh": 3, "kw": 3, "stride": [2, 2], "dilation": [1, 1], "padding": "same"}))
jobs.append(("W2 sizes same dilated asym", {"op": "sizes", "h": 7, "w": 9, "kh": 3, "kw": 2, "stride": [2, 3], "dilation": [2, 3], "padding": "same"}))
jobs.append(("W3 sizes none dilated asym", {"op": "sizes", "h": 7, "w": 9, "kh": 3, "kw": 2, "stride": [2, 3], "dilation": [2, 3], "padding": "none"}))
jobs.append(("W4 sizes none kernel>input", {"op": "sizes", "h": 3, "w": 3, "kh": 5, "kw": 3, "stride": [1, 1], "dilation": [1, 1], "padding": "none"}))
jobs.append(("W5 multipliers per-channel", {"op": "multipliers", "input_scale": 0.05, "kernel_scales": [0.02, 0.03, 0.4], "output_scale": 0.1}))
jobs.append(("W5b multipliers m>=1", {"op": "multipliers", "input_scale": 1.0, "kernel_scales": [1.0, 2.5, 0.5], "output_scale": 1.0}))
jobs.append(("W6 requantize negative halves", {"op": "requantize", "mantissa": 1 << 30, "shift": 1, "accumulators": [-6, -2, 2, 6, -3, 3, 0], "output_zero_point": -5}))
jobs.append(("W6b requantize negative shift", {"op": "requantize", "mantissa": 1 << 30, "shift": -2, "accumulators": [-5, 5], "output_zero_point": 0}))
jobs.append(("W7 activation_bounds nonzero ozp", {"op": "activation_bounds", "output_scale": 0.1, "output_zero_point": 7, "lower": 0.0, "upper": 6.0}))
jobs.append(("W8 activation_bounds saturating", {"op": "activation_bounds", "output_scale": 0.1, "output_zero_point": 40, "lower": -20.0, "upper": 20.0}))
jobs.append(("W13 inverted bounds", {"op": "activation_bounds", "output_scale": 0.1, "output_zero_point": 0, "lower": 5.0, "upper": 1.0}))

inp = {"h": 3, "w": 3, "c": 2, "codes": list(range(1, 19)), "scale": 0.05, "zero_point": -3}
ker = {"kh": 2, "kw": 2, "codes": [1, -1, 2, -2, 3, -3, 4, -4], "scales": [0.02, 0.03], "zero_points": [1, -2]}
jobs.append(("W9 accumulate same zp bias", {"op": "accumulate", "input": inp, "kernel": ker, "bias": [10, -7], "stride": [1, 1], "dilation": [1, 1], "padding": "same"}))
jobs.append(("W10 layer clamped", {"op": "layer", "input": inp, "kernel": ker, "bias": [10, -7], "stride": [1, 1], "dilation": [1, 1], "padding": "same", "output": {"scale": 0.1, "zero_point": 7}, "activation": {"kind": "clamped", "lower": 0.0, "upper": 2.0}}))
jobs.append(("W11 layer dilated none", {"op": "layer", "input": {"h": 5, "w": 4, "c": 1, "codes": list(range(-10, 10)), "scale": 0.25, "zero_point": 4}, "kernel": {"kh": 2, "kw": 2, "codes": [3, -5, 7, 2], "scales": [0.5], "zero_points": [-1]}, "bias": [100], "stride": [2, 1], "dilation": [2, 2], "padding": "none", "output": {"scale": 0.125, "zero_point": -8}, "activation": {"kind": "none"}}))
jobs.append(("W14 layer big bias overflow", {"op": "layer", "input": {"h": 1, "w": 1, "c": 1, "codes": [5], "scale": 1.0, "zero_point": 0}, "kernel": {"kh": 1, "kw": 1, "codes": [1], "scales": [1.0], "zero_points": [0]}, "bias": [2**31], "stride": [1, 1], "dilation": [1, 1], "padding": "none", "output": {"scale": 1.0, "zero_point": 0}, "activation": {"kind": "none"}}))
jobs.append(("W15 unknown padding", {"op": "sizes", "h": 5, "w": 5, "kh": 3, "kw": 3, "stride": [1, 1], "dilation": [1, 1], "padding": "valid"}))
jobs.append(("W16 nonpositive multiplier", {"op": "multipliers", "input_scale": 0.0, "kernel_scales": [1.0], "output_scale": 1.0}))
jobs.append(("W17 dequantize", {"op": "dequantize", "scale": 0.1, "zero_point": 7, "codes": [-128, 0, 127]}))

for name, j in jobs:
    op = j["op"]
    try:
        if op == "sizes":
            r = dict(zip(("out_h", "out_w", "pad_top", "pad_bottom", "pad_left", "pad_right"),
                         ref.geom(j["h"], j["w"], j["kh"], j["kw"], tuple(j["stride"]), tuple(j["dilation"]), j["padding"])))
        elif op == "multipliers":
            m, s = ref.chmul(j["input_scale"], j["kernel_scales"], j["output_scale"])
            r = {"mantissas": m, "shifts": s}
        elif op == "requantize":
            r = {"values": [ref.requant_one(j["mantissa"], j["shift"], a, j["output_zero_point"]) for a in j["accumulators"]]}
        elif op == "activation_bounds":
            lo, hi = ref.act_bounds(j["output_scale"], j["output_zero_point"], j["lower"], j["upper"])
            r = {"low": lo, "high": hi}
        elif op == "accumulate":
            t, k = j["input"], j["kernel"]
            g = ref.geom(t["h"], t["w"], k["kh"], k["kw"], tuple(j["stride"]), tuple(j["dilation"]), j["padding"])
            r = dict(zip(("out_h", "out_w", "pad_top", "pad_bottom", "pad_left", "pad_right"), g))
            r["accumulators"] = ref.accumulate(t["codes"], t["h"], t["w"], t["c"], t["zero_point"], k["codes"], k["kh"], k["kw"], k["zero_points"], j["bias"], tuple(j["stride"]), tuple(j["dilation"]), g)
        elif op == "layer":
            r = ref.layer(j)
        else:
            r = "(note silent)"
    except Exception as e:
        r = f"EXC {type(e).__name__}: {e}"
    print("###", name)
    print("  note :", json.dumps(r) if not isinstance(r, str) else r)
    print("  ship :", json.dumps(shipped(j)))
