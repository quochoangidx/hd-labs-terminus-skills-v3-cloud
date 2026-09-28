# TS-4: stepping the two-node enclosure model

This note fixes what `thermostep.simulate` computes. The curing ovens, the
sample conditioning boxes and the battery soak chamber are all modelled this
way, and the commissioning reports quote its numbers directly, so the stepper
has to give the model's answer and not an approximation of it.

## 1. The model

The enclosure is two lumped nodes. Node 1 is the chamber (air, shelves and
load); node 2 is the wall. Each has a heat capacity, `C1` and `C2` in J/K,
both above nought. Three conductances, in W/K and each nought or more, join
them: `g1` from node 1 to ambient, `g2` from node 2 to ambient and `g12`
between the nodes. The heater puts its power into node 1 only.

With `Ta` the ambient temperature and `P` the heater power, the temperatures
obey

    C1 * dT1/dt = g1 * (Ta - T1) + g12 * (T2 - T1) + q * P
    C2 * dT2/dt = g2 * (Ta - T2) + g12 * (T1 - T2)

where `q` is one while the heater is on and nought while it is off.
Temperatures are in degrees Celsius and times in seconds.

## 2. The schedule

A run is given sample times `t0 < t1 < ... < tn`, the ambient temperature at
each sample time, and one heater power for each interval `[tk, tk+1]`. The
intervals need not be equal.

Between two samples the ambient moves in a straight line from its value at
the first sample to its value at the second. The heater power is constant over
an interval and changes only at sample times.

## 3. What a step computes

The temperatures reported at each sample time are the exact solution of the
equations in section 1 over the whole run, starting from the given `T1` and
`T2` at `t0`: the ambient follows its straight lines, and the heater is on or
off exactly as section 4 says, switching at the exact instants section 4
defines.

## 4. The thermostat

A run may have a thermostat. It watches `T1` and has a lower and an upper
set point, the lower below the upper. While the heater is on, it switches off
at the first instant `T1` reaches the upper set point, that is, when `T1` is
at or above it. While the heater is off, it switches on at the first instant
`T1` reaches the lower set point, `T1` at or below it.

A switch takes effect at the instant it happens: from then on the equations
run with the new `q`. Nothing limits how many switches fall inside one
interval. The rule applies from `t0` on, so
a heater that starts on with `T1` already at or above the upper set point
switches off at `t0`.

Without a thermostat the heater stays in the state the run starts with.

## 5. What a run reports

`simulate` returns a `Run` with three lists:

- `temperatures`: `(T1, T2)` at each sample time `t0 ... tn`;
- `heater`: whether the heater is on at each sample time, after any switch at
  that instant;
- `switches`: every switch as `(time, on)`, in time order, where `on` is the
  heater's state after the switch.
