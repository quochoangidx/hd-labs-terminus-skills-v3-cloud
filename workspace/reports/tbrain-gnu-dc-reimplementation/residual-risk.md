# Residual risk (reviewer notes, not for the platform form)

- The "2^31 or more counts as -1" convention is exact except for 2147483648 and 2147483649 (and their negatives), which GNU wraps to 32-bit values. No retained case uses them.
- The apt `dc` package in tests/Dockerfile is not version-pinned (policy gate); the base image is digest-pinned bookworm, whose dc is 1.07.1-3 (dc 1.4.1).
- In GNU, `q` inside a macro called from the top level of one `-e` ends only that `-e`, while the manual says dc exits. No retained multi-source case exercises this.
- If cases are regenerated, rerun the variant filter (reports/dc-work) and keep excluding `?` when the script itself comes from stdin.
