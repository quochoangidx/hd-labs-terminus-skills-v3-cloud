# thermostep

Steps the two-node enclosure model (chamber and wall) through a sampled
schedule of ambient temperature and heater power, with an optional on/off
thermostat on the chamber node. The oven and soak-chamber commissioning scripts
call `thermostep.simulate` and quote its temperatures and switch times.

    PYTHONPATH=src python3 examples/warmup.py

The model and what a run must report are fixed by `docs/stepping-note.md` (TS-4).
