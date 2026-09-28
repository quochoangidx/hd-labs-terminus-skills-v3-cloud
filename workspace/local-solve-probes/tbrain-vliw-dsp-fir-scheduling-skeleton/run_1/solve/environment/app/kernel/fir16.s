# fir16.s -- 16-tap FIR filter, y[n] = (h[0]x[n] + ... + h[15]x[n+15]) >> 15
#
# Entry: r0 = N, a0 = x (packed pairs), a1 = h (packed pairs), a2 = y.
#
# Software-pipelined version: one pair of outputs (y[2s], y[2s+1]) per
# 16-bundle loop pass, with the MAC unit busy every cycle.
#   r12..r19 = H0..H7 (coefficient pairs)
#   r4..r11  = W0..W7 = X[s..s+7]; turned in place into the realigned words
#              P_j = (x[2s+1+2j], x[2s+2+2j]) = pkhl(W_j, W_{j+1}) for the odd
#              output, then reloaded with X[s+1..s+7] / X[s+8] for the next pass.
#   r3       = X[s+8]  (loaded through a3)
#   acc0     = even output, acc1 = odd output.
# The odd output of pass s is stored early in pass s+1, so the first pass
# stores acc1 = 0 to 0x3FFF (scratch area), and a2 starts one word low.

        ld r12, [a1+=1] ; sar r0, r0, 1         # r0 = N/2 output pairs
        ld r4, [a0+=1]  ; aadd a2, -1           # y[-1] slot = 0x3FFF (scratch)
        ld r13, [a1+=1] ; ali a3, 0x1008        # a3 -> X[8]
        ld r5, [a0+=1]
        ld r14, [a1+=1]
        ld r6, [a0+=1]
        ld r15, [a1+=1]
        ld r7, [a0+=1]
        ld r16, [a1+=1]
        ld r8, [a0+=1]
        ld r17, [a1+=1]
        ld r9, [a0+=1]
        ld r18, [a1+=1]
        ld r10, [a0+=1]                         # a0 -> X[7]
        ld r19, [a1+=1] ; loop r0, pair_end
# body cycle 0..15, pass s (a0 -> X[s+7], a3 -> X[s+8])
        dmacz acc0, r12, r4 ; ld r11, [a0+=-6]  # W7 = X[s+7]; a0 -> X[s+1]
        dmac acc0, r13, r5  ; ld r3, [a3+=1]    # W8 = X[s+8]
        dmac acc0, r14, r6  ; sta acc1, 15, [a2+=1]   # y[2s-1]
        dmac acc0, r15, r7
        dmac acc0, r16, r8
        dmac acc0, r17, r9
        dmac acc0, r18, r10
        dmac acc0, r19, r11 ; pkhl r4, r4, r5
        dmacz acc1, r12, r4 ; pkhl r5, r5, r6   ; ld r4, [a0+=1]
        dmac acc1, r13, r5  ; pkhl r6, r6, r7   ; ld r5, [a0+=1]
        dmac acc1, r14, r6  ; pkhl r7, r7, r8   ; sta acc0, 15, [a2+=1]   # y[2s]
        dmac acc1, r15, r7  ; pkhl r8, r8, r9   ; ld r6, [a0+=1]
        dmac acc1, r16, r8  ; pkhl r9, r9, r10  ; ld r7, [a0+=1]
        dmac acc1, r17, r9  ; pkhl r10, r10, r11 ; ld r8, [a0+=1]
        dmac acc1, r18, r10 ; pkhl r11, r11, r3 ; ld r9, [a0+=1]
pair_end: dmac acc1, r19, r11 ; ld r10, [a0+=1]
        sta acc1, 15, [a2] ; halt               # y[N-1]
