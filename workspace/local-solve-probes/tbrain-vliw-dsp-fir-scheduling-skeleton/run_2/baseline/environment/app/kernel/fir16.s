# fir16.s -- 16-tap FIR filter, y[n] = (h[0]x[n] + ... + h[15]x[n+15]) >> 15
#
# Entry: r0 = N, a0 = x (packed pairs), a1 = h (packed pairs), a2 = y.
# Straightforward version: two outputs per loop pass, every input word
# reloaded for every output.

        ld r12, [a1+=1] ; sar r0, r0, 1        # r0 = N/2 output pairs
        ld r13, [a1+=1]
        ld r14, [a1+=1]
        ld r15, [a1+=1]
        ld r16, [a1+=1]
        ld r17, [a1+=1]
        ld r18, [a1+=1]
        ld r19, [a1+=1]
        loop r0, pair_end
# even output: words X[s] .. X[s+7] against H0 .. H7
        ld r4, [a0+=1]
        ld r5, [a0+=1]
        ld r6, [a0+=1]
        ld r7, [a0+=1]
        ld r8, [a0+=1]
        ld r9, [a0+=1]
        ld r10, [a0+=1]
        ld r11, [a0+=1]
        dmacz acc0, r12, r4 ; ld r3, [a0+=-7]
        dmac acc0, r13, r5
        dmac acc0, r14, r6
        dmac acc0, r15, r7
        dmac acc0, r16, r8
        dmac acc0, r17, r9
        dmac acc0, r18, r10
        dmac acc0, r19, r11
        nop
        nop
        sta acc0, 15, [a2+=1]
# odd output: realigned words (x[2s+1+2j], x[2s+2+2j]) from X[s] .. X[s+8]
        pkhl r4, r4, r5
        pkhl r5, r5, r6
        pkhl r6, r6, r7
        pkhl r7, r7, r8
        pkhl r8, r8, r9
        pkhl r9, r9, r10
        pkhl r10, r10, r11
        pkhl r11, r11, r3
        dmacz acc1, r12, r4
        dmac acc1, r13, r5
        dmac acc1, r14, r6
        dmac acc1, r15, r7
        dmac acc1, r16, r8
        dmac acc1, r17, r9
        dmac acc1, r18, r10
        dmac acc1, r19, r11
        nop
        nop
pair_end: sta acc1, 15, [a2+=1]
        halt
