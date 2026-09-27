      *----------------------------------------------------------------
      * CUSTREC  -  METER-READING INPUT RECORD (80 BYTES)
      *----------------------------------------------------------------
       01  CUST-REC.
           05  REC-TYPE              PIC X.
               88  IS-HEADER         VALUE "H".
               88  IS-CUSTOMER       VALUE "C".
           05  CUST-BODY.
               10  ACCT-NO           PIC X(8).
               10  CUST-NAME         PIC X(24).
               10  TARIFF            PIC X.
                   88  TARIFF-DOMESTIC    VALUE "D".
                   88  TARIFF-COMMERCIAL  VALUE "C".
                   88  TARIFF-RELIEF      VALUE "L".
               10  PREV-READ         PIC 9(6).
               10  CURR-READ         PIC 9(6).
               10  BILL-DAYS         PIC 9(3).
               10  ARREARS           PIC S9(5)V99
                                     SIGN LEADING SEPARATE.
               10  PAID              PIC 9(5)V99.
               10  FILLER            PIC X(16).
           05  HDR-BODY REDEFINES CUST-BODY.
               10  STMT-DATE         PIC 9(8).
               10  HDR-REGION        PIC X(20).
               10  FILLER            PIC X(51).
