"""Step the enclosure model through a schedule."""

from .model import Run

SUBSTEP = 1.0


def _rates(net, t1, t2, ambient, power, on):
    q = power if on else 0.0
    d1 = (net.g1 * (ambient - t1) + net.g12 * (t2 - t1) + q) / net.c1
    d2 = (net.g2 * (ambient - t2) + net.g12 * (t1 - t2)) / net.c2
    return d1, d2


def _check(thermostat, t1, on):
    if thermostat is None:
        return on
    if on and t1 >= thermostat.upper:
        return False
    if not on and t1 <= thermostat.lower:
        return True
    return on


def simulate(network, times, ambient, power, t1, t2, heater_on=True, thermostat=None):
    """Run the model over the sample times.

    ``times`` and ``ambient`` have one entry per sample; ``power`` has one entry per
    interval between samples.
    """
    if len(times) != len(ambient) or len(power) != len(times) - 1:
        raise ValueError("need one ambient per sample and one power per interval")
    run = Run()
    on = bool(heater_on)
    t1 = float(t1)
    t2 = float(t2)
    run.temperatures.append((t1, t2))
    run.heater.append(on)
    for k in range(len(times) - 1):
        start, end = float(times[k]), float(times[k + 1])
        now = start
        while now < end:
            dt = min(SUBSTEP, end - now)
            d1, d2 = _rates(network, t1, t2, float(ambient[k]), float(power[k]), on)
            t1 += d1 * dt
            t2 += d2 * dt
            now += dt
            state = _check(thermostat, t1, on)
            if state != on:
                on = state
                run.switches.append((now, on))
        run.temperatures.append((t1, t2))
        run.heater.append(on)
    return run
