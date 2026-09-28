# WBILL job step - run notes

WBILL prints the quarterly water statements for one district, then posts the
quarter's payments and adjustments against the new balances and prints the
ledger. It is the second step of the quarterly run, after the meter-reading
extract and the payments export.

## Build

    cobc -x WBILL.cbl

GnuCOBOL 3.1.2, default dialect and options. The copybooks `CUSTREC.cpy` and
`TARIFFS.cpy` sit next to the program.

## Run

    CUSTIN=<reading extract> PAYIN=<payments export> STMTOUT=<statement file> ./WBILL

- `CUSTIN` is a line sequential file of 80-byte records laid out as in
  `CUSTREC.cpy`: normally one `H` header record, then one `C` record per
  account. A line shorter than 80 bytes is read as if padded on the right with
  spaces. Numeric fields always hold digits, with a `+` or `-` in front where
  the layout has a separate sign.
- `PAYIN` is a line sequential file of lines up to 80 bytes, one posting per
  line, with fields separated by `;` as the program's `UNSTRING` expects. It
  is keyed by hand at the counters and by the bank feed, so anything
  printable can turn up in it. A line shorter than 80 bytes is read as if
  padded on the right with spaces. An empty file means nothing to post.
- `STMTOUT` is a line sequential file: every record the program writes goes
  out with its trailing spaces removed and a single line feed after it.

## Samples

`samples/2025q1-north.dat` is the Q1 2025 reading extract for the north
district, `samples/2025q1-north.pay` its payments export, and
`samples/2025q1-north.stmt` the statement file this step produced from them.
Printing and posting take `STMTOUT` as it stands, so its exact bytes matter.
