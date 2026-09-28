      *----------------------------------------------------------------
      * TARIFFS  -  BAND LIMITS PER 30 DAYS, UNIT RATES, STANDING
      *             CHARGE PER DAY.  ONE ROW PER TARIFF LETTER.
      *----------------------------------------------------------------
       01  TARIFF-VALUES.
           05  FILLER  PIC X(29) VALUE "D0010003012050185752441003125".
           05  FILLER  PIC X(29) VALUE "C0050020011500140251655009860".
           05  FILLER  PIC X(29) VALUE "L0010003012050185752441003125".
       01  TARIFF-TABLE REDEFINES TARIFF-VALUES.
           05  TARIFF-ROW OCCURS 3 TIMES INDEXED BY TX.
               10  TR-CODE           PIC X.
               10  TR-LIMIT1         PIC 9(4).
               10  TR-LIMIT2         PIC 9(4).
               10  TR-RATE1          PIC 9V9999.
               10  TR-RATE2          PIC 9V9999.
               10  TR-RATE3          PIC 9V9999.
               10  TR-STANDING       PIC 9V9999.
