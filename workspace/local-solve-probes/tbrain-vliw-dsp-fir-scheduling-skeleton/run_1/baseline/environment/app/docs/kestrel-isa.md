# KESTREL-16 programmer's reference

KESTREL-16 is the filter DSP on our sensor board. `kestrel/` holds its
assembler and cycle-accurate simulator; this page describes the machine they
implement.

## 1. State

- Sixteen-bit halves: a 32-bit word `w` has a low half `lo(w)` (bits 0-15) and a
  high half `hi(w)` (bits 16-31), each read as a signed 16-bit number.
- `r0`-`r19`: twenty 32-bit general registers, two's complement. Results wrap
  to 32 bits.
- `acc0`-`acc3`: four accumulators, 64 bits and wide enough that they never
  overflow in practice.
- `a0`-`a3`: four address registers, word addresses from 0 to 65535. Address
  arithmetic wraps modulo 65536.
- Data memory: 65536 words of 32 bits, all zero unless the caller stores
  something.

## 2. Program format

One line is one **bundle**: up to four operations separated by `;`, at most one
for each unit (ALU, MAC, MEM, CTL). A line may start with `label:`. `#` starts
a comment. Immediates are decimal or `0x` hexadecimal and may be negative.

| Unit | Operation | Effect |
|---|---|---|
| ALU | `li rd, imm` | `rd = imm` |
| ALU | `mov rd, rs` | `rd = rs` |
| ALU | `add rd, rs, rt` / `sub` / `and` / `or` / `xor` | `rd = rs op rt` |
| ALU | `addi rd, rs, imm` | `rd = rs + imm` |
| ALU | `shl rd, rs, imm` / `sar rd, rs, imm` / `shr rd, rs, imm` | shift left, arithmetic right, logical right |
| ALU | `pkhl rd, rs, rt` | `lo(rd) = hi(rs)`, `hi(rd) = lo(rt)` |
| ALU | `ali ax, imm` / `aadd ax, imm` / `amov ax, rs` | `ax = imm` / `ax = ax + imm` / `ax = rs` |
| ALU | `nop` | nothing |
| MAC | `dmac accN, rs, rt` | `accN += lo(rs)*lo(rt) + hi(rs)*hi(rt)` |
| MAC | `dmacz accN, rs, rt` | `accN = lo(rs)*lo(rt) + hi(rs)*hi(rt)` |
| MAC | `mac accN, rs, rt` | `accN += lo(rs)*lo(rt)` |
| MAC | `macz accN, rs, rt` | `accN = lo(rs)*lo(rt)` |
| MEM | `ld rd, [ax]` / `ld rd, [ax+=imm]` | `rd = mem[ax]`, then `ax += imm` |
| MEM | `st rs, [ax]` / `st rs, [ax+=imm]` | `mem[ax] = rs`, then `ax += imm` |
| MEM | `sta accN, sh, [ax]` / `sta accN, sh, [ax+=imm]` | `mem[ax] = low 32 bits of (accN >> sh)` (arithmetic shift), then `ax += imm` |
| CTL | `loop rs, label` / `loop imm, label` | hardware loop, section 4 |
| CTL | `halt` | stop |

## 3. Timing

The machine issues one bundle per cycle, in program order, starting at cycle 0.
A bundle waits (stalls) until every value it reads is ready, then all of its
operations issue together in that cycle. Values become ready this many cycles
after the bundle that produces them issues:

| Value | Ready after |
|---|---|
| general register written by the ALU | 1 cycle |
| general register written by `ld` | 3 cycles |
| address register written by the ALU or by a post-increment | 1 cycle |
| accumulator, for the next `dmac`/`mac` into it | 1 cycle |
| accumulator, for `sta` | 3 cycles |

So a `ld` issued in cycle `t` can be used by a bundle issued in cycle `t + 3` or
later; an earlier bundle that uses it stalls until `t + 3`. A `dmac` chain into
one accumulator runs at one per cycle, and `sta` of that accumulator can issue
three cycles after the last `dmac`.

Operations in one bundle all read their operands before any of them writes, so
`dmac acc0, r1, r4 ; ld r4, [a0+=1]` multiplies by the old `r4`. Results are
written in program order: a later bundle always sees the newest write to a
register, waiting for it if it is not ready yet. Two operations in one bundle
may not write the same register. A program ends at `halt`; its cycle count is
the issue cycle of the `halt` bundle plus one.

## 4. Hardware loop

`loop count, label` repeats the bundles after it, up to and including the
bundle labelled `label`, `count` times (at least once). The loop costs no
cycles: after the last bundle of the body, the next bundle issued is the first
bundle of the body, or the bundle after `label` when the count is used up. The
count is read when the `loop` bundle issues. Loops do not nest.

## 5. Tools

`tools/run_fir.py` assembles `kernel/fir16.s`, runs it on random inputs for a
few values of N, checks every output against the definition in the task, and
prints the cycle count against the budget.
