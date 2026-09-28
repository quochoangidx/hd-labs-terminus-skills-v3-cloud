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
  spaces (an empty line as 80 spaces), but a `C` record always runs at least
  through `PAID` (64 bytes) and an `H` record through `STMT-DATE`. Numeric
  fields always hold digits, with a `+` or `-` in front where the layout has a
  separate sign. A district's current charges stay below 1,000,000.00 per
  account and below 100,000,000.00 in total.
- `PAYIN` is a line sequential file of lines up to 80 bytes, one posting per
  line, with fields separated by `;` as the program's `UNSTRING` expects. It
  is keyed by hand at the counters and by the bank feed, so any printable
  ASCII can turn up in it. A line shorter than 80 bytes is read as if padded
  on the right with spaces (an empty line as 80 spaces). An empty file means
  nothing to post. Every posting, once rounded to cents, is at most 99,999.99
  either way, and a run's postings total less than 10,000,000.00 either way.
- An amount passes the program's `TEST-NUMVAL` check when it is spaces, an
  optional `+` or `-` and more spaces, then digits with at most one decimal
  point (`.5` and `5.` included), then spaces; or spaces, digits with at most
  one decimal point, spaces, and an optional trailing `+`, `-`, `CR` or `DB` in
  capitals, then spaces. Anything else, a blank amount included, is refused.
- Both inputs are printable ASCII with line-feed line ends.
- `STMTOUT` is a line sequential file: every record the program writes goes
  out with its trailing spaces removed and a single line feed after it.

## Samples

`samples/2025q1-north.dat` is the Q1 2025 reading extract for the north
district, `samples/2025q1-north.pay` its payments export, and
`samples/2025q1-north.stmt` the statement file this step produced from them.
Printing and posting take `STMTOUT` as it stands, so its exact bytes matter.
