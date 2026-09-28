# Quarterly water statements

`legacy/` holds the COBOL job step that prints the statements (`WBILL.cbl`,
its copybooks and run notes) together with a sample extract and the statement
file it produced. `port/wbill.py` is its Python replacement:

    python3 port/wbill.py legacy/samples/2025q1-north.dat /tmp/north.stmt
