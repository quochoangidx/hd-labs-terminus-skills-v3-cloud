# coopsum

Monthly climatological summaries for the stations of a cooperative climate-observer network.

- `src/coopsum/`: the package; `summarize(form)` returns the month's summary
- `tools/coopsum_run.py`: the driver the network office runs, `python3 tools/coopsum_run.py FORM.json`
- `docs/observer-handbook.md`: network handbook CN-7 part 3, which the summary follows
- `examples/two-stations.json`: a small form in the input format

## Form file

A form is one JSON object for one month of the network:

- `network`: the network's name, a string
- `month`: the month, `YYYY-MM`
- `stations`: a list of objects, each with
  - `id`: the station's id, a string
  - `hour`: the station's observation hour, a whole number of local standard time
  - `days`: a list with one entry per day of the month, the first day first
  - `next`: the station's first observation of the following month, an entry like those of `days`

Each entry is an object with `max`, `min` and `precip`, the three strings the observer wrote on the
form for that observation: `max` and `min` a temperature in degrees Fahrenheit with one decimal place
(`"71.3"`, `"-4.0"`) or `"M"`; `precip` an amount in inches with two decimal places (`"0.37"`,
`"0.00"`), `"T"`, `"M"` or `"A"`.

The summary layout is given in section 6 of the handbook.
