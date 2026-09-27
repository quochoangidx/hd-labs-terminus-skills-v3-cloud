C = []
for p in ['print "abcdefghij", 2^300, "\\n"', 'print 2^200, 2^200, "\\n"', 'print 1, 2^220\n2^220', '"xyz"; 2^220', 'obase=17; print "ab", 2^230, "\\n"', 'print -(2^230), "\\n"', 'x=3^200; print "q", x, " ", x, "\\n"']:
    C.append({"input": p + "\n"})
