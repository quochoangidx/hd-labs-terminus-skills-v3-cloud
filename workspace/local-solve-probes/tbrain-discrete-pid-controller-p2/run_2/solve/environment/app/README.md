# looptune

The PID controller behind the kiln-line temperature loops and the two dosing
flow loops. A loop builds one `Controller` from a `Tuning` and calls `step`
once per sample period; the plant historian logs `terms()` after every step.

    PYTHONPATH=src python3 examples/step_response.py

How a step is computed is fixed by `docs/control-note.md` (LT-7).
