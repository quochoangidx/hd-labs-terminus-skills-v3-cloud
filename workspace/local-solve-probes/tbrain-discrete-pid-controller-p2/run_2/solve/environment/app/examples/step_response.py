"""Print a short closed-loop step response against a first-order plant."""

from looptune import Controller, Tuning


def main():
    tuning = Tuning(gain=1.8, integral_time=4.0, derivative_time=0.6,
                    filter_divisor=8.0, tracking_time=2.0, setpoint_weight=0.7,
                    period=0.1, low=-1.0, high=1.0, slew=2.0)
    loop = Controller(tuning)
    y = 0.0
    for k in range(40):
        u = loop.step(0.5, y)
        y += 0.1 * (u - y)
        if k % 5 == 0:
            parts = ", ".join(f"{key}={value:+.4f}" for key, value in loop.terms().items())
            print(f"{k:3d}  y={y:+.4f}  {parts}")


if __name__ == "__main__":
    main()
