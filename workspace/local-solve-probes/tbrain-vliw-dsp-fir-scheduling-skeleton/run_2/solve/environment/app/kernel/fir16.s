# fir16.s -- 16-tap FIR filter, y[n] = (h[0]x[n] + ... + h[15]x[n+15]) >> 15
#
# Entry: r0 = N, a0 = x (packed pairs), a1 = h (packed pairs), a2 = y.
#
# Software-pipelined: one loop pass (16 bundles) produces the output pair
# y[2s] (acc0, words X[s..s+7] against H0..H7) and y[2s+1] (acc1, realigned
# words P[j] = pkhl(X[j], X[j+1]) against H0..H7). The MAC unit issues every
# cycle. Loads for the next pass are issued in the current pass; the odd
# output of pass s is stored early in pass s+1 through a3 (the very first
# such store writes 0 to 0x3FFF, inside the scratch area).
#
# Registers: r1..r9 = X/P window R0..R8, r10..r17 = H0..H7, r0 = pass count.

        ld r10, [a1+=1] ; sar r0, r0, 1        # H0, r0 = N/2 passes
        ld r1, [a0+=1]  ; ali a3, 0x3FFF       # X0
        ld r11, [a1+=1]                         # H1
        ld r2, [a0+=1]                          # X1
        ld r12, [a1+=1]
        ld r3, [a0+=1]
        ld r13, [a1+=1]
        ld r4, [a0+=1]
        ld r14, [a1+=1]
        ld r5, [a0+=1]
        ld r15, [a1+=1]
        ld r6, [a0+=1]
        ld r16, [a1+=1]
        ld r7, [a0+=1]                          # X6, a0 -> X7
        ld r17, [a1+=1] ; loop r0, pair_end     # H7
        dmacz acc0, r10, r1 ; ld r8, [a0+=1]
        dmac acc0, r11, r2  ; ld r9, [a0+=-7]
        dmac acc0, r12, r3  ; sta acc1, 15, [a3+=2]
        dmac acc0, r13, r4
        dmac acc0, r14, r5
        dmac acc0, r15, r6
        dmac acc0, r16, r7
        dmac acc0, r17, r8  ; pkhl r1, r1, r2
        dmacz acc1, r10, r1 ; pkhl r2, r2, r3 ; ld r1, [a0+=1]
        dmac acc1, r11, r2  ; pkhl r3, r3, r4 ; ld r2, [a0+=1]
        dmac acc1, r12, r3  ; pkhl r4, r4, r5 ; sta acc0, 15, [a2+=2]
        dmac acc1, r13, r4  ; pkhl r5, r5, r6 ; ld r3, [a0+=1]
        dmac acc1, r14, r5  ; pkhl r6, r6, r7 ; ld r4, [a0+=1]
        dmac acc1, r15, r6  ; pkhl r7, r7, r8 ; ld r5, [a0+=1]
        dmac acc1, r16, r7  ; pkhl r8, r8, r9 ; ld r6, [a0+=1]
pair_end: dmac acc1, r17, r8 ; ld r7, [a0+=1]
        sta acc1, 15, [a3+=2] ; halt
