C=======================================================================
C     SNOWPK -- ONE DAY OF SNOWPACK ACCOUNTING FOR ONE ELEVATION BAND
C
C     CALLED ONCE PER DAY, IN DATE ORDER, FROM THE BAND DRIVER.  THE
C     PACK STATE LIVES IN COMMON /PACK/ AND SURVIVES BETWEEN CALLS.
C
C     PX(NHR)  HOURLY PRECIPITATION, MM
C     TA(NHR)  HOURLY AIR TEMPERATURE, DEG C
C     NHR      HOURS SUPPLIED FOR THE DAY (1 TO 24).  RESET TO THE
C              NUMBER OF HOURS ACTUALLY USED ON RETURN.
C     OUTFLW   WATER RELEASED FROM THE PACK THIS DAY, MM
C     IWE      PACK WATER EQUIVALENT IN HUNDREDTHS OF A MM
C     ITAVG    DAILY MEAN TEMPERATURE IN TENTHS OF A DEGREE
C     DMTOT    MELT PRODUCED THIS DAY, MM
C     FRTOT    MELTWATER REFROZEN THIS DAY, MM
C=======================================================================
      SUBROUTINE SNOWPK(PX, TA, NHR, OUTFLW, IWE, ITAVG, DMTOT, FRTOT)
      DIMENSION PX(24), TA(24)
      DOUBLE PRECISION BAL
      COMMON /PACK/ WE, LIQW, HEAT, KDAYS, BAL
      SAVE TOTOUT, NWARM
      DATA TOTOUT /0.0/, NWARM /0/
C
C     BAND CONSTANTS
      PXTEMP = 1.0
      TBASE  = 0.0
      CMELT  = 0.15
      REFRZ  = 0.0025
      HOLD   = 0.04
      TIPM   = 0.2
C
C     DAILY MEAN TEMPERATURE IN TENTHS OF A DEGREE, FROM THE ROUNDED
C     HOURLY VALUES, AND THE HOUR OF THE DAY'S MIDPOINT.
      ITSUM = 0
      DO 10 K = 1, NHR
         ITSUM = ITSUM + NINT(TA(K) * 10.)
   10 CONTINUE
      ITAVG = ITSUM / NHR
      MID = (NHR + 1) / 2
C
C     SEASONAL MELT FACTOR RISES WITH THE COUNT OF WARM DAYS
      IF (ITAVG .GT. 0) NWARM = NWARM + 1
      FMELT = CMELT * (1.0 + NWARM / 10 * 0.25)
C
      OUT = 0.0
      DMTOT = 0.0
      FRTOT = 0.0
      DO 50 K = 1, NHR
C        STOP EARLY ON A MISSING HOUR (FLAGGED BELOW -90)
         IF (TA(K) .LT. -90.0) GO TO 60
C        PARTITION PRECIPITATION: SNOW AT OR BELOW PXTEMP
         IF (TA(K) - PXTEMP) 20, 20, 30
   20    WE = WE + PX(K)
         GO TO 40
   30    LIQW = LIQW + PX(K)
C        ANTECEDENT TEMPERATURE INDEX, WEIGHTED TOWARD THE MIDPOINT
   40    W = TIPM
         IF (K .EQ. MID) W = TIPM * 2.
         HEAT = HEAT + W * (TA(K) - HEAT)
C        MELT OR REFREEZE
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
C        LIQUID BEYOND WHAT THE PACK CAN HOLD DRAINS
         CAP = HOLD * WE
         IF (LIQW .GT. CAP) THEN
            OUT = OUT + (LIQW - CAP)
            LIQW = CAP
         END IF
         BAL = BAL + PX(K) - OUT
   50 CONTINUE
C     HOURS ACTUALLY USED
   60 NHR = K - 1
C
      OUTFLW = OUT
      TOTOUT = TOTOUT + OUT
      KDAYS = KDAYS + 1
      IWE = NINT(WE * 100.)
      RETURN
      END
C=======================================================================
C     SNOWIN -- START A BAND'S PACK
C=======================================================================
      SUBROUTINE SNOWIN(WE0)
      DOUBLE PRECISION BAL
      COMMON /PACK/ WE, LIQW, HEAT, KDAYS, BAL
      WE = WE0
      LIQW = 0
      HEAT = 0.0
      KDAYS = 0
      BAL = 0.0D0
      RETURN
      END
