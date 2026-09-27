C = []
def c(prog): C.append({"input": prog if prog.endswith("\n") else prog + "\n"})
# arithmetic and scale
for p in ["1+2", "7/2", "scale=3; 7/2", "scale=2; 1/3", "-7/2", "scale=4; -7/2", "7%3", "scale=5; 7%3", "scale=2; 7.5%2", "-7%3", "scale=1; -7%3",
          "1.5*1.5", "scale=5; 1.5*1.5", "scale=1; 1.25*1.25", "scale=10; 1.25*1.25", "2^10", "2^-2", "scale=3; 2^-2", "1.5^3", "scale=10; 1.5^3", "scale=1; 1.1^5",
          "0.5", "-0.5", ".5+.5", "1-1.000", "0.000", "-0", "0-0.5", "3.14159*0", "10/4*4", "scale=2; 10/4*4", "2^0", "0^0", "(-2)^3", "-2^2", "-2^3", "2^-3",
          "scale=20; 1/7", "sqrt(16)", "sqrt(2)", "scale=10; sqrt(2)", "sqrt(2.0000)", "scale(1.230)", "length(1.230)", "length(0.001)", "length(123)", "scale(10/3)", "scale=7; scale(10/3)",
          "a=5; a++; a", "a=5; ++a; a", "a=5; a--; --a; a", "a=3; a+=2; a*=3; a", "a=10; a/=4; a", "scale=2; a=10; a/=4; a", "a=7; a%=4; a", "a=2; a^=5; a",
          "a = 3 < 5; a", "(a = 3 < 5); a", "a = (3 < 5); a", "1 < 2 < 3", "3 < 2 || 1", "!0 + 1", "!(0+1)", "!5", "2 && 0", "1 == 1.000", "0.1 != 0.10",
          "x = 2; y = x++ + x; y; x", "last", "5; last + 1", "5; . + 1",
          "ibase=16; FF", "ibase=16; ff=3; ff", "ibase=2; 101", "ibase=2; A", "ibase=2; 12", "ibase=16; 1.8", "ibase=8; 777.4", "ibase=3; 2222", "ibase=16; ZZ", "ibase=36; ZZ",
          "obase=16; 255", "obase=2; 10", "obase=16; -255", "obase=16; 255.5", "obase=8; 64", "obase=17; 300", "obase=100; 123456", "obase=1000; 5", "obase=20; 0", "obase=16; ibase=16; 1F",
          "ibase=16; obase=A; 10", "obase=10; ibase=16; obase=A; obase", "ibase=7; ibase", "ibase=1; ibase", "ibase=40; ibase", "scale=-1", "scale"]:
    c(p)
# long numbers and line wrapping
c("2^300"); c("scale=100; 1/3"); c("-(2^250)"); c("obase=2; 2^100"); c("obase=16; 2^400"); c("x=10^69; x"); c("x=10^67; x"); c("x=10^68; x"); c("obase=17; 2^200")
# strings and print
c('"hello"'); c('"a\\nb"'); c('print "x=", 5, "\\n"'); c('print "tab\\there\\q\\\\end\\n"'); c('print 1, 2, "\\n"'); c('"multi\nline"\n1'); c('print "\\z\\n"'); c('print 1/3, "\\n"')
# control flow
c("for (i=1; i<=5; i++) i"); c("i=0; while (i<3) { i; i=i+1 }"); c("for (i=0; i<10; i++) { if (i==3) continue; if (i==6) break; i }"); c("if (1) 5 else 6"); c("if (0) 5 else 6")
c("for (;;) { break }; 7"); c("i=0; for (; i<2;) { i++ }; i"); c("x=0; if (x) { 1 } else if (x+1) { 2 } else { 3 }")
c("if (0 == 1) quit\n5"); c("5\nquit\n6"); c("1; halt; 2"); c("if (0) halt\n3")
# functions
c("define f(x) { return (x*2); }\nf(3)"); c("define f(x) { return x*2 }\nf(4)"); c("define f() { }\nf()"); c("define f() { return }\nf()")
c("define f(x) { auto y; y = x + 1; return (y) }\ny = 10; f(1); y")
c("define b() { return (z) }\ndefine a() { auto z; z = 5; return (b()) }\nz = 1; a(); b()")
c("define f(n) { if (n <= 1) return (1); return (n * f(n-1)); }\nf(10)")
c("define f(x) { return (x+A) }\nibase=16; f(1)"); c("ibase=16\ndefine f() { return (10) }\nibase=A\nf()"); c("define f() { return (10) }\nibase=16\nf()")
c("define void p(x) { print \"v=\", x, \"\\n\" }\np(3)"); c("define p(x) { print \"v=\", x, \"\\n\" }\np(3)")
c("define s(a[], n) { auto i, t; for (i=0; i<n; i++) t += a[i]; return (t) }\na[0]=1; a[1]=2; a[2]=3; s(a[], 3)")
c("define z(a[]) { a[0] = 99; return (a[0]) }\na[0]=1; z(a[]); a[0]"); c("define z(*a[]) { a[0] = 99; return (a[0]) }\na[0]=1; z(a[]); a[0]")
c("define f(x) { x = x + 1; return (x) }\nx = 5; f(x); x"); c("define f() { scale = 5; return (1/3) }\nf(); scale; 1/3")
c("define f(x) { return (x) }\ndefine f(x) { return (x*10) }\nf(2)"); c("a[3]=7; a[3]; a[2]; a[1]+a[3]")
c("define f(x) {\n  auto i\n  for (i = 0; i < x; i++) print i, \" \"\n  print \"\\n\"\n}\nf(4)")
# comments and misc
c("/* comment */ 1 + /* inner */ 2"); c("1 + 2 # trailing\n3"); c("x = 1 \\\n + 2; x"); c("a=1;b=2;a+b;"); c(";;5"); c("1\n\n2"); c("{ 1; 2 }"); c("{1\n2}")
c("scale=3; 22/7; last*7"); c("scale=2; x=1/3; x*3"); c("scale=5; x=2/3; scale(x); length(x)"); c("scale=4; 3.0000/1.5"); c("scale=0; 3.0000/1.5")
c("2^31 * 2^33"); c("99999999999999999999 * 99999999999999999999"); c("scale=30; 1/81"); c("-1.5 * -2.25"); c("scale=3; -5.5 % 2")
