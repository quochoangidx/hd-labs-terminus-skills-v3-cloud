# Ad Layout Adversarial Verifier Report

Each submission was checked with:

```bash
cd tests && AD_LAYOUTS=../submissions/<name> python3 -m pytest -q test_outputs.py -k "mon_layout_is_valid"
```

| Submission | Edition | Rule broken or why valid | Expected verdict | Observed verdict |
|---|---|---|---|---|
| `wrong-off-page` | `mon` | `AD015` runs beyond the right edge of page 10. | Reject | Reject (`FAIL`) |
| `wrong-overlap` | `mon` | `AD015` overlaps `AD013` on page 2. | Reject | Reject (`FAIL`) |
| `wrong-floating` | `mon` | `AD015` does not rest on the foot or on ads across its full width. | Reject | Reject (`FAIL`) |
| `wrong-front-strip` | `mon` | `AD018` reaches above the bottom six-row front-page strip. | Reject | Reject (`FAIL`) |
| `wrong-page-limit` | `mon` | Page 5 exceeds its maximum ad-cell share. | Reject | Reject (`FAIL`) |
| `wrong-competitor-same-page` | `mon` | `AD009` and `AD040` are cars-group competitors on page 7. | Reject | Reject (`FAIL`) |
| `wrong-competitor-facing` | `mon` | `AD009` and `AD040` are cars-group competitors on facing pages 6 and 7. | Reject | Reject (`FAIL`) |
| `wrong-missing-booked` | `mon` | Booked ad `AD015` is omitted. | Reject | Reject (`FAIL`) |
| `wrong-float-position` | `mon` | `AD015.page` is a JSON float rather than an integer. | Reject | Reject (`FAIL`) |
| `wrong-string-position` | `mon` | `AD015.page` is a JSON string rather than an integer. | Reject | Reject (`FAIL`) |
| `wrong-boolean-position` | `mon` | `AD015.page` is a JSON boolean rather than an integer. | Reject | Reject (`FAIL`) |
| `wrong-unknown-id` | `mon` | The placements object contains unknown ad id `UNKNOWN`. | Reject | Reject (`FAIL`) |
| `wrong-placements-type` | `mon` | `placements` is an array rather than an object. | Reject | Reject (`FAIL`) |
| `wrong-nan` | `mon` | The file contains the non-standard JSON token `NaN`. | Reject | Reject (`FAIL`) |
| `wrong-huge-file` | `mon` | The file is 2,000,001 bytes, one byte above the limit. | Reject | Reject (`FAIL`) |
| `valid-extra-keys` | `mon` | Extra top-level and placement keys are explicitly ignored. | Accept | Accept (`PASS`) |

## Findings

- No expected/observed verdict mismatches were found. The tested checker paths need no fix.
