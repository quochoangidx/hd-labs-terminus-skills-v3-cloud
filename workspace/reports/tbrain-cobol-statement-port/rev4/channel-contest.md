Contest for task 8eaa9cda-42c4-4d68-80a5-6bd99aa99c15 (tbrain-cobol-statement-port), v4 quality panel, Correct Reference Solution findings 1 and 2 (both Major).

Both findings claim the Python reference diverges from the COBOL job step. The verifier's own GnuCOBOL 3.1.2 build stage (tests/Dockerfile, target `legacy`, the exact toolchain the run notes pin) says otherwise on the panel's own inputs, and the reference output is byte-identical in both cases.

Finding 1 — "UNSTRING COUNT IN records the number of characters transferred into PL-ACCT". Cited passage: WBILL.cbl `UNSTRING PAY-LINE DELIMITED BY ";" INTO PL-ACCT COUNT IN PL-ACCT-LEN`. Counterexample: the shipped sample readings (environment/app/legacy/samples/2025q1-north.dat, account 10004821 billed) with PAYIN `10004821X;PAY;1.00;cash`. GnuCOBOL 3.1.2 prints:
    PAYMENTS AND ADJUSTMENTS
    LINE   1 REJECTED BAD ACCOUNT
    POSTED    0  REJECTED   1  PAID          $0.00   OTHER         $0.00
COUNT IN holds 9, the characters examined for the field, so the account-length check rejects the line. The reference prints the same bytes. The graded corpus already decided this: tests/cases/generated_01.pay line 11 has a nine-character account field and the verifier's COBOL-generated expectation is `LINE  11 REJECTED BAD ACCOUNT`, which the reference passed in every platform oracle run.

Finding 2 — "FUNCTION INTEGER(-1.20) is -1". Cited passage: WBILL.cbl `COMPUTE WS-WHOLE = FUNCTION INTEGER(WS-AMT)`. FUNCTION INTEGER is the greatest integer not greater than its argument (INTEGER-PART is the truncating function). Counterexample: readings `H20250331NORTH` + `C10000001Test Person             D000000000000090+00000000000000`, PAYIN `10000001;ADJ;-1.20;x`. GnuCOBOL 3.1.2 prints `ADJ 10000001       -1.20 WHOLE     -2 BAL        28.34   x`; ADJ -1.50, REF -1.20, FEE -1.20 and PAY -1.20 all print WHOLE -2 as well. The reference prints the same bytes. The graded corpus already decided this too: tests/cases/postings_rounding_modes.pay has `91000003;ADJ;-12.345` and `91000001;ADJ;-0.50`, whose COBOL-generated expectations are `WHOLE -13` and `WHOLE -1`, passed by the reference on the platform.

Reproduction: `docker build --target legacy -t cobol-legacy tests/` on the returned ZIP, then `CUSTIN=<readings> PAYIN=<payments> STMTOUT=out.stmt /legacy/WBILL` inside the image, and `python3 solution/wbill.py <readings> <payments> port.stmt`; `cmp` is silent for both pairs.

Rev4 keeps the reference as it is, adds the over-width account lines to postings_account_identifiers so the case is graded by name, and records both checks in the reference's comments. The other three findings (graded disclosed sample, case label in argv/cwd, unasserted 500-record scale) are repaired in the same revision.
