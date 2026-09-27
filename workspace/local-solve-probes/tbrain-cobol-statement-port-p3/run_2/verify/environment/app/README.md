# Quarterly water statements

`legacy/` holds the COBOL job step that prints the statements and posts the
quarter's payments (`WBILL.cbl`, its copybooks and run notes) together with a
sample reading extract, payments export and the statement file it produced.
`port/wbill.py` is its Python replacement:

    python3 port/wbill.py legacy/samples/2025q1-north.dat legacy/samples/2025q1-north.pay /tmp/north.stmt
