#!/bin/bash
# Reference pybc: a pure-Python GNU bc 1.07.1 for the language subset in the task.
#
# Area (manual section)            How
# numbers (Basic Elements)         the bc number library: sign, digits and scale; add/sub keep the larger
#                                  scale, multiply min(sa+sb, max(scale, sa, sb)), divide to scale digits,
#                                  % via a/b to scale digits, ^ by repeated squaring with the scale cut,
#                                  Newton square root at growing scale; everything truncates
# lexer (Comments, Numbers)        flex-style longest match: keywords, names, constants with \<newline>,
#                                  leading zeros dropped, strings, # and /* */ comments, . as last
# parser (Expressions, Statements) yacc precedence (|| && ! relational = + - * / % ^ unary-minus ++ --),
#                                  assignment only after a named expression, GNU's expression flags that
#                                  decide whether a statement prints, code generation with labels
# execution (Statements)           one execution block per complete line; runtime errors end the block;
#                                  constants converted at run time with ibase (the call-time ibase in a
#                                  function); ibase/obase/scale clamping; last updated by every print
# functions (Functions)            parameters and autos pushed on per-name stacks (dynamic scoping),
#                                  arrays copied or aliased (*name[]), void functions, redefinition,
#                                  parse-time quit and run-time halt
# output (Statements)              bc_out_num for every obase (grouped digits above 16, truncated fraction
#                                  digits) with one shared column count: a backslash-newline before the
#                                  69th character of a line, for numbers and strings alike
#
# Strategy: port GNU bc's scanner, grammar actions and byte-code interpreter faithfully,
# on top of an exact decimal implementation of its number library.
set -euo pipefail
install -d /app/pybc
cp /solution/pybc/bc.py /app/pybc/
