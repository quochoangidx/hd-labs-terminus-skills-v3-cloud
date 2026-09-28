C=======================================================================
C     BANDMD -- DAILY STEP OF THE ELEVATION-BAND WATER MODEL
C
C     BANDIN  START A BAND (PACK, SOIL AND ROUTING STORES)
C     BANDDY  ONE DAY: SNOWPACK, SOIL MOISTURE, ROUTING, DAY REPORT
C
C     THE STATE LIVES IN COMMON /PACK/, /SOIL/ AND /ROUTE/ AND IN THE
C     SAVED LOCALS OF SNOWPK AND SOILMX.  ONE BAND IS RUN PER PROGRAM.
C=======================================================================
      SUBROUTINE BANDIN(WE0, SM10, SM20)
      DOUBLE PRECISION BAL
      COMMON /PACK/ WE, LIQW, HEAT, KDAYS, BAL
      COMMON /ROUTE/ QBUF(24), NPOS, QTOT
      WE = WE0
      LIQW = 0
      HEAT = 0.0
      KDAYS = 0
      BAL = 0.0D0
      DO 10 I = 1, 24
         QBUF(I) = 0.0
   10 CONTINUE
      NPOS = 1
      QTOT = 0.0
      CALL SOILIN(SM10, SM20)
      RETURN
      END
C=======================================================================
C     BANDDY -- ONE DAY FOR THE BAND
C
C     PX(NHR), TA(NHR)  HOURLY PRECIPITATION (MM) AND TEMPERATURE (C)
C     NHR     HOURS SUPPLIED; ON RETURN, HOURS USED BY THE SNOWPACK
C     RES(9)  OUTFLW, DMTOT, FRTOT, AET, PERC, QOUT, STORE1, STORE2,
C             RMAX
C     IRES(6) IWE, ITAVG, IPEAK, ISTAT, NSUM, JLAST
C     CODE    DAY CLASS, SIX CHARACTERS
C     *       TAKEN WHEN THE DAY CANNOT BE USED
C=======================================================================
      SUBROUTINE BANDDY(PX, TA, NHR, RES, IRES, CODE, *)
      DIMENSION PX(24), TA(24), RES(9), IRES(6)
      CHARACTER*6 CODE
      DOUBLE PRECISION BAL
      COMMON /PACK/ WE, LIQW, HEAT, KDAYS, BAL
      COMMON /ROUTE/ QQ(12, 2), MPOS, QSUM
      SAVE QPREV
      DATA QPREV /0.0/
C
      KDAYS = KDAYS + 1
      IF (NHR .LT. 1 .OR. NHR .GT. 24) RETURN 1
C
      CALL SNOWPK(PX, TA, NHR, OUTFLW, IWE, ITAVG, DMTOT, FRTOT)
      PET = PETHAM(FLOAT(ITAVG) / 10., KDAYS)
      CALL SOILMX(OUTFLW, PET, PERC, AET, ISTAT)
      CALL UHROUT(PERC, QOUT)
C
C     HALF-DAY STORES STILL IN THE ROUTING BUFFER
      STORE1 = 0.0
      STORE2 = 0.0
      DO 20 I = 1, 12
         STORE1 = STORE1 + QQ(I, 1)
         STORE2 = STORE2 + QQ(I, 2)
   20 CONTINUE
C
C     PEAK FLOW INDEX AND RUNNING MAXIMUM
      IPEAK = MAX1(QOUT * 10., QPREV * 10.)
      RMAX = AMAX0(IPEAK, MOD(ITAVG, 7))
      QPREV = QOUT
C
C     HOURS COUNTED BACK FROM THE END OF THE DAY IN STEPS OF FOUR
      NSUM = 0
      DO 30 J = NHR, 1, -4
         NSUM = NSUM + J
   30 CONTINUE
      JLAST = J
C
C     CLASSIFY THE DAY
      IF (IWE .GT. 0) THEN
         CODE = 'SNOW'
      ELSE
         CODE = 'BARE'
      END IF
      IF (OUTFLW .GT. 0.0) CODE(5:6) = 'RO'
      IF (CODE .EQ. 'SNOW' .AND. ITAVG .LT. 0) CODE(5:5) = 'C'
C
      RES(1) = OUTFLW
      RES(2) = DMTOT
      RES(3) = FRTOT
      RES(4) = AET
      RES(5) = PERC
      RES(6) = QOUT
      RES(7) = STORE1
      RES(8) = STORE2
      RES(9) = RMAX
      IRES(1) = IWE
      IRES(2) = ITAVG
      IRES(3) = IPEAK
      IRES(4) = ISTAT
      IRES(5) = NSUM
      IRES(6) = JLAST
      RETURN
      END
C=======================================================================
C     SNOWPK -- HOURLY SNOWPACK ACCOUNTING FOR ONE DAY
C=======================================================================
      SUBROUTINE SNOWPK(PX, TA, NHR, OUTFLW, IWE, ITAVG, DMTOT, FRTOT)
      DIMENSION PX(24), TA(24)
      DOUBLE PRECISION BAL
      COMMON /PACK/ WE, LIQW, HEAT, KDAYS, BAL
      SAVE NWARM
      DATA NWARM /0/
C
      PXTEMP = 1.0
      TBASE  = 0.0
      CMELT  = 0.15
      REFRZ  = 0.0025
      HOLD   = 0.04
      TIPM   = 0.2
C
      ITSUM = 0
      DO 10 K = 1, NHR
         ITSUM = ITSUM + NINT(TA(K) * 10.)
   10 CONTINUE
      ITAVG = ITSUM / NHR
      MID = (NHR + 1) / 2
      IF (ITAVG .GT. 0) NWARM = NWARM + 1
      FMELT = CMELT * (1.0 + NWARM / 10 * 0.25)
C
      OUT = 0.0
      DMTOT = 0.0
      FRTOT = 0.0
      DO 50 K = 1, NHR
         IF (TA(K) .LT. -90.0) GO TO 60
         IF (TA(K) - PXTEMP) 20, 20, 30
   20    WE = WE + PX(K)
         GO TO 40
   30    LIQW = LIQW + PX(K)
   40    W = TIPM
         IF (K .EQ. MID) W = TIPM * 2.
         HEAT = HEAT + W * (TA(K) - HEAT)
         IF (TA(K) .GT. TBASE) THEN
            DMELT = FMELT * (TA(K) - TBASE) / 24
            DMELT = AMIN1(DMELT, WE)
            WE = WE - DMELT
            LIQW = LIQW + DMELT
            DMTOT = DMTOT + DMELT
         ELSE
            FRZ = REFRZ * DIM(TBASE, HEAT) * SQRT(FLOAT(LIQW) + 1.0)
            FRZ = AMIN1(FRZ, FLOAT(LIQW))
            LIQW = LIQW - FRZ
            WE = WE + FRZ
            FRTOT = FRTOT + FRZ
         END IF
         CAP = HOLD * WE
         IF (LIQW .GT. CAP) THEN
            OUT = OUT + (LIQW - CAP)
            LIQW = CAP
         END IF
         BAL = BAL + PX(K) - OUT
   50 CONTINUE
   60 NHR = K - 1
      OUTFLW = OUT
      IWE = NINT(WE * 100.)
      RETURN
      END
C=======================================================================
C     SOILMX -- TWO-LAYER SOIL MOISTURE FOR ONE DAY
C     ENTRY SOILIN STARTS THE LAYERS
C=======================================================================
      SUBROUTINE SOILMX(WIN, PET, PERC, AET, ISTAT)
      COMMON /SOIL/ SM1, SM2, CAP1, CAP2
      SAVE NDRY, FRAC
      WET(S, C) = S / C
C
      IF (WIN - 0.5) 20, 30, 30
   20 NDRY = NDRY + 1
      GO TO 40
   30 NDRY = 0
   40 SM1 = SM1 + WIN
      IF (SM1 .GT. CAP1) THEN
         XS = SM1 - CAP1
         SM1 = CAP1
      ELSE
         XS = 0.0
      END IF
      PERC = XS * FRAC
      SM2 = SM2 + (XS - PERC)
      IF (SM2 .GT. CAP2) THEN
         PERC = PERC + (SM2 - CAP2)
         SM2 = CAP2
      END IF
      AET = PET * AMIN1(1.0, WET(SM1, CAP1) * 1.25)
      AET = AMIN1(AET, SM1)
      SM1 = SM1 - AET
      KDRY = NDRY / 3
      ISTAT = MIN0(KDRY, 9)
      RETURN
C
      ENTRY SOILIN(S1, S2)
      SM1 = S1
      SM2 = S2
      CAP1 = 25.0
      CAP2 = 120.0
      NDRY = 0
      FRAC = 0.35
      RETURN
      END
C=======================================================================
C     UHROUT -- ROUTE ONE DAY'S PERCOLATION THROUGH THE UNIT HYDROGRAPH
C=======================================================================
      SUBROUTINE UHROUT(QIN, QOUT)
      COMMON /ROUTE/ QBUF(24), NPOS, QTOT
      DIMENSION UH(6)
      DATA UH /0.1, 0.3, 0.25, 0.2, 0.1, 0.05/
C
      DO 10 L = 1, 6
         IDX = MOD(NPOS + L - 2, 24) + 1
         QBUF(IDX) = QBUF(IDX) + QIN * UH(L)
   10 CONTINUE
      QOUT = QBUF(NPOS)
      QBUF(NPOS) = 0.0
      QTOT = QTOT + QOUT
      NPOS = MOD(NPOS, 24) + 1
      RETURN
      END
C=======================================================================
C     PETHAM -- DAILY POTENTIAL EVAPOTRANSPIRATION, MM
C=======================================================================
      REAL FUNCTION PETHAM(TAVG, NDAY)
      DIMENSION C(4), D(2, 2)
      EQUIVALENCE (C(1), D(1, 1))
      ESAT(T) = 6.108 + T * (0.4436 + T * (0.01428 + T * 0.000265))
      DATA C /0.55, 0.021, 1.2, 0.4/
C
C     DAY LENGTH FACTOR FROM THE DAY NUMBER IN A 360-DAY YEAR
      NDY = MOD(NDAY - 1, 360)
      IPH = NDY / 30 - 6
      DL = D(1, 2) + D(2, 1) * FLOAT(ISIGN(IPH, 6 - NDY / 30) * IPH)
      IF (TAVG .LE. 0.0) THEN
         PETHAM = 0.0
      ELSE
         PETHAM = D(1, 1) * DL * ESAT(TAVG) * D(2, 2) / 5.
      END IF
      RETURN
      END
