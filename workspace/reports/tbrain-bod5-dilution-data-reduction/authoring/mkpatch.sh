#!/bin/bash
# Regenerate solution/fix.patch from authoring/shipped -> authoring/oracle (paths a/app/src/..., applied with patch -p1 from /).
set -u
cd "$(dirname "$0")"
TASK=../../../tasks/tbrain-bod5-dilution-data-reduction
: > "$TASK/solution/fix.patch"
for f in $(cd oracle/app/src && find . -name '*.py' | sort); do
  f=${f#./}
  diff -u --label "a/app/src/$f" --label "b/app/src/$f" "shipped/app/src/$f" "oracle/app/src/$f" >> "$TASK/solution/fix.patch"
done
exit 0
