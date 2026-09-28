       IDENTIFICATION DIVISION.
       PROGRAM-ID. WBILL.
      *----------------------------------------------------------------
      * WBILL - QUARTERLY WATER STATEMENT RUN.
      * READS THE METER-READING FILE (CUSTIN) AND WRITES THE PRINTED
      * STATEMENT FILE (STMTOUT).  ONE HEADER RECORD, THEN ONE RECORD
      * PER ACCOUNT.  THEN POSTS THE PAYMENTS AND ADJUSTMENTS FILE
      * (PAYIN) AGAINST THE NEW BALANCES AND PRINTS THE LEDGER.
      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT CUST-IN  ASSIGN TO CUSTIN
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT STMT-OUT ASSIGN TO STMTOUT
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT PAY-IN   ASSIGN TO PAYIN
               ORGANIZATION IS LINE SEQUENTIAL.
       DATA DIVISION.
       FILE SECTION.
       FD  CUST-IN.
       01  IN-REC                    PIC X(80).
       FD  STMT-OUT.
       01  OUT-REC                   PIC X(72).
       FD  PAY-IN.
       01  PAY-REC                   PIC X(80).
       WORKING-STORAGE SECTION.
       COPY "CUSTREC.cpy".
       COPY "TARIFFS.cpy".
       01  WS-FLAGS.
           05  WS-EOF                PIC X VALUE "N".
               88  END-OF-INPUT      VALUE "Y".
           05  WS-PAY-EOF            PIC X VALUE "N".
               88  END-OF-PAY        VALUE "Y".
       01  ACCT-TABLE.
           05  AT-COUNT              PIC 9(4) VALUE 0.
           05  AT-ENTRY OCCURS 1 TO 999 TIMES
                   DEPENDING ON AT-COUNT INDEXED BY AX.
               10  AT-ACCT           PIC X(8).
               10  AT-BAL            PIC S9(9)V99.
       01  PAY-WORK.
           05  PAY-LINE              PIC X(80).
           05  PL-ACCT               PIC X(8)  VALUE SPACES.
           05  PL-KIND               PIC X(3)  VALUE SPACES.
               88  KIND-PAY          VALUE "PAY".
               88  KIND-ADJ          VALUE "ADJ".
               88  KIND-FEE          VALUE "FEE".
               88  KIND-REF          VALUE "REF".
           05  PL-AMT-TXT            PIC X(16) VALUE SPACES.
           05  PL-MEMO               PIC X(30) VALUE SPACES.
           05  PL-FIELDS             PIC 99.
           05  PL-ACCT-LEN           PIC 99.
           05  WS-LINE-NO            PIC 9(3)  VALUE 0.
           05  WS-AMT                PIC S9(7)V99.
           05  WS-WHOLE              PIC S9(7).
           05  WS-PART               PIC S9(7)V99.
           05  WS-REM                PIC S9(3)V99.
           05  WS-APPLIED            PIC 9(3)  VALUE 0.
           05  WS-PAY-REJECTED       PIC 9(3)  VALUE 0.
           05  WS-TOT-PAID           PIC S9(9)V99 VALUE 0.
           05  WS-TOT-OTHER          PIC S9(9)V99 VALUE 0.
       01  WS-WORK.
           05  WS-UNITS              PIC 9(7).
           05  WS-TEMP               PIC 9(7).
           05  WS-LIM1               PIC 9(5)V9.
           05  WS-LIM2               PIC 9(5)V9.
           05  WS-B1                 PIC 9(5)V9.
           05  WS-B2                 PIC 9(5)V9.
           05  WS-B3                 PIC 9(7)V9.
           05  WS-C1                 PIC 9(6)V99.
           05  WS-C2                 PIC 9(6)V99.
           05  WS-C3                 PIC 9(7)V99.
           05  WS-USAGE              PIC 9(7)V99.
           05  WS-STANDING           PIC 9(5)V99.
           05  WS-DISCOUNT           PIC 9(6)V99.
           05  WS-NET                PIC 9(7)V99.
           05  WS-VAT                PIC 9(6)V99.
           05  WS-CURRENT            PIC 9(7)V99.
           05  WS-INTEREST           PIC 9(5)V99.
           05  WS-BALANCE            PIC S9(7)V99.
           05  WS-CARRY              PIC S9(7)V99.
           05  WS-DUE                PIC 9(7)V99.
           05  WS-NAME               PIC X(24).
           05  WS-NAME-OUT           PIC X(24).
           05  WS-REASON             PIC X(20).
           05  WS-DATE-DMY           PIC 9(8).
       01  WS-TOTALS.
           05  WS-BILLED             PIC 9(3)    VALUE 0.
           05  WS-REJECTED           PIC 9(3)    VALUE 0.
           05  WS-CREDITS            PIC 9(3)    VALUE 0.
           05  WS-TOT-UNITS          PIC 9(11)   VALUE 0.
           05  WS-TOT-CURRENT        PIC 9(11)V99 VALUE 0.
           05  WS-TOT-DUE            PIC 9(11)V99 VALUE 0.
           05  WS-TOT-NET            PIC S9(11)V99 VALUE 0.
           05  WS-AVERAGE            PIC 9(9)V99 VALUE 0.
       01  L-HEAD.
           05  FILLER                PIC X(15) VALUE "STATEMENTS FOR ".
           05  LH-REGION             PIC X(20).
           05  FILLER                PIC X(7)  VALUE " DATED ".
           05  LH-DATE               PIC 99/99/9999.
       01  L-ACCT.
           05  FILLER                PIC X(8)  VALUE "ACCOUNT ".
           05  LA-MASK               PIC X(4)  VALUE "****".
           05  LA-TAIL               PIC X(4).
           05  FILLER                PIC X(2)  VALUE SPACES.
           05  LA-NAME               PIC X(24).
           05  FILLER                PIC X(8)  VALUE " TARIFF ".
           05  LA-TARIFF             PIC X.
       01  L-READ.
           05  FILLER                PIC X(9)  VALUE "READINGS ".
           05  LR-PREV               PIC ZZZZZ9.
           05  FILLER                PIC X(4)  VALUE " TO ".
           05  LR-CURR               PIC ZZZZZ9.
           05  FILLER                PIC X(8)  VALUE "  USAGE ".
           05  LR-UNITS              PIC Z,ZZZ,ZZ9.
           05  FILLER                PIC X(6)  VALUE " OVER ".
           05  LR-DAYS               PIC ZZ9.
           05  FILLER                PIC X(5)  VALUE " DAYS".
       01  L-BANDS.
           05  FILLER                PIC X(6)  VALUE "BANDS ".
           05  LB-1                  PIC ZZ,ZZ9.9.
           05  FILLER                PIC X     VALUE SPACE.
           05  LB-2                  PIC ZZ,ZZ9.9.
           05  FILLER                PIC X     VALUE SPACE.
           05  LB-3                  PIC Z,ZZZ,ZZ9.9.
       01  L-CHARGE.
           05  FILLER                PIC X(13) VALUE "USAGE CHARGE ".
           05  LC-USAGE              PIC $$,$$$,$$9.99.
           05  FILLER                PIC X(10) VALUE "  STANDING".
           05  LC-STANDING           PIC $$$,$$9.99.
       01  L-DISC.
           05  FILLER                PIC X(9)  VALUE "DISCOUNT ".
           05  LD-DISCOUNT           PIC ZZ,ZZ9.99 BLANK WHEN ZERO.
           05  FILLER                PIC X(5)  VALUE "  VAT".
           05  LD-VAT                PIC ZZZ,ZZ9.99.
           05  FILLER                PIC X(9)  VALUE "  CURRENT".
           05  LD-CURRENT            PIC $$$,$$9.99.
       01  L-ARR.
           05  FILLER                PIC X(8)  VALUE "ARREARS ".
           05  LX-ARREARS            PIC ++,+++,++9.99.
           05  FILLER                PIC X(10) VALUE "  INTEREST".
           05  LX-INTEREST           PIC ZZ,ZZ9.99 BLANK WHEN ZERO.
           05  FILLER                PIC X(6)  VALUE "  PAID".
           05  LX-PAID               PIC ZZ,ZZ9.99.
       01  L-BAL.
           05  FILLER                PIC X(8)  VALUE "BALANCE ".
           05  LL-BALANCE            PIC Z,ZZZ,ZZ9.99CR.
           05  FILLER                PIC X(12) VALUE "  AMOUNT DUE".
           05  LL-DUE                PIC ***,**9.99.
       01  L-CARRY.
           05  FILLER                PIC X(11) VALUE "CREDIT C/F ".
           05  LY-CARRY              PIC $$$,$$9.99-.
       01  L-REJECT.
           05  FILLER                PIC X(7)  VALUE "REJECT ".
           05  LJ-ACCT               PIC X(8).
           05  FILLER                PIC X     VALUE SPACE.
           05  LJ-REASON             PIC X(20).
       01  L-LEDGER.
           05  FILLER                PIC X(24)
                                     VALUE "PAYMENTS AND ADJUSTMENTS".
       01  L-POST.
           05  LP-KIND               PIC X(3).
           05  FILLER                PIC X     VALUE SPACE.
           05  LP-ACCT               PIC X(8).
           05  FILLER                PIC X     VALUE SPACE.
           05  LP-AMT                PIC ----,--9.99.
           05  FILLER                PIC X(7)  VALUE " WHOLE ".
           05  LP-WHOLE              PIC -----9.
           05  FILLER                PIC X(5)  VALUE " BAL ".
           05  LP-BAL                PIC Z,ZZZ,ZZ9.99CR.
           05  FILLER                PIC X     VALUE SPACE.
           05  LP-MEMO               PIC X(30).
       01  L-SPLIT.
           05  FILLER                PIC X(16) VALUE "    FEE SPLIT 3X".
           05  LS-PART               PIC ---,--9.99.
           05  FILLER                PIC X(11) VALUE " REMAINDER ".
           05  LS-REM                PIC -9.99.
       01  L-PAYREJ.
           05  FILLER                PIC X(5)  VALUE "LINE ".
           05  LQ-LINE               PIC ZZ9.
           05  FILLER                PIC X(10) VALUE " REJECTED ".
           05  LQ-REASON             PIC X(20).
       01  L-PAYTOT.
           05  FILLER                PIC X(8)  VALUE "POSTED  ".
           05  LV-APPLIED            PIC ZZ9.
           05  FILLER                PIC X(11) VALUE "  REJECTED ".
           05  LV-REJECTED           PIC ZZ9.
           05  FILLER                PIC X(8)  VALUE "  PAID  ".
           05  LV-PAID               PIC $$,$$$,$$9.99-.
           05  FILLER                PIC X(8)  VALUE "  OTHER ".
           05  LV-OTHER              PIC $$,$$$,$$9.99-.
       01  L-TOT1.
           05  FILLER                PIC X(16) VALUE "ACCOUNTS BILLED ".
           05  LT-BILLED             PIC ZZ9.
           05  FILLER                PIC X(11) VALUE "  REJECTED ".
           05  LT-REJECTED           PIC ZZ9.
           05  FILLER                PIC X(10) VALUE "  CREDITS ".
           05  LT-CREDITS            PIC ZZ9.
       01  L-TOT2.
           05  FILLER                PIC X(12) VALUE "TOTAL UNITS ".
           05  LT-UNITS              PIC ZZZ,ZZZ,ZZ9.
           05  FILLER                PIC X(16) VALUE "  TOTAL CURRENT ".
           05  LT-CURRENT            PIC $$$,$$$,$$9.99.
       01  L-TOT3.
           05  FILLER                PIC X(10) VALUE "TOTAL DUE ".
           05  LT-DUE                PIC $$$,$$$,$$9.99.
           05  FILLER                PIC X(15) VALUE "  AVERAGE BILL ".
           05  LT-AVERAGE            PIC $$,$$$,$$9.99.
       01  L-TOT4.
           05  FILLER                PIC X(13) VALUE "NET POSITION ".
           05  LT-NET                PIC ---,---,--9.99.
       PROCEDURE DIVISION.
       MAIN-LINE.
           OPEN INPUT CUST-IN
                OUTPUT STMT-OUT
           PERFORM READ-IN
           IF NOT END-OF-INPUT AND IS-HEADER
               PERFORM WRITE-HEADER
               PERFORM READ-IN
           END-IF
           PERFORM UNTIL END-OF-INPUT
               IF IS-CUSTOMER
                   PERFORM ONE-ACCOUNT
               END-IF
               PERFORM READ-IN
           END-PERFORM
           PERFORM WRITE-TOTALS
           PERFORM POST-PAYMENTS
           CLOSE CUST-IN STMT-OUT
           STOP RUN.

       READ-IN.
           READ CUST-IN INTO CUST-REC
               AT END SET END-OF-INPUT TO TRUE
           END-READ.

       WRITE-HEADER.
           MOVE HDR-REGION TO LH-REGION
           MOVE STMT-DATE(7:2) TO WS-DATE-DMY(1:2)
           MOVE STMT-DATE(5:2) TO WS-DATE-DMY(3:2)
           MOVE STMT-DATE(1:4) TO WS-DATE-DMY(5:4)
           MOVE WS-DATE-DMY TO LH-DATE
           WRITE OUT-REC FROM L-HEAD
           MOVE SPACES TO OUT-REC
           WRITE OUT-REC.

       ONE-ACCOUNT.
           MOVE SPACES TO WS-REASON
           SET TX TO 1
           SEARCH TARIFF-ROW
               AT END MOVE "UNKNOWN TARIFF" TO WS-REASON
               WHEN TR-CODE(TX) = TARIFF
                   CONTINUE
           END-SEARCH
           EVALUATE TRUE
               WHEN WS-REASON NOT = SPACES
                   CONTINUE
               WHEN BILL-DAYS = 0
                   MOVE "NO BILLING DAYS" TO WS-REASON
               WHEN BILL-DAYS > 120
                   MOVE "PERIOD TOO LONG" TO WS-REASON
           END-EVALUATE
           IF WS-REASON NOT = SPACES
               ADD 1 TO WS-REJECTED
               MOVE ACCT-NO TO LJ-ACCT
               MOVE WS-REASON TO LJ-REASON
               WRITE OUT-REC FROM L-REJECT
               MOVE SPACES TO OUT-REC
               WRITE OUT-REC
           ELSE
               PERFORM CALC-BILL
               PERFORM PRINT-BILL
           END-IF.

       CALC-BILL.
           IF CURR-READ >= PREV-READ
               SUBTRACT PREV-READ FROM CURR-READ GIVING WS-UNITS
           ELSE
               COMPUTE WS-UNITS = CURR-READ + 1000000 - PREV-READ
           END-IF
           MULTIPLY TR-LIMIT1(TX) BY BILL-DAYS GIVING WS-TEMP
           DIVIDE WS-TEMP BY 30 GIVING WS-LIM1 ROUNDED
           MULTIPLY TR-LIMIT2(TX) BY BILL-DAYS GIVING WS-TEMP
           DIVIDE WS-TEMP BY 30 GIVING WS-LIM2 ROUNDED
           MOVE 0 TO WS-B1 WS-B2 WS-B3
           IF WS-UNITS > WS-LIM1
               MOVE WS-LIM1 TO WS-B1
               IF WS-UNITS > WS-LIM2
                   SUBTRACT WS-LIM1 FROM WS-LIM2 GIVING WS-B2
                   SUBTRACT WS-LIM2 FROM WS-UNITS GIVING WS-B3
               ELSE
                   SUBTRACT WS-LIM1 FROM WS-UNITS GIVING WS-B2
               END-IF
           ELSE
               MOVE WS-UNITS TO WS-B1
           END-IF
           MULTIPLY WS-B1 BY TR-RATE1(TX) GIVING WS-C1 ROUNDED
           MULTIPLY WS-B2 BY TR-RATE2(TX) GIVING WS-C2 ROUNDED
           MULTIPLY WS-B3 BY TR-RATE3(TX) GIVING WS-C3 ROUNDED
           ADD WS-C1 WS-C2 WS-C3 GIVING WS-USAGE
           MULTIPLY BILL-DAYS BY TR-STANDING(TX)
               GIVING WS-STANDING ROUNDED
           MOVE 0 TO WS-DISCOUNT
           IF TARIFF-RELIEF
               MULTIPLY WS-USAGE BY 0.15 GIVING WS-DISCOUNT
               SUBTRACT WS-DISCOUNT FROM WS-USAGE
           END-IF
           ADD WS-USAGE WS-STANDING GIVING WS-NET
           MULTIPLY WS-NET BY 0.05 GIVING WS-VAT ROUNDED
           ADD WS-NET WS-VAT GIVING WS-CURRENT
           MOVE 0 TO WS-INTEREST
           IF ARREARS > 0
               MULTIPLY ARREARS BY 0.015 GIVING WS-INTEREST ROUNDED
           END-IF
           COMPUTE WS-BALANCE = WS-CURRENT + ARREARS + WS-INTEREST
                              - PAID
           MOVE 0 TO WS-DUE WS-CARRY
           IF WS-BALANCE > 0
               MOVE WS-BALANCE TO WS-DUE
           END-IF
           IF WS-BALANCE < 0
               MULTIPLY WS-BALANCE BY 0.975 GIVING WS-CARRY ROUNDED
               ADD 1 TO WS-CREDITS
           END-IF
           ADD 1 TO WS-BILLED
           ADD 1 TO AT-COUNT
           MOVE ACCT-NO TO AT-ACCT(AT-COUNT)
           MOVE WS-BALANCE TO AT-BAL(AT-COUNT)
           ADD WS-UNITS TO WS-TOT-UNITS
           ADD WS-CURRENT TO WS-TOT-CURRENT
           ADD WS-DUE TO WS-TOT-DUE
           ADD WS-BALANCE TO WS-TOT-NET.

       PRINT-BILL.
           MOVE CUST-NAME TO WS-NAME
           INSPECT WS-NAME CONVERTING "abcdefghijklmnopqrstuvwxyz"
                                   TO "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
           MOVE SPACES TO WS-NAME-OUT
           STRING WS-NAME DELIMITED BY "  " INTO WS-NAME-OUT
           IF WS-NAME-OUT = SPACES
               MOVE "(NO NAME ON FILE)" TO WS-NAME-OUT
           END-IF
           MOVE ACCT-NO(5:4) TO LA-TAIL
           MOVE WS-NAME-OUT TO LA-NAME
           MOVE TARIFF TO LA-TARIFF
           WRITE OUT-REC FROM L-ACCT
           MOVE PREV-READ TO LR-PREV
           MOVE CURR-READ TO LR-CURR
           MOVE WS-UNITS TO LR-UNITS
           MOVE BILL-DAYS TO LR-DAYS
           WRITE OUT-REC FROM L-READ
           MOVE WS-B1 TO LB-1
           MOVE WS-B2 TO LB-2
           MOVE WS-B3 TO LB-3
           WRITE OUT-REC FROM L-BANDS
           MOVE WS-USAGE TO LC-USAGE
           MOVE WS-STANDING TO LC-STANDING
           WRITE OUT-REC FROM L-CHARGE
           MOVE WS-DISCOUNT TO LD-DISCOUNT
           MOVE WS-VAT TO LD-VAT
           MOVE WS-CURRENT TO LD-CURRENT
           WRITE OUT-REC FROM L-DISC
           MOVE ARREARS TO LX-ARREARS
           MOVE WS-INTEREST TO LX-INTEREST
           MOVE PAID TO LX-PAID
           WRITE OUT-REC FROM L-ARR
           MOVE WS-BALANCE TO LL-BALANCE
           MOVE WS-DUE TO LL-DUE
           WRITE OUT-REC FROM L-BAL
           IF WS-BALANCE < 0
               MOVE WS-CARRY TO LY-CARRY
               WRITE OUT-REC FROM L-CARRY
           END-IF
           MOVE SPACES TO OUT-REC
           WRITE OUT-REC.

       WRITE-TOTALS.
           MOVE WS-BILLED TO LT-BILLED
           MOVE WS-REJECTED TO LT-REJECTED
           MOVE WS-CREDITS TO LT-CREDITS
           WRITE OUT-REC FROM L-TOT1
           MOVE WS-TOT-UNITS TO LT-UNITS
           MOVE WS-TOT-CURRENT TO LT-CURRENT
           WRITE OUT-REC FROM L-TOT2
           IF WS-BILLED > 0
               DIVIDE WS-TOT-CURRENT BY WS-BILLED
                   GIVING WS-AVERAGE ROUNDED
           END-IF
           MOVE WS-TOT-DUE TO LT-DUE
           MOVE WS-AVERAGE TO LT-AVERAGE
           WRITE OUT-REC FROM L-TOT3
           MOVE WS-TOT-NET TO LT-NET
           WRITE OUT-REC FROM L-TOT4.

       POST-PAYMENTS.
           MOVE SPACES TO OUT-REC
           WRITE OUT-REC
           WRITE OUT-REC FROM L-LEDGER
           OPEN INPUT PAY-IN
           PERFORM READ-PAY
           PERFORM UNTIL END-OF-PAY
               ADD 1 TO WS-LINE-NO
               PERFORM ONE-PAYMENT
               PERFORM READ-PAY
           END-PERFORM
           CLOSE PAY-IN
           MOVE WS-APPLIED TO LV-APPLIED
           MOVE WS-PAY-REJECTED TO LV-REJECTED
           MOVE WS-TOT-PAID TO LV-PAID
           MOVE WS-TOT-OTHER TO LV-OTHER
           WRITE OUT-REC FROM L-PAYTOT.

       READ-PAY.
           READ PAY-IN INTO PAY-LINE
               AT END SET END-OF-PAY TO TRUE
           END-READ.

       ONE-PAYMENT.
           MOVE 0 TO PL-FIELDS PL-ACCT-LEN
           UNSTRING PAY-LINE DELIMITED BY ";"
               INTO PL-ACCT COUNT IN PL-ACCT-LEN
                    PL-KIND
                    PL-AMT-TXT
                    PL-MEMO
               TALLYING IN PL-FIELDS
           END-UNSTRING
           MOVE SPACES TO WS-REASON
           EVALUATE TRUE
               WHEN PL-FIELDS < 3
                   MOVE "TOO FEW FIELDS" TO WS-REASON
               WHEN PL-ACCT-LEN NOT = 8
                   MOVE "BAD ACCOUNT" TO WS-REASON
               WHEN FUNCTION TEST-NUMVAL(PL-AMT-TXT) NOT = 0
                   MOVE "BAD AMOUNT" TO WS-REASON
               WHEN NOT (KIND-PAY OR KIND-ADJ OR KIND-FEE OR KIND-REF)
                   MOVE "BAD KIND" TO WS-REASON
           END-EVALUATE
           IF WS-REASON = SPACES
               SET AX TO 1
               SEARCH AT-ENTRY
                   AT END MOVE "NO SUCH ACCOUNT" TO WS-REASON
                   WHEN AT-ACCT(AX) = PL-ACCT
                       CONTINUE
               END-SEARCH
           END-IF
           IF WS-REASON NOT = SPACES
               ADD 1 TO WS-PAY-REJECTED
               MOVE WS-LINE-NO TO LQ-LINE
               MOVE WS-REASON TO LQ-REASON
               WRITE OUT-REC FROM L-PAYREJ
           ELSE
               PERFORM APPLY-PAYMENT
           END-IF.

       APPLY-PAYMENT.
           EVALUATE TRUE
               WHEN KIND-PAY
                   COMPUTE WS-AMT ROUNDED MODE NEAREST-EVEN
                       = FUNCTION NUMVAL(PL-AMT-TXT)
                   SUBTRACT WS-AMT FROM AT-BAL(AX)
                   ADD WS-AMT TO WS-TOT-PAID
               WHEN KIND-ADJ
                   COMPUTE WS-AMT ROUNDED
                       = FUNCTION NUMVAL(PL-AMT-TXT)
                   ADD WS-AMT TO AT-BAL(AX)
                   ADD WS-AMT TO WS-TOT-OTHER
               WHEN KIND-FEE
                   COMPUTE WS-AMT = FUNCTION NUMVAL(PL-AMT-TXT)
                   ADD WS-AMT TO AT-BAL(AX)
                   ADD WS-AMT TO WS-TOT-OTHER
                   DIVIDE WS-AMT BY 3 GIVING WS-PART
                       REMAINDER WS-REM
               WHEN KIND-REF
                   COMPUTE WS-AMT ROUNDED MODE TOWARD-LESSER
                       = FUNCTION NUMVAL(PL-AMT-TXT)
                   ADD WS-AMT TO AT-BAL(AX)
                   ADD WS-AMT TO WS-TOT-OTHER
           END-EVALUATE
           COMPUTE WS-WHOLE = FUNCTION INTEGER(WS-AMT)
           INSPECT PL-MEMO CONVERTING "0123456789" TO "XXXXXXXXXX"
               AFTER INITIAL "#"
           ADD 1 TO WS-APPLIED
           MOVE PL-KIND TO LP-KIND
           MOVE PL-ACCT TO LP-ACCT
           MOVE WS-AMT TO LP-AMT
           MOVE WS-WHOLE TO LP-WHOLE
           MOVE AT-BAL(AX) TO LP-BAL
           MOVE PL-MEMO TO LP-MEMO
           WRITE OUT-REC FROM L-POST
           IF KIND-FEE
               MOVE WS-PART TO LS-PART
               MOVE WS-REM TO LS-REM
               WRITE OUT-REC FROM L-SPLIT
           END-IF.
