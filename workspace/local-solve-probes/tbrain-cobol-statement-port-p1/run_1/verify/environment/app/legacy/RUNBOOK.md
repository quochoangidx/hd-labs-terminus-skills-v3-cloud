# WBILL job step - run notes

WBILL prints the quarterly water statements for one district. It is the
second step of the quarterly run, after the meter-reading extract.

## Build

    cobc -x WBILL.cbl

GnuCOBOL 3.1.2, default dialect and options. The copybooks `CUSTREC.cpy` and
`TARIFFS.cpy` sit next to the program.

## Run

    CUSTIN=<reading extract> STMTOUT=<statement file> ./WBILL

- `CUSTIN` is a line sequential file of 80-byte records laid out as in
  `CUSTREC.cpy`: normally one `H` header record, then one `C` record per
  account. A line shorter than 80 bytes is read as if padded on the right with
  spaces. Numeric fields always hold digits, with a `+` or `-` in front where
  the layout has a separate sign.
- `STMTOUT` is a line sequential file: every record the program writes goes
  out with its trailing spaces removed and a single line feed after it.

## Samples

`samples/2025q1-north.dat` is the Q1 2025 extract for the north district and
`samples/2025q1-north.stmt` is the statement file this step produced from it.
Printing and posting take `STMTOUT` as it stands, so its exact bytes matter.
