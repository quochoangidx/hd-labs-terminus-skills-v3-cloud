"""Warm the conditioning box from a cold start with the thermostat on."""

from thermostep import Network, Thermostat, simulate


def main():
    box = Network(c1=4.0e4, c2=2.5e5, g1=6.0, g2=9.0, g12=35.0)
    times = [0.0, 300.0, 600.0, 900.0, 1500.0, 2100.0, 3000.0]
    ambient = [18.0, 18.5, 19.0, 19.0, 21.0, 22.0, 20.0]
    power = [900.0] * 6
    run = simulate(box, times, ambient, power, t1=18.0, t2=18.0,
                   heater_on=True, thermostat=Thermostat(lower=27.0, upper=29.0))
    for t, (a, b), on in zip(times, run.temperatures, run.heater):
        print(f"{t:7.1f}  T1={a:8.4f}  T2={b:8.4f}  heater={'on' if on else 'off'}")
    for t, on in run.switches:
        print(f"switch at {t:.3f} s -> {'on' if on else 'off'}")


if __name__ == "__main__":
    main()
