# Contract review r1: tbrain-virtual-channel-credit-arbiter

Scope read: `instruction.md`, `environment/` (Dockerfile, app/README.md, app/docs/spec.md, app/rtl/vc_arb.v, app/sim/*). Nothing else.

## Part 1: contract review

Goal and data contract are clear. The ports, widths and bit packing (`in_data[8v+7:8v]`, `credits[3v+2:3v]`) are fixed in §1. State ranges have floors and ceilings: cnt 0..2, cred 0..7 with an explicit clamp, run 1..2, last 0..2. Every output is registered (§3.1), and §3.4 zeroes `out_vc`/`out_data` when the output is invalid. The order of credit arithmetic is spelled out (base, then -grant, then +ret, then clamp). The full-buffer-plus-grant, flush-plus-write and flush-leaves-output cases are each governed by one sentence. Reset values are complete. I found one real conflict.

### F1 (blocking): §4.1 and §4.4 disagree on `run` at a non-opportunity edge with `flush[last]`=1
- §4.1: "On any other edge no grant is made and `out_valid`, `out_vc`, `out_data`, `last` and `run` keep their values."
- §4.4: "If `flush[last]` is 1 at an edge where no grant is made, `run` becomes 2."
- A non-opportunity edge (`out_valid`=1, `out_ready`=0) is by definition "an edge where no grant is made". Both sentences therefore govern it and give different `run` values. §4.3's "(except as 4.4 says)" sits only in the no-eligible-VC bullet at an opportunity, so it does not settle which rule wins here. `run` is not a port, but it decides later grants, and those show up on `out_vc`/`out_data`.
- Counterexample trace. Start with last=1, run=1, out_valid=1, cnt[1]=1, cnt[2]=1, cred=4/4/4.
  - Edge A: out_ready=0, flush=3'b010, in_valid[1]=1 (the written byte survives the flush, so cnt[1]=1). Reading 1 (§4.1 wins) gives run=1. Reading 2 (§4.4 wins) gives run=2.
  - Edge B: out_ready=1, no flush, and VC1 and VC2 are both eligible. Reading 1 grants VC1 (the run continues, so out_vc=1 after edge B). Reading 2 tries last+1 first, grants VC2, and gives out_vc=2.
- The instruction says the bench aims at "flushes while a grant is pending" and "back-pressure", so this case will come up.
- Fix: say explicitly whether §4.4 applies on non-opportunity edges. For example, exempt `run` in §4.1 ("... keep their values, except `run` per 4.4"), or limit §4.4 to opportunities.

### F2 (polish): the order of eligibility and selection when `run`=2 and only `last` is eligible
§4.3 bullet 2 ends the order with `last`, so a lone eligible `last` is granted with run=1. That is unambiguous, but it rewards careful reading. No change is needed.

### F3 (polish): §6 example 3 overlaps F1 only at an opportunity edge
It says "no VC eligible", so it does not settle F1. Adding a second example at a back-pressured edge would close F1 once the rule is chosen.

No other sentence was left open. Things I checked:
- a grant with a `cfg_we` load of 0 plus `cr_ret` (0-1+1=0 because the clamp comes last)
- a load of 7 plus `cr_ret` (clamps to 7)
- `cfg_vc`=3
- a flush on a full buffer with `in_valid` (in_ready=0, so no write and cnt becomes 0)
- `in_valid` on a full buffer that is being granted (rejected)
- a flush of the VC whose byte sits in the output register (the output is untouched)
- inputs during reset (ignored)
- an opportunity edge with out_valid=0 and no grant (outputs hold at 0)

## Witnesses (worked by hand; state columns show values after each edge)

W1. Reset, then VC0 writes 0xAA at edge 1 with out_ready=1. Edge 1: cnt0=1, not eligible yet (§4.2, cnt is read before the edge). Edge 2: grant VC0 (order after last=2 is 0,1,2). out_valid=1, out_vc=0, out_data=AA, cred0=3, run=1, last=0, cnt0=0. No guess needed.

W2. The credit arithmetic. cred0=1, cnt0=1, opportunity, cfg_we=1, cfg_vc=0, cfg_credits=0, cr_ret[0]=1. VC0 is eligible (the old cred is 1) and is granted. base=0, then -1 gives -1, then +1 gives 0, and the clamp leaves 0. Result: credits[2:0]=0, out_vc=0. No guess needed.

W3. cred1=7, cr_ret[1]=1, VC1 not granted. 8 clamps to 7. With a cfg load of 7 on VC1 and cr_ret, the result is still 7. No guess needed.

W4. A full buffer that is both granted and written. cnt2=2 (bytes B0,B1), in_valid[2]=1 with byte B2, grant to VC2. in_ready[2]=0 before the edge, so there is no write. After the edge: cnt2=1 holding B1, out_data=B0, in_ready[2]=1. No guess needed.

W5. A flush and a write together. cnt1=2, flush[1]=1, in_valid[1]=1. in_ready[1]=0, so there is no write and cnt1 becomes 0. If instead cnt1=1, the write happens, the old byte is discarded and cnt1=1 holding the new byte. VC1 is not eligible at this edge. No guess needed.

W6. The §6 run sequence (last=0, run=2, everything eligible, out_ready=1) grants 1,1,2,2,0 with run 1,2,1,2,1. It reproduces the example.

W7. Back-pressure lifts. out_valid=1, out_ready=1, a VC is eligible. It is an opportunity, so the new byte replaces the old one in the same edge (grant takes priority over the drain in §4.5). out_valid stays 1. No guess needed.

W8. The F1 trace above. After edge B, out_vc is 1 or 2 depending on how F1 is read. **I had to guess here.**

W9. A drain with no eligible VC. out_valid=1, out_ready=1, nothing eligible: out_valid, out_vc and out_data all become 0. last and run hold, unless flush[last] sets run=2. No guess needed.

## Part 2: solver-path screen

A) Pre-mortem. A strong solver reads the spec's roughly 30 rules and writes one always block with next-state logic computed from the pre-edge registers. It then writes a Python or Verilog reference model from the same text, plus a random-stimulus comparison against its RTL. That self-check shares every misreading between the model and the RTL, so it only catches coding slips, not interpretation errors. The natural places to go wrong are few:
- (a) F1: most solvers will code §4.4 as "no grant" in the literal sense, including non-opportunity edges. Some will gate it inside the opportunity branch, because §4.1 says run holds.
- (b) Using post-write cnt or post-return credit for eligibility. §4.2 names this explicitly, so the risk is low.
- (c) Clamping between steps of the credit arithmetic. §4.8 fixes the order.
- (d) Allowing a write into a full buffer at a grant edge. §4.6 forbids it explicitly.
- (e) Forgetting that flush makes the VC ineligible, or making the written byte survive the flush wrongly.

Everything except F1 is stated directly. The design is small (about 150 lines of RTL).

B) Scores (5 = strongly resists solving):
- reference_unreachable: 1. The spec is complete, closed-form and small.
- authority_incomplete_for_grading: 3. F1 is a single real contradiction that the bench is likely to hit, and it is a defect, not difficulty.
- hidden_state_not_closed_form: 1. All state is enumerated in §2.
- restraint_traps: 1. Every exception is written into its rule sentence (the §4.2 exclusions, the §4.6 full-buffer rule, the §4.7 output-untouched rule), so none of them count.
- fuzz_blind_spot: 2. Coincident events are enumerated in the instruction, and a solver's random self-bench will exercise them. It just cannot tell a misreading from correct behaviour.

C)
- self_verification_resistance: 2
- prediction: collapses once F1 is fixed. With F1 left as is, the outcome turns on how the grader resolves F1, not on skill.
- confidence: medium-high
- decisive_reason: every per-edge rule is stated explicitly with its coincident-event exceptions written into the rule itself, so a careful solver can derive a cycle-exact model directly. The only real divergence point is the §4.1/§4.4 contradiction, which is a contract defect rather than earned difficulty.
