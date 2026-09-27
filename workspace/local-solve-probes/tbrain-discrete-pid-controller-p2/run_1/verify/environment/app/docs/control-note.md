# LT-7: the loop controller

This note fixes how `looptune` computes one step. It is the reference for the
package; where the two disagree, the note is right.

## 1. Scope and terms

The controller runs once every sample period `h` seconds. Each step is given a
setpoint `r`, a measurement `y` and a feedforward `f`, and returns an output
`u`. The error is `e = r - y`.

The settings are the gain `K`, the integral time `Ti`, the derivative time
`Td`, the filter divisor `N`, the tracking time `Tt`, the setpoint weight `b`,
the output limits `low` and `high`, and the slew rate `s` (output units per
second). The period is fixed when the controller is built, and this note is
written for a period above nought. Every other setting is read afresh on each
step, so a retune (section 8) acts from the next step.

"The first step" means the first call to `step` on a controller, whatever mode
it is in. "The previous output" and "the previous measurement" mean the `u`
returned by, and the `y` given to, the step before this one.

Sections 2 to 6 describe a step in automatic mode. Section 7 says what changes
in manual mode.

## 2. Proportional term

For a setpoint weight from nought to one, both included, the proportional
term is

    P = K * (b * r - y)

so a setpoint step is softened by the weight while a disturbance in the
measurement still meets the full gain.

## 3. Integral term

The integral state `I` starts at nought. Whatever the integral and tracking
times, an automatic step adds to `I` only after its output has been formed
(section 5), so the step that makes an addition does not see it: the `I` that
enters `v` is the value `I` had when the step began.

With an integral time above nought, this section's addition is

    K * h / Ti * e

using the full error whatever the setpoint weight is; weighting the setpoint
in the integral would leave a steady offset.

## 4. Derivative term

The derivative term `D` starts at nought. It acts on the measurement alone, so
a setpoint step does not kick the output. It is filtered with time constant
`Td / N` and discretised with the backward difference:

    a = Td / (Td + N * h)
    D = a * D_before - K * N * a * (y - y_previous)

where `D_before` is the value `D` had when the step began and `y_previous` is
the previous measurement. On the first step there is no previous measurement,
and `y_previous` is taken to be `y` itself.

Everything in this section is for a derivative time and a filter divisor that
are both above nought.

## 5. Forming the output

The unlimited output is

    v = P + I + D + f

with the feedforward inside it, so the limits act on the feedforward too.

For a low limit below the high limit, `v` is then held within the limits:
`w` is `low` when `v` is below `low`, `high` when `v` is above `high`, and `v`
otherwise.

The slew rate acts on `w`, after the limits. A slew rate above nought limits
how far the output moves in one step: `u` is `w` moved no further than `s * h`
from the previous output, or, on the first step, `w` itself.

## 6. Anti-windup tracking

Anti-windup feeds the part of `v` that did not reach the output back into the
integral. With a tracking time above nought, each automatic step adds

    h / Tt * (u - v)

to `I`, alongside the addition of section 3 and at the same point in the step.

## 7. Manual mode

`set_manual(m)` puts the controller in manual mode with manual output `m`;
calling it again changes `m`. `set_auto()` returns it to automatic mode. A
controller starts in automatic mode.

A manual step returns `m` unchanged: the limits and the slew rate do not apply
to it. `P` and `D` are formed as in sections 2 and 4, and `I` is set to
`m - P - D - f`, so that `v` is `m`. Sections 3 and 6 add nothing in manual
mode. A manual step's output is the previous output for the step after it.

## 8. Retuning

`retune(**settings)` changes the named settings from the next step on. When a
retune changes the gain or the setpoint weight, and the controller has already
taken a step, `I` changes by the old proportional term minus the new one: the
proportional terms the controller computes with the old and with the new
settings, at the setpoint and measurement of the last step. A change to any
other setting is not compensated.

## 9. Diagnostics

`terms()` returns the parts of the last step as a dictionary with the keys
`p`, `i`, `d`, `f`, `v` and `u`: the proportional term, the integral that
entered `v`, the derivative term, the feedforward, the unlimited output and
the output. After a manual step, `i` is the integral that the step set and `v`
is `m`.
