# vc_arb: three-channel credit-based link transmit arbiter

`vc_arb` sits in front of a link transmitter. Three virtual channels (VC 0, 1,
2) each queue bytes in a two-entry buffer. The far end grants credits per VC;
a byte may only be sent on a VC that holds a credit. The block picks at most
one byte per cycle into a single output register that the link drains with a
valid/ready handshake.

## 1. Ports

| Port | Dir | Width | Meaning |
|---|---|---|---|
| `clk` | in | 1 | clock; every register changes only on its rising edge |
| `rst_n` | in | 1 | synchronous reset, active low |
| `in_valid` | in | 3 | bit v: VC v offers a byte |
| `in_data` | in | 24 | bits `8v+7:8v`: the byte VC v offers |
| `in_ready` | out | 3 | bit v: VC v's buffer accepts a byte this cycle |
| `out_valid` | out | 1 | the output register holds a byte |
| `out_vc` | out | 2 | VC of the byte in the output register |
| `out_data` | out | 8 | the byte in the output register |
| `out_ready` | in | 1 | the link takes the output byte this cycle |
| `cr_ret` | in | 3 | bit v: the far end returns one credit to VC v |
| `flush` | in | 3 | bit v: discard VC v's buffered bytes |
| `cfg_we` | in | 1 | load a credit count |
| `cfg_vc` | in | 2 | VC whose count is loaded (value 3 selects no VC) |
| `cfg_credits` | in | 3 | the count to load |
| `credits` | out | 9 | bits `3v+2:3v`: VC v's credit count |

## 2. State

Per VC v: a FIFO buffer of at most two bytes, `cnt[v]` (0, 1 or 2) and a credit
count `cred[v]` (0 to 7). Shared: the output register (`out_valid`, `out_vc`,
`out_data`), `last` (the VC of the most recent grant, 0 to 2) and `run` (1 or
2, how many grants in a row `last` has received in its current run).

## 3. Outputs

3.1 Every output is a function of the registers alone. No input reaches an
output within the same cycle.

3.2 `in_ready[v]` is 1 exactly when `cnt[v]` is less than 2.

3.3 `credits` shows `cred[v]` in bits `3v+2:3v`.

3.4 `out_vc` and `out_data` are 0 whenever `out_valid` is 0.

## 4. One clock edge

All rules below describe the rising edge of `clk` with `rst_n` high. Every rule
reads the register values held before the edge and the inputs sampled at the
edge; all of them take effect together at that edge.

4.1 **Opportunity.** The edge is a grant opportunity when `out_valid` is 0 or
`out_ready` is 1. On any other edge no grant is made and `out_valid`,
`out_vc`, `out_data`, `last` and `run` keep their values.

4.2 **Eligibility.** VC v is eligible when `cnt[v] > 0`, `cred[v] > 0` and
`flush[v]` is 0. A credit returned, a credit count loaded or a byte written at
this edge does not make a VC eligible at this edge.

4.3 **Selection.** At an opportunity:
- if `run` is 1 and `last` is eligible, `last` is granted and `run` becomes 2;
- otherwise the VCs are tried in the order `last+1`, `last+2`, `last` (modulo
  3) and the first eligible one is granted; `run` becomes 1 and `last` becomes
  the granted VC;
- if no VC is eligible, nothing is granted and `last` and `run` keep their
  values (except as 4.4 says).

4.4 **Flush ends a run.** If `flush[last]` is 1 at an edge where no grant is
made, `run` becomes 2. (At an edge with a grant, 4.3 sets `run`.)

4.5 **Output register.** On a grant to VC g, `out_valid` becomes 1, `out_vc`
becomes g and `out_data` becomes the oldest byte in VC g's buffer. With no
grant, if `out_valid` is 1 and `out_ready` is 1 the byte leaves:
`out_valid`, `out_vc` and `out_data` become 0. Otherwise they hold.

4.6 **Buffer.** VC v writes `in_data[8v+7:8v]` when `in_valid[v]` is 1 and
`in_ready[v]` (3.2) is 1. A grant to v removes its oldest byte. Both may happen
at one edge; the written byte goes behind any byte that stays. A full buffer
never accepts a byte, even at an edge that removes one.

4.7 **Flush.** When `flush[v]` is 1, every byte that was in VC v's buffer before
the edge is discarded. A byte written by VC v at the same edge (4.6) is kept
and becomes the only byte in the buffer. Flush does not touch the output
register, even when it holds a VC v byte, and does not change `cred[v]`.

4.8 **Credits.** Let `base` be `cfg_credits` when `cfg_we` is 1 and `cfg_vc`
is v, else `cred[v]`. The new `cred[v]` is `base`, minus 1 if VC v is granted
at this edge, plus 1 if `cr_ret[v]` is 1, then limited to the range 0 to 7
(a result below 0 becomes 0, above 7 becomes 7).

## 5. Reset

At a rising edge with `rst_n` low every other input is ignored and: all buffers
are empty, every `cred[v]` is 4, `out_valid`, `out_vc` and `out_data` are 0,
`last` is 2 and `run` is 2. The first grant after reset therefore tries VC 0
first.

## 6. Examples

Credit returned at the edge where VC 0 has a byte but no credit: nothing is
granted at that edge, and VC 0 is granted at the next one. Columns show the
registers after each edge.

```
                 before   edge 0   edge 1
cr_ret[0]                   1        0
cred[0]            0        1        0
cnt[0]             1        1        0
out_valid          0        0        1
```

Runs with `out_ready` held at 1 and every buffer and credit count nonzero,
starting from `last` = 0, `run` = 2:

```
edge        0    1    2    3    4
granted     1    1    2    2    0
run         1    2    1    2    1
```

A flush of VC 1 while `last` = 1 and `run` = 1, with no VC eligible, ends the
run; if VC 1 then writes a byte at that same edge, the next grant still starts
from VC 2.

## 7. Build rules

`/app/rtl/vc_arb.v` holds the whole module: synthesizable Verilog-2005 that
Yosys `synth -top vc_arb` accepts, one clock, no latches, no `initial` blocks,
no delays, no system tasks or functions (`$display`, `$fopen`, `$readmemh`,
...), no `` `include ``, and no hierarchical (dotted) names.
