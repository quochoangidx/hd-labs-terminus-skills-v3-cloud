C = []
for p in ["length(0)", "length(0.000)", "length(0.010)", "length(10.0)", "length(-0.5)", "sqrt(1.000)", "scale=3; sqrt(1)", "sqrt(0.0000)", "scale=2; sqrt(0.25)", "scale=0; sqrt(0.25)", "scale=0; sqrt(10.00)", "scale=4; -7/3", "scale=0; -7.9/1", "scale=1; -0.04*1", "0.0 * -1", "scale=2; -1/1000"]:
    C.append({"input": p + "\n"})
